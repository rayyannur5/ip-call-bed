import subprocess
import time
import paho.mqtt.client as mqtt
from threading import Event
import wifimangement_linux as wifi
import requests
import re
import vlc
from getmac import get_mac_address

# SERIAL NUMBER VERSION

calling = Event()
playing = Event()
after_calling = Event()
reregister = Event()
player = vlc.MediaPlayer()

list_nursestation = {
    '1': [
        "Net_4X8G7L2M9K5_1",
        "Net_4X8G7L2M9K5_2",
        "Net_4X8G7L2M9K5_3",
        "Net_4X8G7L2M9K5_4",
        "Net_4X8G7L2M9K5_5",
        "Net_4X8G7L2M9K5_6",
        "Net_4X8G7L2M9K5_7",
        "Net_4X8G7L2M9K5_8",
        "Net_4X8G7L2M9K5_9",
        "Net_4X8G7L2M9K5_10",
    ],
    '2': [
        "Net_4X8G7L2M9K5_11",
        "Net_4X8G7L2M9K5_12",
        "Net_4X8G7L2M9K5_13",
        "Net_4X8G7L2M9K5_14",
        "Net_4X8G7L2M9K5_15",
        "Net_4X8G7L2M9K5_16",
        "Net_4X8G7L2M9K5_17",
        "Net_4X8G7L2M9K5_18",
        "Net_4X8G7L2M9K5_19",
        "Net_4X8G7L2M9K5_20",
    ],
    '3': [
        "Net_4X8G7L2M9K5_21",
        "Net_4X8G7L2M9K5_22",
        "Net_4X8G7L2M9K5_23",
        "Net_4X8G7L2M9K5_24",
        "Net_4X8G7L2M9K5_25",
        "Net_4X8G7L2M9K5_26",
        "Net_4X8G7L2M9K5_27",
        "Net_4X8G7L2M9K5_28",
        "Net_4X8G7L2M9K5_29",
        "Net_4X8G7L2M9K5_30",
    ],
    '4': [
        "Net_4X8G7L2M9K5_21",
        "Net_4X8G7L2M9K5_22",
        "Net_4X8G7L2M9K5_23",
        "Net_4X8G7L2M9K5_24",
        "Net_4X8G7L2M9K5_25",
        "Net_4X8G7L2M9K5_26",
        "Net_4X8G7L2M9K5_27",
        "Net_4X8G7L2M9K5_28",
        "Net_4X8G7L2M9K5_29",
        "Net_4X8G7L2M9K5_30",
    ],
}

def on_media_finished(event):
    global playing
    playing.clear()
    print("lagu selesai")

event_manager = player.event_manager()
event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, on_media_finished)

def execute(command):
    return subprocess.run(command, capture_output=True, shell=True).stdout.decode()

def scan_wifi():
    try:
        # Jalankan perintah `nmcli dev wifi`
        execute("nmcli dev wifi rescan")
        time.sleep(3)
        execute("nmcli device disconnect wlan0")
        time.sleep(3)
        output = execute("nmcli -f SSID,BSSID,SIGNAL device wifi")

        # Parsing output
        wifi_list = []
        for line in output.split("\n")[1:]:  # Lewati header
            if line.strip():  # Abaikan baris kosong
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) >= 3:
                    wifi_list.append({
                        "SSID": parts[0].strip(),
                        "BSSID": parts[1].strip(),
                        "RSSI": parts[2].strip()
                    })
        return wifi_list

    except FileNotFoundError:
        print("Perintah nmcli tidak ditemukan. Pastikan NetworkManager terinstal.")
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")

ssid_r = open("/home/nursecall/ip-call-bed/config/ssid.txt", "r")
nursetation_r = open("/home/nursecall/ip-call-bed/config/nursestation.txt", "r")
pswd_r = open("/home/nursecall/ip-call-bed/config/pass.txt", "r")
id_r = open("/home/nursecall/ip-call-bed/config/id.txt", "r")

mac_address = get_mac_address('wlan0').replace(":", "")

# id 				= id_r.read()
id = "b" + mac_address
nursestation    = nursetation_r.read()
ssid            = ssid_r.read()
pswd            = pswd_r.read()

