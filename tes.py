import vlc
import time

player = vlc.MediaPlayer()

while True:
    if player.is_playing() == 0:
        print("coba lagi")
        player.set_media(vlc.Media("http://192.168.0.102:8000/stream.mp3"))
        player.play()
    
    time.sleep(5)