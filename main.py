import subprocess
import time
import paho.mqtt.client as mqtt
from threading import Event
import wifimangement_linux as wifi
import requests

calling = Event()
after_calling = Event()

ssid = open("/home/opi1/ip-call-bed/config/ssid.txt", "r")
pswd = open("/home/opi1/ip-call-bed/config/pass.txt", "r")
id_r = open("/home/opi1/ip-call-bed/config/id.txt", "r")

wifi.connect(ssid.read(),pswd.read())
ssid.close()
pswd.close()

id 				= id_r.read()
id_r.close()

if id == "":
    exit()

btn_call 		= 3
btn_cancel 		= 4
btn_emergency 	= 9
btn_infus 		= 0
led_1 			= 5
buzzer			= 1
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

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("LOG| Connected with result code "+str(rc))
    
    client.subscribe(f"stop/{id}")
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
        calling.clear()
    elif 'x' in str(msg.payload):
        after_calling.clear()
        calling.clear()
#     else :
#         first_on.set()
    
    

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

def execute(command):
    return subprocess.run(command, capture_output=True, shell=True).stdout.decode()

def millis():
    return round(time.time() * 1000)

def checkWifiConnection():
    res = execute("nmcli con show")
    while "wlan0" not in res:
        res = execute("nmcli con show")
    
    execute(f"gpio write {led_1} 0")
    time.sleep(1)
    execute(f"gpio write {led_1} 1")
    print("LOG| WIFI CONNECTED")

def checkServer():
    res = execute(f"ping -c 1 {host}")
    while "1 received" not in res:
        res = execute(f"ping -c 1 {host}")
        
    execute(f"gpio write {led_1} 0")
    time.sleep(0.5)
    execute(f"gpio write {led_1} 1")
    print("LOG| SERVER ONLINE")

def setupGPIO():
    execute(f"gpio mode {btn_call} in")
    execute(f"gpio mode {btn_cancel} in")
    execute(f"gpio mode {btn_emergency} in")
    execute(f"gpio mode {btn_infus} in")
    execute(f"gpio mode {led_1} out")
    execute(f"gpio write {led_1} 1")
    print("LOG| SETUP GPIO SUCCESSFULL")
    
def setupLinphone():
    execute("linphonecsh init")
    print("LOG| LINPHONE REGISTERING")
    execute(f"linphonecsh register --host {host} --username {username} --password {password}")
    res = execute("linphonecsh status register")
    before_linphone = millis()
    while "registered," not in res:
        execute(f"gpio write {led_1} 0")
        execute("linphonecsh init")
        execute(f"linphonecsh register --host {host} --username {username} --password {password}")
        res = execute("linphonecsh status register")
        time.sleep(0.1)
        execute(f"gpio write {led_1} 1")
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
    x = requests.get(f'http://{host}/ip-call-server/bed/get_one.php?id={id}').json()
    execute(f"amixer set Master {x['data'][0]['vol']}%")
    return x['data'][0]['tw'], int(x['data'][0]['vol']), int(x['data'][0]['mic'])

setupGPIO()
execute(f"gpio write {led_1} 0")
time.sleep(0.5)
execute(f"gpio write {led_1} 1")
time.sleep(10)
checkWifiConnection()
checkServer()
tw, vol, mic = checkTwoWay()
client.connect(host, 1883, 60)
client.loop_start()
setupLinphone()
execute(f"gpio write {led_1} 1")
print("MULAI")
time.sleep(10)
execute(f"gpio write {led_1} 0")
time.sleep(1)
execute(f"gpio write {led_1} 1")


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

send_activation = millis()

if tw == '1':
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

        
        if '0' in execute(f"gpio read {btn_cancel}"):
            cancel_lock = True
            before_cancel_lock = millis()
            
        hasil_cancel_lock = millis() - before_cancel_lock
        if cancel_lock and ('1' in execute(f"gpio read {btn_cancel}"))  and hasil_cancel_lock > 200:
            client.publish(f"call/{id}", payload="c", qos=1, retain=True)
            client.publish(f"stop/{id}", payload="c", qos=1, retain=True)
            after_calling.clear()
            calling.clear()
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
            calling.clear()
        else:
            oncall = False


        if calling.is_set() :
            if millis() - before_calling > 2000:
                execute('ogg123 /home/opi1/ip-call-bed/ringback.ogg')
                before_calling = millis()
        
        if after_calling.is_set() :
            if millis() - before_calling > 1000:
                execute(f"gpio write {led_1} 0")
                time.sleep(0.2)
                execute(f"gpio write {led_1} 1")
                before_calling = millis()
        
        if millis() - send_activation > 5000:
            client.publish("aktif", payload=id, qos=0, retain=False)
            send_activation = millis()
else :
    while True:
        if '0' in execute(f"gpio read {btn_call}"):
            if not oncall and not after_calling.is_set():
                call_lock = True
                before_call_lock = millis()
            
            
        hasil_call_lock = millis() - before_call_lock
        if call_lock and ('1' in execute(f"gpio read {btn_call}"))  and hasil_call_lock > 200:
            client.publish(f"assist/{id}", payload="a", qos=1, retain=True)
            calling.set()
            print("LOG| btn call clicked")
            before_call_lock = millis()
            call_lock = False

        
        if '0' in execute(f"gpio read {btn_cancel}"):
            cancel_lock = True
            before_cancel_lock = millis()
            
        hasil_cancel_lock = millis() - before_cancel_lock
        if cancel_lock and ('1' in execute(f"gpio read {btn_cancel}"))  and hasil_cancel_lock > 200:
            client.publish(f"assist/{id}", payload="c", qos=1, retain=True)
            calling.clear()
            print("LOG| btn cancel clicked")
            before_cancel_lock = millis()
            cancel_lock = False
            
        
        if calling.is_set() :
            if millis() - before_calling > 1000:
                execute(f"gpio write {led_1} 0")
                time.sleep(0.2)
                execute(f"gpio write {led_1} 1")
                before_calling = millis()
        
        if millis() - send_activation > 5000:
            client.publish("aktif", payload=id, qos=0, retain=False)
            send_activation = millis()

