import sys
import csvSQLite
import muzikaCSVspajanje
import kmeans_klaster

#koraci za updejt baze, u formatu broj koraka, naziv koraka, funkcija + okvir sa =
def korak(broj, naziv, funkcija):
    print("\n" + "=" * 60)
    print(f"  KORAK {broj}: {naziv}")
    print("=" * 60)
    try:
        funkcija()
    except Exception as e:
        print(f"\nGreska: {e}")
        sys.exit(1)

#prolazak kroz sve one manje skripte za updejt baze
def main():
    print("### Ažuriranje baze pokrenuto ###")

    korak(1, "Upisivanje CSV podataka u bazu", csvSQLite.main)
    korak(2, "Spajanje lokalnih fileova", muzikaCSVspajanje.main)
    korak(3, "K-Means klasteriranje", kmeans_klaster.main)

    print("\n" + "=" * 60)
    print("  Baza azurirana.")
    print("=" * 60)


if __name__ == "__main__":
    main()