import pygame
import random
import sys
import os
import math
import array
import base64
import binascii
import hashlib
import hmac
import json


def app_resource_path(filename):
    """Return the path to a bundled asset or local project asset."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, filename)


def app_data_path(filename):
    """Return a writable path for local game data."""
    if sys.platform == "win32":
        data_root = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        data_root = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        data_root = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))

    data_dir = os.path.join(data_root, "Busting in Space")
    try:
        os.makedirs(data_dir, exist_ok=True)
    except OSError:
        data_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(data_dir, filename)


pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# =========================
# Window settings
# =========================
# Increase the game window dimensions to provide more space for additional enemy types
# and falling bonus items. A wider and taller play field makes the game
# feel less cramped when many objects are on screen.
WIDTH = 800
HEIGHT = 950

screen = pygame.display.set_mode((WIDTH, HEIGHT))
# Set a proper game title for the window
pygame.display.set_caption("Busting in space")

clock = pygame.time.Clock()

FONT = pygame.font.SysFont("Arial", 26)
SMALL_FONT = pygame.font.SysFont("Arial", 22)
BIG_FONT = pygame.font.SysFont("Arial", 48)
TITLE_FONT = pygame.font.SysFont("Arial", 56)

# =========================
# Colors
# =========================
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
DARK_GRAY = (45, 45, 45)

BLUE = (0, 120, 255)
LIGHT_BLUE = (80, 180, 255)

RED = (220, 0, 0)
DARK_RED = (120, 0, 0)

YELLOW = (255, 220, 0)
GREEN = (0, 200, 0)
ORANGE = (255, 140, 0)
PURPLE = (160, 80, 255)

# =========================
# Game constants
# =========================
PLAYER_WIDTH = 50
PLAYER_HEIGHT = 40

BULLET_WIDTH = 8
BULLET_HEIGHT = 18
BULLET_SPEED = 10
TRIPLE_SHOT_DURATION = 6000
TRIPLE_SHOT_SPREAD = 4
RAPID_FIRE_DELAY = 90

ENEMY_WIDTH = 45
ENEMY_HEIGHT = 35
# Base vertical speed of enemies. Increase slightly for a faster paced game.
# Enemies now move faster to increase the game's challenge.
ENEMY_SPEED_START = 5
ENEMY_SPAWN_DELAY = 700

# Increase the star count slightly to fill the larger play area
STAR_COUNT = 180

# Path to the background music file. Ensure a file named background.mp3 exists in the same folder.
BACKGROUND_MUSIC_PATH = app_resource_path("background.mp3")
LOGO_PATH = app_resource_path("icon.png")
SAVE_PATH = app_data_path(".busting_save.dat")
SAVE_SECRET = b"busting-in-space-high-score-v1"

# =========================
# Bonus and power‑up settings
# =========================
# Size of bonus items and their fall speed
BONUS_SIZE = 20
BONUS_SPEED = 4
# Types of bonuses that can drop from defeated enemies
BONUS_TYPES = ["life", "rapid", "shield", "triple"]
SHIP_DESIGNS = ["Classic", "Interceptor", "Heavy", "Needle", "Wing"]

# Runtime state for bonuses, power-up timers and shield status. These are reset in reset_game().
bonuses = []
rapid_fire_bonus_timer = 0
triple_shot_bonus_timer = 0
player_shield = False

# =========================
# Settings dictionary
# =========================
settings = {
    "master_volume": 0.45,
    "music_volume": 0.30,
    "sfx_volume": 0.55,
    "player_speed": 7,
    "ship_design": 0,
    "starting_lives": 3,
    "move_left": pygame.K_a,
    "move_right": pygame.K_d,
    "shoot": pygame.K_SPACE,
    "pause": pygame.K_p,
    "mute": pygame.K_m,
}

# Global sound flag and key waiting state used when remapping controls
sound_enabled = True
waiting_for_key = None

# =========================
# Sound generation helpers
# =========================
def create_tone(frequency=440, duration_ms=150, volume=0.4):
    """Create a simple tone sound at a given frequency and duration."""
    sample_rate = 44100
    samples = int(sample_rate * duration_ms / 1000)
    buffer = array.array("h")
    for i in range(samples):
        t = i / sample_rate
        fade = 1.0
        fade_out_start = int(samples * 0.65)
        if i > fade_out_start:
            fade = 1 - ((i - fade_out_start) / (samples - fade_out_start))
        value = int(
            32767
            * volume
            * fade
            * math.sin(2 * math.pi * frequency * t)
        )
        buffer.append(value)
        buffer.append(value)
    return pygame.mixer.Sound(buffer=buffer)


def create_explosion_sound():
    """Create a noise-based explosion sound."""
    sample_rate = 44100
    duration_ms = 350
    samples = int(sample_rate * duration_ms / 1000)
    buffer = array.array("h")
    for i in range(samples):
        t = i / sample_rate
        fade = 1 - (i / samples)
        noise = random.uniform(-1, 1)
        low_boom = math.sin(2 * math.pi * 70 * t)
        value = int(
            32767
            * 0.45
            * fade
            * (0.65 * noise + 0.35 * low_boom)
        )
        buffer.append(value)
        buffer.append(value)
    return pygame.mixer.Sound(buffer=buffer)


def create_laser_sound():
    """Create a laser firing sound that descends in pitch."""
    sample_rate = 44100
    duration_ms = 110
    samples = int(sample_rate * duration_ms / 1000)
    buffer = array.array("h")
    for i in range(samples):
        t = i / sample_rate
        fade = 1 - (i / samples)
        frequency = 900 - 500 * (i / samples)
        value = int(
            32767
            * 0.28
            * fade
            * math.sin(2 * math.pi * frequency * t)
        )
        buffer.append(value)
        buffer.append(value)
    return pygame.mixer.Sound(buffer=buffer)


# Generate basic sounds for events
shoot_sound = create_laser_sound()
explosion_sound = create_explosion_sound()
game_over_sound = create_tone(130, 700, 0.45)
start_sound = create_tone(660, 180, 0.35)
bonus_sound = create_tone(880, 120, 0.35)
menu_sound = create_tone(520, 100, 0.25)


def apply_volume_settings():
    """Apply current volume settings to music and sound effects."""
    pygame.mixer.music.set_volume(settings["master_volume"] * settings["music_volume"])
    shoot_sound.set_volume(settings["master_volume"] * settings["sfx_volume"])
    explosion_sound.set_volume(settings["master_volume"] * settings["sfx_volume"])
    game_over_sound.set_volume(settings["master_volume"] * settings["sfx_volume"])
    start_sound.set_volume(settings["master_volume"] * settings["sfx_volume"])
    bonus_sound.set_volume(settings["master_volume"] * settings["sfx_volume"])
    menu_sound.set_volume(settings["master_volume"] * settings["sfx_volume"])


def play_sound(sound):
    """Play a sound effect if sound is enabled."""
    if sound_enabled:
        sound.play()


def start_background_music():
    """Load and start playing looping background music."""
    if os.path.exists(BACKGROUND_MUSIC_PATH):
        try:
            pygame.mixer.music.load(BACKGROUND_MUSIC_PATH)
            apply_volume_settings()
            pygame.mixer.music.play(-1)
        except pygame.error as e:
            print("Could not load background music:", e)
    else:
        print("No background music file found.")
        print(f"Put {BACKGROUND_MUSIC_PATH} in the same folder as shooter.py")


def toggle_sound():
    """Toggle master sound on or off and pause/resume music accordingly."""
    global sound_enabled
    sound_enabled = not sound_enabled
    if sound_enabled:
        apply_volume_settings()
        pygame.mixer.music.unpause()
    else:
        pygame.mixer.music.pause()


# =========================
# Text and utility functions
# =========================
def draw_text(text, font, color, x, y):
    """Draw text at a specific position."""
    img = font.render(text, True, color)
    screen.blit(img, (x, y))


def draw_centered_text(text, font, color, y):
    """Draw text centered horizontally at a specific vertical position."""
    img = font.render(text, True, color)
    x = WIDTH // 2 - img.get_width() // 2
    screen.blit(img, (x, y))


def draw_centered_image(image, y):
    """Draw an image centered horizontally at a specific vertical position."""
    x = WIDTH // 2 - image.get_width() // 2
    screen.blit(image, (x, y))


def draw_startup_logo_splash(duration_ms=7000):
    """Show the studio logo before the game and music begin."""
    start_time = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start_time < duration_ms:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        elapsed = pygame.time.get_ticks() - start_time
        fade_in = min(1.0, elapsed / 1000)
        fade_out = min(1.0, max(0, duration_ms - elapsed) / 1000)
        alpha_factor = min(fade_in, fade_out)
        logo_color = tuple(int(channel * alpha_factor) for channel in WHITE)
        accent_color = tuple(int(channel * alpha_factor) for channel in ORANGE)

        screen.fill(BLACK)
        draw_centered_text("Busting Balls", TITLE_FONT, logo_color, HEIGHT // 2 - 80)
        draw_centered_text("Entertainment", BIG_FONT, accent_color, HEIGHT // 2 + 5)
        pygame.display.flip()
        clock.tick(60)


def key_name(key):
    """Return a human-readable name for a pygame key constant."""
    return pygame.key.name(key).upper()


def load_game_logo():
    """Load the game logo and apply it as the window icon."""
    if not os.path.exists(LOGO_PATH):
        return None

    try:
        logo = pygame.image.load(LOGO_PATH).convert_alpha()
        pygame.display.set_icon(logo)
        max_logo_size = 150
        width, height = logo.get_size()
        scale = min(max_logo_size / width, max_logo_size / height)
        display_size = (int(width * scale), int(height * scale))
        return pygame.transform.smoothscale(logo, display_size)
    except pygame.error as e:
        print("Could not load game logo:", e)
        return None


def load_high_score():
    """Load the saved high score from a signed save file."""
    try:
        with open(SAVE_PATH, "rb") as file:
            encoded_save = file.read().strip()
        save_data = json.loads(base64.b64decode(encoded_save).decode("utf-8"))
        score_text = str(save_data["score"])
        expected_signature = hmac.new(
            SAVE_SECRET,
            score_text.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(save_data.get("signature", ""), expected_signature):
            return 0
        return max(0, int(score_text))
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError, binascii.Error, OSError):
        return 0


def save_high_score(high_score):
    """Save the high score to a signed save file."""
    try:
        score_text = str(max(0, int(high_score)))
        signature = hmac.new(
            SAVE_SECRET,
            score_text.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        save_data = {"score": score_text, "signature": signature}
        encoded_save = base64.b64encode(json.dumps(save_data).encode("utf-8"))
        temp_path = SAVE_PATH + ".tmp"
        with open(temp_path, "wb") as file:
            file.write(encoded_save)
        os.replace(temp_path, SAVE_PATH)
    except OSError as e:
        print("Could not save high score:", e)


def update_high_score(score, high_score):
    """Update and persist the high score when the player sets a new record."""
    if score > high_score:
        high_score = score
        save_high_score(high_score)
    return high_score


# =========================
# Star background functions
# =========================
def create_stars():
    """Generate a list of star dictionaries for the background."""
    stars = []
    for _ in range(STAR_COUNT):
        star = {
            "x": random.randint(0, WIDTH),
            "y": random.randint(0, HEIGHT),
            "speed": random.randint(1, 5),
            "size": random.randint(1, 3),
        }
        stars.append(star)
    return stars


def draw_stars(stars):
    """Draw stars and update their positions to create a scrolling effect."""
    for star in stars:
        pygame.draw.circle(
            screen,
            WHITE,
            (star["x"], star["y"]),
            star["size"]
        )
        star["y"] += star["speed"]
        if star["y"] > HEIGHT:
            star["x"] = random.randint(0, WIDTH)
            star["y"] = 0
            star["speed"] = random.randint(1, 5)
            star["size"] = random.randint(1, 3)


# =========================
# Game state reset
# =========================
def reset_game():
    """Reset the game to its initial state and return relevant variables."""
    player = pygame.Rect(
        WIDTH // 2 - PLAYER_WIDTH // 2,
        HEIGHT - 80,
        PLAYER_WIDTH,
        PLAYER_HEIGHT
    )
    bullets = []
    enemies = []
    explosions = []
    score = 0
    lives = settings["starting_lives"]
    enemy_speed = ENEMY_SPEED_START
    last_enemy_spawn = pygame.time.get_ticks()
    last_auto_fire = pygame.time.get_ticks()
    # Reset bonus state and power‑up timers
    global bonuses, rapid_fire_bonus_timer, triple_shot_bonus_timer, player_shield
    bonuses = []
    rapid_fire_bonus_timer = 0
    triple_shot_bonus_timer = 0
    player_shield = False
    return (
        player,
        bullets,
        enemies,
        explosions,
        score,
        lives,
        enemy_speed,
        last_enemy_spawn,
        last_auto_fire
    )


# =========================
# Enemy and bullet logic
# =========================
def spawn_enemy(enemies):
    """Spawn a new enemy with a random type.

    Each enemy is represented as a dictionary containing a rect, a type string,
    a health value, a horizontal speed (dx) and a score value based on its
    difficulty. The spawn probabilities bias toward basic enemies while still
    introducing tougher, moving and splitting foes.
    """
    # Start the enemy at a random x position above the top of the screen
    x = random.randint(0, WIDTH - ENEMY_WIDTH)
    y = -ENEMY_HEIGHT
    # Decide the enemy type using weighted probabilities:
    # basic (60%), tough (20%), moving (10%), split (10%).
    rand = random.random()
    if rand < 0.6:
        enemy_type = "basic"
        health = 1
        dx = 0
        score_value = 1
    elif rand < 0.8:
        enemy_type = "tough"
        health = 2
        dx = 0
        score_value = 2
    elif rand < 0.9:
        enemy_type = "moving"
        health = 1
        # Increase horizontal speed slightly for moving enemies
        dx = random.choice([-3, 3])
        score_value = 2
    else:
        enemy_type = "split"
        health = 1
        dx = 0
        score_value = 3
    rect = pygame.Rect(x, y, ENEMY_WIDTH, ENEMY_HEIGHT)
    enemies.append({
        "rect": rect,
        "type": enemy_type,
        "health": health,
        "dx": dx,
        "score_value": score_value,
    })

# -----------------------------------------------------------
# Bonus spawning
# -----------------------------------------------------------
def spawn_bonus(x: float, y: float) -> None:
    """Randomly spawn a bonus item at the given position.

    A small chance exists for a defeated enemy to drop a bonus. When a bonus is
    spawned it is appended to the global ``bonuses`` list. The bonus will
    subsequently fall downward until collected by the player or leaving the
    screen.

    Parameters
    ----------
    x : float
        The horizontal centre position where the bonus should appear.
    y : float
        The vertical position where the bonus should begin falling.
    """
    # 25% chance to drop a bonus
    if random.random() < 0.25:
        bonus_type = random.choice(BONUS_TYPES)
        # Create a square bonus centred horizontally on the supplied x coordinate
        bonus_rect = pygame.Rect(int(x - BONUS_SIZE // 2), int(y), BONUS_SIZE, BONUS_SIZE)
        bonuses.append({"rect": bonus_rect, "type": bonus_type})


def create_bullet(player, dx=0):
    """Create a bullet with horizontal and vertical velocity."""
    rect = pygame.Rect(
        player.centerx - BULLET_WIDTH // 2,
        player.y - BULLET_HEIGHT,
        BULLET_WIDTH,
        BULLET_HEIGHT
    )
    return {"rect": rect, "dx": dx, "dy": -BULLET_SPEED}


def shoot_bullet(player, bullets):
    """Create one or three bullets from the player's position."""
    if pygame.time.get_ticks() < triple_shot_bonus_timer:
        for dx in (-TRIPLE_SHOT_SPREAD, 0, TRIPLE_SHOT_SPREAD):
            bullets.append(create_bullet(player, dx))
    else:
        bullets.append(create_bullet(player))
    play_sound(shoot_sound)


