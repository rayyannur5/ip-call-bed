from flask import Flask, request, redirect, render_template, jsonify
import os
import re
import subprocess
import time

app = Flask(__name__)

def execute(command):
    """Menjalankan perintah shell dan mengembalikan output."""
    try:
        return subprocess.run(command, capture_output=True, shell=True, text=True).stdout.strip()
    except Exception as e:
        print(f"Error executing command '{command}': {e}")
        return ""

def scan_wifi():
    try:
        # Jalankan perintah `nmcli dev wifi`
        execute("nmcli dev wifi rescan")
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

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        id = request.form.get('id')
        # nursestation = request.form.get('nursestation')
        ssid = request.form.get('ssid')
        pswd = request.form.get('pswd')
        ip = request.form.get('static_ip')
        print(ip)
        
        f = open("/home/nursecall/ip-call-bed/config/id.txt", "w")
        f.write(id)
        f.close()

        # f = open("/home/nursecall/ip-call-bed/config/nursestation.txt", "w")
        # f.write(nursestation)
        # f.close()
        
        f = open("/home/nursecall/ip-call-bed/config/ssid.txt", "w")
        f.write(ssid)
        f.close()
        
        f = open("/home/nursecall/ip-call-bed/config/pass.txt", "w")
        f.write(pswd)
        f.close()

        f = open("/home/nursecall/ip-call-bed/config/ip.txt", "w")
        f.write(ip)
        f.close()
        
        return redirect('/')
    
    ssid = open("/home/nursecall/ip-call-bed/config/ssid.txt", "r")
    nursestation = open("/home/nursecall/ip-call-bed/config/nursestation.txt", "r")
    pswd = open("/home/nursecall/ip-call-bed/config/pass.txt", "r")
    id_r = open("/home/nursecall/ip-call-bed/config/id.txt", "r")
    ip_r = open("/home/nursecall/ip-call-bed/config/ip.txt", "r")
    _ssid = ssid.read()
    _nursestation = nursestation.read()
    _pswd = pswd.read()
    _id_r = id_r.read()
    _ip = ip_r.read()
    
    ssid.close()
    nursestation.close()
    pswd.close()
    id_r.close()
    ip_r.close()
    
    return render_template('index.html', id=_id_r, ssid=_ssid, pswd=_pswd, static_ip=_ip)


@app.route('/scan')
def scan():
    return jsonify(scan_wifi())

@app.route('/reboot')
def reboot():
    os.system('reboot')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
