import pygame,sys,os,math  #[MODIFICIRANO] dodani os, math
import sqlite3, random #[NOVO]
from pygame.locals import *
import obd                    #[NOVO]
#connection = obd.OBD("COM3")  #spajanje prek COM3 porta (trenutno golf)

#[ORIGINAL] - boje
BLACK=pygame.color.THECOLORS["black"]
WHITE=pygame.color.THECOLORS["white"]
RED=pygame.color.THECOLORS["red"]
GREEN=pygame.color.THECOLORS["green"]
BLUE=pygame.color.THECOLORS["blue"]
YELLOW=pygame.color.THECOLORS["yellow"]
SCREEN_WIDTH=640
SCREEN_HEIGHT=480
HALF_SCREEN_HEIGHT=int(SCREEN_HEIGHT/2)

#[NOVO] - putanje za bazu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = r"D:\FOI\3. godina\ZAVRSNI\DriveBeat\glazba.db"

#[NOVO] - brzinski pragovi za odabir klastera (privremeno, zamijenit ce KNN)
SPEED_SLOW = 60   #km/h ispod ovoga - spori klaster
SPEED_FAST = 120   #km/h iznad ovoga - brzi klaster
                  #između - srednji klaster

#[NOVO] - smoothing tj. kolko sekundi brzina mora bit u novom klasteru prije promjene pjesme
CLUSTER_CHANGE_DELAY = 4.0  # sekundi

#[NOVO] - fade trajanje u ms
FADE_MS = 1000

#[NOVO] - kerosene granica
KEROSENE = 170

#[NOVO] - limit kocenja za stisavanje muzike (u km/h po sekundi)
KOCENJE_TIHO = 10

#[NOVO] - mapiranje naziva klastera na cluster ID iz baze - nije svaki put isto nekad je naopacke (2 je brzo, a 0 sporo) !!!!!!!!!!
CLUSTER_MAP = {
    "slow": 2,   # klaster s najnizim tempom
    "mid":  1,   # klaster s srednjim tempom
    "fast": 0,   # klaster s najvišim tempom
}

#[NOVO] - glazbene funkcije
def load_songs(db_path):
    #Učitaj sve pjesme iz baze u memoriju.
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    cur.execute("SELECT id, title, artist, tempo, cluster, file_path FROM songs WHERE file_path IS NOT NULL AND cluster IS NOT NULL")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "artist": r[2], "tempo": r[3], "cluster": r[4], "file_path": r[5]} for r in rows]

def get_cluster(speed):
    #Vrati naziv klastera na temelju brzine.
    if speed < SPEED_SLOW:
        return "slow"
    elif speed < SPEED_FAST:
        return "mid"
    else:
        return "fast"

def pick_song(songs, cluster, last_id=None):
    #Odaberi random pjesmu iz odgovarajućeg klastera, ne ponavljaj istu.
    cluster_id = CLUSTER_MAP[cluster]
    pool = [s for s in songs if s["cluster"] == cluster_id]

    if last_id and len(pool) > 1:
        pool = [s for s in pool if s["id"] != last_id]

    return random.choice(pool) if pool else None

def play_song(song):
    #Učitaj i pusti pjesmu s fade in.
    if not song or not song["file_path"]:
        return
    try:
        pygame.mixer.music.load(song["file_path"])
        pygame.mixer.music.play(fade_ms=FADE_MS)  #[MODIFICIRANO] dodan fade in
    except Exception as e:
        print(f"[Greška pri reproduciranju]: {e}")


