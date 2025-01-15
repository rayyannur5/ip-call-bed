import subprocess
import time
import wifimangement_linux as wifi

ssid = open("/home/nursecall/ip-call-bed/config/ssid.txt", "r")
pswd = open("/home/nursecall/ip-call-bed/config/pass.txt", "r")

ssid_r = ssid.read()
pswd_r = pswd.read()

ssid.close()
pswd.close()

host 			= "192.168.0.254"

def execute(command):
    return subprocess.run(command, capture_output=True, shell=True).stdout.decode()


def millis():
    return round(time.time() * 1000)

before_5detik = millis()
while True:
    if millis() - before_5detik > 5000:
        res = execute(f"ping -c 1 {host}")
        before_reboot = millis()
        while "1 received" not in res:
            wifi.connect(ssid_r,pswd_r)
            res = execute(f"ping -c 1 {host}")
            if millis() - before_reboot > 120000:
                execute("reboot")
        print("PING OKE")
        before_5detik = millis()