# DriveBeat

Sustav koji čita brzinu vozila u realnom vremenu i automatski odabire glazbu odgovarajućeg tempa i energije. Što brža vožnja - energičnija glazba, što sporija - mirnija glazba. 

Završni rad — FOI Varaždin, 2026.

---

## Kako radi

Brzina vozila (OBD2 adapter) mapira se na audio feature Spotify pjesami. K-Means algoritam grupira pjesme u klastere prema tempu, energiji i ostalim karakteristikama. KNN u realnom vremenu odabire najprikladniju pjesmu za trenutnu brzinu vožnje.

---

## Faze razvoja

- **Faza 1**  — pygame simulator s K-Means klasteriranjem i lokalnim audio fajlovima - GOTOVO
- **Faza 2** — KNN odabiro pjesme + Spotify integracija
- **Faza 3** — OBD citanje brzine iz pravog auta, RPM kao dodatni ulaz uz brzinu, BPM matching pri tranziciji i dodatno po potrebi

---

## Tehnologije

- Python, pygame, SQLite
- Spotipy (Spotify Web API)
- python-obd (OBD2 adapter)

---

## Struktura projekta

```
baza_local/
├── csvSQLite.py          # puni SQLite bazu iz Exportify CSV-a
├── muzikaCSVspajanje.py  # upisuje putanje lokalnih audio fileova u bazu
├── kmeans_klaster.py     # K-Means klasteriranje, upisuje cluster u bazu
├── kmeans_klaster.ipynb  # isti kod + Elbow graf i Silhouette Score analiza za testiranje
└── zavrsni_test_local.csv

simulator_simple_road/
├── simulator.py          # pygame simulator vožnje
└── simple_road.py  	  # originalna py datoteka simple road
```

---

## Pokretanje

### 1. Instalacija dependencies
```bash
pip install pygame scikit-learn pandas python-obd spotipy
```

### 2. Priprema lokalne baze

> **Napomena:** prije pokretanja skripti potrebno je iz odabrane spotify playliste exportati CSV datoteku pomoću [Exportify](https://exportify.net). CSV datoteka mora biti u istom direktorija kao i py skripte te se svi audio fajlovi moraju rucno skinuti.

```bash
python baza_local/csvSQLite.py
python baza_local/muzikaCSVspajanje.py
python baza_local/kmeans_klaster.py
```

### 3. Pokretanje simulatora
```bash
python simulator_simple_road/simulator.py
```

> **Napomena:** prije pokretanja provjeriti `DB_PATH` u svakoj skripti i postaviti na lokaciju kreirane baze `glazba.db`. Također provjeriti `CLUSTER_MAP` u `simulator.py` nakon svakog ponovnog klasteriranja jer se redoslijed klastera može promijeniti prilikom novog pokretanja.

---
