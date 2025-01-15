import subprocess
import time
import paho.mqtt.client as mqtt
from threading import Event
import wifimangement_linux as wifi
import requests
import re

calling = Event()
after_calling = Event()

list_nursestation = {
    '1': [
        "IPCallServer",
        "IPCallServer2",
        "IPCallServer3",
        "IPCallServer4",
        "IPCallServer5",
        "IPCallServer6",
        "IPCallServer7",
        "IPCallServer8",
        "IPCallServer9",
        "IPCallServer10",
    ],
    '2': [
        "IPCallServer11",
        "IPCallServer12",
        "IPCallServer13",
        "IPCallServer14",
        "IPCallServer15",
        "IPCallServer16",
        "IPCallServer17",
        "IPCallServer18",
        "IPCallServer19",
        "IPCallServer20",
    ],
    '3': [
        "IPCallServer21",
        "IPCallServer22",
        "IPCallServer23",
        "IPCallServer24",
        "IPCallServer25",
        "IPCallServer26",
        "IPCallServer27",
        "IPCallServer28",
        "IPCallServer29",
        "IPCallServer30",
    ],
    '4': [
        "IPCallServer31",
        "IPCallServer32",
        "IPCallServer33",
        "IPCallServer34",
        "IPCallServer35",
        "IPCallServer36",
        "IPCallServer37",
        "IPCallServer38",
        "IPCallServer39",
        "IPCallServer40",
    ],
}

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

id 				= id_r.read()
nursestation    = nursetation_r.read()
ssid            = ssid_r.read()
pswd            = pswd_r.read()

if id == "":
    exit()

id_r.close()
nursetation_r.close()
ssid_r.close()
pswd_r.close()

btn_call 		= 22
btn_cancel 		= 2
btn_emergency 	= 6
btn_infus 		= 0
led_cancel		= 20
led_emergency	= 3
led_infus		= 4
pin_relay		= 23
buzzer			= 17
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

# The callback for when a PUBLISH message is received from the server.
# first_on = Event()
def on_message(client, userdata, msg):
#     if first_on.is_set() :
    print(msg.topic+" "+str(msg.payload))
    if 's' in str(msg.payload):
        calling.clear()
    elif 'm' in str(msg.payload):
        after_calling.set()
    elif 'c' in str(msg.payload):
        after_calling.clear()
#         calling.clear()
    elif 'x' in str(msg.payload):
        after_calling.clear()
#         calling.clear()
#     else :
#         first_on.set()

client = mqtt.Client()
client.on_connect = on_connect
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
    execute(f"gpio mode {btn_call} in")
    execute(f"gpio mode {btn_cancel} in")
    execute(f"gpio mode {btn_emergency} in")
    execute(f"gpio mode {btn_infus} in")
    execute(f"gpio mode {led_cancel} out")
    execute(f"gpio mode {led_infus} out")
    execute(f"gpio mode {led_emergency} out")
    execute(f"gpio mode {pin_relay} out")
    execute(f"gpio write {led_cancel} 1")
    execute(f"gpio write {led_infus} 1")
    execute(f"gpio write {led_emergency} 1")
    execute(f"gpio write {pin_relay} 0")
    print("LOG| SETUP GPIO SUCCESSFULL")
    
def setupLinphone():
    execute("linphonecsh init")
    print("LOG| LINPHONE REGISTERING")
    execute(f"linphonecsh register --host {host} --username {username} --password {password}")
    res = execute("linphonecsh status register")
    before_linphone = millis()
    while "registered," not in res:
        execute(f"gpio write {led_cancel} 0")
        execute("linphonecsh init")
        execute(f"linphonecsh register --host {host} --username {username} --password {password}")
        res = execute("linphonecsh status register")
        time.sleep(0.1)
        execute(f"gpio write {led_cancel} 1")
        time.sleep(0.1)
        if millis() - before_linphone >60000:
            execute("reboot")
    print("LOG| LINPHONE REGISTERED")
    
    res = execute("linphonecsh generic 'soundcard list'")
    while "echo" not in res:
        res = execute("linphonecsh generic 'soundcard list'")
        
    res = res.split("\n")
    for i in res:
        if "echo" in i:
            index_soundcard = i[0]
            res = execute(f"linphonecsh generic 'soundcard use {index_soundcard}'")
            print(f"LOG| {res}")
            break

def call(sip):
    res = execute(f"linphonecsh dial {sip}")
    print(f"LOG| {res}")

def checkTwoWay():
    requests.get(f"http://{host}/ip-call/server/bed/set_ip.php?id={id}&ip={wifi.ip()}")
    x = requests.get(f'http://{host}/ip-call/server/bed/get_one.php?id={id}').json()
    execute(f"amixer set Master {x['data'][0]['vol']}%")
    return x['data'][0]['mode'], int(x['data'][0]['vol']), int(x['data'][0]['mic'])

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
            before_call_lock = millis()
        
        
    hasil_call_lock = millis() - before_call_lock
    if call_lock and ('1' in execute(f"gpio read {btn_call}"))  and hasil_call_lock > 200:
        execute("linphonecsh generic terminate")
        client.publish(f"call/{id}", payload="1", qos=1, retain=True)
        calling.set()
        print("LOG| btn call clicked")
        before_call_lock = millis()
        call_lock = False

    
    if '0' in execute(f"gpio read {btn_infus}"):
        infus_lock = True
        before_infus_lock = millis()
        
        
    hasil_infus_lock = millis() - before_infus_lock
    if infus_lock and ('1' in execute(f"gpio read {btn_infus}"))  and hasil_infus_lock > 200:
        client.publish(f"infus/{id}", payload="i", qos=1, retain=True)
        after_calling.set()
        print("LOG| btn infus clicked")
        before_infus_lock = millis()
        infus_lock = False

    
    if '0' in execute(f"gpio read {btn_emergency}"):
        emergency_lock = True
        before_emergency_lock = millis()
        
        
    hasil_emergency_lock = millis() - before_emergency_lock
    if emergency_lock and ('1' in execute(f"gpio read {btn_emergency}"))  and hasil_emergency_lock > 200:
        client.publish(f"bed/{id}", payload="e", qos=1, retain=True)
        after_calling.set()
        print("LOG| btn emergency clicked")
        before_emergency_lock = millis()
        emergency_lock = False

    
    if '0' in execute(f"gpio read {btn_cancel}"):
        cancel_lock = True
        before_cancel_lock = millis()

        
    hasil_cancel_lock = millis() - before_cancel_lock
    if cancel_lock and ('1' in execute(f"gpio read {btn_cancel}"))  and hasil_cancel_lock > 200:
        client.publish(f"call/{id}", payload="c", qos=1, retain=True)
        client.publish(f"stop/{id}", payload="c", qos=1, retain=True)
        client.publish(f"infus/{id}", payload="c", qos=1, retain=True)
        client.publish(f"bed/{id}", payload="c", qos=1, retain=True)
        after_calling.clear()
#         calling.clear()
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
        execute(f"gpio write {pin_relay} 1")
        calling.clear()
    else:
        if calling.is_set():
            execute(f"gpio write {pin_relay} 1")
        else:
            execute(f"gpio write {pin_relay} 0")
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
    
    if millis() - send_activation > 5000:
        client.publish("aktif", payload=id, qos=0, retain=False)
        send_activation = millis()