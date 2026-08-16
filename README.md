# DriveBeat

Sustav koji u stvarnom vremenu čita brzinu vozila i automatski odabire te pušta glazbu odgovarajućeg tempa i energije — što brža vožnja, energičnija glazba, što sporija vožnja, mirnija glazba.

---

## Kako radi

1. **Brzina** dolazi s tipkovnice (simulator, za testiranje) ili iz pravog auta preko USB OBD adaptera
2. **KNN model** na temelju brzine bira pjesmu čiji su audio featuri najbliži ciljanom profilu za tu brzinu
3. **Reprodukcija** ide preko Spotify Connect API-ja ili preko lokalnih audio fajlova
4. **K-Means klasteriranje** služi kao neovisna evaluacija — provjerava slaže li se KNN odabir sa stvarnim klasterima pjesama

---

## Tech stack

| Komponenta | Tehnologija |
|---|---|
| Jezik | Python |
| Strojno učenje | (KNN, K-Means) |
| Reprodukcija | pygame (lokalno) / Spotipy (Spotify Connect) |
| Očitanje brzine | python-obd (USB OBD2 adapter) |
| Baza podataka | SQLite |
| Audio featuri | Exportify (offline export, zbog gašenja Spotify Audio Features endpointa) |

---

## Struktura projekta

```
DriveBeat/
├── DriveBeat.py               # launcher - ASCII izbornik, pokrece sve ostalo
├── skripte/
│   ├── azuriraj_bazu.py       # orkestracija - puni bazu iz Exportify CSV-a i klasterira
│   ├── csvSQLite.py           # prebacuje podatke iz Exportify CSV-a u SQLite bazu
│   ├── muzikaCSVspajanje.py   # spaja pjesme s lokalnim audio fajlovima
│   ├── kmeans_klaster.py      # K-Means klasteriranje
│   ├── knn_odabir.py          # KNN odabir pjesme
│   ├── playback.py            # reprodukcija (lokalno/Spotify)
│   └── obd_reader.py          # citanje brzine s OBD adaptera
├── simulator/
│   └── simulator.py           # pygame simulator + prava voznja (OBD)
├── muzika/                    # folder za lokalne audio fajlove
├── exportify/                 # folder za Exportify CSV
```

---

## Pokretanje

### 1. Instalacija ovisnosti (ako treba)
```bash
pip install pygame
pip install scikit-learn
pip install pandas
pip install spotipy
pip install python-dotenv
pip install python-obd
```

### 2. Priprema baze pjesama
1. Složi Spotify playlistu
2. Exportaj CSV preko [Exportify](https://exportify.net), spremi u `exportify/`
3. Za lokalni playback dodaj odgovarajuće `.wma` fajlove u `muzika/`
4. Pokreni `DriveBeat.py` → opcija **1. Ažuriraj bazu**

### 3. Spotify Developer App (ako se koristi Spotify Connect playback)
Registriraj app na [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard), zatim u root folderu kreiraj `.env`:
```
SPOTIPY_CLIENT_ID=...
SPOTIPY_CLIENT_SECRET=...
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```
> Redirect URI mora koristiti `127.0.0.1`. Račun mora imati aktivan Premium.

### 4. Pokretanje
```bash
python DriveBeat.py
```
Izbornik nudi simulator (tipkovnica) ili voznju (OBD, port se postavlja preko `OBD_PORT` u `simulator.py`)
