from flask import Flask, request, redirect, render_template
import os

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        id = request.form.get('id')
        ssid = request.form.get('ssid')
        pswd = request.form.get('pswd')
        
        f = open("/home/nursecall/ip-call-bed/config/id.txt", "w")
        f.write(id)
        f.close()
        
        f = open("/home/nursecall/ip-call-bed/config/ssid.txt", "w")
        f.write(ssid)
        f.close()
        
        f = open("/home/nursecall/ip-call-bed/config/pass.txt", "w")
        f.write(pswd)
        f.close()
        
        return redirect('/')
    
    ssid = open("/home/nursecall/ip-call-bed/config/ssid.txt", "r")
    pswd = open("/home/nursecall/ip-call-bed/config/pass.txt", "r")
    id_r = open("/home/nursecall/ip-call-bed/config/id.txt", "r")
    _ssid = ssid.read()
    _pswd = pswd.read()
    _id_r = id_r.read()
    
    ssid.close()
    pswd.close()
    id_r.close()
    
    return render_template('index.html', id=_id_r, ssid=_ssid, pswd=_pswd)

@app.route('/reboot')
def reboot():
    os.system('reboot')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
