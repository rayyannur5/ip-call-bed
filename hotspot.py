import subprocess
import time
import wifimangement_linux as wifi 


def execute(command):
    return subprocess.run(command, capture_output=True, shell=True).stdout.decode()

def millis():
    return round(time.time() * 1000)

execute(f"gpio mode 2 in")
execute(f"gpio mode 23 in")
def run():
    execute(f"gpio write 23 1")
    execute('ogg123 /home/nursecall/ip-call-bed/bluetooth-connected.ogg')
#     execute("nmcli c modify Hotspot 802-11-wireless-security.pmf 1")
    execute("nmcli connection up Hotspot")
    
while True:
    if '0' in execute(f"gpio read 2"):
        print("tes")
        before_5detik = millis()
        while '0' in execute(f"gpio read 2"):
            if millis() - before_5detik > 5000:
                run()
        
