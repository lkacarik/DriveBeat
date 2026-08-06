"""
knn_eval.py — evaluacija i kalibracija KNN odabira (nije dio simulatora).

Pokretanje:  python knn_eval.py [putanja_do_baze]

Ispisuje:
  - regresije (R^2)                -> koliko tempo predviđa energy/acousticness
  - prosjek odabira po brzini      -> raste li glazba (tempo/energy) s brzinom (monotonost)
  - raznolikost na fiksnoj brzini  -> vrti li se istih par pjesama ili ima šarolikosti
  - slaganje s K-Means klasterima  -> neovisna potvrda da KNN bira iz očekivanog raspona
                                      (samo ako su cluster oznake popunjene u bazi)

Korisno prije puštanja u simulator (sanity-check), pri ugađanju (NOISE_STD, percentili,
dodavanje pjesama), i za poglavlje evaluacije u završnom radu.
"""

import sys,os
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skripte"))

from knn_odabir import (
    KNNOdabir, KNN_FEATURES,
    SPEED_MIN, SPEED_MAX,
    TEMPO_PCT_LOW, TEMPO_PCT_HIGH,
)

DEFAULT_DB = r"D:\FOI\3. godina\ZAVRSNI\DriveBeat\glazba.db"


def regresije(knn):
    print("\nRegresije (tempo -> featur):")
    Xt = np.array([s["tempo"] for s in knn.songs]).reshape(-1, 1)
    for f, reg in knn.regressions.items():
        yt = np.array([s[f] for s in knn.songs])
        print(f"  {f:<13} = {reg.coef_[0]:+.5f} * tempo {reg.intercept_:+.3f}"
              f"   (R^2 = {reg.score(Xt, yt):.3f})")


def monotonost(knn, n=30):
    print(f"\nProsjek odabira po brzini ({n} odabira po brzini):")
    print(f"  {'brzina':>9} {'prosj.tempo':>12} {'prosj.energy':>13} {'#razl.':>8}")
    for spd in range(0, 181, 30):
        picks = [knn.pick_song(spd) for _ in range(n)]
        mt = np.mean([p["tempo"] for p in picks])
        me = np.mean([p["energy"] for p in picks])
        nd = len(set(p["id"] for p in picks))
        print(f"  {spd:>6} km/h {mt:>12.1f} {me:>13.2f} {nd:>8}")


def raznolikost(knn, brzine=(30, 90, 150), n=40):
    print(f"\nRaznolikost na fiksnoj brzini ({n} uzastopnih odabira):")
    for spd in brzine:
        picks = [knn.pick_song(spd) for _ in range(n)]
        c = Counter(p["id"] for p in picks)
        top2 = sum(broj for _, broj in c.most_common(2))
        print(f"  {spd:>3} km/h:  {len(c):>2} različitih pjesama, "
              f"prve 2 čine {top2 / n * 100:.0f}%")


def slaganje_kmeans(knn):
    """Slaganje KNN odabira sa STVARNIM K-Means klasterima iz baze.

    Za svaku brzinu uzima se ciljni vektor (bez šuma) i pridružuje najbližem
    stvarnom K-Means centroidu; gleda se pada li pjesma koju KNN stvarno odabere
    u taj isti klaster. Nema umjetnih trećina - koriste se prave grupe.

    Napomena: K-Means klasterira na 6 featura, a KNN koristi 3 (tempo, energy,
    acousticness), pa se stvarni klasteri projiciraju u taj 3-feature prostor
    (centroid = prosjek pjesama klastera u istom z-prostoru koji KNN koristi).
    """
    if not (knn.songs and all(s["cluster"] is not None for s in knn.songs)):
        print("\n(K-Means oznake nisu popunjene u bazi - preskačem metriku slaganja.)")
        return

    labels = np.array([s["cluster"] for s in knn.songs])
    X = np.array([[s[f] for f in KNN_FEATURES] for s in knn.songs], dtype=float)
    Xz = knn.scaler.transform(X)                       # isti z-prostor kao KNN
    cluster_ids = sorted(set(labels.tolist()))
    centroids = {c: Xz[labels == c].mean(axis=0) for c in cluster_ids}

    def nearest_centroid(z):
        return min(cluster_ids, key=lambda c: np.linalg.norm(z - centroids[c]))

    def nearest_song(z):                               # deterministički najbliži (bez šuma)
        _, idxs = knn.nn.kneighbors([z])
        return knn.songs[idxs[0][0]]

    agree_clean = tot_clean = 0
    agree_noisy = tot_noisy = 0
    for spd in range(0, 181, 5):
        z   = knn.target_vector(spd, noisy=False)      # ciljni vektor bez šuma
        exp = nearest_centroid(z)                      # očekivani (stvarni) klaster

        # bez šuma: deterministička najbliža pjesma (jedan odabir dovoljan)
        tot_clean += 1
        agree_clean += (nearest_song(z)["cluster"] == exp)

        # sa šumom: stvarni odabir kakav ide u simulator (20 ponavljanja)
        for _ in range(20):
            tot_noisy += 1
            agree_noisy += (knn.pick_song(spd)["cluster"] == exp)

    print("\nSlaganje sa stvarnim K-Means klasterima (0-180 km/h):")
    print(f"  bez šuma (fidelitet):       {agree_clean / tot_clean * 100:.1f}%")
    print(f"  sa šumom (stvarni odabir):  {agree_noisy / tot_noisy * 100:.1f}%"
          f"   (razlika = cijena raznolikosti)")


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    np.random.seed(0)  # reproducibilnost

    knn = KNNOdabir(db)
    print(f"Učitano {len(knn.songs)} pjesama (s file_path i featurima).")
    print(f"Brzina -> tempo:  {SPEED_MIN:.0f} km/h = {knn.tempo_lo:.1f} bpm"
          f"   ...   {SPEED_MAX:.0f} km/h = {knn.tempo_hi:.1f} bpm  "
          f"(percentili {TEMPO_PCT_LOW}./{TEMPO_PCT_HIGH}.)")

    regresije(knn)
    monotonost(knn)
    raznolikost(knn)
    slaganje_kmeans(knn)


if __name__ == "__main__":
    main()
