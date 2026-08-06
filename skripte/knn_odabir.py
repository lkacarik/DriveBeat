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
                #treba zbog raznolikosti jer je KNN determinističan
K_NEIGHBORS = 5 #kolko susjeda dohvatit (preskakanje zadnje pjesme)

#tempo je sidro koje vodi brzina, a ostala dva featura se predvidaju regresijom
ANCHOR_FEATURE = "tempo"
PREDICTED_FEATURES = ["energy", "acousticness"]
KNN_FEATURES = [ANCHOR_FEATURE] + PREDICTED_FEATURES #redoslijed stupaca u prostoru

#ucitava bazu, fita scaler, regresiju i KNN jednom pa bira pjesmu po brzini
class KNNOdabir:

    def __init__(self, db_path):
        self.songs = self._load_songs(db_path)
        if not self.songs:
            raise RuntimeError(
                "Nema pjesama s file_path/featurima u bazi - KNN nema iz cega birat")

        #matrica featura [tempo, energy, acousticness]
        X = np.array([[s[f] for f in KNN_FEATURES] for s in self.songs], dtype=float)
        tempos = X[:, 0]

        #standardizacija
        self.scaler = StandardScaler().fit(X)
        Xz = self.scaler.transform(X)

        #linearne regresije: tempo - svaki predvidani feature
        self.regressions = {}
        t = tempos.reshape(-1, 1)
        for i, f in enumerate(PREDICTED_FEATURES):
            y = X[:, 1 + i]
            self.regressions[f] = LinearRegression().fit(t, y)

        #krajevi mapiranja brzina - tempo(percentili)
        self.tempo_lo = float(np.percentile(tempos, TEMPO_PCT_LOW))
        self.tempo_hi = float(np.percentile(tempos, TEMPO_PCT_HIGH))

        #KNN sa standardiziranim featurima
        n = min(K_NEIGHBORS, len(self.songs))
        self.nn = NearestNeighbors(n_neighbors=n).fit(Xz)

        #cash kerosena(simulator je treba za prekid na 180)
        self._kerosene = next(
            (s for s in self.songs if "Kerosene" in s["title"]), None)

    def _load_songs(self, db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, title, artist, tempo, energy, acousticness, file_path, cluster
            FROM songs
            WHERE file_path       IS NOT NULL
              AND tempo           IS NOT NULL
              AND energy          IS NOT NULL
              AND acousticness    IS NOT NULL
        """)
        rows = cur.fetchall()
        conn.close()
        return [
            {"id": r[0], "title": r[1], "artist": r[2], "tempo": r[3],
             "energy": r[4], "acousticness": r[5], "file_path": r[6], "cluster": r[7]}
            for r in rows
        ]

    #vraca kerosene ili none ako je nema
    def kerosene_song(self):
        return self._kerosene

    #mapiranje brzine na ciljni tempo
    def _speed_to_tempo(self, speed):
        s = max(SPEED_MIN, min(speed, SPEED_MAX))
        frac = (s - SPEED_MIN) / (SPEED_MAX - SPEED_MIN)
        return self.tempo_lo + frac * (self.tempo_hi - self.tempo_lo)

    #ciljni vektor za neku brzinu
    def target_vector(self, speed, noisy=True):
        tempo = self._speed_to_tempo(speed)
        raw = [tempo] + [
            float(self.regressions[f].predict([[tempo]])[0])
            for f in PREDICTED_FEATURES
        ]
        z = self.scaler.transform([raw])[0]
        if noisy and NOISE_STD > 0:
            z = z + np.random.normal(0.0, NOISE_STD, size=z.shape)
        return z

    #odabir pjesme najblize ciljnom vektoru i dodaje šum, preskace zadnju pjesmu
    def pick_song(self, speed, last_song_id=None):

        z = self.target_vector(speed, noisy=True)
        _, idxs = self.nn.kneighbors([z])
        for i in idxs[0]:
            song = self.songs[i]
            if song["id"] != last_song_id:
                return song
        return self.songs[idxs[0][0]] #rezerva svi susjedi == last_id (mala baza)
