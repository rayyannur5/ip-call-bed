import subprocess
import time

monitorPin = 27
state = 0


def execute(command):
    return subprocess.run(command, capture_output=True, shell=True).stdout.decode()

execute(f"gpio mode {monitorPin} out")

while True:
    execute(f"gpio write {monitorPin} {state}")
    state = 1 if not state else 0
    time.sleep(1)
    