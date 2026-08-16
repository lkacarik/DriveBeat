import pygame, time, threading, spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from dotenv import load_dotenv

load_dotenv() #ucitava .env (SPOTIPY_CLIENT_ID/SECRET/REDIRECT_URI)

SPOTIFY_SCOPE = "user-modify-playback-state user-read-playback-state user-read-currently-playing"
#scope-ovi za modify, read playback i read current
POLL_INTERVAL = 1.5#sekunde izmedu zvanja sp.currently_playing() u pozadini

#zajednicko sucelje za playback (lokalni i spotify), zove se iz simulatora
class Playback:
    def play_song(self, song):
        raise NotImplementedError

    def set_volume(self, volume):
        raise NotImplementedError

    def fadeout(self, ms):
        raise NotImplementedError

    def is_busy(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

#lokalni playback
class LocalPygamePlayback(Playback):

    def __init__(self):
        pygame.mixer.init()

    #ucitaj i pusti pjesmu s fade in
    def play_song(self, song, fade_ms=1000):
        if not song or not song["file_path"]:
            return
        try:
            pygame.mixer.music.load(song["file_path"]) #ako dode neki problem s file pathom
            pygame.mixer.music.play(fade_ms=fade_ms)
        except Exception as e:
            print(f"[Greška pri reproduciranju]: {e}")

    def set_volume(self, volume):
        pygame.mixer.music.set_volume(volume)

    def fadeout(self, ms):
        pygame.mixer.music.fadeout(ms)

    def is_busy(self):
        return pygame.mixer.music.get_busy()

    def stop(self):
        pygame.mixer.music.stop()


#spotify playback
class SpotifyConnectPlayback(Playback):

    #Oauth pokretanje ovdje
    def __init__(self):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SPOTIFY_SCOPE))
        self.device_id = self._get_active_device()

        self._busy_lock = threading.Lock()
        self._last_busy = True #pretpostavi da svira dok prvi poll ne kaze drukcije
        self._expected_id = None #zadnji spotify_id koji je poslan
        self._last_volume_sent = None #zadnja poslana glasnoca (0-100) - da se ne zove sp.volume() svaki frame
        threading.Thread(target=self._poll_loop, daemon=True).start()

    #trazi aktivan uredaj
    def _get_active_device(self):
        devices = self.sp.devices().get("devices", [])
        active = next((d for d in devices if d["is_active"]), None)
        if not active and devices:
            active = devices[0] #nijedan aktivan - uzme prvi koji ima
        if not active:
            raise RuntimeError(
                "Nema dostupnih Spotify uređaja!")
        return active["id"]

    def _run_async(self, fn, *args, **kwargs):
        #network poziv ne smije blokirati game loop
        def wrapper():
            try:
                fn(*args, **kwargs)
            except SpotifyException as e:
                #ako je device_id zastario - osvjezi i pokusaj opet
                #da bi sprijecili onaj error kod skipanja pjesme
                if e.http_status == 404 and "device_id" in kwargs:
                    try:
                        self.device_id = self._get_active_device()
                        kwargs["device_id"] = self.device_id
                        fn(*args, **kwargs)
                    except Exception as e2:
                        print(f"[Spotify greska, ponovni pokusaj failed]: {e2}")
                else:
                    print(f"[Spotify greska]: {e}")
            except Exception as e:
                print(f"[Spotify greska]: {e}")
        threading.Thread(target=wrapper, daemon=True).start()

    #beskonacan loop
    #svakih POLL INTERVAL pita spotify koja muzika svira
    #usporeduje spotify track koji svira sa servera s expected (ono sto bi prema mojem trebalo bit)
    def _poll_loop(self):
        while True:
            try:
                current = self.sp.currently_playing()                 
                with self._busy_lock:
                    expected = self._expected_id
                if current and current.get("item") and current["item"]["id"] != expected:
                    #ako spotify jos javlja staru muziku (lag) - ignorira ovaj poll
                    pass
                else:
                    busy = bool(current and current.get("is_playing"))
                    with self._busy_lock:
                        self._last_busy = busy #azurira last busy na is playing kad se poklope ocekivana pjesma i spotifyeva
            except Exception as e:
                print(f"[Spotify greska pri provjeri statusa]: {e}")
            time.sleep(POLL_INTERVAL)

    def play_song(self, song, fade_ms=None):
        #fade_ms se ignorira - spotify nema fade (tu je zbog lokalnog)
        if not song or not song.get("spotify_id"):
            return
        uri = f"spotify:track:{song['spotify_id']}"
        with self._busy_lock:
            self._last_busy = True #odma pretpostavi busy da se ne triggera lazni kraj
            self._expected_id = song["spotify_id"]
        self._run_async(self.sp.start_playback, device_id=self.device_id, uris=[uri])

    def set_volume(self, volume):
        #salje sp.volume samo kad se ciljna glasnoca promijeni
        #(GLASNOCA_RASPON ima 12 razina pa ovo radi samo na prijelaz razine, ne svaki frame)
        vol_percent = int(round(volume * 100))
        if vol_percent == self._last_volume_sent:
            return
        self._last_volume_sent = vol_percent
        self._run_async(self.sp.volume, vol_percent, device_id=self.device_id)

    def fadeout(self, ms):
        #nema pravog fadea, isto ko stop
        self.stop()

    def is_busy(self):
        with self._busy_lock:
            return self._last_busy

    def stop(self):
        self._run_async(self.sp.pause_playback, device_id=self.device_id)