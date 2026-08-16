import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SIMULATOR_PATH = os.path.join(BASE_DIR, "simulator", "simulator.py")

_BANNER_LINES = [
    "########  ########  #### ##     ## ######## ########  ########    ###    ########",
    "##     ## ##     ##  ##  ##     ## ##       ##     ## ##         ## ##      ##   ",
    "##     ## ##     ##  ##  ##     ## ##       ##     ## ##        ##   ##     ##   ",
    "##     ## ########   ##  ##     ## ######   ########  ######   ##     ##    ##   ",
    "##     ## ##   ##    ##   ##   ##  ##       ##     ## ##       #########    ##   ",
    "##     ## ##    ##   ##    ## ##   ##       ##     ## ##       ##     ##    ##   ",
    "########  ##     ## ####    ###    ######## ########  ######## ##     ##    ##   ",
]
_BANNER_WIDTH = max(len(l) for l in _BANNER_LINES)
_BANNER_BORDER = "+" + "-" * (_BANNER_WIDTH + 2) + "+"
BANNER = "\n".join(
    [_BANNER_BORDER]
    + [f"| {l.ljust(_BANNER_WIDTH)} |" for l in _BANNER_LINES]
    + [_BANNER_BORDER]
)

#rijecnik sa 3 argumenta, treci argument je lista zbog playbacka i simulatora/OBD
SKRIPTE = {
    "1": ("Azuriraj bazu",                    os.path.join(BASE_DIR, "skripte", "azuriraj_bazu.py"), []),
    "2": ("Pokreni simulator (Spotify)",      SIMULATOR_PATH, ["sim", "spotify"]),
    "3": ("Pokreni simulator (lokalno)",      SIMULATOR_PATH, ["sim", "local"]),
    "4": ("Pokreni voznju - OBD (Spotify)",   SIMULATOR_PATH, ["obd", "spotify"]),
    "5": ("Pokreni voznju - OBD (lokalno)",   SIMULATOR_PATH, ["obd", "local"]),
}

UPUTE = """
============================================
  UPUTE - dodavanje/azuriranje muzike
============================================

1. SLOZI PLAYLISTU NA SPOTIFY
   Dodaj/makni pjesme na Spotify playlisti.

2. EXPORTAJ PREKO EXPORTIFY
   Idi na https://exportify.net, prijavi se svojim Spotify
   racunom, odaberi playlistu i klikni Export. Skida se .csv
   fajl sa svim audio featurima (tempo, energy, itd.).

3. SPREMI CSV NA ISPRAVNO MJESTO
   Spremi skinuti CSV u mapu "exportify", u mapi smije 
   postojat samo jedna CSV datoteka.

4. (SAMO ZA LOKALNI PLAYBACK) DODAJ .wma FILEOVE
   Ako se koristi lokalni pygame playback, nove pjesme
   moraju imati i lokalni audio fajl u folderu "muzika".
   Za Spotify playback ovo nije potrebno.

5. POKRENI "Azuriraj bazu" (opcija 1)
   Ako je neka pjesma obrisana iz spotify playliste i baza
   se azurira - ta pjesma se automatski brise iz baze.

6. ODABERI NACIN POKRETANJA (opcije 2-5)
   Simulator -> tipkovnica, testni prikaz s cestom.
   Voznja -> ocitava pravu brzinu preko OBD2 adaptera.
   Spotify/lokalno -> odabire izvor reprodukcije.

   SIMULATOR - Strelica gore -> gas
   SIMULATOR - Strelica dolje - >kocnica
   SIMULATOR - SPACE -> tempomat
   VOZNJA - brzina dolazi direktno iz auta

============================================
"""


def prikazi_meni():
    print(BANNER)
    print("=" * 38)
    for kljuc, (naziv, _, _) in SKRIPTE.items():
        print(f"  {kljuc}. {naziv}")
    print("  6. Upute")
    print("  0. Izlaz")
    print("=" * 38)

#provjera jel postoji fajl
def pokreni_skriptu(putanja, argumenti=None):
    if not os.path.exists(putanja):
        print(f"\nGreska: fajl ne postoji - {putanja}")
        return
    komanda = [sys.executable, putanja] + (argumenti or [])
    subprocess.run(komanda)


def main():
    while True:
        prikazi_meni()
        izbor = input("Odabir: ").strip()

        if izbor == "0":
            #print()
            break
        elif izbor == "6":
            print(UPUTE)
            input("Pritisni ENTER za povratak na izbornik...")
        elif izbor in SKRIPTE:
            _, putanja, argumenti = SKRIPTE[izbor]
            pokreni_skriptu(putanja, argumenti)
        else:
            print("Nepoznata opcija.")


if __name__ == "__main__":
    main()