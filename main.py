import subprocess
import time

btn_call 		= 2
btn_cancel 		= 5
btn_emergency 	= 7
btn_infus 		= 8
led_1 			= 6
host 			= "192.168.1.117"
port_sip 		= "5060"
username 		= "rpi"
password 		= "22222222"
nurse_sip		= "5004"
id 				= "010101"


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

time.sleep(10)
setupGPIO()
checkWifiConnection()
setupLinphone()
execute(f"gpio write {led_1} 1")
while True:
    if '1' in execute(f"gpio read {btn_call}"):
        while '1' in execute(f"gpio read {btn_call}"):
            pass
        execute(f"mosquitto_pub -h {host} -t call/{id} -m 1")
        print("LOG| btn call clicked")
    elif '1' in execute(f"gpio read {btn_cancel}"):
        while '1' in execute(f"gpio read {btn_cancel}"):
            pass
        execute(f"mosquitto_pub -h {host} -t bed/{id} -m c")
        print("LOG| btn cancel clicked")
    elif '1' in execute(f"gpio read {btn_emergency}"):
        while '1' in execute(f"gpio read {btn_emergency}"):
            pass
        execute(f"mosquitto_pub -h {host} -t bed/{id} -m e")
        print("LOG| btn emergency clicked")
    elif '1' in execute(f"gpio read {btn_infus}"):
        while '1' in execute(f"gpio read {btn_infus}"):
            pass
        execute(f"mosquitto_pub -h {host} -t bed/{id} -m i")
        print("LOG| btn infus clicked")
        
        
    res = execute("linphonecsh status hook")
    
    if "Incoming call" in res:
        res = res.split()
        res = res[-1][1:-1]
        time.sleep(1)
        execute(f"linphonecsh generic answer")