#[MODIFICIRANO] - main je djelomicno modificiran i neke stvari su dodane
def main():

    pygame.init()
    pygame.mixer.init() #[NOVO] - mixer potreban za muziku

    #[ORIGINAL] Open Pygame window
    screen = pygame.display.set_mode((640, 480),)
    pygame.display.set_caption("simulator")
    font       = pygame.font.SysFont('Arial', 30)
    small_font = pygame.font.SysFont('Arial', 14) #[NOVO] izvuceno iz loopa

    #[MODIFICIRANO] images — os.path umjesto relative stringa (relativne putanje) jer iz nekog razloga nije moglo nac png-ove
    light_road = pygame.image.load(os.path.join(BASE_DIR, 'light_road.png')).convert()
    dark_road  = pygame.image.load(os.path.join(BASE_DIR, 'dark_road.png')).convert()

    #[NOVO] - glazba
    songs           = load_songs(DB_PATH)
    current_song    = None
    last_song_id    = None
    current_cluster = None
    was_paused      = False  #prati je li glazba pauzirana zbog v=0 (brzina 0)

    #[NOVO] - fade i smoothing stanje
    pending_song         = None   #pjesma koja čeka da fadeout završi
    fading_out           = False  #je li trenutno u tijeku fadeout
    candidate_cluster    = None   #klaster koji čeka potvrdu (smoothing)
    cluster_change_timer = 0.0    #koliko dugo smo u candidate_clusteru

    #[NOVO] - speedometar varijable
    speed     = 0.0
    max_speed = 180.0
    accel     = 10.0   # km/h po sekundi
    brake     = 18.0   # km/h po sekundi
    friction  = 3.0    # km/h po sekundi
    clock     = pygame.time.Clock()

    #[ORIGINAL] variables
    texture_position            = 0
    ddz                         = 0.001
    dz                          = 0
    z                           = 0
    road_pos                    = 0
    road_acceleration           = 80
    texture_position_acceleration = 4
    texture_position_threshold  = 300
    half_texture_position_threshold = int(texture_position_threshold / 2)

    #[NOVO] - pusti prvu pjesmu (spori klaster, vozilo stoji na pocetku)
    current_cluster = get_cluster(speed)
    if speed >= KEROSENE: #provjera za kerosene
        current_song = next((s for s in songs if "Kerosene" in s["title"]), None)
    else:
        current_song = pick_song(songs, current_cluster)

    if current_song:
        play_song(current_song)
        last_song_id = current_song["id"]

    #[MODIFICIRANO] - Game loop
    prev_speed = 0.0#pracenje przine za naglo kocenje i stisavanje muzike
    while True:

        dt = clock.tick(30) / 1000.0  #[MODIFICIRANO] pohranjen u var (orig: nije korišten)

        #[ORIGINAL]
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        #[MODIFICIRANO] - movement controls - dodano DOWN, fizika brzine s delta timeom
        keys = pygame.key.get_pressed()
        if keys[K_UP]:
            speed    = min(speed + accel * dt, max_speed)
            road_pos += road_acceleration * (speed / max_speed)
            if road_pos >= texture_position_threshold:
                road_pos = 0
        elif keys[K_DOWN]:
            speed = max(speed - brake * dt, 0)
        else:
            speed = max(speed - friction * dt, 0)
            if speed > 0:
                road_pos += road_acceleration * (speed / max_speed)
                if road_pos >= texture_position_threshold:
                    road_pos = 0
        
        #speed = connection.query(obd.commands.SPEED).value.magnitude

        #naglo kocenje - stisavanje muzike
        deceleration = (prev_speed - speed) / dt if dt > 0 else 0
        if deceleration > KOCENJE_TIHO:  # km/h po sekundi
            pygame.mixer.music.set_volume(0.1)

        prev_speed = speed

        #glasnoca ovisno o brzini (ispod 50 km/h - fade in jacina)
        if speed < 50:
            volume = speed / 50.0
        else:
            volume = 1.0
        pygame.mixer.music.set_volume(volume)            

        #[NOVO] - logika glazbe
        #kerosene triger da se odma pusti
        if speed >= KEROSENE and current_song and "Kerosene" not in current_song["title"]:
            pending_song = next((s for s in songs if "Kerosene" in s["title"]), None)
            fading_out = True
            pygame.mixer.music.fadeout(FADE_MS)
        
        if speed < 1:
            #edge case: vozilo stoji - pauziraj s fadeoutom
            if not was_paused:
                pygame.mixer.music.fadeout(FADE_MS)
                was_paused           = True
                fading_out           = False  #nije promjena pjesme, samo pauza
                pending_song         = None
                candidate_cluster    = None
                cluster_change_timer = 0.0
        else:
            #nastavi reprodukciju ako smo bili pauzirani
            if was_paused:
                was_paused      = False
                current_cluster = get_cluster(speed)
                if speed >= KEROSENE:#provjera za kerosene
                    current_song = next((s for s in songs if "Kerosene" in s["title"]), None)
                else:
                    current_song    = pick_song(songs, current_cluster, last_song_id)
                
                if current_song:
                    play_song(current_song)
                    last_song_id = current_song["id"]

            #[NOVO] - smoothing: provjeri novi klaster, ali ne mijenjaj odmah
            if not fading_out:
                new_cluster = get_cluster(speed)

                if new_cluster != current_cluster:
                    #brzina je u drugom klasteru - počni mjeriti
                    if new_cluster == candidate_cluster:
                        cluster_change_timer += dt
                    else:
                        #novi kandidat, resetiraj timer
                        candidate_cluster    = new_cluster
                        cluster_change_timer = 0.0
                else:
                    #vratili smo se u trenutni klaster - odustani od promjene
                    candidate_cluster    = None
                    cluster_change_timer = 0.0

                #potvrdi promjenu tek nakon CLUSTER_CHANGE_DELAY sekundi
                if candidate_cluster and cluster_change_timer >= CLUSTER_CHANGE_DELAY:
                    if speed >= KEROSENE:#provjera za kerosene
                        pending_song = next((s for s in songs if "Kerosene" in s["title"]), None)
                    else:
                        pending_song         = pick_song(songs, candidate_cluster, last_song_id)
                    current_cluster      = candidate_cluster
                    candidate_cluster    = None
                    cluster_change_timer = 0.0
                    fading_out           = True
                    pygame.mixer.music.fadeout(FADE_MS)

            #[NOVO] - fadeout završio, pokreni pending pjesmu
            if fading_out and not pygame.mixer.music.get_busy():
                fading_out = False
                if pending_song:
                    play_song(pending_song)
                    current_song = pending_song
                    last_song_id = current_song["id"]
                    pending_song = None

            #pjesma završila prirodno - pusti sljedeću iz istog klastera s fade in
            if not fading_out and not was_paused and not pygame.mixer.music.get_busy():
                if speed >= KEROSENE:
                    current_song = next((s for s in songs if "Kerosene" in s["title"]), None)
                else:
                    current_song = pick_song(songs, current_cluster, last_song_id)
                
                if current_song:
                    play_song(current_song)
                    last_song_id = current_song["id"]

        #[ORIGINAL] draw the road
        texture_position = road_pos
        dz = 0
        z  = 0
        screen.fill(BLUE)
        for i in range(HALF_SCREEN_HEIGHT-1, -1, -1):
            if texture_position < half_texture_position_threshold:
                screen.blit(light_road, (0, i+HALF_SCREEN_HEIGHT), (0, i, SCREEN_WIDTH, 1))
            else:
                screen.blit(dark_road,  (0, i+HALF_SCREEN_HEIGHT), (0, i, SCREEN_WIDTH, 1))
            dz += ddz
            z  += dz
            texture_position += texture_position_acceleration + z
            if texture_position >= texture_position_threshold:
                texture_position = 0

        #[NOVO] - speedometar
        cx, cy, r = SCREEN_WIDTH-80, SCREEN_HEIGHT-80, 60
        pygame.draw.circle(screen, (20,20,20), (cx,cy), r)
        pygame.draw.circle(screen, (60,60,60), (cx,cy), r, 2)
        start_angle = -210
        total_arc   = 240
        for kmh in range(0, 181, 20):
            angle_deg = start_angle + (kmh / max_speed) * total_arc
            angle_rad = math.radians(angle_deg)
            x1 = int(cx + math.cos(angle_rad) * (r-8))
            y1 = int(cy + math.sin(angle_rad) * (r-8))
            x2 = int(cx + math.cos(angle_rad) * (r-2))
            y2 = int(cy + math.sin(angle_rad) * (r-2))
            pygame.draw.line(screen, WHITE, (x1,y1), (x2,y2), 2)
        needle_angle = math.radians(start_angle + (speed / max_speed) * total_arc)
        nx = int(cx + math.cos(needle_angle) * (r-14))
        ny = int(cy + math.sin(needle_angle) * (r-14))
        pygame.draw.line(screen, RED, (cx,cy), (nx,ny), 3)
        pygame.draw.circle(screen, (80,80,80), (cx,cy), 5)
        speed_text = font.render(f'{int(speed)}', True, WHITE)
        screen.blit(speed_text, (cx - speed_text.get_width()//2, cy+10))
        label = small_font.render('km/h', True, (180,180,180))
        screen.blit(label, (cx - label.get_width()//2, cy+32))

        #[NOVO] - info overlay: pjesma i klaster
        cluster_label = small_font.render(
            f"Klaster: {current_cluster or '—'}", True, YELLOW)
        screen.blit(cluster_label, (SCREEN_WIDTH//2 - cluster_label.get_width()//2, 10))
        if current_song and speed >= 1:
            song_label = small_font.render(
                f"{current_song['artist']} — {current_song['title']}", True, YELLOW)
            screen.blit(song_label, (SCREEN_WIDTH//2 - song_label.get_width()//2, 30))

        pygame.display.flip() #[ORIGINAL]

if __name__ == "__main__":
    main()