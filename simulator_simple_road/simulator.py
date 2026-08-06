import pygame,sys,os,math  #[MODIFICIRANO] dodani os, math
from pygame.locals import *
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skripte"))
from knn_odabir import KNNOdabir   #[KNN] odabir pjesme preseljen u zasebnu skriptu
 
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
 
#[KNN] - trigger za ponovni odabir prati PROMJENU BRZINE
SPEED_CHANGE_THRESHOLD = 20 #kolika promjena brzine pokrece ponovni odabir
SPEED_CHANGE_DELAY     = 4.0 #sekundi koliko promjena mora trajat prije promjene pjesme
 
#[NOVO] - fade trajanje u ms
FADE_MS = 1000
 
#[NOVO] - kerosene granica
KEROSENE = 180
 
#[MODIFICIRANO] - stisavanje glazbe (ducking) kod naglog kocenja
KOCENJE_TIHO = 15 #km/h/s - deceleracija koja aktivira stisavanje
                    #(kocenje decelerira 18, voznja bez gasa samo 3)
DUCK_VOLUME  = 0.1 #glasnoca na koju padne glazba dok traje ducking
DUCK_HOLD    = 0.8 #sekundi koliko glazba ostaje tiha nakon naglog kocenja
DUCK_RAMP    = 0.5 #sekundi za postupan povratak glasnoce
 
#[NOVO] - glazbene funkcije
def play_song(song):
    #ucitaj i pusti pjesmu s fade in
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
 
    #[KNN] - inicijalizacija KNN odabir (ucita bazu, fita skaler/regresije/KNN jednom)
    knn           = KNNOdabir(DB_PATH)
    kerosene_song = knn.kerosene_song() #keširana kerosene (ili none)
 
    #[NOVO] - glazba
    current_song    = None
    last_song_id    = None
    was_paused      = False #prati je li glazba pauzirana zbog v=0 (brzina 0)
 
    #[NOVO] - fade stanje
    pending_song = None #pjesma koja čeka da fadeout završi
    fading_out   = False #je li trenutno u tijeku fadeout
 
    #[KNN] - stanje speed-change trigera
    last_pick_speed   = 0.0 #brzina pri kojoj je zadnji put odabrana pjesma
    speed_change_timer = 0.0 #koliko dugo je brzina izvan praga od last_pick_speed
 
    #[NOVO] - speedometar varijable
    speed     = 0.0
    max_speed = 180.0
    accel     = 12.0   # km/h po sekundi
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
 
    #[KNN] - pusti prvu pjesmu
    if speed >= KEROSENE and kerosene_song: #provjera za kerosene
        current_song = kerosene_song
    else:
        current_song = knn.pick_song(speed)
    last_pick_speed = speed
 
    if current_song:
        play_song(current_song)
        last_song_id = current_song["id"]
 
    #[MODIFICIRANO] - Game loop
    prev_speed = 0.0 #pracenje przine za naglo kocenje i stisavanje muzike
    duck_timer = 0.0 #[MODIFICIRANO] koliko jos traje stisavanje
    duck_gain  = 1.0 #[MODIFICIRANO] trenutna max glasnoca
    while True:
 
        dt = clock.tick(30) / 1000.0  #[MODIFICIRANO]
 
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
 
        #[MODIFICIRANO] glasnoca
        #base glasnoca ovisno o brzini (ispod 30 km/h - fade in jacina)
        if speed < 30:
            volume = speed / 30.0
        else:
            volume = 1.0
 
        #naglo kocenje - odmah stisavanje i pokreni hold tajmer
        deceleration = (prev_speed - speed) / dt if dt > 0 else 0
        if deceleration > KOCENJE_TIHO:
            duck_timer = DUCK_HOLD
            duck_gain  = DUCK_VOLUME
 
        #drzi stišano dok traje hold, pa postupno vrati max na 1.0 kroz DUCK_RAMP
        if duck_timer > 0:
            duck_timer -= dt
        elif duck_gain < 1.0:
            duck_gain = min(1.0, duck_gain + (1.0 - DUCK_VOLUME) / DUCK_RAMP * dt)
 
        volume = min(volume, duck_gain)
 
        pygame.mixer.music.set_volume(volume)
 
        prev_speed = speed
 
        #[KNN] - logika glazbe
        #kerosene triger da se odma pusti
        if speed >= KEROSENE and kerosene_song and current_song \
                and current_song["id"] != kerosene_song["id"]:
            pending_song = kerosene_song
            last_pick_speed = speed
            speed_change_timer = 0.0
            fading_out = True
            pygame.mixer.music.fadeout(FADE_MS)
 
        if speed < 1:
            #vozilo stoji - pauziraj s fadeoutom
            if not was_paused:
                pygame.mixer.music.fadeout(FADE_MS)
                was_paused         = True
                fading_out         = False  #nije promjena pjesme, samo pauza
                pending_song       = None
                speed_change_timer = 0.0
        else:
            #nastavi reprodukciju ako smo bili pauzirani
            if was_paused:
                was_paused = False
                if speed >= KEROSENE and kerosene_song: #provjera za kerosene
                    current_song = kerosene_song
                else:
                    current_song = knn.pick_song(speed, last_song_id)
                last_pick_speed    = speed
                speed_change_timer = 0.0
 
                if current_song:
                    play_song(current_song)
                    last_song_id = current_song["id"]
 
            #[KNN] - speed-change trigger - ponovni odabir kad se brzina dovoljno promijeni i to traje
            if not fading_out:
                if abs(speed - last_pick_speed) >= SPEED_CHANGE_THRESHOLD:
                    speed_change_timer += dt
                else:
                    #brzina se vratila blizu zadnjeg odabira - odustani
                    speed_change_timer = 0.0
 
                #potvrdi promjenu tek nakon SPEED_CHANGE_DELAY sekundi
                if speed_change_timer >= SPEED_CHANGE_DELAY:
                    if speed >= KEROSENE and kerosene_song: #provjera za kerosene
                        pending_song = kerosene_song
                    else:
                        pending_song = knn.pick_song(speed, last_song_id)
                    last_pick_speed    = speed
                    speed_change_timer = 0.0
                    fading_out         = True
                    pygame.mixer.music.fadeout(FADE_MS)
 
            #[NOVO] - fadeout zavrsio pokreni pending pjesmu
            if fading_out and not pygame.mixer.music.get_busy():
                fading_out = False
                if pending_song:
                    play_song(pending_song)
                    current_song = pending_song
                    last_song_id = current_song["id"]
                    pending_song = None
 
            #[KNN] - pjesma zavrsila prirodno - odaberi sljedecu
            if not fading_out and not was_paused and not pygame.mixer.music.get_busy():
                if speed >= KEROSENE and kerosene_song:
                    current_song = kerosene_song
                else:
                    current_song = knn.pick_song(speed, last_song_id)
                last_pick_speed    = speed
                speed_change_timer = 0.0
 
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
 
        #[KNN] - info overlay
        if current_song and speed >= 1:
            song_label = small_font.render(
                f"{current_song['artist']} — {current_song['title']}", True, YELLOW)
            screen.blit(song_label, (SCREEN_WIDTH//2 - song_label.get_width()//2, 10))
 
        pygame.display.flip() #[ORIGINAL]
 
if __name__ == "__main__":
    main()
