import obd
import threading
import time

POLL_INTERVAL   = 0.2 #sekundi izmedu ocitanja
CONNECT_RETRIES = 5 #kolko puta pokusat spajanje prije odustajanja
CONNECT_RETRY_DELAY = 2.0 #sekunde izmedu pokusaja spajanja

#limit za izgladivanje OBD citanja
MAX_SPEED_RATE = 25.0  #najveca dopustena promjena vracene brzine po sekundi

class OBDReader:
    def __init__(self, port):
        self._lock = threading.Lock()
        self._raw_speed = 0.0  #zadnje sirovo OBD ocitanje (moze skocit odjednom svakih POLL_INTERVAL)
        self._smoothed_speed = 0.0  #vrijednost koju vraca get_speed(), pomice se prema raw
        self._last_get_time = None  #za racunanje dt izmedju poziva get_speed()

        #retry spajanja, adapter nekad nece iz prve iz nekog razloga
        self._connection = None
        for pokusaj in range(1, CONNECT_RETRIES + 1):
            print(f"Spajam se na OBD adapter ({port}), pokusaj {pokusaj}/{CONNECT_RETRIES}...")
            self._connection = obd.OBD(port)
            if self._connection.is_connected():
                break
            time.sleep(CONNECT_RETRY_DELAY)

        if not self._connection or not self._connection.is_connected():
            raise RuntimeError(
                f"Nije se uspjelo spojiti na OBD adapter na portu {port} nakon "
                f"{CONNECT_RETRIES} pokusaja."
            )

        #pokretanje threada
        self._running = True
        self._thread  = threading.Thread(target=self._poll_loop, daemon=True)
        #daemon automatski gasi thread kad se program zavrsi
        self._thread.start()

    #petlja za speed
    def _poll_loop(self):
        while self._running:
            try:
                response = self._connection.query(obd.commands.SPEED)
                if response and not response.is_null():
                    with self._lock:
                        self._raw_speed = response.value.magnitude
            except Exception:
                pass  # mrezna/serial greska ne smije srusiti simulator, samo se preskace ocitanje

            threading.Event().wait(POLL_INTERVAL)

    #smoothing za brzinu
    #bez ovog bi brzina skakala i ne bi isla glatko
    def get_speed(self):
        now = time.monotonic()
        with self._lock:
            raw = self._raw_speed

        if self._last_get_time is None:
            dt = 0.0
        else:
            dt = now - self._last_get_time
        self._last_get_time = now

        max_delta = MAX_SPEED_RATE * dt
        diff = raw - self._smoothed_speed
        if abs(diff) <= max_delta or max_delta <= 0:
            self._smoothed_speed = raw
        else:
            self._smoothed_speed += max_delta if diff > 0 else -max_delta

        return self._smoothed_speed

    #poziva se u simulatoru da se zaustavi
    def stop(self):
        self._running = False
        self._connection.close()