import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "baza_local"))
import csvSQLite
import muzikaCSVspajanje
import kmeans_klaster

#lokalni playback, kad rijseim spotify onda ide FALSE da se preskoci
SPOJI_LOKALNE_FILEOVE = True


def korak(broj, naziv, funkcija):
    print("\n" + "=" * 60)
    print(f"  KORAK {broj}: {naziv}")
    print("=" * 60)
    funkcija()


def main():
    print("### Ažuriranje baze pokrenuto ###")

    korak(1, "CSV -> SQLite (csvSQLite)", csvSQLite.main)

    if SPOJI_LOKALNE_FILEOVE:
        korak(2, "Spajanje lokalnih fileova (muzikaCSVspajanje)", muzikaCSVspajanje.main)
    else:
        print("\n(Korak 2 preskočen - SPOJI_LOKALNE_FILEOVE = False)")

    korak(3, "K-Means klasteriranje (kmeans_klaster)", kmeans_klaster.main)

    print("\n" + "=" * 60)
    print("  Baza ažurirana.")
    print("=" * 60)


if __name__ == "__main__":
    main()
