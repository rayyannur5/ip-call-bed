import subprocess
import time
import paho.mqtt.client as mqtt
from threading import Event
import wifimangement_linux as wifi
import requests
import re
import vlc
import datetime

# --- Utility Functions ---

def log_print(*args, **kwargs):
    """Fungsi print kustom yang menambahkan timestamp di awal pesan."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_prefix = f"[{timestamp}]"
    print(log_prefix, *args, **kwargs)

def execute(command):
    """Menjalankan perintah shell dan mengembalikan output."""
    try:
        return subprocess.run(command, capture_output=True, shell=True, text=True).stdout.strip()
    except Exception as e:
        log_print(f"Error executing command '{command}': {e}")
        return ""

def millis():
    """Mengembalikan waktu saat ini dalam milidetik."""
    return round(time.time() * 1000)

# --- Button Debounce Class ---

class Button:
    """
    Class untuk menangani logika debounce dan deteksi penekanan tombol (pendek & lama).
    Logika diperbaiki untuk memastikan long press dan buzzer berfungsi dengan benar.
    """
    def __init__(self, pin, debounce_ms=200, long_press_ms=None):
        self.pin = pin
        self.debounce_ms = debounce_ms
        self.long_press_ms = long_press_ms
        # Status internal
        self._is_pressed = False
        self._press_start_time = 0
        self._buzzer_on = False
        self._long_press_fired = False
        execute(f"gpio mode {self.pin} in")

    def check(self):
        is_reading_pressed = '0' in execute(f"gpio read {self.pin}")

        # --- Tombol sedang ditekan ---
        if is_reading_pressed:
            # Jika ini adalah awal penekanan tombol
            if not self._is_pressed:
                self._is_pressed = True
                self._long_press_fired = False
                self._press_start_time = millis()
            
            press_duration = millis() - self._press_start_time

            # Nyalakan buzzer jika debounce terlewati
            if not self._buzzer_on and press_duration > self.debounce_ms:
                self._buzzer_on = True
                execute(f"gpio write {buzzer} 0")

            # Periksa event long press (hanya jika ada dan belum terpicu)
            if self.long_press_ms and not self._long_press_fired and press_duration > self.long_press_ms:
                self._long_press_fired = True # Tandai bahwa long press sudah terjadi
                
                # Matikan buzzer normal jika menyala
                if self._buzzer_on:
                    execute(f"gpio write {buzzer} 1")

                 # Beri umpan balik khusus untuk long press
                execute(f"gpio write {buzzer} 0"); time.sleep(0.1)
                execute(f"gpio write {buzzer} 1"); time.sleep(0.1)
                execute(f"gpio write {buzzer} 0"); time.sleep(0.1)
                execute(f"gpio write {buzzer} 1")
                
                while '0' in execute(f"gpio read {self.pin}"): pass

                return "long_press"
        
        # --- Tombol dilepas ---
        else:
            # Jika tombol sebelumnya dalam keadaan ditekan
            if self._is_pressed:
                press_duration = millis() - self._press_start_time
                
                # Reset semua status
                self._is_pressed = False
                if self._buzzer_on:
                    self._buzzer_on = False
                    execute(f"gpio write {buzzer} 1")
                
                # Periksa apakah ini short press yang valid
                if not self._long_press_fired and press_duration > self.debounce_ms:
                    return "short_press"
        
        return None

# --- Global Variables & Events ---
calling, playing, after_calling, reregister = Event(), Event(), Event(), Event()
player = vlc.MediaPlayer()

# --- Configuration Loading ---
try:
    with open("/home/nursecall/ip-call-bed/config/id.txt", "r") as f: id = f.read().strip()
    with open("/home/nursecall/ip-call-bed/config/nursestation.txt", "r") as f: nursestation = f.read().strip()
    with open("/home/nursecall/ip-call-bed/config/ssid.txt", "r") as f: ssid = f.read().strip()
    with open("/home/nursecall/ip-call-bed/config/pass.txt", "r") as f: pswd = f.read().strip()
    with open("/home/nursecall/ip-call-bed/config/audio.txt", "r") as f: state_audio = f.read().strip()
    with open("/home/nursecall/ip-call-bed/config/ip.txt", "r") as f: static_ip = f.read().strip()
except FileNotFoundError as e:
    log_print(f"Error: File konfigurasi tidak ditemukan - {e}"); exit()

if not id: log_print("Error: ID perangkat kosong."); exit()
if state_audio == '': state_audio = '0'

# --- Hardware & Network Constants ---
btn_call, btn_cancel, btn_emergency, btn_infus = 23, 22, 6, 2
led_cancel, led_emergency, led_infus = 20, 3, 4
pin_relay, buzzer, host = 25, 3, "192.168.0.1"
username, password = id, id
mic, vol, oncall = 100, 100, False
state_btn_activity, timer_after_activity, timeout_time_activity = False, 60000, 60000
timer_ping, send_activation = 0, 0
before_calling, before_after_calling = 0, 0
x_server_emergency, x_server_call, x_server_infus = 0,0,0

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    log_print(f"MQTT terhubung dengan kode: {rc}")
    client.subscribe([(f"stop/{id}", 1), (f"infus/{id}", 1), (f"bed/{id}", 1), 
                      (f"assist/{id}", 1), (f"call/{id}", 1),  (f"serial/{id}", 1), (id, 1), 
                      ("schedule_audio", 1), ("ping", 1)])

def on_disconnect(client, userdata, rc):
    if rc != 0:
        log_print("Koneksi MQTT terputus! Mencoba menyambung kembali...")
        start_timer = millis()
        while True:
            if millis() - start_timer > 60000:
                log_print('Rebooting... Gagal terhubung ke MQTT selama 1 menit.')
                execute('reboot')
            try:
                client.reconnect()
                log_print("Berhasil menyambung ulang ke broker MQTT!")
                break
            except Exception as e:
                log_print(f"Gagal menyambung ulang: {e}. Mencoba lagi dalam 5 detik...")
                time.sleep(5)
    else:
        log_print("Koneksi MQTT terputus dengan normal.")

def on_message(client, userdata, msg):
    global playing, state_btn_activity, player, timer_ping, timer_after_activity, timeout_time_activity, x_server_call, x_server_emergency, x_server_infus
    payload = msg.payload.decode('utf-8', errors='ignore')
    log_print(f"MQTT Diterima | Topik: {msg.topic} | Pesan: {payload}")
    
    if msg.topic == 'schedule_audio' and not state_btn_activity and (millis() - timer_after_activity > timeout_time_activity):
        if '1' in payload: playing.set()
        elif '0' in payload: player.stop(); playing.clear()
    elif 's' in payload: calling.clear()
    elif 'm' in payload: after_calling.set()
    elif 'c' in payload: after_calling.clear()
    elif 'x' in payload:
        if 'bed' in msg.topic:
            x_server_emergency = 0
        elif 'infus' in msg.topic:
            x_server_infus = 0
        elif 'call' in msg.topic:
            x_server_call = 0
        after_calling.clear()
        state_btn_activity = False
    elif 'r' in payload: reregister.set()
    elif msg.topic == f"serial/{id}":
        if 'r' in payload: log_print("Reboot via MQTT."); execute("reboot")
        elif 'z' in payload: log_print("Test Buzzer via MQTT."); execute(f"gpio write {buzzer} 0"); time.sleep(1); execute(f"gpio write {buzzer} 1")
        elif 'l' in payload: log_print("Test Lamp via MQTT."); execute(f"gpio write {led_cancel} 0"); time.sleep(1); execute(f"gpio write {led_cancel} 1")
    if msg.topic == 'ping': timer_ping = millis()

# --- Setup Functions ---
def setupGPIO():
    log_print("Inisialisasi GPIO...")
    for pin in [led_cancel, led_infus, led_emergency, pin_relay, buzzer, 5]:
        execute(f"gpio mode {pin} out"); execute(f"gpio write {pin} 1")
    log_print("Inisialisasi GPIO berhasil.")

def check_connection(name, command, check_str):
    log_print(f"Mengecek koneksi {name}...")
    while check_str not in execute(command):
        log_print(f"Menunggu koneksi {name}..."); time.sleep(2)
    execute(f"gpio write {led_cancel} 0"); time.sleep(0.5); execute(f"gpio write {led_cancel} 1")
    log_print(f"{name} terhubung.")


def set_ip():
    log_print("Mengirim IP dan mengambil pengaturan dari server...")
    try:
        ip_address = wifi.ip()
        if not ip_address:
            log_print("Gagal mendapatkan alamat IP lokal."); return
        requests.get(f"http://{host}/ip-call/server/bed/set_ip.php?id={id}&ip={ip_address}", timeout=5)
    except Exception as e:
        log_print(f"Gagal memproses pengaturan dari server: {e}")

def get_settings():
    """Mengirim IP ke server dan mengambil pengaturan Vol/Mic."""
    global vol, mic, timeout_time_activity
    try:
        response = requests.get(f"http://{host}/ip-call/server/bed/get_one.php?id={id}", timeout=5)
        response.raise_for_status()
        data = response.json()
        if data and data.get('data'):
            settings = data['data'][0]
            vol = int(settings.get('vol', 100))
            mic = int(settings.get('mic', 100))
            timeout_time_activity = int(settings.get('timeout', 60000))
            execute(f"amixer set Master {vol}%")
            log_print(f"Pengaturan diterima: Vol={vol}%, Mic={mic}%, Timeout={timeout_time_activity}ms")
        else:
            log_print("Tidak ada data pengaturan dari server.")
    except Exception as e:
        log_print(f"Gagal memproses pengaturan dari server: {e}")

def setupLinphone():
    log_print("Inisialisasi & Registrasi Linphone...")
    execute("linphonecsh init")
    execute(f"linphonecsh register --host {host} --username {username} --password {password}")
    timeout = millis() + 60000
    while "registered" not in execute("linphonecsh status register"):
        if millis() > timeout: log_print("Gagal registrasi Linphone, reboot."); execute("reboot")
        execute("linphonecsh iterate"); time.sleep(1)
    log_print("Linphone terdaftar.")
    log_print("Mencari soundcard 'echo'...")
    soundcard_list = execute("linphonecsh generic 'soundcard list'")
    found_echo = False
    for line in soundcard_list.splitlines():
        if "echo" in line.lower():
            try:
                index = line.strip().split()[0]
                res = execute(f"linphonecsh generic 'soundcard use {index}'")
                log_print(f"Soundcard 'echo' ditemukan dan diatur: {res}")
                found_echo = True
                break
            except Exception: pass
    if not found_echo: log_print("Peringatan: Soundcard 'echo' tidak ditemukan.")
    reregister.clear()
# --- Fungsi Network yang Baru dan Cerdas ---

def check_connection_exists(con_name: str) -> bool:
    """Mengecek apakah profil koneksi dengan nama tertentu sudah ada."""
    command = f"nmcli -t -f NAME con show | grep -q '^{con_name}$'"
    try:
        subprocess.run(command, shell=True, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_current_ip(con_name: str) -> str:
    """Mengambil alamat IP yang saat ini terkonfigurasi pada sebuah profil."""
    # -g (get) adalah cara yang lebih langsung untuk mendapatkan nilai properti
    ip_with_prefix = execute(f"nmcli -g ipv4.addresses con show '{con_name}'")
    if '/' in ip_with_prefix:
        # Mengembalikan hanya alamat IP-nya, tanpa prefix /24
        return ip_with_prefix.split('/')[0]
    return ""

def setup_network_upsert(ssid: str, pswd: str, static_ip: str = None):
    """
    Fungsi cerdas untuk setup jaringan: Membuat profil jika belum ada, atau
    MEMPERBARUI jika konfigurasi IP berubah. Fallback ke DHCP jika static_ip kosong.
    """
    log_print("Memulai penyiapan jaringan (mode Create/Update)...")
    con_name = f"{ssid}-static"
    ifname = "wlan0"
    gateway = "192.168.0.254"

    # Periksa apakah profil sudah ada
    if check_connection_exists(con_name):
        log_print(f"Profil '{con_name}' sudah ada. Memeriksa konfigurasi IP...")
        
        # Jika profil ada, bandingkan IP yang ada dengan konfigurasi baru
        current_ip = get_current_ip(con_name)
        log_print(f"IP terkonfigurasi saat ini: '{current_ip}'")
        log_print(f"IP yang diinginkan       : '{static_ip}'")

        if current_ip != static_ip:
            log_print("IP berbeda! Memperbarui profil koneksi...")
            
            if static_ip:
                # Perbarui ke IP statis yang baru
                mod_cmd = f"""nmcli con mod '{con_name}' ipv4.method manual \
                            ipv4.addresses {static_ip}/24 ipv4.gateway {gateway} \
                            ipv4.dns "8.8.8.8" """
            else:
                # Perbarui ke DHCP
                mod_cmd = f"""nmcli con mod '{con_name}' ipv4.method auto \
                            ipv4.addresses "" ipv4.gateway "" ipv4.dns "" """
            
            result = execute(mod_cmd)
            # nmcli con mod tidak punya output sukses yang konsisten, jadi kita cek error
            if "Error:" in result:
                 log_print(f"FATAL: Gagal memperbarui profil! Error: {result}")
                 sys.exit()
            log_print("Profil berhasil diperbarui.")
            # Setelah modifikasi, koneksi harus diaktifkan ulang untuk menerapkan perubahan
            execute(f"nmcli con down '{con_name}'") # Matikan dulu untuk memastikan
            time.sleep(1)

        else:
            log_print("Konfigurasi IP sudah sesuai. Tidak ada perubahan.")

    else:
        # Jika profil belum ada, buat baru (logika dari sebelumnya)
        log_print(f"Profil '{con_name}' tidak ditemukan, membuat profil baru...")
        if static_ip:
            add_cmd = f"""nmcli con add type wifi con-name "{con_name}" ifname "{ifname}" ssid "{ssid}" -- \
                        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "{pswd}" \
                        ip4 {static_ip}/24 gw4 {gateway} \
                        ipv4.dns "8.8.8.8" ipv4.method manual"""
        else: # Fallback to DHCP
            add_cmd = f"""nmcli con add type wifi con-name "{con_name}" ifname "{ifname}" ssid "{ssid}" -- \
                        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "{pswd}" \
                        ipv4.method auto"""
        
        result = execute(add_cmd)
        if "successfully added" not in result:
            log_print(f"FATAL: Gagal membuat profil koneksi! Error: {result}")
            sys.exit()
        log_print("Profil berhasil dibuat.")
        execute(f"nmcli con mod '{con_name}' connection.autoconnect yes")

    # Langkah terakhir: selalu aktifkan koneksi
    log_print(f"Mengaktifkan koneksi '{con_name}'...")
    up_result = execute(f"nmcli con up '{con_name}'")
    if "Connection successfully activated" in up_result:
        log_print("Koneksi WiFi berhasil diaktifkan.")
    else:
        # Jika gagal, coba lagi. Mungkin nmcli masih sibuk.
        time.sleep(3)
        up_result_retry = execute(f"nmcli con up '{con_name}'")
        if "Connection successfully activated" in up_result_retry:
            log_print("Koneksi WiFi berhasil diaktifkan (percobaan kedua).")
        else:
            log_print(f"PERINGATAN: Gagal mengaktifkan koneksi WiFi. Mungkin sudah aktif atau sinyal lemah. Pesan: {up_result}")

# --- Main Program ---
# 1. Inisialisasi Awal
setupGPIO()
log_print("Sistem dimulai..."); time.sleep(5)
# wifi.connect(ssid, pswd)
setup_network_upsert(ssid, pswd, static_ip)

check_connection("WiFi", "nmcli con show", "wlan0")
check_connection("Server", f"ping -c 1 {host}", "1 received")
set_ip()
get_settings()

# 2. Inisialisasi Tombol
call_button = Button(btn_call)
infus_button = Button(btn_infus)
emergency_button = Button(btn_emergency)
cancel_button = Button(btn_cancel, long_press_ms=10000)

# 3. Koneksi MQTT & Linphone
client = mqtt.Client(client_id=f"bed-device-{id}")
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.connect(host, 1883, 60); client.loop_start()
setupLinphone()

log_print("--- SISTEM SIAP ---")
execute(f"gpio write {led_cancel} 0"); time.sleep(1); execute(f"gpio write {led_cancel} 1")
timer_ping = send_activation = millis()

# 4. Loop Utama
while True:
    # Periksa setiap tombol
    if call_button.check() == "short_press":
        log_print("Tombol PANGGIL ditekan.")
        execute("linphonecsh generic terminate")
        client.publish(f"call/{id}", payload="1", qos=1, retain=True)
        calling.set(); state_btn_activity = True; player.stop(); playing.clear(); x_server_call = 1

    if infus_button.check() == "short_press":
        log_print("Tombol INFUS ditekan.")
        client.publish(f"infus/{id}", payload="i", qos=1, retain=True)
        after_calling.set(); state_btn_activity = True; player.stop(); playing.clear(); x_server_infus = 1

    if emergency_button.check() == "short_press":
        log_print("Tombol EMERGENCY ditekan.")
        client.publish(f"bed/{id}", payload="e", qos=1, retain=True)
        after_calling.set(); state_btn_activity = True; player.stop(); playing.clear(); x_server_emergency = 1


    cancel_button_state = cancel_button.check()

    if cancel_button_state == "short_press":
        log_print("Tombol BATAL ditekan.")
        for topic in ["call", "stop", "infus", "bed"]:
            client.publish(f"{topic}/{id}", payload="c", qos=1, retain=True)
        after_calling.clear(); state_btn_activity = False
        x_server_call, x_server_emergency, x_server_infus = 0,0,0

    if cancel_button_state == "long_press":


        log_print("masuk sini")

        state_audio = '0' if state_audio == '1' else '1'
        log_print(f"Status Audio diubah menjadi: {'AKTIF' if state_audio == '1' else 'NONAKTIF'}")
        if state_audio == '0': player.stop()
        with open("/home/nursecall/ip-call-bed/config/audio.txt", "w") as f: f.write(state_audio)

    # Logika status panggilan & audio
    res = execute("linphonecsh status hook")
    oncall = "hook=answered" in res
    if "Incoming call" in res:
        time.sleep(1); execute("linphonecsh generic answer")
    elif oncall:
        execute(f"amixer set Capture {mic}%")
        calling.clear(); player.stop()
    
    # Kontrol Relay
    relay_on = oncall or calling.is_set() or (playing.is_set() and state_audio == '1')
    execute(f"gpio write {pin_relay} {'0' if relay_on else '1'}")

    # Umpan balik visual dan audio
    if player.is_playing() == 0 and state_audio == '1' and playing.is_set() and not oncall:
        if millis() - timer_after_activity > timeout_time_activity:
            log_print("Memutar audio stream latar belakang.")
            player.set_media(vlc.Media(f"http://{host}:8000/stream.mp3")); player.play(); time.sleep(0.5)
    if calling.is_set() and millis() - before_calling > 2000:
        execute('ogg123 /home/nursecall/ip-call-bed/ringback.ogg'); before_calling = millis()

    if x_server_infus == 0 and x_server_call == 0 and x_server_emergency == 0:
        pass
    else:
        if millis() - before_after_calling > 1000:
            execute(f"gpio write {led_cancel} 0"); time.sleep(0.2); execute(f"gpio write {led_cancel} 1")
            before_after_calling = millis()

    # if after_calling.is_set() and millis() - before_after_calling > 1000:
    #     execute(f"gpio write {led_cancel} 0"); time.sleep(0.2); execute(f"gpio write {led_cancel} 1")
    #     before_after_calling = millis()
    
    # Tugas periodik
    if reregister.is_set(): setupLinphone()
    if state_btn_activity: timer_after_activity = millis()
    if millis() - timer_ping > 120000: log_print("Ping timeout, reboot."); execute("reboot")
    if millis() - send_activation > 30000: # Kirim status aktif & update setting setiap 30 detik

        if x_server_emergency == 1:
            client.publish(f"bed/{id}", payload="e", qos=1, retain=True)
        
        if x_server_infus == 1:
            client.publish(f"infus/{id}", payload="i", qos=1, retain=True)

        if x_server_emergency == 0 and x_server_infus == 0:
            client.publish(f"bed/{id}", payload="c", qos=1, retain=True)
            client.publish(f"infus/{id}", payload="c", qos=1, retain=True)

        client.publish("aktif", payload=id, qos=0, retain=False)
        get_settings()
        send_activation = millis()

