import pandas as pd
import sqlite3
import os

# -------------------------------------------------------
# POSTAVKE — promijeni po potrebi
# -------------------------------------------------------
CSV_PATH = "D:\\FOI\\3. godina\\ZAVRSNI\\baza_local\\zavrsni_test_local.csv"  # putanja do Exportify CSV-a
DB_PATH = "D:\\FOI\\3. godina\\ZAVRSNI\\baza_local\\glazba.db"                # gdje će se kreirati SQLite baza
# -------------------------------------------------------

def extract_spotify_id(uri: str) -> str:
    """spotify:track:XXXXX  →  XXXXX"""
    return uri.split(":")[-1]

def main():
    # Učitaj CSV
    df = pd.read_csv(CSV_PATH)
    print(f"Učitano {len(df)} pjesama iz CSV-a.")

    # Pripremi čisti DataFrame s kolonama koje nas zanimaju
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
        "file_path":         None,   # popunit ćeš ručno / skriptom kasnije
        "cluster":           None,   # popunit će K-Means faza
    })

    # Spoji se na bazu (kreira je ako ne postoji)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Kreiraj tablicu
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

    # Umetni pjesme (preskoči duplikate po spotify_id)
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
            # spotify_id već postoji u bazi
            skipped += 1

    con.commit()
    con.close()

    print(f"Umetnutu: {inserted} pjesama.")
    if skipped:
        print(f"Preskočeno (već postoje): {skipped} pjesama.")
    print(f"Baza spremljena u: {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    main()