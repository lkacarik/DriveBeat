import pygame,sys,os,math
import time
from pygame.locals import *
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skripte"))
from knn_odabir import KNNOdabir
from playback import LocalPygamePlayback, SpotifyConnectPlayback
from obd_reader import OBDReader
 
#[ORIGINAL "pseudo_3d_road_collection_source"] - boje
#-----------------------------------------------------------------------------------------
BLACK=pygame.color.THECOLORS["black"]
WHITE=pygame.color.THECOLORS["white"]
RED=pygame.color.THECOLORS["red"]
GREEN=pygame.color.THECOLORS["green"]
BLUE=pygame.color.THECOLORS["blue"]
YELLOW=pygame.color.THECOLORS["yellow"]
SCREEN_WIDTH=640
SCREEN_HEIGHT=480
HALF_SCREEN_HEIGHT=int(SCREEN_HEIGHT/2)
#-----------------------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = r"D:\FOI\3. godina\ZAVRSNI\DriveBeat\glazba.db"
 
#flagovi za spotify/lokalni playback i simulator/obd
#default (bez argumenata) = simulator+local
USE_OBD = len(sys.argv) > 1 and sys.argv[1] == "obd"
USE_SPOTIFY = len(sys.argv) > 2 and sys.argv[2] == "spotify"
OBD_PORT = "COM3"
 
#trigger za ponovni odabir prati promjenu brzine
SPEED_CHANGE_THRESHOLD = 20 #kolka promjena brzine pokrece ponovni odabir
SPEED_CHANGE_DELAY = 10.0 #sekundi kolko promjena mora trajat prije promjene pjesme

#delay prije pauziranja kad brzina padne na 0
STOP_DELAY = 6.0 #sekundi kolko brzina mora ostat 0 prije pauze

#delay prije nastavka sviranja kad brzina ode preko 0
RESUME_DELAY = 3.0 #sekundi kolko brzina mora ostat veca od 0 prije nastavka
 
#fade (u ms)
FADE_MS = 1000

#maksimalni dt po frameu (sec) - stiti tajmere od skokova kad frame kasni
#rjesava problem s BT na autu (pauziranje pjesme)
MAX_DT = 0.1

#glasnoca po rasponu brzine
GLASNOCA_RASPON = [
    (10,  0.25),
    (20,  0.3),
    (30,  0.35),
    (40,  0.4),
    (50,  0.45),
    (60,  0.5),
    (70,  0.55),
    (80,  0.6),
    (100, 0.65),
    (120, 0.75),
    (140, 0.85),
    (160, 0.95),
]
GLASNOCA_MAX = 1.0 #glasnoca iznad zadnjeg praga u rasponu (160+)

#stavlja glasnocu ovisno o tablici raspona glasnoce
def glasnoca_po_brzini(speed):
    for prag, glasnoca in GLASNOCA_RASPON:
        if speed < prag:
            return glasnoca
    return GLASNOCA_MAX
 
