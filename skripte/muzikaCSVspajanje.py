import sqlite3
import os

DB_PATH = r"D:\FOI\3. godina\ZAVRSNI\DriveBeat\glazba.db"
MUZIKA_DIR = r"D:\FOI\3. godina\ZAVRSNI\DriveBeat\muzika"

def normalize(s: str) -> str:
    #makni razmake s rubova i pretvori u mala slova za usporedbu
    #da ne bi bilo razlike izmedu naziva samog fajla pjesme i pjesme
    return s.strip().lower()

def main():
    #ucitavanje pjesama iz foldera
    #odvoji se ime i .wma i normalizira ime
    files_in_dir = {}
    for fname in os.listdir(MUZIKA_DIR):
        name_no_ext, ext = os.path.splitext(fname)
        #rijecnik s popisom pjesama u folderu
        files_in_dir[normalize(name_no_ext)] = os.path.join(MUZIKA_DIR, fname)

    print(f"Pronadeno je: {len(files_in_dir)} fajlova u folderu.\n")

    #dohvaca id i title
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id, title FROM songs")
    songs = cur.fetchall()

    matched   = []
    unmatched = []

    #provjerava je li pjesma iz baze stvarno u folderu 
    #ako je, tuple (putanja i id) ide u listu
    for song_id, title in songs:
        key = normalize(title)
        if key in files_in_dir:
            matched.append((files_in_dir[key], song_id))
        else:
            unmatched.append((song_id, title))
            #tu cuvam i id da se moze brisat file path kasnije

    #upisivanje file_path u bazu
    cur.executemany(
        "UPDATE songs SET file_path = ? WHERE id = ?",
        matched
    )
    #stavlja se file path na NULL za unmatchane fajlove
    cur.executemany(
        "UPDATE songs SET file_path = NULL WHERE id = ?",
        [(song_id,) for song_id, _ in unmatched]
    )
    con.commit()
    con.close()

    print(f"Matchano i upisano: {len(matched)} pjesama.")

    if unmatched:
        print(f"\nNije pronaden fajl za {len(unmatched)} pjesama:")
        for _, t in unmatched: #dodo sam _, jer sa ima i tuple sa id i title zbog brisanja na NULL
            print(f"   - {t}")
    else:
        print("Sve pjesme su spojene!")

if __name__ == "__main__":
    main()