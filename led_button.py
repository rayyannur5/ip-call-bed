import subprocess
import time
import requests

btn_call 		= 25
btn_cancel 		= 7
btn_emergency 	= 0
btn_infus 		= 2
led_cancel		= 8
led_emergency	= 1
led_infus		= 5
host 			= "192.168.0.1"

id_r = open("/home/nursecall/ip-call-bed/config/id.txt", "r")
id 				= id_r.read()
id_r.close()

def execute(command):
    return subprocess.run(command, capture_output=True, shell=True).stdout.decode()

def millis():
    return round(time.time() * 1000)

before_3_menit  = millis()

while True :
    if '0' in execute(f"gpio read {btn_infus}"):
        execute(f"gpio write {led_infus} 0")
        time.sleep(0.2)
        execute(f"gpio write {led_infus} 1")
        time.sleep(0.2)
        execute(f"gpio write {led_infus} 0")
        time.sleep(0.2)
        execute(f"gpio write {led_infus} 1")
        time.sleep(1)
        execute(f"gpio write {led_infus} 0")
        time.sleep(0.2)
        execute(f"gpio write {led_infus} 1")
        time.sleep(0.2)
        execute(f"gpio write {led_infus} 0")
        time.sleep(0.2)
        execute(f"gpio write {led_infus} 1")

    if '0' in execute(f"gpio read {btn_emergency}"):
        execute(f"gpio write {led_emergency} 0")
        time.sleep(0.2)
        execute(f"gpio write {led_emergency} 1")
        time.sleep(0.2)
        execute(f"gpio write {led_emergency} 0")
        time.sleep(0.2)
        execute(f"gpio write {led_emergency} 1")
        time.sleep(1)
        execute(f"gpio write {led_emergency} 0")
        time.sleep(0.2)
        execute(f"gpio write {led_emergency} 1")
        time.sleep(0.2)
        execute(f"gpio write {led_emergency} 0")
        time.sleep(0.2)
        execute(f"gpio write {led_emergency} 1")

    if millis() - before_3_menit > 180000:
        x = requests.get(f'http://{host}/ip-call/server/bed/get_one.php?id={id}').json()
        execute(f"amixer set Master {x['data'][0]['vol']}%")
        before_3_menit = millis()