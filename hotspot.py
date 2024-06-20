import subprocess
import time
import wifimangement_linux as wifi 


def execute(command):
    return subprocess.run(command, capture_output=True, shell=True).stdout.decode()

def millis():
    return round(time.time() * 1000)

execute(f"gpio mode 4 in")
def run():
    execute('ogg123 /home/nursecall/ip-call-bed/bluetooth-connected.ogg')
#     execute("nmcli c modify Hotspot 802-11-wireless-security.pmf 1")
    execute("nmcli connection up Hotspot")
    
while True:
    if '0' in execute(f"gpio read 4"):
        print("tes")
        before_5detik = millis()
        while '0' in execute(f"gpio read 4"):
            if millis() - before_5detik > 5000:
                run()
        