if id == "":
    exit()

id_r.close()
nursetation_r.close()
ssid_r.close()
pswd_r.close()

btn_call 		= 23
btn_cancel 		= 22
btn_emergency 	= 6
btn_infus 		= 2
led_cancel		= 20
led_emergency	= 3
led_infus		= 4
pin_relay		= 25
buzzer			= 3
host 			= "192.168.0.1"
port_sip 		= "5060"
username 		= id
password 		= id
nurse_sip		= "100"
state_led		= True
btn_session 	= None
oncall			= False
vol				= 100
mic				= 100
id_server		= ""

# mode autoconnect
if nursestation != "":
    wifi_networks = scan_wifi()
    
    max_signal = 0

    nursestation_wifi_list = list_nursestation[nursestation]

    if wifi_networks:
        for i, network in enumerate(wifi_networks, start=1):
            
            _ssid = network['SSID']
            _rssi = int(network['RSSI'])
            
            for item in nursestation_wifi_list:
                if _ssid == item:
                    print(f"{_ssid}\t{_rssi}")
                    if max_signal < _rssi:
                        ssid = _ssid
                        max_signal = _rssi 
        
        print(ssid)
        with open('/home/nursecall/ip-call-bed/config/ssid.txt', 'w') as file:
            file.write(ssid)


wifi.connect(ssid,pswd)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("LOG| Connected with result code "+str(rc))
    
    client.subscribe(f"stop/{id}")
    client.subscribe(f"infus/{id}")
    client.subscribe(f"bed/{id}")
    client.subscribe(f"assist/{id}")
    client.subscribe(f"serial/{id}")
    client.subscribe(id)
    client.subscribe("schedule")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Koneksi terputus secara tidak terduga! Mencoba menyambung ulang...")
        start_timer_mqtt_disconnect = millis()
        while True:
            try:
                if millis() - start_timer_mqtt_disconnect > 60000:
                    print('reboot')
                    execute('reboot')
                client.reconnect()  # Mencoba menyambung ulang
                print("Berhasil menyambung ulang ke broker MQTT!")
                break
            except Exception as e:
                print(f"Gagal menyambung ulang: {e}. Mencoba lagi dalam 5 detik...")
                time.sleep(5)
    else:
        print("Koneksi terputus dengan sengaja.")

def on_message(client, userdata, msg):
    global player, playing
    print(msg.topic+" "+str(msg.payload))
    
    if msg.topic == 'schedule':
        
        audio_url = msg.payload.decode("utf-8")
        player.set_media(vlc.Media(audio_url))
        playing.set()
        player.play()
        
    elif 's' in str(msg.payload):
        calling.clear()
        playing.clear()
    elif 'm' in str(msg.payload):
        after_calling.set()
        playing.clear()
    elif 'c' in str(msg.payload):
        after_calling.clear()
        playing.clear()
    elif 'x' in str(msg.payload):
        after_calling.clear()
        playing.clear()
    elif 'serial' in msg.topic and 'r' in str(msg.payload):
        print("reboot")
        execute("reboot")
    elif 'serial' in msg.topic and 'z' in str(msg.payload):
        print("buzzer")
        execute(f"gpio write {buzzer} 0")
        time.sleep(1)
        execute(f"gpio write {buzzer} 1")
    elif 'serial' in msg.topic and 'l' in str(msg.payload):
        print("lampp")
        execute(f"gpio write {led_cancel} 0")
        time.sleep(1)
        execute(f"gpio write {led_cancel} 1")
    elif 'r' in str(msg.payload):
        reregister.set()


client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

def millis():
    return round(time.time() * 1000)

def checkWifiConnection():
    res = execute("nmcli con show")
    while "wlan0" not in res:
        res = execute("nmcli con show")
    
    execute(f"gpio write {led_cancel} 0")
    time.sleep(1)
    execute(f"gpio write {led_cancel} 1")
    print("LOG| WIFI CONNECTED")

def checkServer():
    res = execute(f"ping -c 1 {host}")
    while "1 received" not in res:
        res = execute(f"ping -c 1 {host}")
        
    execute(f"gpio write {led_cancel} 0")
    time.sleep(0.5)
    execute(f"gpio write {led_cancel} 1")
    print("LOG| SERVER ONLINE")

