import subprocess
import time

btn_call 		= 6
btn_cancel 		= 4
btn_emergency 	= 9
btn_infus 		= 3
led_1 			= 1
host 			= "10.42.0.1"
port_sip 		= "5060"
username 		= "010101"
password 		= "010101"
nurse_sip		= "5004"
id 				= "010101"
btn_session 	= None
oncall			= False

def execute(command):
    return subprocess.run(command, capture_output=True, shell=True).stdout.decode()

def checkWifiConnection():
    res = execute("nmcli con show")
    while "wlan0" not in res:
        res = execute("nmcli con show")
    
    execute(f"gpio write {led_1} 1")
    time.sleep(1)
    execute(f"gpio write {led_1} 0")
    print("LOG| WIFI CONNECTED")

def setupGPIO():
    execute(f"gpio mode {btn_call} in")
    execute(f"gpio mode {btn_cancel} in")
    execute(f"gpio mode {btn_emergency} in")
    execute(f"gpio mode {btn_infus} in")
    execute(f"gpio mode {led_1} out")
    execute(f"gpio write {led_1} 0")
    print("LOG| SETUP GPIO SUCCESSFULL")
    
def setupLinphone():
    execute("linphonecsh init")
    print("LOG| LINPHONE REGISTERING")
    execute(f"linphonecsh register --host {host} --username {username} --password {password}")
    res = execute("linphonecsh status register")
    while "registered," not in res:
        execute(f"gpio write {led_1} 1")
        execute("linphonecsh init")
        execute(f"linphonecsh register --host {host} --username {username} --password {password}")
        res = execute("linphonecsh status register")
        time.sleep(0.1)
        execute(f"gpio write {led_1} 0")
        time.sleep(0.1)
        pass
    print("LOG| LINPHONE REGISTERED")
    
    res = execute("linphonecsh generic 'soundcard list'")
    while "USB" not in res:
        res = execute("linphonecsh generic 'soundcard list'")
        
    res = res.split("\n")
    for i in res:
        if "USB" in i:
            index_soundcard = i[0]
            res = execute(f"linphonecsh generic 'soundcard use {index_soundcard}'")
            print(f"LOG| {res}")
            break

def call(sip):
    res = execute(f"linphonecsh dial {sip}")
    print(f"LOG| {res}")

def millis():
    return round(time.time() * 1000)

time.sleep(10)
setupGPIO()
checkWifiConnection()
setupLinphone()
execute(f"gpio write {led_1} 0")
time.sleep(30)
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
while True:
    if '0' in execute(f"gpio read {btn_call}"):
        if oncall:
            continue
        call_lock = True
        before_call_lock = millis()
        
        
    hasil_call_lock = millis() - before_call_lock
    if call_lock and ('1' in execute(f"gpio read {btn_cancel}"))  and hasil_call_lock > 200:
        execute("linphonecsh generic terminate")
        execute(f"mosquitto_pub -h {host} -t call/{id} -m 1")
        print("LOG| btn call clicked")
        before_call_lock = millis()
        call_lock = False
    

    
    if '0' in execute(f"gpio read {btn_cancel}"):
        cancel_lock = True
        before_cancel_lock = millis()
        
    hasil_cancel_lock = millis() - before_cancel_lock
    if cancel_lock and ('1' in execute(f"gpio read {btn_cancel}"))  and hasil_cancel_lock > 200:
        execute(f"mosquitto_pub -h {host} -t infus/{id} -m c")
        execute(f"mosquitto_pub -h {host} -t bed/{id} -m c")
        execute(f"mosquitto_pub -h {host} -t blue/{id} -m c")
        execute(f"mosquitto_pub -h {host} -t assist/{id} -m c")
        print("LOG| btn cancel clicked")
        before_cancel_lock = millis()
        cancel_lock = False
        
        
    if '0' in execute(f"gpio read {btn_infus}"):
        infus_lock = True
        before_infus_lock = millis()
        
    hasil_infus_lock = millis() - before_infus_lock
    if infus_lock and ('1' in execute(f"gpio read {btn_infus}")) and hasil_infus_lock > 200:
        execute(f"mosquitto_pub -h {host} -t infus/{id} -m i")
        print("LOG| btn infus clicked")
        before_infus_lock = millis()
        infus_lock = False
        
    
    if '0' in execute(f"gpio read {btn_emergency}") and not emergency_lock:
        emergency_lock = True
        counter_emergency += 1
        print(counter_emergency)
        before_emergency_lock = millis()
        
        
    hasil_emergency_lock = millis() - before_emergency_lock
    if emergency_lock and hasil_emergency_lock > 5000:
        emergency_lock = True
        counter_emergency = 0
        print("LOG| EMERGENCY")
        execute(f"mosquitto_pub -h {host} -t bed/{id} -m e")
        
        before_emergency_lock = millis()
        before_idle = millis()
        
        
    elif emergency_lock and ('1' in execute(f"gpio read {btn_emergency}")) and hasil_emergency_lock > 200:
        before_emergency_lock = millis()
        before_idle = millis()
        emergency_lock = False
    
    hasil_before_idle = millis() - before_idle
    if not emergency_lock and hasil_before_idle > 1000 and counter_emergency != 0:
        print("IDLE")
        print(f"HASIL : {counter_emergency}")
        
        if counter_emergency == 1 :
            print("LOG| ASSIST NURSE")
            execute(f"mosquitto_pub -h {host} -t assist/{id} -m a")
            
        elif counter_emergency == 3:
            print("CODE_BLUE")
            execute(f"mosquitto_pub -h {host} -t blue/{id} -m b")
        
        counter_emergency = 0
        before_idle = millis()
                
        
    res = execute("linphonecsh status hook")
    
    if "Incoming call" in res:
        res = res.split()
        res = res[-1][1:-1]
#         time.sleep(1)
        execute(f"linphonecsh generic answer")
    elif "hook=answered" in res:
        oncall = True
    else:
        oncall = False
        
