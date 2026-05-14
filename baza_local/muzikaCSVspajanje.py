import sqlite3
import os

# -------------------------------------------------------
# POSTAVKE — promijeni po potrebi
# -------------------------------------------------------
DB_PATH = r"D:\FOI\3. godina\ZAVRSNI\baza_local\glazba.db"
MUZIKA_DIR = r"D:\FOI\3. godina\ZAVRSNI\muzika"
# -------------------------------------------------------

def normalize(s: str) -> str:
    """Makni razmake s rubova i pretvori u mala slova za usporedbu."""
    return s.strip().lower()

def main():
    # Učitaj sve fileove iz foldera
    files_in_dir = {}
    for fname in os.listdir(MUZIKA_DIR):
        name_no_ext, ext = os.path.splitext(fname)
        files_in_dir[normalize(name_no_ext)] = os.path.join(MUZIKA_DIR, fname)

    print(f"Pronađeno {len(files_in_dir)} fileova u folderu.\n")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id, title FROM songs")
    songs = cur.fetchall()

    matched   = []
    unmatched = []

    for song_id, title in songs:
        key = normalize(title)
        if key in files_in_dir:
            matched.append((files_in_dir[key], song_id))
        else:
            unmatched.append(title)

    # Upiši file_path u bazu
    cur.executemany(
        "UPDATE songs SET file_path = ? WHERE id = ?",
        matched
    )
    con.commit()
    con.close()

    print(f"✅ Matchano i upisano: {len(matched)} pjesama.")

    if unmatched:
        print(f"\n⚠️  Nije pronađen file za {len(unmatched)} pjesama:")
        for t in unmatched:
            print(f"   - {t}")
    else:
        print("Sve pjesme su matchane!")

if __name__ == "__main__":
    main()