# =========================
# Drawing functions
# =========================
def draw_player(player):
    """Draw the selected player spaceship with flame animation."""
    design = SHIP_DESIGNS[settings["ship_design"] % len(SHIP_DESIGNS)]
    cx = player.centerx

    if design == "Interceptor":
        body_points = [
            (cx, player.y - 28),
            (player.x + 8, player.bottom),
            (cx, player.bottom - 12),
            (player.right - 8, player.bottom),
        ]
        inner_points = [
            (cx, player.y - 10),
            (player.x + 18, player.bottom - 10),
            (player.right - 18, player.bottom - 10),
        ]
        pygame.draw.polygon(screen, GREEN, body_points)
        pygame.draw.polygon(screen, LIGHT_BLUE, inner_points)
        pygame.draw.line(screen, WHITE, (cx, player.y - 20), (cx, player.bottom - 12), 3)
    elif design == "Heavy":
        body = pygame.Rect(player.x + 5, player.y - 8, player.width - 10, player.height + 8)
        nose_points = [
            (cx, player.y - 24),
            (player.x + 10, player.y + 8),
            (player.right - 10, player.y + 8),
        ]
        wing_left = [(player.x + 5, player.y + 14), (player.x - 10, player.bottom), (player.x + 16, player.bottom - 6)]
        wing_right = [(player.right - 5, player.y + 14), (player.right + 10, player.bottom), (player.right - 16, player.bottom - 6)]
        pygame.draw.rect(screen, PURPLE, body, border_radius=8)
        pygame.draw.polygon(screen, PURPLE, nose_points)
        pygame.draw.polygon(screen, BLUE, wing_left)
        pygame.draw.polygon(screen, BLUE, wing_right)
        pygame.draw.rect(screen, LIGHT_BLUE, body.inflate(-18, -12), border_radius=5)
    elif design == "Needle":
        body_points = [
            (cx, player.y - 34),
            (player.x + 18, player.bottom),
            (cx, player.bottom - 8),
            (player.right - 18, player.bottom),
        ]
        side_left = [(player.x + 17, player.y + 12), (player.x - 6, player.bottom - 2), (player.x + 23, player.bottom - 10)]
        side_right = [(player.right - 17, player.y + 12), (player.right + 6, player.bottom - 2), (player.right - 23, player.bottom - 10)]
        pygame.draw.polygon(screen, YELLOW, body_points)
        pygame.draw.polygon(screen, ORANGE, side_left)
        pygame.draw.polygon(screen, ORANGE, side_right)
        pygame.draw.line(screen, WHITE, (cx, player.y - 22), (cx, player.bottom - 10), 2)
    elif design == "Wing":
        body_points = [
            (cx, player.y - 20),
            (player.x + 14, player.bottom),
            (player.right - 14, player.bottom),
        ]
        wing_left = [(cx, player.y + 8), (player.x - 16, player.bottom - 8), (player.x + 18, player.bottom - 4)]
        wing_right = [(cx, player.y + 8), (player.right + 16, player.bottom - 8), (player.right - 18, player.bottom - 4)]
        pygame.draw.polygon(screen, RED, wing_left)
        pygame.draw.polygon(screen, RED, wing_right)
        pygame.draw.polygon(screen, BLUE, body_points)
        pygame.draw.circle(screen, LIGHT_BLUE, (cx, player.y + 14), 7)
    else:
        body_points = [
            (cx, player.y - 25),
            (player.x - 5, player.bottom),
            (player.right + 5, player.bottom)
        ]
        inner_points = [
            (cx, player.y - 8),
            (player.x + 12, player.bottom - 8),
            (player.right - 12, player.bottom - 8)
        ]
        pygame.draw.polygon(screen, BLUE, body_points)
        pygame.draw.polygon(screen, LIGHT_BLUE, inner_points)

    cannon = pygame.Rect(cx - 5, player.y - 18, 10, 18)
    pygame.draw.rect(screen, GREEN, cannon)
    flame_height = random.randint(12, 28)
    flame_points = [
        (cx - 10, player.bottom),
        (cx + 10, player.bottom),
        (cx, player.bottom + flame_height)
    ]
    pygame.draw.polygon(screen, ORANGE, flame_points)
    small_flame_points = [
        (cx - 5, player.bottom),
        (cx + 5, player.bottom),
        (cx, player.bottom + flame_height // 2)
    ]
    pygame.draw.polygon(screen, YELLOW, small_flame_points)


def draw_bullets(bullets):
    """Draw all bullets."""
    for bullet in bullets:
        rect = bullet["rect"]
        pygame.draw.ellipse(screen, YELLOW, rect)
        glow = pygame.Rect(
            rect.x - 2,
            rect.y + 3,
            rect.width + 4,
            rect.height - 3
        )
        pygame.draw.ellipse(screen, ORANGE, glow, 1)


def draw_enemies(enemies):
    """Draw all enemies based on their type.

    Each enemy dictionary contains a ``rect``, ``type``, ``health`` and ``dx``. The
    appearance of the enemy is determined by its type:

    * basic: standard red alien with eyes and shadow.
    * tough: purple alien with a smaller red core to indicate extra health.
    * moving: orange alien with horizontal stripes to hint at its movement.
    * split / split_child: yellow alien with a vertical dividing line.
    """
    for enemy in enemies:
        rect = enemy["rect"]
        etype = enemy["type"]
        # Basic enemy: red ellipse with shadow and eyes
        if etype == "basic":
            # Body and shadow
            pygame.draw.ellipse(screen, RED, rect)
            shadow = pygame.Rect(rect.x + 5, rect.y + rect.height // 2, rect.width - 10, rect.height // 2)
            pygame.draw.ellipse(screen, DARK_RED, shadow)
            # Eyes
            eye_left = pygame.Rect(rect.x + 10, rect.y + 9, 8, 8)
            eye_right = pygame.Rect(rect.x + rect.width - 18, rect.y + 9, 8, 8)
            pygame.draw.ellipse(screen, WHITE, eye_left)
            pygame.draw.ellipse(screen, WHITE, eye_right)
            # Pupils
            pupil_left = pygame.Rect(rect.x + 13, rect.y + 12, 3, 3)
            pupil_right = pygame.Rect(rect.x + rect.width - 15, rect.y + 12, 3, 3)
            pygame.draw.ellipse(screen, BLACK, pupil_left)
            pygame.draw.ellipse(screen, BLACK, pupil_right)
        elif etype == "tough":
            # Tough enemy: purple body with a smaller red core and eyes
            pygame.draw.ellipse(screen, PURPLE, rect)
            inner = rect.inflate(-10, -10)
            pygame.draw.ellipse(screen, RED, inner)
            # Eyes
            eye_left = pygame.Rect(rect.x + 12, rect.y + 10, 10, 10)
            eye_right = pygame.Rect(rect.x + rect.width - 22, rect.y + 10, 10, 10)
            pygame.draw.ellipse(screen, WHITE, eye_left)
            pygame.draw.ellipse(screen, WHITE, eye_right)
            # Pupils
            pupil_left = pygame.Rect(rect.x + 15, rect.y + 13, 4, 4)
            pupil_right = pygame.Rect(rect.x + rect.width - 19, rect.y + 13, 4, 4)
            pygame.draw.ellipse(screen, BLACK, pupil_left)
            pygame.draw.ellipse(screen, BLACK, pupil_right)
        elif etype == "moving":
            # Moving enemy: orange body with two horizontal stripes and eyes
            pygame.draw.ellipse(screen, ORANGE, rect)
            stripe1_y = rect.y + int(rect.height * 0.3)
            stripe2_y = rect.y + int(rect.height * 0.6)
            pygame.draw.line(screen, DARK_RED, (rect.x + 5, stripe1_y), (rect.x + rect.width - 5, stripe1_y), 2)
            pygame.draw.line(screen, DARK_RED, (rect.x + 5, stripe2_y), (rect.x + rect.width - 5, stripe2_y), 2)
            # Eyes
            eye_left = pygame.Rect(rect.x + 10, rect.y + 10, 8, 8)
            eye_right = pygame.Rect(rect.x + rect.width - 18, rect.y + 10, 8, 8)
            pygame.draw.ellipse(screen, WHITE, eye_left)
            pygame.draw.ellipse(screen, WHITE, eye_right)
            pupil_left = pygame.Rect(rect.x + 13, rect.y + 13, 3, 3)
            pupil_right = pygame.Rect(rect.x + rect.width - 15, rect.y + 13, 3, 3)
            pygame.draw.ellipse(screen, BLACK, pupil_left)
            pygame.draw.ellipse(screen, BLACK, pupil_right)
        else:
            # Split or split_child enemy: yellow body with a vertical dividing line and eyes
            pygame.draw.ellipse(screen, YELLOW, rect)
            # Vertical dividing line
            pygame.draw.line(screen, ORANGE, (rect.centerx, rect.y + 5), (rect.centerx, rect.y + rect.height - 5), 3)
            # Eyes
            eye_left = pygame.Rect(rect.x + 8, rect.y + 8, 6, 6)
            eye_right = pygame.Rect(rect.x + rect.width - 14, rect.y + 8, 6, 6)
            pygame.draw.ellipse(screen, WHITE, eye_left)
            pygame.draw.ellipse(screen, WHITE, eye_right)
            pupil_left = pygame.Rect(rect.x + 10, rect.y + 10, 2, 2)
            pupil_right = pygame.Rect(rect.x + rect.width - 12, rect.y + 10, 2, 2)
            pygame.draw.ellipse(screen, BLACK, pupil_left)
            pygame.draw.ellipse(screen, BLACK, pupil_right)

# -----------------------------------------------------------
# Bonus drawing
# -----------------------------------------------------------
def draw_bonuses(bonuses):
    """Draw falling bonus items. Each bonus type has a unique appearance."""
    for bonus in bonuses:
        rect = bonus["rect"]
        btype = bonus["type"]
        cx, cy = rect.center
        radius = rect.width // 2
        if btype == "life":
            # Green circle with a white plus sign
            pygame.draw.circle(screen, GREEN, (cx, cy), radius)
            # Vertical bar of the plus
            pygame.draw.rect(screen, WHITE, (cx - 2, cy - radius + 4, 4, radius * 2 - 8))
            # Horizontal bar of the plus
            pygame.draw.rect(screen, WHITE, (cx - radius + 4, cy - 2, radius * 2 - 8, 4))
        elif btype == "rapid":
            # Orange circle with a yellow lightning bolt
            pygame.draw.circle(screen, ORANGE, (cx, cy), radius)
            bolt = [
                (cx - 3, cy - radius + 3),
                (cx + 1, cy - radius + 3),
                (cx - 1, cy),
                (cx + 3, cy),
                (cx - 3, cy + radius - 3),
                (cx - 1, cy + radius - 3),
                (cx + 1, cy + radius - 3),
                (cx - 1, cy)
            ]
            pygame.draw.polygon(screen, YELLOW, bolt)
        elif btype == "shield":
            # Blue circle with a white border indicating a shield
            pygame.draw.circle(screen, LIGHT_BLUE, (cx, cy), radius)
            pygame.draw.circle(screen, WHITE, (cx, cy), radius, 2)
        else:  # triple-shot bonus
            pygame.draw.circle(screen, PURPLE, (cx, cy), radius)
            pygame.draw.line(screen, WHITE, (cx, cy + 6), (cx, cy - 7), 2)
            pygame.draw.line(screen, WHITE, (cx, cy + 6), (cx - 7, cy - 5), 2)
            pygame.draw.line(screen, WHITE, (cx, cy + 6), (cx + 7, cy - 5), 2)
            pygame.draw.circle(screen, ORANGE, (cx, cy), radius, 2)


# =========================
# Explosion logic
# =========================
def add_explosion(explosions, x, y):
    """Create a new explosion with particles and ring."""
    explosion = {
        "x": x,
        "y": y,
        "radius": 4,
        "max_radius": 38,
        "particles": []
    }
    for _ in range(18):
        particle = {
            "x": x,
            "y": y,
            "dx": random.randint(-6, 6),
            "dy": random.randint(-6, 6),
            "life": random.randint(12, 26),
            "size": random.randint(2, 5)
        }
        explosion["particles"].append(particle)
    explosions.append(explosion)
    play_sound(explosion_sound)


def draw_explosions(explosions):
    """Draw and update all ongoing explosions."""
    for explosion in explosions[:]:
        pygame.draw.circle(
            screen,
            ORANGE,
            (explosion["x"], explosion["y"]),
            explosion["radius"],
            3
        )
        pygame.draw.circle(
            screen,
            YELLOW,
            (explosion["x"], explosion["y"]),
            max(1, explosion["radius"] // 2),
            2
        )
        explosion["radius"] += 2
        for particle in explosion["particles"][:]:
            color = YELLOW if particle["life"] > 8 else ORANGE
            pygame.draw.circle(
                screen,
                color,
                (particle["x"], particle["y"]),
                particle["size"]
            )
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]
            particle["life"] -= 1
            if particle["life"] <= 0:
                explosion["particles"].remove(particle)
        if explosion["radius"] > explosion["max_radius"] and len(explosion["particles"]) == 0:
            explosions.remove(explosion)


# =========================
# Menu drawing
# =========================
def draw_start_screen(stars, high_score):
    """Render the main menu with high score information."""
    screen.fill(BLACK)
    draw_stars(stars)
    if game_logo is not None:
        draw_centered_image(game_logo, 55)
        title_y = 220
    else:
        title_y = 115
    draw_centered_text("Busting in space", TITLE_FONT, WHITE, title_y)
    draw_centered_text(f"High Score: {high_score}", FONT, ORANGE, title_y + 90)
    draw_centered_text("Press ENTER to start", FONT, GREEN, title_y + 170)
    draw_centered_text("Press S for settings", FONT, WHITE, title_y + 215)
    draw_centered_text("Press ESC to quit", FONT, GRAY, title_y + 260)
    draw_centered_text("Controls can be changed in Settings", SMALL_FONT, GRAY, title_y + 395)
    pygame.display.flip()


def draw_pause_screen():
    """Display a translucent overlay and pause instructions."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))
    draw_centered_text("PAUSED", BIG_FONT, WHITE, HEIGHT // 2 - 60)
    draw_centered_text(f"Press {key_name(settings['pause'])} to continue", FONT, GRAY, HEIGHT // 2 + 10)


def draw_settings_screen(stars, selected_setting):
    """Render the settings menu, highlighting the selected option."""
    screen.fill(BLACK)
    draw_stars(stars)
    draw_centered_text("SETTINGS", BIG_FONT, WHITE, 60)
    setting_rows = get_setting_rows()
    start_y = 140
    row_gap = 38
    for i, (label, value) in enumerate(setting_rows):
        y = start_y + i * row_gap
        if i == selected_setting:
            # highlight selected row
            pygame.draw.rect(
                screen,
                DARK_GRAY,
                pygame.Rect(70, y - 5, 460, 34),
                border_radius=8
            )
            label_color = GREEN
            value_color = ORANGE
        else:
            label_color = WHITE
            value_color = GRAY
        draw_text(label, FONT, label_color, 90, y)
        draw_text(value, FONT, value_color, 390, y)

    draw_centered_text("SHIP PREVIEW", SMALL_FONT, GRAY, 570)
    draw_player(pygame.Rect(WIDTH // 2 - PLAYER_WIDTH // 2, 645, PLAYER_WIDTH, PLAYER_HEIGHT))
    # Footer instructions
    if waiting_for_key is not None:
        draw_centered_text("Press a new key...", FONT, YELLOW, 735)
    else:
        draw_centered_text("UP/DOWN: select | LEFT/RIGHT: change", SMALL_FONT, GRAY, 735)
        draw_centered_text("ENTER: change key | BACKSPACE: reset controls | ESC: back", SMALL_FONT, GRAY, 770)
    pygame.display.flip()


def get_setting_rows():
    """Build the settings rows shown in the settings menu."""
    return [
        ("Master Volume", f"{int(settings['master_volume'] * 100)}%"),
        ("Music Volume", f"{int(settings['music_volume'] * 100)}%"),
        ("SFX Volume", f"{int(settings['sfx_volume'] * 100)}%"),
        ("Player Speed", str(settings['player_speed'])),
        ("Ship Design", SHIP_DESIGNS[settings["ship_design"]]),
        ("Starting Lives", str(settings['starting_lives'])),
        ("Move Left", key_name(settings['move_left'])),
        ("Move Right", key_name(settings['move_right'])),
        ("Shoot", key_name(settings['shoot'])),
        ("Pause", key_name(settings['pause'])),
        ("Mute", key_name(settings['mute'])),
    ]


def settings_row_count():
    """Return the number of rows in the settings menu."""
    return len(get_setting_rows())



def reset_controls_to_default():
    """Reset control keys to their default values."""
    settings["move_left"] = pygame.K_a
    settings["move_right"] = pygame.K_d
    settings["shoot"] = pygame.K_SPACE
    settings["pause"] = pygame.K_p
    settings["mute"] = pygame.K_m


def adjust_setting(index, direction):
    """Adjust a numeric setting based on selected index and direction."""
    if index == 0:
        settings["master_volume"] = max(0.0, min(1.0, settings["master_volume"] + 0.05 * direction))
        apply_volume_settings()
    elif index == 1:
        settings["music_volume"] = max(0.0, min(1.0, settings["music_volume"] + 0.05 * direction))
        apply_volume_settings()
    elif index == 2:
        settings["sfx_volume"] = max(0.0, min(1.0, settings["sfx_volume"] + 0.05 * direction))
        apply_volume_settings()
        play_sound(menu_sound)
    elif index == 3:
        settings["player_speed"] = max(3, min(14, settings["player_speed"] + direction))
    elif index == 4:
        settings["ship_design"] = (settings["ship_design"] + direction) % len(SHIP_DESIGNS)
        play_sound(menu_sound)
    elif index == 5:
        settings["starting_lives"] = max(1, min(9, settings["starting_lives"] + direction))


def setting_index_to_key_name(index):
    """Map a settings index to its corresponding key name in the settings dict."""
    mapping = {
        6: "move_left",
        7: "move_right",
        8: "shoot",
        9: "pause",
        10: "mute"
    }
    return mapping.get(index)


# =========================
# Initialization
# =========================
apply_volume_settings()
draw_startup_logo_splash()
start_background_music()

game_logo = load_game_logo()
stars = create_stars()

(
    player,
    bullets,
    enemies,
    explosions,
    score,
    lives,
    enemy_speed,
    last_enemy_spawn,
    last_auto_fire
) = reset_game()

# Game state variables
game_state = "start"
auto_fire = False
cheat_input = ""
paused = False
game_over_sound_played = False
high_score = load_high_score()
selected_setting = 0

# =========================
# Main game loop
# =========================
while True:
    clock.tick(60)
    current_time = pygame.time.get_ticks()

    # =========================
    # Event handling
    # =========================
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            # If remapping a control key in settings
            if waiting_for_key is not None:
                if event.key != pygame.K_ESCAPE:
                    settings[waiting_for_key] = event.key
                    play_sound(menu_sound)
                waiting_for_key = None
                continue

            # Global escape key behaviour
            if event.key == pygame.K_ESCAPE:
                if game_state == "settings":
                    game_state = "start"
                    play_sound(menu_sound)
                else:
                    pygame.quit()
                    sys.exit()

            # Toggle mute/unmute
            if event.key == settings["mute"]:
                toggle_sound()

            # Pause/unpause within playing state
            if game_state == "playing" and event.key == settings["pause"]:
                paused = not paused
                if paused:
                    pygame.mixer.music.pause()
                else:
                    if sound_enabled:
                        pygame.mixer.music.unpause()

            # -------------------------
            # Start menu events
            # -------------------------
            if game_state == "start":
                if event.key == pygame.K_RETURN:
                    (
                        player,
                        bullets,
                        enemies,
                        explosions,
                        score,
                        lives,
                        enemy_speed,
                        last_enemy_spawn,
                        last_auto_fire
                    ) = reset_game()
                    auto_fire = False
                    cheat_input = ""
                    paused = False
                    game_over_sound_played = False
                    game_state = "playing"
                    play_sound(start_sound)
                elif event.key == pygame.K_s:
                    selected_setting = 0
                    game_state = "settings"
                    play_sound(menu_sound)

            # -------------------------
            # Settings menu events
            # -------------------------
            elif game_state == "settings":
                if event.key == pygame.K_UP:
                    selected_setting = (selected_setting - 1) % settings_row_count()
                    play_sound(menu_sound)
                elif event.key == pygame.K_DOWN:
                    selected_setting = (selected_setting + 1) % settings_row_count()
                    play_sound(menu_sound)
                elif event.key == pygame.K_LEFT:
                    adjust_setting(selected_setting, -1)
                elif event.key == pygame.K_RIGHT:
                    adjust_setting(selected_setting, 1)
                elif event.key == pygame.K_RETURN:
                    key_setting = setting_index_to_key_name(selected_setting)
                    if key_setting is not None:
                        waiting_for_key = key_setting
                        play_sound(menu_sound)
                elif event.key == pygame.K_BACKSPACE:
                    reset_controls_to_default()
                    play_sound(menu_sound)

            # -------------------------
            # Playing state events
            # -------------------------
            elif game_state == "playing" and not paused:
                # Collect cheat code characters
                if event.unicode.isalpha():
                    cheat_input += event.unicode.lower()
                    if len(cheat_input) > 20:
                        cheat_input = cheat_input[-20:]
                    if "rapidfire" in cheat_input:
                        auto_fire = not auto_fire
                        cheat_input = ""
                        play_sound(bonus_sound)
                if event.key == settings["shoot"]:
                    shoot_bullet(player, bullets)

            # -------------------------
            # Game over events
            # -------------------------
            elif game_state == "game_over":
                if event.key == pygame.K_r:
                    (
                        player,
                        bullets,
                        enemies,
                        explosions,
                        score,
                        lives,
                        enemy_speed,
                        last_enemy_spawn,
                        last_auto_fire
                    ) = reset_game()
                    auto_fire = False
                    cheat_input = ""
                    paused = False
                    game_over_sound_played = False
                    game_state = "playing"
                    play_sound(start_sound)
                if event.key == pygame.K_RETURN:
                    game_state = "start"
                    game_over_sound_played = False

    # =========================
    # Non-menu drawing loops
    # =========================
    if game_state == "start":
        draw_start_screen(stars, high_score)
        continue

    if game_state == "settings":
        draw_settings_screen(stars, selected_setting)
        continue

    keys = pygame.key.get_pressed()

    # =========================
    # Gameplay update logic
    # =========================
    if game_state == "playing" and not paused:
        # Player movement using either custom keys or arrow keys
        if keys[settings["move_left"]] or keys[pygame.K_LEFT]:
            player.x -= settings["player_speed"]
        if keys[settings["move_right"]] or keys[pygame.K_RIGHT]:
            player.x += settings["player_speed"]
        # Clamp player within screen
        if player.left < 0:
            player.left = 0
        if player.right > WIDTH:
            player.right = WIDTH

        # Determine whether rapid fire is active from cheat or temporary bonus
        rapid_fire_active = auto_fire or (current_time < rapid_fire_bonus_timer)
        # Automatic bullet firing when rapid fire is active
        if rapid_fire_active:
            if current_time - last_auto_fire > RAPID_FIRE_DELAY:
                shoot_bullet(player, bullets)
                last_auto_fire = current_time

        # Spawn a new enemy at regular intervals
        if current_time - last_enemy_spawn > ENEMY_SPAWN_DELAY:
            spawn_enemy(enemies)
            last_enemy_spawn = current_time

        # Update bullets and remove those that leave the screen
        for bullet in bullets[:]:
            rect = bullet["rect"]
            rect.x += bullet["dx"]
            rect.y += bullet["dy"]
            if rect.bottom < 0 or rect.right < 0 or rect.left > WIDTH:
                bullets.remove(bullet)

        # Update enemies and handle movement, collisions and removal
        for enemy in enemies[:]:
            rect = enemy["rect"]
            etype = enemy["type"]
            # Vertical descent
            rect.y += enemy_speed
            # Horizontal movement for moving and split_child types
            if etype in ("moving", "split_child"):
                rect.x += enemy["dx"]
                # Bounce off side walls
                if rect.left <= 0 or rect.right >= WIDTH:
                    enemy["dx"] *= -1
                    rect.x += enemy["dx"] * 2
            # Remove enemy if it exits the screen
            if rect.top > HEIGHT:
                # Remove enemies that pass off-screen without penalising the player.
                # Lives should only decrease when the ship is hit directly by an enemy.
                enemies.remove(enemy)
                continue
            # Collision with the player's ship
            if rect.colliderect(player):
                if player_shield:
                    # Consume shield and destroy enemy
                    player_shield = False
                    add_explosion(explosions, rect.centerx, rect.centery)
                    enemies.remove(enemy)
                    continue
                else:
                    # Reduce lives when the player is hit. End the game only when lives reach zero.
                    lives -= 1
                    if lives <= 0:
                        game_state = "game_over"
                        high_score = update_high_score(score, high_score)
                        if not game_over_sound_played:
                            play_sound(game_over_sound)
                            game_over_sound_played = True
                        break
                    # Otherwise, destroy the enemy and keep playing
                    add_explosion(explosions, rect.centerx, rect.centery)
                    enemies.remove(enemy)
                    continue

        # Handle bullet-enemy collisions and enemy destruction
        for bullet in bullets[:]:
            hit_enemy = None
            for enemy in enemies:
                if bullet["rect"].colliderect(enemy["rect"]):
                    hit_enemy = enemy
                    break
            if hit_enemy is not None:
                # Remove the bullet
                if bullet in bullets:
                    bullets.remove(bullet)
                # Apply damage
                hit_enemy["health"] -= 1
                if hit_enemy["health"] <= 0:
                    # Spawn explosion and potential bonus
                    add_explosion(explosions, hit_enemy["rect"].centerx, hit_enemy["rect"].centery)
                    spawn_bonus(hit_enemy["rect"].centerx, hit_enemy["rect"].y)
                    # Split enemies spawn child enemies when destroyed
                    if hit_enemy["type"] == "split":
                        # When a split enemy is destroyed, spawn two split_child enemies. Each child
                        # moves horizontally faster and awards fewer points when destroyed.
                        for dx_dir in (-3, 3):
                            child_rect = pygame.Rect(hit_enemy["rect"].x, hit_enemy["rect"].y, ENEMY_WIDTH, ENEMY_HEIGHT)
                            enemies.append({
                                "rect": child_rect,
                                "type": "split_child",
                                "health": 1,
                                "dx": dx_dir,
                                "score_value": 1,
                            })
                    # Remove the enemy
                    if hit_enemy in enemies:
                        enemies.remove(hit_enemy)
                    # Increment score based on the enemy's difficulty
                    score += hit_enemy.get("score_value", 1)
                    high_score = update_high_score(score, high_score)
                    # Increase difficulty every 10 points regardless of enemy type
                    if score % 10 == 0:
                        enemy_speed += 0.5
                        play_sound(bonus_sound)
                # Continue to next bullet
                continue

        # Update bonus items
        for bonus in bonuses[:]:
            bonus["rect"].y += BONUS_SPEED
            # Remove bonus if it falls off-screen
            if bonus["rect"].top > HEIGHT:
                bonuses.remove(bonus)
                continue
            # Player collects bonus
            if bonus["rect"].colliderect(player):
                if bonus["type"] == "life":
                    lives += 1
                elif bonus["type"] == "rapid":
                    # Activate rapid fire for 5 seconds
                    rapid_fire_bonus_timer = current_time + 5000
                elif bonus["type"] == "shield":
                    player_shield = True
                else:  # triple-shot bonus
                    triple_shot_bonus_timer = current_time + TRIPLE_SHOT_DURATION
                bonuses.remove(bonus)
                play_sound(bonus_sound)
                continue

    # =========================
    # Draw the game frame
    # =========================
    screen.fill(BLACK)
    draw_stars(stars)
    draw_player(player)
    draw_bullets(bullets)
    draw_enemies(enemies)
    # Draw falling bonus items after enemies so they appear on top
    draw_bonuses(bonuses)
    draw_explosions(explosions)
    # Score and UI text
    draw_text(f"Score: {score}", FONT, WHITE, 10, 10)
    draw_text(f"High: {high_score}", SMALL_FONT, ORANGE, 10, 42)
    draw_text(f"Lives: {lives}", FONT, WHITE, WIDTH - 110, 10)
    # Show rapid‑fire status (from cheat or bonus)
    if auto_fire or (pygame.time.get_ticks() < rapid_fire_bonus_timer):
        draw_text("RAPID FIRE ON", FONT, ORANGE, WIDTH // 2 - 100, 10)
    if pygame.time.get_ticks() < triple_shot_bonus_timer:
        draw_text("TRIPLE SHOT", FONT, PURPLE, WIDTH // 2 - 85, 35)
    # Show shield status when active
    if player_shield:
        draw_text("SHIELD", FONT, LIGHT_BLUE, WIDTH // 2 - 45, 65)
    # Show mute status
    if not sound_enabled:
        draw_text("MUTED", FONT, GRAY, WIDTH // 2 - 45, 95)
    # Pause overlay
    if paused:
        draw_pause_screen()
    # Game over overlay
    if game_state == "game_over":
        draw_centered_text("GAME OVER", BIG_FONT, RED, HEIGHT // 2 - 90)
        draw_centered_text(f"Final Score: {score}", FONT, WHITE, HEIGHT // 2 - 20)
        draw_centered_text(f"High Score: {high_score}", FONT, ORANGE, HEIGHT // 2 + 20)
        draw_centered_text("Press R to restart", FONT, WHITE, HEIGHT // 2 + 70)
        draw_centered_text("Press ENTER for menu", FONT, GRAY, HEIGHT // 2 + 110)
        draw_centered_text("Press ESC to quit", FONT, GRAY, HEIGHT // 2 + 150)
    # Refresh display
    pygame.display.flip()