def main():
 
    pygame.init()

    #ispis greske ako inicijalizacija ne radi (playback spotify ili lokalni)
    try:
        playback = SpotifyConnectPlayback() if USE_SPOTIFY else LocalPygamePlayback()
    except Exception as e:
        print(f"\nGreska: {e}")
        pygame.quit()
        sys.exit(1)
 
    #[ORIGINAL "pseudo_3d_road_collection_source"] - Open Pygame window
    #-----------------------------------------------------------------------------------------
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),)
    pygame.display.set_caption("simulator")
    font       = pygame.font.SysFont('Arial', 30)
    small_font = pygame.font.SysFont('Arial', 14) #[NOVO] izvuceno iz loopa (ime pjesme)
    big_speed_font = pygame.font.SysFont('Arial', 90) #[NOVO] za voznja HUD
    #-----------------------------------------------------------------------------------------
 
    #[ORIGINAL "pseudo_3d_road_collection_source"] - images
    #[NOVO] — os.path umjesto relative stringa jer iz nekog razloga nije moglo nac png-ove
    #-----------------------------------------------------------------------------------------
    light_road = pygame.image.load(os.path.join(BASE_DIR, 'light_road.png')).convert()
    dark_road  = pygame.image.load(os.path.join(BASE_DIR, 'dark_road.png')).convert()
    #-----------------------------------------------------------------------------------------
 
    try:
        #inicijalizacija KNN odabir (ucita bazu, fita scaler/regresije/KNN jednom)
        knn = KNNOdabir(DB_PATH)

        #OBD citac (samo u voznji)
        obd_reader = OBDReader(OBD_PORT) if USE_OBD else None
    except Exception as e:
        print(f"\nGreska: {e}")
        playback.stop()
        pygame.quit()
        sys.exit(1)
 
    #muzika
    current_song    = None
    last_song_id    = None
    was_paused      = True
    #pocinje kao pauzirano - speed je 0 na startu
    #postojeci (RESUME_DELAY) pokrece tek kad auto krene
 
    #fade stanje
    pending_song = None #pjesma koja ceka da fade zavrsi
    fading_out   = False #je li fade u tijeku
 
    #stanje speed-change trigera
    last_pick_speed   = 0.0 #brzina kad je odabrana pjesma
    speed_change_timer = 0.0 #kolko dugo je brzina izvan praga od last_pick_speed
 
    #speedometar varijable
    speed     = 0.0
    max_speed = 180.0
    accel     = 12.0 #ubrzanje
    brake     = 18.0 #kocenje
    friction  = 3.0 #friction bez kocenja (usporavanje prirodno)
    clock     = pygame.time.Clock()
 
    #[ORIGINAL "pseudo_3d_road_collection_source"] - variables
    #-----------------------------------------------------------------------------------------
    texture_position            = 0
    ddz                         = 0.001
    dz                          = 0
    z                           = 0
    road_pos                    = 0
    road_acceleration           = 80
    texture_position_acceleration = 4
    texture_position_threshold  = 300
    half_texture_position_threshold = int(texture_position_threshold / 2)
    #-----------------------------------------------------------------------------------------
 
    #Game loop
    speed_locked = False #je li brzina zakljucana (tempomat)
    was_space_pressed = False #sprjecava treperenje togglea dok se SPACE drzi
    stop_timer = 0.0 #timer za STOP_DELAY
    resume_timer = 0.0 #timer za RESUME_DELAY

    while True:
 
        #dt ogranicen na MAX_DT da BT audio problem ne izazove skok u fizici
        #brzina skoci na 0 iako se realno nista nije promijenilo pa se pauzira
        dt = min(clock.tick(30) / 1000.0, MAX_DT)
 
        #[ORIGINAL "pseudo_3d_road_collection_source"]
        #-----------------------------------------------------------------------------------------
        for event in pygame.event.get():
            if event.type == QUIT:
                playback.stop()
                if USE_SPOTIFY:
                    time.sleep(0.3) #[NOVO] - da async pauza stigne do Spotify servera prije izlaska
                if USE_OBD:
                    obd_reader.stop() #[NOVO] - zatvori OBD konekciju
                pygame.quit()
                sys.exit()
        #-----------------------------------------------------------------------------------------                
 
        if USE_OBD:
            #voznja - speed dolazi iz OBD
            speed = obd_reader.get_speed()
        else:
            #kontrole - dodano kocenje, fizika brzine s delta timeom
            keys = pygame.key.get_pressed()

            #tempomat toggle (SPACE) samo jedan toggle po pritisku
            if keys[K_SPACE] and not was_space_pressed:
                speed_locked = not speed_locked
            was_space_pressed = keys[K_SPACE]

            if not speed_locked:
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
            else:
                #brzina zakljucana, cesta i dalje animira trenutnu brzinu
                if speed > 0:
                    road_pos += road_acceleration * (speed / max_speed)
                    if road_pos >= texture_position_threshold:
                        road_pos = 0
 
        #glasnoca po brzini
        volume = glasnoca_po_brzini(speed)

        playback.set_volume(volume)
 
        #logika glazbe
        if speed < 1:
            #brzina je 0, ali pauza tek nakon STOP_DELAY
            resume_timer = 0.0 #ponovno stajanje, reset resume tajmer
            if not was_paused:
                stop_timer += dt
                if stop_timer >= STOP_DELAY:
                    playback.fadeout(FADE_MS)
                    was_paused         = True
                    fading_out         = False
                    pending_song       = None
                    speed_change_timer = 0.0
        else:
            stop_timer = 0.0 #brzina se vratila, reset stop tajmer

            if was_paused:
                #brzina veca od 0, ali nastavi tek nakon RESUME_DELAY
                resume_timer += dt
                if resume_timer >= RESUME_DELAY:
                    was_paused    = False
                    resume_timer  = 0.0

                    current_song = knn.pick_song(speed, last_song_id)
                    last_pick_speed    = speed
                    speed_change_timer = 0.0

                    if current_song:
                        playback.play_song(current_song, fade_ms=FADE_MS)
                        last_song_id = current_song["id"]

            if not was_paused:
                #speed-change trigger - ponovni odabir kad se brzina dovoljno promijeni i to traje
                if not fading_out: #A grana
                    if abs(speed - last_pick_speed) >= SPEED_CHANGE_THRESHOLD:
                        speed_change_timer += dt
                    else:
                        #brzina se vraca blizu zadnjeg odabira - odustani
                        speed_change_timer = 0.0
 
                    #potvrdi promjenu pjesme tek nakon SPEED_CHANGE_DELAY
                    if speed_change_timer >= SPEED_CHANGE_DELAY:
                        pending_song = knn.pick_song(speed, last_song_id)

                        last_pick_speed    = speed
                        speed_change_timer = 0.0
                        fading_out         = True
                        playback.fadeout(FADE_MS)
 
                #fadeout zavrsio pokreni pending pjesmu
                if fading_out and not playback.is_busy(): #B grana
                    fading_out = False
                    if pending_song:
                        playback.play_song(pending_song, fade_ms=FADE_MS)
                        current_song = pending_song
                        last_song_id = current_song["id"]
                        pending_song = None
 
                #pjesma zavrsila prirodno
                if not fading_out and not playback.is_busy(): #C grana
                    current_song = knn.pick_song(speed, last_song_id)
                
                    last_pick_speed    = speed
                    speed_change_timer = 0.0
 
                    if current_song:
                        playback.play_song(current_song, fade_ms=FADE_MS)
                        last_song_id = current_song["id"]
            #!!! A/B/C namjerno sprijecava dvostruki odabir u istom frameu, NE MIJENJAJ !!!
 
        if USE_OBD:
            #sucelje za voznju
            screen.fill(BLACK)

            speed_text = big_speed_font.render(f'{int(speed)}', True, WHITE)
            screen.blit(speed_text, (SCREEN_WIDTH//2 - speed_text.get_width()//2,
                                      SCREEN_HEIGHT//2 - speed_text.get_height()//2 - 20))
            label = small_font.render('km/h', True, (180,180,180))
            screen.blit(label, (SCREEN_WIDTH//2 - label.get_width()//2,
                                 SCREEN_HEIGHT//2 + 50))

            if current_song and speed >= 1:
                song_label = small_font.render(
                    f"{current_song['artist']} — {current_song['title']}", True, YELLOW)
                screen.blit(song_label, (SCREEN_WIDTH//2 - song_label.get_width()//2,
                                          SCREEN_HEIGHT - 40))
        else:
            #[ORIGINAL "pseudo_3d_road_collection_source"] - draw the road
            #-----------------------------------------------------------------------------------------
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
            #-----------------------------------------------------------------------------------------
 
            #speedometar
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

            if speed_locked: #HUD indikator tempomata
                lock_label = small_font.render('TEMPOMAT', True, YELLOW)
                screen.blit(lock_label, (SCREEN_WIDTH - lock_label.get_width() - 10, 10))
 
            #info HUD
            if current_song and speed >= 1:
                song_label = small_font.render(
                    f"{current_song['artist']} — {current_song['title']}", True, YELLOW)
                screen.blit(song_label, (SCREEN_WIDTH//2 - song_label.get_width()//2, 10))
 
        pygame.display.flip()
 
if __name__ == "__main__":
    main()