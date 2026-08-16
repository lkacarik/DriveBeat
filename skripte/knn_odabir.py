import sqlite3
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.neighbors import NearestNeighbors

#konstante
SPEED_MIN = 0.0 #donji kraj mapiranja brzine(tempo)
SPEED_MAX = 180.0 #gornji kraj mapiranja brzine(tempo)
TEMPO_PCT_LOW  = 5 #percentil tempa vezan sa SPEED_MIN(izbjegava outliere)
TEMPO_PCT_HIGH = 95 #percentil tempa vezan sa SPEED_MAX
NOISE_STD = 0.4 #standardna devijacija gaussovog suma na ciljni vektor (u z-prostoru)
                #treba zbog raznolikosti jer je KNN deterministican pa ce pustat istu pjesmu uvijek
K_NEIGHBORS = 5 #kolko susjeda dohvatit (preskakanje zadnje pjesme)

#tempo je sidro koje vodi brzina, a ostala dva featura se predvidaju regresijom
ANCHOR_FEATURE = "tempo"
PREDICTED_FEATURES = ["energy", "acousticness"]
KNN_FEATURES = [ANCHOR_FEATURE] + PREDICTED_FEATURES #redoslijed stupaca u prostoru

class KNNOdabir:

    #gradi matricu svih pjesama
    def __init__(self, db_path):
        self.songs = self._load_songs(db_path)
        if not self.songs:
            raise RuntimeError(
                "Nema pjesama sa spotify_id/featurima u bazi - KNN nema iz cega birat!")

        #matrica featura [tempo, energy, acousticness]
        X = np.array([[s[f] for f in KNN_FEATURES] for s in self.songs], dtype=float)
        tempos = X[:, 0]

        #standardizacija na sve 3 kolone odjednom, svaka kolona dobiva svoj prosjek/varijancu
        #ovaj isti scaler se kasnije koristi za ciljni vektor tak da su u istom z-prostoru
        self.scaler = StandardScaler().fit(X)
        Xz = self.scaler.transform(X)

        #dvije linearne regresije, jedna za energy i jedna za acousticness iz nestandardiziranog tempa
        #i=0 je energy, i=1 je acousticness
        self.regressions = {}
        t = tempos.reshape(-1, 1)
        for i, f in enumerate(PREDICTED_FEATURES):
            y = X[:, 1 + i]
            self.regressions[f] = LinearRegression().fit(t, y)

        #krajevi mapiranja brzina - tempo(percentili)
        self.tempo_lo = float(np.percentile(tempos, TEMPO_PCT_LOW))
        self.tempo_hi = float(np.percentile(tempos, TEMPO_PCT_HIGH))

        #zastita ak ubacim manje od 5 pjesama iz nekog razloga
        #trazi se onoliko susjeda koliko ima pjesama da ne bi dosla greska jer ne moze nac 5 susjeda
        n = min(K_NEIGHBORS, len(self.songs))
        self.nn = NearestNeighbors(n_neighbors=n).fit(Xz)

    #ucitavanje pjesama
    def _load_songs(self, db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, title, artist, tempo, energy, acousticness, file_path, cluster, spotify_id
            FROM songs
            WHERE spotify_id      IS NOT NULL
              AND tempo           IS NOT NULL
              AND energy          IS NOT NULL
              AND acousticness    IS NOT NULL
        """) #ovi NOT NULL su tu da me exportify ne zezne pa mi opet da pjesmu bez nekog featura
        rows = cur.fetchall()
        conn.close()
        return [
            {"id": r[0], "title": r[1], "artist": r[2], "tempo": r[3],
             "energy": r[4], "acousticness": r[5], "file_path": r[6], "cluster": r[7],
             "spotify_id": r[8]}
            for r in rows
        ]

    #pretvaranje brzine od 0-180 u postotak
    def _speed_to_tempo(self, speed):
        s = max(SPEED_MIN, min(speed, SPEED_MAX))
        frac = (s - SPEED_MIN) / (SPEED_MAX - SPEED_MIN)
        return self.tempo_lo + frac * (self.tempo_hi - self.tempo_lo)

    #ciljni vektor za neku brzinu
    def target_vector(self, speed, noisy=True): #ovaj noisy je da se moze vidjet bez suma za eval
        tempo = self._speed_to_tempo(speed)
        raw = [tempo] + [
            float(self.regressions[f].predict([[tempo]])[0])
            for f in PREDICTED_FEATURES
        ]
        z = self.scaler.transform([raw])[0]
        if noisy and NOISE_STD > 0:
            z = z + np.random.normal(0.0, NOISE_STD, size=z.shape)
        return z

    #trazi 5 najblizih susjeda ciljnom vektoru i sortira ih po udaljenosti (koji je najbolji)
    #vraca prvu onu koja nije ista zadnjoj koja je svirala
    def pick_song(self, speed, last_song_id=None):

        z = self.target_vector(speed, noisy=True)
        _, idxs = self.nn.kneighbors([z])
        for i in idxs[0]:
            song = self.songs[i]
            if song["id"] != last_song_id:
                return song
        return self.songs[idxs[0][0]] #ako iz nekog razloga baza ima samo jednu pjesmu za svaki slucaj nek bude