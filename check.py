import subprocess
import time
host 			= "192.168.0.1"

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
            res = execute(f"ping -c 1 {host}")
            if millis() - before_reboot > 120000:
                execute("reboot")
        print("PING OKE")
        before_5detik = millis()

        
