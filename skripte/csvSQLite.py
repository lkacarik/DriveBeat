import pandas as pd
import sqlite3
import os

CSV_DIR = "D:\\FOI\\3. godina\\ZAVRSNI\\DriveBeat\\exportify" #folder di se stavlja csv
DB_PATH = "D:\\FOI\\3. godina\\ZAVRSNI\\DriveBeat\\glazba.db" #gdje se radi SQLite baza

#trazenje csv-a, greske ako ga nema ili ako je vise od jednog
def pronadi_csv(folder):
    csv_fajlovi = [f for f in os.listdir(folder) if f.lower().endswith(".csv")]
    if not csv_fajlovi:
        raise FileNotFoundError(f"Nema CSV fajla u exportify folderu!")
    if len(csv_fajlovi) > 1:
        raise RuntimeError(
            f"Postoji vise csv fajlova u exportify folderu!")
    return os.path.join(folder, csv_fajlovi[0])

#izvlacenje spotify id iz exporitfy csv-a, razbijanje stringa po :
def extract_spotify_id(uri: str) -> str:
    """spotify:track:XXXXX  →  XXXXX"""
    return uri.split(":")[-1]

def main():
    #citanje csv
    df = pd.read_csv(pronadi_csv(CSV_DIR))
    print(f"Ucitano {len(df)} pjesama iz CSV-a.")

    #novi dataframe songs, pretvara se u bolja imena [ista shema ko baza]
    songs = pd.DataFrame({
        "spotify_id":        df["Track URI"].apply(extract_spotify_id),
        "title":             df["Track Name"],
        "artist":            df["Artist Name(s)"],
        "tempo":             df["Tempo"],
        "energy":            df["Energy"],
        "valence":           df["Valence"],
        "danceability":      df["Danceability"],
        "acousticness":      df["Acousticness"],
        "instrumentalness":  df["Instrumentalness"],
        "file_path":         None, #popunit ce se sa muzikaCSVspajanje
        "cluster":           None, #popunit ce se sa kmeans_klaster
    })

    #spajanje na bazu
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    #kreiranje tablice ak ne postoji
    cur.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            spotify_id       TEXT UNIQUE,
            title            TEXT,
            artist           TEXT,
            tempo            REAL,
            energy           REAL,
            valence          REAL,
            danceability     REAL,
            acousticness     REAL,
            instrumentalness REAL,
            file_path        TEXT,
            cluster          INTEGER
        )
    """)
    con.commit()

    #brisanje pjesama kojih nema u CSV
    csv_ids = set(songs["spotify_id"])
    cur.execute("SELECT spotify_id FROM songs")
    db_ids = {row[0] for row in cur.fetchall()}

    to_delete = db_ids - csv_ids
    if to_delete:
        cur.executemany(
            "DELETE FROM songs WHERE spotify_id = ?",
            [(sid,) for sid in to_delete]
        )
        con.commit()
        print(f"Obrisano {len(to_delete)} pjesama (vise nisu u playlisti).")

    #ubacivanje pjesama (ili preskakanje ak su vec tu)
    inserted = 0
    skipped  = 0
    for _, row in songs.iterrows():
        try:
            cur.execute("""
                INSERT INTO songs
                    (spotify_id, title, artist, tempo, energy, valence,
                     danceability, acousticness, instrumentalness, file_path, cluster)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["spotify_id"], row["title"], row["artist"],
                row["tempo"], row["energy"], row["valence"],
                row["danceability"], row["acousticness"], row["instrumentalness"],
                row["file_path"], row["cluster"]
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    con.commit()
    con.close()

    print(f"Insertano je: {inserted} pjesama.")
    if skipped:
        print(f"Skipano je: {skipped} pjesama.")
    print(f"Baza je spremljena u: {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    main()