def setupGPIO():
    # buzzer

    execute(f"gpio mode {btn_call} in")
    execute(f"gpio mode {btn_cancel} in")
    execute(f"gpio mode {btn_emergency} in")
    execute(f"gpio mode {btn_infus} in")
    execute(f"gpio mode {led_cancel} out")
    execute(f"gpio mode {led_infus} out")
    execute(f"gpio mode {led_emergency} out")

    execute(f"gpio mode {pin_relay} out")
    execute(f"gpio write {pin_relay} 1")

    execute(f"gpio mode {buzzer} out")
    execute(f"gpio write {buzzer} 1")

    execute(f"gpio write {led_cancel} 1")
    execute(f"gpio write {led_infus} 1")
    execute(f"gpio write {led_emergency} 1")

    execute(f"gpio mode 5 out")
    execute(f"gpio write 5 1")
    print("LOG| SETUP GPIO SUCCESSFULL")
    
def setupLinphone():
    if id_server == "":
        return
    execute("linphonecsh init")
    print("LOG| LINPHONE REGISTERING")
    execute(f"linphonecsh register --host {host} --username {id_server} --password {id_server}")
    res = execute("linphonecsh status register")
    before_linphone = millis()
    while "registered," not in res:
        execute(f"gpio write {led_cancel} 0")
        execute("linphonecsh init")
        execute(f"linphonecsh register --host {host} --username {id_server} --password {id_server}")
        res = execute("linphonecsh status register")
        time.sleep(0.1)
        execute(f"gpio write {led_cancel} 1")
        time.sleep(0.1)
        if millis() - before_linphone > 60000:
            execute("reboot")
    print("LOG| LINPHONE REGISTERED")
    
    res = execute("linphonecsh generic 'soundcard list'")
    before_linphone = millis()
    while "echo" not in res:
        if millis() - before_linphone > 60000:
            execute("reboot")
        res = execute("linphonecsh generic 'soundcard list'")
        
    res = res.split("\n")
    for i in res:
        if "echo" in i:
            index_soundcard = i[0]
            res = execute(f"linphonecsh generic 'soundcard use {index_soundcard}'")
            print(f"LOG| {res}")
            break
    
    reregister.clear()

def call(sip):
    res = execute(f"linphonecsh dial {sip}")
    print(f"LOG| {res}")

def checkTwoWay():
    global id_server
    try:
        requests.get(f"http://{host}/ip-call/server/bed/set_ip.php?id={id}&ip={wifi.ip()}")
        x = requests.get(f"http://{host}/ip-call/server/bed/get_one.php?id={id}").json()
        print(x)
        if len(x['data']) > 0:
            id_server = x['data'][0]['id']
            print(id_server)
            execute(f"amixer set Master {x['data'][0]['vol']}%")
            return x['data'][0]['mode'], int(x['data'][0]['vol']), int(x['data'][0]['mic'])
        else:
            return 0, 100, 100
    except:
        return 0, 100, 100

setupGPIO()
execute(f"gpio write {led_cancel} 0")
time.sleep(0.5)
execute(f"gpio write {led_cancel} 1")
time.sleep(10)
checkWifiConnection()
checkServer()
mode, vol, mic = checkTwoWay()
client.connect(host, 1883, 60)
client.loop_start()
setupLinphone()
execute(f"gpio write {led_cancel} 1")
print("MULAI")
time.sleep(10)
execute(f"gpio write {led_cancel} 0")
time.sleep(1)
execute(f"gpio write {led_cancel} 1")


before_call_lock = millis()
call_lock = False
before_cancel_lock = millis()
cancel_lock = False
before_infus_lock = millis()
infus_lock = False

counter_emergency = 0
before_idle = millis()
before_emergency_lock = millis()
emergency_lock = False

before_calling = millis()
before_after_calling = millis()

send_activation = millis()

while True:
    if '0' in execute(f"gpio read {btn_call}"):
        if not oncall and not after_calling.is_set():
            call_lock = True
            execute(f"gpio write {buzzer} 0")
            before_call_lock = millis()
        
        
    hasil_call_lock = millis() - before_call_lock
    if call_lock and ('1' in execute(f"gpio read {btn_call}"))  and hasil_call_lock > 200:
        execute("linphonecsh generic terminate")
        client.publish(f"call/{id}", payload="1", qos=1, retain=True)
        calling.set()
        player.stop()
        execute(f"gpio write {buzzer} 1")
        print("LOG| btn call clicked")
        before_call_lock = millis()
        call_lock = False

    
    if '0' in execute(f"gpio read {btn_infus}"):
        infus_lock = True
        execute(f"gpio write {buzzer} 0")
        before_infus_lock = millis()
        
        
    hasil_infus_lock = millis() - before_infus_lock
    if infus_lock and ('1' in execute(f"gpio read {btn_infus}"))  and hasil_infus_lock > 200:
        client.publish(f"infus/{id}", payload="i", qos=1, retain=True)
        after_calling.set()
        execute(f"gpio write {buzzer} 1")
        print("LOG| btn infus clicked")
        before_infus_lock = millis()
        infus_lock = False
    
    if '0' in execute(f"gpio read {btn_emergency}"):
        emergency_lock = True
        execute(f"gpio write {buzzer} 0")
        before_emergency_lock = millis()
        
        
    hasil_emergency_lock = millis() - before_emergency_lock
    if emergency_lock and ('1' in execute(f"gpio read {btn_emergency}"))  and hasil_emergency_lock > 200:
        client.publish(f"bed/{id}", payload="e", qos=1, retain=True)
        after_calling.set()
        execute(f"gpio write {buzzer} 1")
        print("LOG| btn emergency clicked")
        before_emergency_lock = millis()
        emergency_lock = False
    
    if '0' in execute(f"gpio read {btn_cancel}"):
        cancel_lock = True
        execute(f"gpio write {buzzer} 0")
        before_cancel_lock = millis()

        
    hasil_cancel_lock = millis() - before_cancel_lock
    if cancel_lock and ('1' in execute(f"gpio read {btn_cancel}"))  and hasil_cancel_lock > 200:
        client.publish(f"call/{id}", payload="c", qos=1, retain=True)
        client.publish(f"stop/{id}", payload="c", qos=1, retain=True)
        client.publish(f"infus/{id}", payload="c", qos=1, retain=True)
        client.publish(f"bed/{id}", payload="c", qos=1, retain=True)
        after_calling.clear()
#         calling.clear()
        execute(f"gpio write {buzzer} 1")
        print("LOG| btn cancel clicked")
        before_cancel_lock = millis()
        cancel_lock = False

        
    res = execute("linphonecsh status hook")
    
    if "Incoming call" in res:
        res = res.split()
        res = res[-1][1:-1]
        time.sleep(1)
        execute(f"linphonecsh generic answer")
    elif "hook=answered" in res:
        execute(f"amixer set Capture {mic}%")
        oncall = True
        execute(f"gpio write {pin_relay} 0")
        calling.clear()
        player.stop()
    else:
        if calling.is_set():
            execute(f"gpio write {pin_relay} 0")
        elif playing.is_set():
            execute(f"gpio write {pin_relay} 0")
        else:
            execute(f"gpio write {pin_relay} 1")
        oncall = False
        


    if calling.is_set() :
        if millis() - before_calling > 2000:
            execute('ogg123 /home/nursecall/ip-call-bed/ringback.ogg')
            before_calling = millis()
    
    if after_calling.is_set() :
        if millis() - before_after_calling > 1000:
            execute(f"gpio write {led_cancel} 0")
            time.sleep(0.2)
            execute(f"gpio write {led_cancel} 1")
            before_after_calling = millis()
            
    if reregister.is_set():
        execute("linphonecsh unregister")
        setupLinphone()
    
    if millis() - send_activation > 5000:
        client.publish("aktif", payload=id, qos=0, retain=False)
        
#         client.subscribe(f"stop/{id}")
#         client.subscribe(f"infus/{id}")
#         client.subscribe(f"bed/{id}")
#         client.subscribe(f"assist/{id}")
#         client.subscribe(f"serial/{id}")
#         client.subscribe(id)
#         client.subscribe("schedule")
            
        send_activation = millis()
