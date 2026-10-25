"""
MEMORIA - The Game That Forgets You
Development of an Adaptive Memory-Based Psychological Puzzle Game Using Python.

Run with:   py main.py
Needs:      Python 3 and pygame-ce  (pip install pygame-ce)

Everything lives in this one file so it is easy to read, demonstrate and explain:
    1. Settings and colours
    2. Drawing helpers (glow, text, object icons, symbols)
    3. Button, Player, DatabaseManager, LevelManager classes
    4. Game class (screens, gameplay, scoring)
"""

import math
import os
import random
import sqlite3
import sys
from datetime import datetime

os.environ.setdefault("SDL_VIDEO_CENTERED", "1")   # open the window centred
import pygame                                      # pygame-ce is imported as "pygame"

# ----------------------------------------------------------------------------
# 1. SETTINGS
# ----------------------------------------------------------------------------
WIDTH, HEIGHT = 1000, 650
FPS = 60
TOTAL_LEVELS = 5
MAX_NAME_LENGTH = 16

# Scoring rules
POINTS_CORRECT = 100       # points for one correct answer
TIME_BONUS_MAX = 50        # extra points for answering quickly (scaled by time left)
HINT_PENALTY = 25          # points lost when a hint is used
COMPLETION_BONUS = 100     # points for passing a level

# Adaptive difficulty range (see LevelManager.update_offset)
MIN_OFFSET, MAX_OFFSET = -1, 2

# Colours (dark purple mystery theme)
COL_BG_TOP = (9, 5, 20)
COL_BG_BOTTOM = (38, 15, 70)
COL_PANEL = (20, 12, 38)
COL_CARD = (31, 20, 56)
COL_PANEL_EDGE = (96, 68, 156)
COL_TEXT = (234, 227, 249)
COL_MUTED = (160, 146, 196)
COL_ACCENT = (160, 110, 255)
COL_LAVENDER = (198, 178, 242)
COL_GOOD = (122, 222, 160)
COL_BAD = (244, 112, 134)
COL_GOLD = (250, 208, 112)

# Layout shared by drawing code and click code, so they always match
ROOM_RECT = pygame.Rect(40, 130, 920, 262)
CARD_W, CARD_H = 136, 118
PAD_RADIUS = 52

OBJECT_NAMES = ["Key", "Book", "Clock", "Lamp", "Cup", "Candle",
                "Mirror", "Vase", "Chair", "Umbrella", "Glasses", "Bottle"]

OBJECT_COLORS = {
    "Key": (250, 208, 112), "Book": (190, 90, 150), "Clock": (190, 170, 240),
    "Lamp": (255, 190, 90), "Cup": (90, 200, 200), "Candle": (240, 228, 205),
    "Mirror": (150, 190, 240), "Vase": (232, 120, 160), "Chair": (190, 140, 100),
    "Umbrella": (150, 110, 240), "Glasses": (210, 200, 250), "Bottle": (100, 210, 150),
}

# Pads used by the sequence levels: (shape, colour, spoken name)
PAD_STYLES = [
    ("circle", (170, 110, 255), "Violet Circle"),
    ("square", (80, 200, 230), "Cyan Square"),
    ("triangle", (250, 190, 70), "Amber Triangle"),
    ("diamond", (240, 100, 150), "Rose Diamond"),
    ("hexagon", (110, 220, 140), "Green Hexagon"),
    ("star", (100, 140, 255), "Blue Star"),
]

LEVEL_ICONS = {1: "Key", 2: "Mirror", 3: "Chair", 4: "Clock", 5: "Candle"}

BUTTON_STYLES = {
    "primary": {"fill": (88, 52, 170), "hover": (126, 82, 222),
                "border": (196, 166, 255), "text": (248, 243, 255)},
    "secondary": {"fill": (30, 20, 56), "hover": (54, 38, 94),
                  "border": (126, 98, 190), "text": (222, 212, 245)},
    "danger": {"fill": (104, 32, 62), "hover": (152, 48, 86),
               "border": (240, 140, 170), "text": (255, 236, 242)},
}


# ----------------------------------------------------------------------------
# 2. DRAWING HELPERS
# ----------------------------------------------------------------------------
def clamp(value, low, high):
    return max(low, min(high, value))


def lerp_color(color_a, color_b, amount):
    """Blend two colours. amount 0 = color_a, 1 = color_b."""
    amount = clamp(amount, 0.0, 1.0)
    return (int(color_a[0] + (color_b[0] - color_a[0]) * amount),
            int(color_a[1] + (color_b[1] - color_a[1]) * amount),
            int(color_a[2] + (color_b[2] - color_a[2]) * amount))


_GLOW_CACHE = {}


def get_glow(radius, color, strength=110):
    """A soft round glow (cached so it is only built once)."""
    key = (radius, color, strength)
    glow = _GLOW_CACHE.get(key)
    if glow is None:
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        steps = 16
        for i in range(steps, 0, -1):
            alpha = int(strength * (1 - i / steps) ** 2)
            pygame.draw.circle(glow, (color[0], color[1], color[2], alpha),
                               (radius, radius), max(1, int(radius * i / steps)))
        _GLOW_CACHE[key] = glow
    return glow


def blit_glow(surface, center, radius, color, strength=110):
    surface.blit(get_glow(radius, color, strength), (center[0] - radius, center[1] - radius))


def draw_rect_glow(surface, rect, color, spread=12, strength=80, radius=14):
    """A soft glowing outline around a rectangle."""
    glow = pygame.Surface((rect.width + spread * 2, rect.height + spread * 2), pygame.SRCALPHA)
    for i in range(spread):
        alpha = int(strength * ((i + 1) / spread) ** 2)
        inner = pygame.Rect(i, i, rect.width + (spread - i) * 2, rect.height + (spread - i) * 2)
        pygame.draw.rect(glow, (color[0], color[1], color[2], alpha), inner, 2,
                         border_radius=radius + spread - i)
    surface.blit(glow, (rect.x - spread, rect.y - spread))


def draw_text(surface, text, font, color, pos, anchor="topleft"):
    """Draw one line of text. anchor can be topleft, center, midtop, topright..."""
    if text == "":
        return pygame.Rect(int(pos[0]), int(pos[1]), 0, 0)
    image = font.render(text, True, color)
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(image, rect)
    return rect


def wrap_text(text, font, max_width):
    """Split text into lines that fit max_width. Blank lines are kept."""
    lines = []
    for paragraph in text.split("\n"):
        if paragraph.strip() == "":
            lines.append("")
            continue
        current = ""
        for word in paragraph.split(" "):
            test = (current + " " + word).strip()
            if font.size(test)[0] <= max_width or current == "":
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def draw_wrapped(surface, text, font, color, x, y, max_width, line_height, align="left"):
    """Draw wrapped text. Returns the y position after the last line."""
    for line in wrap_text(text, font, max_width):
        if line:
            if align == "center":
                draw_text(surface, line, font, color, (x, y), "midtop")
            else:
                draw_text(surface, line, font, color, (x, y), "topleft")
        y += line_height
    return y


def fit_line(text, font, max_width):
    """Shorten a line with '...' if it is too wide."""
    if font.size(text)[0] <= max_width:
        return text
    while len(text) > 1 and font.size(text + "...")[0] > max_width:
        text = text[:-1]
    return text + "..."


def draw_panel(surface, rect, fill=COL_PANEL, border=COL_PANEL_EDGE, radius=18):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, 2, border_radius=radius)


def draw_object_icon(surface, name, center, size, dim=False):
    """Draw one of the 12 room objects using only shapes (no image files)."""
    s = size / 100.0
    ox = center[0] - 50 * s
    oy = center[1] - 50 * s
    color = OBJECT_COLORS.get(name, COL_LAVENDER)
    if dim:
        color = lerp_color(color, (30, 22, 50), 0.65)
    dark = lerp_color(color, (10, 6, 22), 0.55)
    light = lerp_color(color, (255, 255, 255), 0.45)

    def p(x, y):
        return (int(ox + x * s), int(oy + y * s))

    def n(value):
        return max(1, int(value * s))

    def box(x, y, w, h):
        return pygame.Rect(int(ox + x * s), int(oy + y * s), max(1, int(w * s)), max(1, int(h * s)))

    draw = pygame.draw
    if name == "Key":
        draw.circle(surface, color, p(30, 40), n(18), n(7))
        draw.line(surface, color, p(45, 48), p(86, 76), n(8))
        draw.line(surface, color, p(72, 66), p(66, 80), n(6))
        draw.line(surface, color, p(82, 73), p(77, 86), n(6))
    elif name == "Book":
        draw.rect(surface, color, box(22, 14, 56, 72), border_radius=n(5))
        draw.rect(surface, dark, box(22, 14, 12, 72), border_radius=n(5))
        draw.rect(surface, light, box(42, 30, 28, 6), border_radius=n(2))
        draw.rect(surface, light, box(42, 44, 20, 5), border_radius=n(2))
        draw.rect(surface, light, box(22, 14, 56, 72), n(2), border_radius=n(5))
    elif name == "Clock":
        draw.circle(surface, color, p(30, 22), n(9))
        draw.circle(surface, color, p(70, 22), n(9))
        draw.circle(surface, dark, p(50, 54), n(34))
        draw.circle(surface, color, p(50, 54), n(34), n(5))
        for angle in (0, 90, 180, 270):
            a = math.radians(angle)
            draw.line(surface, light, p(50 + 26 * math.cos(a), 54 + 26 * math.sin(a)),
                      p(50 + 31 * math.cos(a), 54 + 31 * math.sin(a)), n(3))
        draw.line(surface, light, p(50, 54), p(50, 34), n(4))
        draw.line(surface, light, p(50, 54), p(64, 60), n(4))
    elif name == "Lamp":
        draw.polygon(surface, color, [p(32, 16), p(68, 16), p(84, 52), p(16, 52)])
        draw.polygon(surface, light, [p(32, 16), p(68, 16), p(84, 52), p(16, 52)], n(2))
        draw.line(surface, light, p(50, 52), p(50, 78), n(5))
        draw.ellipse(surface, light, box(30, 76, 40, 12))
        draw.circle(surface, COL_GOLD if not dim else dark, p(50, 60), n(5))
    elif name == "Cup":
        draw.polygon(surface, color, [p(22, 36), p(68, 36), p(62, 78), p(28, 78)])
        draw.arc(surface, color, box(58, 42, 26, 28), -math.pi / 2, math.pi / 2, n(6))
        draw.ellipse(surface, light, box(14, 76, 64, 12))
        draw.line(surface, light, p(38, 28), p(42, 16), n(3))
        draw.line(surface, light, p(52, 28), p(48, 14), n(3))
    elif name == "Candle":
        draw.rect(surface, color, box(36, 40, 28, 46), border_radius=n(4))
        draw.ellipse(surface, light, box(36, 37, 28, 8))
        draw.rect(surface, light, box(30, 84, 40, 7), border_radius=n(3))
        draw.line(surface, dark, p(50, 36), p(50, 41), n(3))
        flame_outer = COL_GOLD if not dim else dark
        flame_inner = (255, 150, 70) if not dim else dark
        draw.polygon(surface, flame_outer, [p(50, 12), p(40, 30), p(50, 38), p(60, 30)])
        draw.polygon(surface, flame_inner, [p(50, 20), p(45, 31), p(50, 36), p(55, 31)])
    elif name == "Mirror":
        draw.ellipse(surface, color, box(24, 8, 52, 72))
        draw.ellipse(surface, lerp_color(color, (20, 20, 60), 0.6), box(31, 15, 38, 58))
        draw.line(surface, light, p(40, 30), p(48, 22), n(4))
        draw.line(surface, light, p(40, 40), p(44, 36), n(3))
        draw.line(surface, color, p(50, 80), p(38, 94), n(5))
        draw.line(surface, color, p(50, 80), p(62, 94), n(5))
    elif name == "Vase":
        stem = (110, 200, 140) if not dim else dark
        draw.line(surface, stem, p(50, 40), p(40, 14), n(3))
        draw.line(surface, stem, p(50, 40), p(60, 12), n(3))
        draw.line(surface, stem, p(50, 40), p(50, 8), n(3))
        draw.circle(surface, COL_GOLD if not dim else dark, p(40, 14), n(7))
        draw.circle(surface, (200, 170, 255) if not dim else dark, p(60, 12), n(7))
        draw.circle(surface, light, p(50, 8), n(7))
        draw.ellipse(surface, color, box(26, 44, 48, 46))
        draw.rect(surface, color, box(41, 36, 18, 16))
        draw.ellipse(surface, light, box(38, 32, 24, 8))
    elif name == "Chair":
        draw.rect(surface, color, box(28, 10, 8, 52), border_radius=n(2))
        draw.rect(surface, color, box(64, 10, 8, 52), border_radius=n(2))
        draw.rect(surface, color, box(36, 18, 28, 6))
        draw.rect(surface, color, box(36, 32, 28, 6))
        draw.rect(surface, light, box(24, 52, 56, 9), border_radius=n(3))
        draw.rect(surface, color, box(28, 60, 8, 32))
        draw.rect(surface, color, box(64, 60, 8, 32))
    elif name == "Umbrella":
        arch = [p(50 + 40 * math.cos(math.pi * i / 12), 54 - 38 * math.sin(math.pi * i / 12))
                for i in range(13)]
        draw.polygon(surface, color, arch)
        for rib_x in (18, 34, 66, 82):
            draw.line(surface, dark, p(50, 16), p(rib_x, 54), n(2))
        draw.line(surface, light, p(50, 54), p(50, 81), n(5))
        draw.arc(surface, light, box(38, 74, 14, 14), math.pi, 2 * math.pi, n(5))
    elif name == "Glasses":
        lens = lerp_color(color, (20, 14, 50), 0.6)
        draw.circle(surface, lens, p(30, 52), n(19))
        draw.circle(surface, lens, p(70, 52), n(19))
        draw.circle(surface, color, p(30, 52), n(19), n(5))
        draw.circle(surface, color, p(70, 52), n(19), n(5))
        draw.line(surface, color, p(48, 48), p(52, 48), n(5))
        draw.line(surface, color, p(11, 48), p(2, 38), n(4))
        draw.line(surface, color, p(89, 48), p(98, 38), n(4))
        draw.line(surface, light, p(22, 46), p(28, 42), n(3))
    elif name == "Bottle":
        draw.rect(surface, color, box(32, 38, 36, 52), border_radius=n(8))
        draw.rect(surface, color, box(43, 16, 14, 26))
        draw.rect(surface, light, box(40, 8, 20, 9), border_radius=n(3))
        draw.rect(surface, light, box(37, 56, 26, 18), border_radius=n(3))
        draw.line(surface, dark, p(42, 62), p(58, 62), n(2))
        draw.line(surface, dark, p(42, 68), p(54, 68), n(2))
    else:
        draw.circle(surface, color, center, n(30), n(5))


def draw_symbol(surface, kind, center, radius, color):
    """Draw one of the six pad shapes."""
    cx, cy = center
    r = radius
    if kind == "circle":
        pygame.draw.circle(surface, color, (cx, cy), r)
    elif kind == "square":
        pygame.draw.rect(surface, color, pygame.Rect(int(cx - r * 0.85), int(cy - r * 0.85),
                                                     int(r * 1.7), int(r * 1.7)), border_radius=4)
    elif kind == "triangle":
        pygame.draw.polygon(surface, color, [(cx, cy - r), (cx + r * 0.95, cy + r * 0.75),
                                             (cx - r * 0.95, cy + r * 0.75)])
    elif kind == "diamond":
        pygame.draw.polygon(surface, color, [(cx, cy - r), (cx + r * 0.8, cy),
                                             (cx, cy + r), (cx - r * 0.8, cy)])
    elif kind == "hexagon":
        pygame.draw.polygon(surface, color, [(cx + r * math.cos(k * math.pi / 3),
                                              cy + r * math.sin(k * math.pi / 3)) for k in range(6)])
    else:  # star
        points = []
        for k in range(10):
            radius_k = r if k % 2 == 0 else r * 0.45
            angle = -math.pi / 2 + k * math.pi / 5
            points.append((cx + radius_k * math.cos(angle), cy + radius_k * math.sin(angle)))
        pygame.draw.polygon(surface, color, points)


def draw_pad(surface, center, kind, color, active, hover=False):
    """A round pad that glows when active."""
    if active:
        blit_glow(surface, center, PAD_RADIUS + 40, color, 130)
    pygame.draw.circle(surface, (22, 14, 40), center, PAD_RADIUS)
    shade = 0.0 if active else (0.35 if hover else 0.6)
    ring = lerp_color(color, (20, 12, 40), shade)
    pygame.draw.circle(surface, ring, center, PAD_RADIUS, 4)
    draw_symbol(surface, kind, center, int(PAD_RADIUS * 0.5), lerp_color(color, (20, 12, 40), shade * 0.8))


def draw_card(surface, rect, name, font, state="normal"):
    """An illustrated card: icon on top, label below."""
    fill, border, width = COL_CARD, COL_PANEL_EDGE, 2
    text_color = COL_TEXT
    if state == "selected":
        draw_rect_glow(surface, rect, COL_ACCENT, 12, 110)
        fill, border, width = lerp_color(COL_CARD, COL_ACCENT, 0.25), COL_ACCENT, 3
    elif state == "hover":
        border = COL_LAVENDER
    elif state == "correct":
        draw_rect_glow(surface, rect, COL_GOOD, 12, 110)
        border, width = COL_GOOD, 4
    elif state == "wrong":
        draw_rect_glow(surface, rect, COL_BAD, 12, 110)
        border, width = COL_BAD, 4
    elif state == "disabled":
        fill, border, text_color = (20, 14, 34), (50, 40, 76), (96, 86, 124)
    pygame.draw.rect(surface, fill, rect, border_radius=14)
    pygame.draw.rect(surface, border, rect, width, border_radius=14)
    draw_object_icon(surface, name, (rect.centerx, rect.y + 50), 74, dim=(state == "disabled"))
    draw_text(surface, name, font, text_color, (rect.centerx, rect.bottom - 16), "center")


def slot_rects(count):
    """Rectangles for 'count' card slots, centred inside the room panel."""
    if count <= 5:
        row_sizes = [count]
    else:
        first = (count + 1) // 2
        row_sizes = [first, count - first]
    gap_x, gap_y = 22, 12
    total_height = len(row_sizes) * CARD_H + (len(row_sizes) - 1) * gap_y
    y = ROOM_RECT.centery - total_height // 2
    rects = []
    for size in row_sizes:
        row_width = size * CARD_W + (size - 1) * gap_x
        x = ROOM_RECT.centerx - row_width // 2
        for column in range(size):
            rects.append(pygame.Rect(x + column * (CARD_W + gap_x), y, CARD_W, CARD_H))
        y += CARD_H + gap_y
    return rects


def pad_centers(count):
    spacing = 150
    start_x = ROOM_RECT.centerx - (count - 1) * spacing / 2
    return [(int(start_x + i * spacing), ROOM_RECT.centery) for i in range(count)]


def slot_text(slot):
    """Human-readable position for the 4x2 room grid."""
    return "row %d, column %d" % (slot // 4 + 1, slot % 4 + 1)


# ----------------------------------------------------------------------------
# 3. SIMPLE CLASSES
# ----------------------------------------------------------------------------
class Button:
    """A clickable button. The same rect is used for drawing and clicking."""

    def __init__(self, rect, text, callback, style="primary",
                 enabled_check=None, visible_check=None, pulse_check=None):
        self.rect = pygame.Rect(rect)
        self.text = text                  # a string, or a function returning a string
        self.callback = callback
        self.style = style
        self.enabled_check = enabled_check
        self.visible_check = visible_check
        self.pulse_check = pulse_check

    def is_enabled(self):
        return self.enabled_check() if self.enabled_check else True

    def is_visible(self):
        return self.visible_check() if self.visible_check else True

    def label(self):
        return self.text() if callable(self.text) else self.text

    def draw(self, surface, font, mouse_pos, now):
        if not self.is_visible():
            return
        enabled = self.is_enabled()
        hover = enabled and self.rect.collidepoint(mouse_pos)
        colors = BUTTON_STYLES[self.style]
        if not enabled:
            fill, border, text_color = (30, 24, 44), (64, 56, 86), (118, 108, 140)
        else:
            fill = colors["hover"] if hover else colors["fill"]
            border, text_color = colors["border"], colors["text"]
        if hover:
            draw_rect_glow(surface, self.rect, colors["border"], 12, 90, 12)
        elif enabled and self.pulse_check and self.pulse_check():
            draw_rect_glow(surface, self.rect, COL_GOLD, 12, int(50 + 50 * (0.5 + 0.5 * math.sin(now * 4))), 12)
        pygame.draw.rect(surface, fill, self.rect, border_radius=12)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=12)
        draw_text(surface, self.label(), font, text_color, self.rect.center, "center")


class Player:
    """Holds one player's profile and progress."""

    def __init__(self, name, player_id=None):
        self.player_id = player_id
        self.name = name
        self.unlocked_level = 1
        self.difficulty_offset = 0
        self.total_correct = 0
        self.total_questions = 0
        self.levels = {n: {"completed": False, "best_score": 0, "attempts": 0}
                       for n in range(1, TOTAL_LEVELS + 1)}

    def total_score(self):
        """Overall score = sum of the BEST score of each level (retries never add up)."""
        return sum(record["best_score"] for record in self.levels.values())

    def best_level_score(self):
        return max(record["best_score"] for record in self.levels.values())

    def best_level_number(self):
        best_number, best_value = 0, 0
        for number, record in self.levels.items():
            if record["best_score"] > best_value:
                best_number, best_value = number, record["best_score"]
        return best_number

    def completed_count(self):
        return sum(1 for record in self.levels.values() if record["completed"])

    def all_completed(self):
        return self.completed_count() == TOTAL_LEVELS

    def accuracy_percent(self):
        if self.total_questions == 0:
            return 0
        return int(round(100.0 * self.total_correct / self.total_questions))

    def is_unlocked(self, level):
        return 1 <= level <= self.unlocked_level

    def register_question(self, correct):
        """Called exactly once for every answered question."""
        self.total_questions += 1
        if correct:
            self.total_correct += 1

    def register_level_result(self, level, score, passed):
        record = self.levels[level]
        record["attempts"] += 1
        record["best_score"] = max(record["best_score"], score)
        if passed:
            record["completed"] = True
            self.unlocked_level = max(self.unlocked_level, min(TOTAL_LEVELS, level + 1))


class DatabaseManager:
    """Saves and loads players using SQLite (standard library)."""

    def __init__(self, filename="memoria_save.db"):
        folder = os.path.dirname(os.path.abspath(__file__))
        self.path = os.path.join(folder, filename)
        self.save_ok = True
        try:
            self.connection = self._open(self.path)
        except (sqlite3.Error, OSError):
            # Could not use the file: keep playing, but progress will not be saved.
            self.save_ok = False
            self.connection = self._open(":memory:")

    def _open(self, target):
        connection = sqlite3.connect(target)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS players (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                   unlocked_level INTEGER NOT NULL DEFAULT 1,
                   difficulty_offset INTEGER NOT NULL DEFAULT 0,
                   total_correct INTEGER NOT NULL DEFAULT 0,
                   total_questions INTEGER NOT NULL DEFAULT 0,
                   best_score INTEGER NOT NULL DEFAULT 0,
                   overall_score INTEGER NOT NULL DEFAULT 0,
                   last_played TEXT NOT NULL)""")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS level_progress (
                   player_id INTEGER NOT NULL,
                   level_number INTEGER NOT NULL,
                   completed INTEGER NOT NULL DEFAULT 0,
                   best_score INTEGER NOT NULL DEFAULT 0,
                   attempts INTEGER NOT NULL DEFAULT 0,
                   PRIMARY KEY (player_id, level_number),
                   FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE)""")
        connection.commit()
        return connection

    def _query_one(self, sql, params=()):
        try:
            return self.connection.execute(sql, params).fetchone()
        except sqlite3.Error:
            return None

    def player_exists(self, name):
        return self._query_one("SELECT id FROM players WHERE name = ?", (name,)) is not None

    def get_latest_player_name(self):
        row = self._query_one("SELECT name FROM players ORDER BY last_played DESC, id DESC LIMIT 1")
        return row["name"] if row else None

    def create_player(self, name):
        """Create a fresh profile. An existing profile with the same name is replaced."""
        player = Player(name)
        try:
            with self.connection:
                old = self.connection.execute("SELECT id FROM players WHERE name = ?", (name,)).fetchone()
                if old:
                    self.connection.execute("DELETE FROM level_progress WHERE player_id = ?", (old["id"],))
                    self.connection.execute("DELETE FROM players WHERE id = ?", (old["id"],))
                cursor = self.connection.execute(
                    "INSERT INTO players (name, last_played) VALUES (?, ?)",
                    (name, datetime.now().isoformat()))
                player.player_id = cursor.lastrowid
                for level in range(1, TOTAL_LEVELS + 1):
                    self.connection.execute(
                        "INSERT INTO level_progress (player_id, level_number) VALUES (?, ?)",
                        (player.player_id, level))
        except sqlite3.Error:
            self.save_ok = False
            player.player_id = None
        return player

    def load_player(self, name):
        """Load a saved player. Returns None if missing. Bad values are repaired."""
        row = self._query_one("SELECT * FROM players WHERE name = ?", (name,))
        if row is None:
            return None
        player = Player(row["name"], row["id"])
        player.unlocked_level = clamp(int(row["unlocked_level"] or 1), 1, TOTAL_LEVELS)
        player.difficulty_offset = clamp(int(row["difficulty_offset"] or 0), MIN_OFFSET, MAX_OFFSET)
        player.total_correct = max(0, int(row["total_correct"] or 0))
        player.total_questions = max(player.total_correct, int(row["total_questions"] or 0))
        try:
            rows = self.connection.execute(
                "SELECT * FROM level_progress WHERE player_id = ?", (player.player_id,)).fetchall()
        except sqlite3.Error:
            rows = []
        for level_row in rows:
            number = level_row["level_number"]
            if number in player.levels:
                player.levels[number] = {"completed": bool(level_row["completed"]),
                                         "best_score": max(0, int(level_row["best_score"])),
                                         "attempts": max(0, int(level_row["attempts"]))}
        # Repair: a completed level always unlocks the next one.
        for number, record in player.levels.items():
            if record["completed"]:
                player.unlocked_level = max(player.unlocked_level, min(TOTAL_LEVELS, number + 1))
        return player

    def save_player(self, player):
        if player.player_id is None:
            return False
        try:
            with self.connection:
                self.connection.execute(
                    """UPDATE players SET unlocked_level = ?, difficulty_offset = ?,
                       total_correct = ?, total_questions = ?, best_score = ?,
                       overall_score = ?, last_played = ? WHERE id = ?""",
                    (player.unlocked_level, player.difficulty_offset, player.total_correct,
                     player.total_questions, player.best_level_score(), player.total_score(),
                     datetime.now().isoformat(), player.player_id))
                for number, record in player.levels.items():
                    self.connection.execute(
                        """INSERT OR REPLACE INTO level_progress
                           (player_id, level_number, completed, best_score, attempts)
                           VALUES (?, ?, ?, ?, ?)""",
                        (player.player_id, number, int(record["completed"]),
                         record["best_score"], record["attempts"]))
            return True
        except sqlite3.Error:
            self.save_ok = False
            return False

    def close(self):
        try:
            self.connection.close()
        except sqlite3.Error:
            pass


class LevelManager:
    """Builds puzzles for the five levels and holds the adaptive-difficulty rules.

    ADAPTIVE DIFFICULTY (simple rules, no machine learning):
      The player has a difficulty 'offset' from -1 to +2.
        wrong answer or timeout                      -> offset - 1  (easier)
        correct, no hint, with >= 25% time left      -> offset + 1  (harder)
        correct but slow, or correct with a hint     -> unchanged
      The offset picks values from the tables below (object count, time, etc.).
    """

    TITLES = {1: "The Forgotten Room", 2: "False Memories", 3: "The Changing Room",
              4: "The Memory Sequence", 5: "The Final Reconstruction"}
    OFFSET_NAMES = {-1: "Gentle", 0: "Normal", 1: "Challenging", 2: "Intense"}

    OBSERVE_SECONDS = {-1: 20, 0: 15, 1: 13, 2: 11}
    ANSWER_SECONDS = {-1: 26, 0: 20, 1: 18, 2: 16}
    SEQUENCE_LENGTH = {-1: 3, 0: 4, 1: 5, 2: 6}
    PAD_COUNT = {-1: 4, 0: 5, 1: 6, 2: 6}
    SHOW_TIMES = {-1: (0.9, 0.30), 0: (0.7, 0.25), 1: (0.6, 0.22), 2: (0.5, 0.20)}

    @staticmethod
    def difficulty_name(offset):
        return LevelManager.OFFSET_NAMES.get(offset, "Normal")

    @staticmethod
    def update_offset(offset, correct, hints_used, time_fraction):
        if not correct:
            offset -= 1
        elif hints_used == 0 and time_fraction >= 0.25:
            offset += 1
        return clamp(offset, MIN_OFFSET, MAX_OFFSET)

    def observation_time(self, offset):
        return self.OBSERVE_SECONDS[offset]

    def answer_time(self, offset):
        return self.ANSWER_SECONDS[offset]

    # ----- sequence helpers -----
    def make_sequence(self, length, pad_count):
        """Random pad order. The same pad never appears three times in a row."""
        sequence = []
        while len(sequence) < length:
            pad = random.randrange(pad_count)
            if len(sequence) >= 2 and sequence[-1] == pad and sequence[-2] == pad:
                continue
            sequence.append(pad)
        return sequence

    def make_sequence_question(self, offset, label, prompt, observe_prompt):
        length = self.SEQUENCE_LENGTH[offset]
        pads = self.PAD_COUNT[offset]
        show_on, show_gap = self.SHOW_TIMES[offset]
        return {"type": "sequence", "label": label, "prompt": prompt,
                "observe_prompt": observe_prompt,
                "sequence": self.make_sequence(length, pads), "pad_count": pads,
                "show_on": show_on, "show_gap": show_gap,
                "time_limit": 8 + 3 * length + (4 if offset < 0 else 0),
                "explanation": "Compare your order with the correct order shown below."}

    # ----- level builders -----
    def build_puzzle(self, level, offset):
        builders = {1: self.build_level_1, 2: self.build_level_2, 3: self.build_level_3,
                    4: self.build_level_4, 5: self.build_level_5}
        puzzle = None
        for _ in range(20):                       # regenerate if a puzzle fails the check
            puzzle = builders[level](offset)
            if self.is_solvable(puzzle):
                return puzzle
        return puzzle

    def _base_puzzle(self, level, offset):
        return {"level": level, "observe_layout": None, "observe_count": 0,
                "observe_time": float(self.observation_time(offset)), "observe_prompt": "",
                "answer_layout": None, "answer_count": 0, "show_slots": False,
                "pass_required": 1, "questions": []}

    def build_level_1(self, offset):
        """Five objects, one vanishes, pick it from three choices."""
        count = {-1: 4, 0: 5, 1: 6, 2: 7}[offset]
        shown = random.sample(OBJECT_NAMES, count)
        missing = random.choice(shown)
        remaining = [name for name in shown if name != missing]
        unused = [name for name in OBJECT_NAMES if name not in shown]
        options = [missing] + random.sample(unused, 2)
        random.shuffle(options)
        puzzle = self._base_puzzle(1, offset)
        puzzle.update({
            "observe_layout": dict(enumerate(shown)), "observe_count": count,
            "observe_prompt": "Memorize all %d objects. One of them will vanish when the timer ends." % count,
            "answer_layout": dict(enumerate(remaining)), "answer_count": count - 1})
        puzzle["questions"] = [{
            "type": "choice", "label": "Missing object",
            "prompt": "One object has vanished. Which one was in the room before? Select it, then press Submit Answer.",
            "options": options, "answer": missing, "time_limit": float(self.answer_time(offset)),
            "explanation": "The %s was removed from the room." % missing}]
        return puzzle

    def build_level_2(self, offset):
        """Six objects, one is replaced by a different object."""
        count = {-1: 5, 0: 6, 1: 7, 2: 8}[offset]
        shown = random.sample(OBJECT_NAMES, count)
        slot = random.randrange(count)
        replaced = shown[slot]
        intruder = random.choice([name for name in OBJECT_NAMES if name not in shown])
        new_room = list(shown)
        new_room[slot] = intruder
        puzzle = self._base_puzzle(2, offset)
        puzzle.update({
            "observe_layout": dict(enumerate(shown)), "observe_count": count,
            "observe_prompt": "Memorize every object. One of them will be secretly replaced.",
            "answer_layout": dict(enumerate(new_room)), "answer_count": count})
        puzzle["questions"] = [{
            "type": "room_click", "label": "False memory",
            "prompt": "A false memory crept in. Click the object that was NOT in the room before, then press Submit Answer.",
            "answer": slot, "time_limit": float(self.answer_time(offset)),
            "explanation": "The %s was replaced by the %s." % (replaced, intruder)}]
        return puzzle

    def build_level_3(self, offset):
        """Objects sit in fixed positions. One object moves to an empty position."""
        count = {-1: 4, 0: 5, 1: 6, 2: 6}[offset]
        slots = random.sample(range(8), count)
        names = random.sample(OBJECT_NAMES, count)
        layout = dict(zip(slots, names))
        old_slot = random.choice(slots)
        new_slot = random.choice([s for s in range(8) if s not in layout])
        new_layout = dict(layout)
        moved = new_layout.pop(old_slot)
        new_layout[new_slot] = moved
        puzzle = self._base_puzzle(3, offset)
        puzzle.update({
            "observe_layout": layout, "observe_count": 8, "show_slots": True,
            "observe_prompt": "Memorize where each object stands. One object will move to a new spot.",
            "answer_layout": new_layout, "answer_count": 8})
        puzzle["questions"] = [{
            "type": "room_click", "label": "Moved object",
            "prompt": "One object has moved. Click the object that now stands in a different position, then press Submit Answer.",
            "answer": new_slot, "time_limit": float(self.answer_time(offset)),
            "explanation": "The %s moved from %s to %s." % (moved, slot_text(old_slot), slot_text(new_slot))}]
        return puzzle

    def build_level_4(self, offset):
        """Watch a glowing sequence, then repeat it."""
        puzzle = self._base_puzzle(4, offset)
        puzzle["observe_time"] = 0.0
        puzzle["questions"] = [self.make_sequence_question(
            offset, "Memory sequence",
            "Click the symbols in the same order you saw them, then press Submit Answer.",
            "Watch the glowing symbols closely and remember their order.")]
        return puzzle

    def build_level_5(self, offset):
        """Room changes three ways (vanish, replace, move), then an escape lock."""
        count = {-1: 5, 0: 6, 1: 6, 2: 7}[offset]
        slots = random.sample(range(8), count)
        names = random.sample(OBJECT_NAMES, count)
        layout = dict(zip(slots, names))
        vanish_slot, replace_slot, move_slot = random.sample(slots, 3)
        unused = [name for name in OBJECT_NAMES if name not in names]
        intruder = random.choice(unused)
        target_slot = random.choice([s for s in range(8) if s not in layout])

        new_layout = dict(layout)
        vanished = new_layout.pop(vanish_slot)
        replaced = new_layout[replace_slot]
        new_layout[replace_slot] = intruder
        moved = new_layout.pop(move_slot)
        new_layout[target_slot] = moved

        distractor_pool = [name for name in unused if name != intruder]
        options = [vanished] + random.sample(distractor_pool, 2)
        random.shuffle(options)
        time_limit = float(self.answer_time(offset))

        puzzle = self._base_puzzle(5, offset)
        puzzle.update({
            "observe_layout": layout, "observe_count": 8, "show_slots": True,
            "observe_prompt": "Memorize the whole room. Objects will vanish, change and move.",
            "answer_layout": new_layout, "answer_count": 8, "pass_required": 3})
        puzzle["questions"] = [
            {"type": "choice", "label": "Missing object",
             "prompt": "Something vanished. Which object was in the room before? Select it, then press Submit Answer.",
             "options": options, "answer": vanished, "time_limit": time_limit,
             "explanation": "The %s vanished from the room." % vanished},
            {"type": "room_click", "label": "Replaced object",
             "prompt": "Something was replaced. Click the object that was NOT in the room before, then press Submit Answer.",
             "answer": replace_slot, "time_limit": time_limit,
             "explanation": "The %s was replaced by the %s." % (replaced, intruder)},
            {"type": "room_click", "label": "Moved object",
             "prompt": "Something moved. Click the object that now stands in a different position, then press Submit Answer.",
             "answer": target_slot, "time_limit": time_limit,
             "explanation": "The %s moved from %s to %s." % (moved, slot_text(move_slot), slot_text(target_slot))},
            self.make_sequence_question(
                offset, "Escape lock",
                "Repeat the lock's pattern in the same order, then press Submit Answer to escape.",
                "The exit lock flashes a pattern. Watch it closely."),
        ]
        return puzzle

    # ----- safety check: every puzzle must be solvable -----
    def is_solvable(self, puzzle):
        try:
            if not puzzle["questions"]:
                return False
            if puzzle["pass_required"] < 1 or puzzle["pass_required"] > len(puzzle["questions"]):
                return False
            for key in ("observe_layout", "answer_layout"):
                layout = puzzle[key]
                if layout is not None:
                    limit = puzzle["observe_count"] if key == "observe_layout" else puzzle["answer_count"]
                    names = list(layout.values())
                    if len(set(names)) != len(names):
                        return False
                    if any(not (0 <= slot < limit) for slot in layout):
                        return False
            if puzzle["observe_layout"] is not None and puzzle["observe_time"] <= 0:
                return False
            for question in puzzle["questions"]:
                if question["time_limit"] <= 0:
                    return False
                if question["type"] == "choice":
                    options = question["options"]
                    if len(options) != 3 or len(set(options)) != 3:
                        return False
                    if question["answer"] not in options:
                        return False
                    shown = list(puzzle["answer_layout"].values())
                    if any(option in shown for option in options):
                        return False
                elif question["type"] == "room_click":
                    if question["answer"] not in puzzle["answer_layout"]:
                        return False
                elif question["type"] == "sequence":
                    sequence = question["sequence"]
                    if not (3 <= len(sequence) <= 6):
                        return False
                    if any(not (0 <= pad < question["pad_count"] <= len(PAD_STYLES)) for pad in sequence):
                        return False
                else:
                    return False
            return True
        except (KeyError, TypeError):
            return False


# ----------------------------------------------------------------------------
# 4. THE GAME
# ----------------------------------------------------------------------------
class Game:
    """Owns the window, the screens (states) and the game loop."""

    NAME_BOX = pygame.Rect(300, 262, 400, 56)

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("MEMORIA - The Game That Forgets You")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.now = 0.0
        self.state_time = 0.0

        ui = "segoeui,calibri,arial,verdana"
        serif = "georgia,cambria,palatinolinotype,timesnewroman"
        self.f_title = pygame.font.SysFont(serif, 100, bold=True)
        self.f_h1 = pygame.font.SysFont(serif, 46, bold=True)
        self.f_sub = pygame.font.SysFont(serif, 30, italic=True)
        self.f_story = pygame.font.SysFont(serif, 23)
        self.f_how = pygame.font.SysFont(ui, 18)
        self.f_h2 = pygame.font.SysFont(ui, 27, bold=True)
        self.f_h3 = pygame.font.SysFont(ui, 20, bold=True)
        self.f_btn = pygame.font.SysFont(ui, 21, bold=True)
        self.f_body = pygame.font.SysFont(ui, 20)
        self.f_small = pygame.font.SysFont(ui, 16)
        self.f_big = pygame.font.SysFont(ui, 64, bold=True)

        self.db = DatabaseManager()
        self.levels = LevelManager()
        self.player = None
        self.state = "splash"
        self.return_state = "splash"
        self.buttons = []
        self.toast_text = ""
        self.toast_time = 0.0

        self.name_input = ""
        self.profile_error = ""
        self.pending_overwrite = None
        self.story_lines = []
        self.story_timer = 0.0
        self.level_rects = {}
        self.last_result = None

        self.reset_play_variables()
        self.background = self.create_background()
        self.particles = [{"x": random.uniform(0, WIDTH), "y": random.uniform(0, HEIGHT),
                           "speed": random.uniform(8, 26), "radius": random.choice([4, 6, 8]),
                           "phase": random.uniform(0, 6.28)} for _ in range(36)]

        self.builders = {"splash": self.build_splash, "how_to": self.build_how_to,
                         "profile": self.build_profile, "story": self.build_story,
                         "level_select": self.build_level_select, "play": self.build_play,
                         "result": self.build_result, "ending": self.build_ending,
                         "dashboard": self.build_dashboard}
        self.set_state("splash")

    # ------------------------------------------------------------------ setup
    def reset_play_variables(self):
        self.level_number = 1
        self.level_start_offset = 0
        self.puzzle = None
        self.question_index = 0
        self.question_results = []
        self.phase = "observe"          # observe, blackout, answer, feedback
        self.timer = 0.0
        self.timer_limit = 1.0
        self.cards = []
        self.selected_index = None
        self.hint_used = False
        self.entered_sequence = []
        self.playback_active = False
        self.playback_time = 0.0
        self.pad_flash = {}
        self.feedback_correct = False
        self.feedback_headline = ""
        self.feedback_detail = ""

    def create_background(self):
        surface = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            pygame.draw.line(surface, lerp_color(COL_BG_TOP, COL_BG_BOTTOM, y / (HEIGHT - 1)),
                             (0, y), (WIDTH, y))
        blit_glow(surface, (800, 120), 300, (70, 40, 130), 90)
        blit_glow(surface, (140, 560), 260, (60, 30, 110), 80)
        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(24):
            alpha = int(150 * (1 - i / 24) ** 2)
            pygame.draw.rect(vignette, (0, 0, 0, alpha),
                             pygame.Rect(i * 3, i * 3, WIDTH - i * 6, HEIGHT - i * 6), 3)
        surface.blit(vignette, (0, 0))
        return surface

    def set_state(self, new_state):
        self.state = new_state
        self.state_time = 0.0
        self.buttons = []
        self.builders[new_state]()

    def show_toast(self, text):
        self.toast_text = text
        self.toast_time = 2.8

    # ---------------------------------------------------------------- main loop
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.1)   # cap dt so timers never jump
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()
            pygame.display.flip()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_click(event.pos)
        elif event.type == pygame.KEYDOWN:
            self.handle_key(event)

    def handle_click(self, pos):
        for button in list(self.buttons):
            if button.is_visible() and button.rect.collidepoint(pos):
                if button.is_enabled():
                    button.callback()
                return
        if self.state == "level_select":
            self.click_level_select(pos)
        elif self.state == "play":
            self.click_play(pos)

    def handle_key(self, event):
        key = event.key
        if key == pygame.K_ESCAPE:
            self.go_back()
        elif self.state == "profile":
            self.key_profile(event)
        elif self.state == "story":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.set_state("level_select")
        elif self.state == "play":
            self.key_play(event)

    def go_back(self):
        if self.state == "profile":
            self.set_state("splash")
        elif self.state in ("how_to", "dashboard"):
            self.set_state(self.return_state)
        elif self.state in ("level_select", "ending"):
            self.set_state("splash")
        elif self.state in ("play", "result"):
            self.set_state("level_select")

    def quit_game(self):
        self.running = False

    # ------------------------------------------------------------------ update
    def update(self, dt):
        self.now += dt
        self.state_time += dt
        if self.toast_time > 0:
            self.toast_time -= dt
        for particle in self.particles:
            particle["y"] -= particle["speed"] * dt
            if particle["y"] < -10:
                particle["y"] = HEIGHT + 10
                particle["x"] = random.uniform(0, WIDTH)
        if self.state == "story":
            self.story_timer += dt
        elif self.state == "play":
            self.update_play(dt)

    # ------------------------------------------------------------------- draw
    def draw(self):
        self.screen.blit(self.background, (0, 0))
        for particle in self.particles:
            x = particle["x"] + math.sin(self.now * 0.6 + particle["phase"]) * 14
            blit_glow(self.screen, (int(x), int(particle["y"])), particle["radius"], (170, 140, 235), 120)
        drawers = {"splash": self.draw_splash, "how_to": self.draw_how_to,
                   "profile": self.draw_profile, "story": self.draw_story,
                   "level_select": self.draw_level_select, "play": self.draw_play,
                   "result": self.draw_result, "ending": self.draw_ending,
                   "dashboard": self.draw_dashboard}
        drawers[self.state]()
        mouse = pygame.mouse.get_pos()
        for button in self.buttons:
            button.draw(self.screen, self.f_btn, mouse, self.now)
        if self.toast_time > 0 and self.toast_text:
            rect = pygame.Rect(0, 0, min(880, self.f_body.size(self.toast_text)[0] + 50), 44)
            rect.midtop = (WIDTH // 2, 68)
            pygame.draw.rect(self.screen, (40, 24, 72), rect, border_radius=12)
            pygame.draw.rect(self.screen, COL_ACCENT, rect, 2, border_radius=12)
            draw_text(self.screen, self.toast_text, self.f_body, COL_TEXT, rect.center, "center")

    # =============================================================== SPLASH
    def build_splash(self):
        x = (WIDTH - 320) // 2
        self.buttons = [
            Button((x, 290, 320, 54), "Start Game", self.go_profile),
            Button((x, 358, 320, 54), "Continue Game", self.continue_game),
            Button((x, 426, 320, 54), "How to Play", self.open_how_to, "secondary"),
            Button((x, 494, 320, 54), "Exit", self.quit_game, "danger"),
        ]

    def go_profile(self):
        self.name_input = ""
        self.profile_error = ""
        self.pending_overwrite = None
        self.set_state("profile")

    def continue_game(self):
        name = self.db.get_latest_player_name()
        player = self.db.load_player(name) if name else None
        if player is None:
            self.show_toast("No saved game found. Choose Start Game first.")
            return
        self.player = player
        self.set_state("level_select")

    def open_how_to(self):
        self.return_state = self.state
        self.set_state("how_to")

    def draw_splash(self):
        surf = self.screen
        pulse = 240 + (int(math.sin(self.now * 1.5) * 12) // 6) * 6
        blit_glow(surf, (WIDTH // 2, 125), pulse, (110, 60, 200), 80)
        title = "MEMORIA"
        letters = [self.f_title.render(ch, True, COL_LAVENDER) for ch in title]
        total_width = sum(img.get_width() for img in letters)
        x = WIDTH // 2 - total_width // 2
        forget_index = int(self.now / 3.0) % len(title)
        local = self.now % 3.0
        for i, img in enumerate(letters):
            alpha = int(205 + 50 * math.sin(self.now * 1.6 + i * 0.9))
            if i == forget_index and local < 0.6:
                alpha = int(50 + 150 * (local / 0.6))      # one letter "forgets" itself
            img.set_alpha(clamp(alpha, 0, 255))
            surf.blit(img, (x, 52))
            x += img.get_width()
        draw_text(surf, "The Game That Forgets You", self.f_sub, COL_MUTED, (WIDTH // 2, 190), "midtop")
        draw_text(surf, "Do you remember how you got here?", self.f_small, (120, 106, 160),
                  (WIDTH // 2, 238), "midtop")
        if not self.db.save_ok:
            draw_text(surf, "Warning: the save file could not be used. Progress will not be saved.",
                      self.f_small, COL_BAD, (WIDTH // 2, 590), "midtop")
        draw_text(surf, "MCA Capstone Project  |  Python + pygame-ce + SQLite", self.f_small,
                  (110, 96, 150), (WIDTH // 2, 620), "midtop")

    # ============================================================= HOW TO PLAY
    def build_how_to(self):
        self.buttons = [Button(((WIDTH - 220) // 2, 566, 220, 52), "Back", self.go_back, "secondary")]

    def draw_how_to(self):
        surf = self.screen
        draw_text(surf, "How to Play", self.f_h1, COL_LAVENDER, (WIDTH // 2, 24), "midtop")
        panel = pygame.Rect(60, 96, 880, 454)
        draw_panel(surf, panel)
        items = [
            ("Goal", "Escape the building by clearing five memory rooms."),
            ("Observe", "Study the objects until the timer ends. Press I'm Ready to skip ahead."),
            ("Answer", "Click a card to select it, then press Submit Answer. In the sequence rooms, "
                       "click the symbols in the order you saw them."),
            ("Hints", "One hint per question. It removes a wrong option or replays a sequence. It costs "
                      "%d points." % HINT_PENALTY),
            ("Scoring", "%d points per correct answer, up to %d bonus points for speed, and +%d for "
                        "finishing a level. Only your best score for each level counts toward your total, "
                        "so retrying never inflates it." % (POINTS_CORRECT, TIME_BONUS_MAX, COMPLETION_BONUS)),
            ("Adaptive", "Play well and rooms get more objects and less time. Struggle, and you get more "
                         "time and fewer objects."),
            ("Keys", "Esc = back, Enter = submit or continue, H = hint, Space = ready, Backspace = undo."),
        ]
        y = panel.y + 18
        for heading, text in items:
            draw_text(surf, heading, self.f_h3, COL_ACCENT, (panel.x + 24, y))
            y = draw_wrapped(surf, text, self.f_how, COL_TEXT, panel.x + 140, y + 1, 710, 23) + 12

    # ================================================================= PROFILE
    def build_profile(self):
        self.buttons = [
            Button((300, 400, 190, 52), "Create Profile", self.submit_profile),
            Button((510, 400, 190, 52), "Back", self.go_back, "secondary"),
        ]

    def key_profile(self, event):
        key = event.key
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.submit_profile()
        elif key == pygame.K_BACKSPACE:
            self.name_input = self.name_input[:-1]
            self.profile_error = ""
            self.pending_overwrite = None
        else:
            ch = event.unicode
            if ch and ch.isascii() and (ch.isalnum() or ch in " -_") \
                    and len(self.name_input) < MAX_NAME_LENGTH:
                self.name_input += ch
                self.profile_error = ""
                self.pending_overwrite = None

    def submit_profile(self):
        name = " ".join(self.name_input.split())
        if not name:
            self.profile_error = "Please enter a name before continuing."
            return
        if self.db.player_exists(name) and self.pending_overwrite != name.lower():
            self.pending_overwrite = name.lower()
            self.profile_error = ("'%s' already has a saved game. Click Create Profile again to erase it, "
                                  "or go Back and choose Continue Game." % name)
            return
        self.player = self.db.create_player(name)
        self.pending_overwrite = None
        self.set_state("story")

    def draw_profile(self):
        surf = self.screen
        panel = pygame.Rect(220, 130, 560, 350)
        draw_panel(surf, panel)
        draw_text(surf, "Who are you?", self.f_h1, COL_LAVENDER, (WIDTH // 2, 150), "midtop")
        draw_text(surf, "Enter your name (letters, numbers, space, - or _)", self.f_small, COL_MUTED,
                  (WIDTH // 2, 226), "midtop")
        draw_rect_glow(surf, self.NAME_BOX, COL_ACCENT, 10, 70)
        pygame.draw.rect(surf, (12, 7, 26), self.NAME_BOX, border_radius=10)
        pygame.draw.rect(surf, COL_ACCENT, self.NAME_BOX, 2, border_radius=10)
        shown = self.name_input
        text_rect = draw_text(surf, shown, self.f_h2, COL_TEXT, (self.NAME_BOX.x + 16, self.NAME_BOX.centery), "midleft")
        if int(self.now * 2) % 2 == 0:
            cursor_x = text_rect.right + 3 if shown else self.NAME_BOX.x + 17
            pygame.draw.line(surf, COL_LAVENDER, (cursor_x, self.NAME_BOX.y + 12),
                             (cursor_x, self.NAME_BOX.bottom - 12), 2)
        if not shown:
            draw_text(surf, "Type here...", self.f_body, (96, 84, 130),
                      (self.NAME_BOX.x + 16, self.NAME_BOX.centery + 2), "midleft")
        if self.profile_error:
            color = COL_GOLD if self.pending_overwrite else COL_BAD
            draw_wrapped(surf, self.profile_error, self.f_small, color, WIDTH // 2, 330, 500, 21, "center")

    # =================================================================== STORY
    def build_story(self):
        name = self.player.name if self.player else "stranger"
        text = ("Welcome, %s.\n\n"
                "You wake on a cold floor. The air smells of dust and candle smoke. A folded note in your "
                "pocket holds a single line: \"Remember, and the doors will open.\"\n\n"
                "Every room in this building rearranges itself when you look away. Objects vanish. Objects "
                "lie. Even your own memory cannot be trusted.\n\n"
                "Five rooms stand between you and the exit. Observe carefully, and trust only what you "
                "truly saw.\n\n"
                "The building is listening. It remembers you, even if you have started to forget yourself."
                % name)
        self.story_lines = wrap_text(text, self.f_story, 690)
        self.story_timer = 0.0
        self.buttons = [Button(((WIDTH - 220) // 2, 566, 220, 52), "Continue",
                               lambda: self.set_state("level_select"))]

    def draw_story(self):
        surf = self.screen
        panel = pygame.Rect(100, 40, 800, 500)
        draw_panel(surf, panel)
        remaining = int(self.story_timer * 45)
        y = panel.y + 28
        for line in self.story_lines:
            if remaining <= 0:
                break
            piece = line[:remaining]
            remaining -= len(line)
            if piece:
                draw_text(surf, piece, self.f_story, COL_TEXT, (panel.x + 50, y))
            y += 29

    # ============================================================ LEVEL SELECT
    def build_level_select(self):
        card_w, gap = 172, 14
        x0 = (WIDTH - (5 * card_w + 4 * gap)) // 2
        self.level_rects = {n: pygame.Rect(x0 + (n - 1) * (card_w + gap), 128, card_w, 276)
                            for n in range(1, TOTAL_LEVELS + 1)}
        self.buttons = [
            Button((60, 566, 250, 52), "Dashboard", self.open_dashboard, "secondary"),
            Button((375, 566, 250, 52), "View Ending", lambda: self.set_state("ending"),
                   enabled_check=lambda: self.player.levels[TOTAL_LEVELS]["completed"]),
            Button((690, 566, 250, 52), "Main Menu", lambda: self.set_state("splash"), "secondary"),
        ]

    def open_dashboard(self):
        self.return_state = self.state
        self.set_state("dashboard")

    def click_level_select(self, pos):
        for number, rect in self.level_rects.items():
            if rect.collidepoint(pos):
                if self.player.is_unlocked(number):
                    self.start_level(number)
                else:
                    self.show_toast("Locked. Complete the previous level first.")
                return

    def draw_level_select(self):
        surf = self.screen
        draw_text(surf, "Choose a Room", self.f_h1, COL_LAVENDER, (WIDTH // 2, 20), "midtop")
        draw_text(surf, "%s   |   Total score %d   |   Difficulty: %s"
                  % (self.player.name, self.player.total_score(),
                     LevelManager.difficulty_name(self.player.difficulty_offset)),
                  self.f_body, COL_MUTED, (WIDTH // 2, 82), "midtop")
        mouse = pygame.mouse.get_pos()
        for number, rect in self.level_rects.items():
            record = self.player.levels[number]
            unlocked = self.player.is_unlocked(number)
            hover = unlocked and rect.collidepoint(mouse)
            if hover:
                draw_rect_glow(surf, rect, COL_ACCENT, 14, 110, 16)
            draw_panel(surf, rect, COL_CARD if unlocked else (16, 10, 28),
                       COL_LAVENDER if hover else (COL_GOOD if record["completed"] else COL_PANEL_EDGE), 16)
            draw_text(surf, str(number), self.f_h1, COL_LAVENDER if unlocked else (84, 74, 112),
                      (rect.centerx, rect.y + 10), "midtop")
            draw_object_icon(surf, LEVEL_ICONS[number], (rect.centerx, rect.y + 118), 72, dim=not unlocked)
            if not unlocked:                                   # padlock
                body = pygame.Rect(0, 0, 40, 30)
                body.center = (rect.centerx, rect.y + 120)
                pygame.draw.rect(surf, (120, 106, 160), body, border_radius=6)
                pygame.draw.arc(surf, (120, 106, 160), pygame.Rect(body.x + 6, body.y - 22, 28, 34),
                                0, math.pi, 5)
            draw_wrapped(surf, LevelManager.TITLES[number], self.f_h3,
                         COL_TEXT if unlocked else (96, 86, 124), rect.centerx, rect.y + 170, 156, 24, "center")
            if record["completed"]:
                status, color = "COMPLETED", COL_GOOD
            elif unlocked:
                status, color = "UNLOCKED", COL_ACCENT
            else:
                status, color = "LOCKED", (110, 98, 146)
            draw_text(surf, status, self.f_small, color, (rect.centerx, rect.y + 226), "midtop")
            draw_text(surf, "Best: %d" % record["best_score"], self.f_small, COL_MUTED,
                      (rect.centerx, rect.y + 248), "midtop")
        draw_text(surf, "Click an unlocked room to enter. Completed rooms can be replayed; your best score is kept.",
                  self.f_small, COL_MUTED, (WIDTH // 2, 422), "midtop")
        if self.player.all_completed():
            draw_text(surf, "You escaped! Press View Ending to see how your story ends.",
                      self.f_body, COL_GOLD, (WIDTH // 2, 456), "midtop")
        elif self.player.difficulty_offset < 0:
            draw_text(surf, "The building senses you struggling, so rooms give you more time and fewer objects.",
                      self.f_small, COL_GOLD, (WIDTH // 2, 456), "midtop")

    # ================================================================ GAMEPLAY
    def build_play(self):
        def is_phase(name):
            return self.phase == name

        def current_type():
            return self.puzzle["questions"][self.question_index]["type"]

        def last_question():
            return self.question_index + 1 >= len(self.puzzle["questions"])

        self.buttons = [
            Button((40, 578, 130, 48), "Menu", lambda: self.set_state("level_select"), "secondary"),
            Button((190, 578, 130, 48), "Clear", self.clear_sequence, "secondary",
                   visible_check=lambda: is_phase("answer") and current_type() == "sequence",
                   enabled_check=lambda: not self.playback_active),
            Button((560, 578, 180, 48),
                   lambda: "Hint used" if self.hint_used else "Hint (-%d)" % HINT_PENALTY,
                   self.use_hint, "secondary",
                   visible_check=lambda: is_phase("answer"),
                   enabled_check=self.can_use_hint,
                   pulse_check=lambda: self.player.difficulty_offset < 0 and not self.hint_used),
            Button((760, 578, 200, 48), "Submit Answer", self.submit_answer,
                   visible_check=lambda: is_phase("answer"), enabled_check=self.can_submit),
            Button((760, 578, 200, 48), "I'm Ready", self.begin_blackout,
                   visible_check=lambda: is_phase("observe") and current_type() != "sequence"),
            Button((760, 578, 200, 48),
                   lambda: "See Results" if last_question() else "Continue",
                   self.continue_after_feedback, visible_check=lambda: is_phase("feedback")),
        ]

    def start_level(self, number):
        self.reset_play_variables()
        self.level_number = number
        self.level_start_offset = self.player.difficulty_offset
        self.puzzle = self.levels.build_puzzle(number, self.player.difficulty_offset)
        self.set_state("play")
        self.enter_question(0)

    def current_question(self):
        return self.puzzle["questions"][self.question_index]

    def make_room_cards(self, layout, slot_count, clickable):
        rects = slot_rects(slot_count)
        cards = []
        for slot in sorted(layout):
            cards.append({"rect": rects[slot], "name": layout[slot], "slot": slot, "role": "room",
                          "clickable": clickable, "disabled": False, "state": "normal"})
        return cards

    def enter_question(self, index):
        self.question_index = index
        question = self.current_question()
        self.hint_used = False
        self.selected_index = None
        self.entered_sequence = []
        self.cards = []
        if question["type"] == "sequence":
            self.phase = "observe"
            self.start_playback()
        elif index == 0 and self.puzzle["observe_layout"] is not None:
            self.phase = "observe"
            self.timer_limit = self.puzzle["observe_time"]
            self.timer = self.timer_limit
            self.cards = self.make_room_cards(self.puzzle["observe_layout"],
                                              self.puzzle["observe_count"], False)
        else:
            self.begin_answer()

    def begin_blackout(self):
        if self.phase != "observe":
            return
        self.phase = "blackout"
        self.timer = 1.4
        self.timer_limit = 1.4
        self.cards = []

    def begin_answer(self):
        question = self.current_question()
        self.phase = "answer"
        self.timer_limit = question["time_limit"]
        self.timer = self.timer_limit
        self.hint_used = False
        self.selected_index = None
        self.entered_sequence = []
        self.playback_active = False
        self.cards = []
        if question["type"] != "sequence":
            self.cards = self.make_room_cards(self.puzzle["answer_layout"], self.puzzle["answer_count"],
                                              question["type"] == "room_click")
            if question["type"] == "choice":
                total = 3 * CARD_W + 2 * 50
                x = WIDTH // 2 - total // 2
                for i, option in enumerate(question["options"]):
                    self.cards.append({"rect": pygame.Rect(x + i * (CARD_W + 50), 424, CARD_W, CARD_H),
                                       "name": option, "slot": None, "role": "choice",
                                       "clickable": True, "disabled": False, "state": "normal"})

    # --- sequence playback
    def start_playback(self):
        self.playback_active = True
        self.playback_time = -0.8

    def update_playback(self, dt):
        question = self.current_question()
        step_length = question["show_on"] + question["show_gap"]
        self.playback_time += dt
        if self.playback_time >= len(question["sequence"]) * step_length + 0.3:
            self.playback_active = False
            if self.phase == "observe":
                self.begin_answer()

    def highlighted_pad(self):
        if not self.playback_active or self.playback_time < 0:
            return None
        question = self.current_question()
        step_length = question["show_on"] + question["show_gap"]
        step = int(self.playback_time // step_length)
        if step < len(question["sequence"]) and self.playback_time - step * step_length < question["show_on"]:
            return question["sequence"][step]
        return None

    # --- per-frame update
    def update_play(self, dt):
        for pad in list(self.pad_flash):
            self.pad_flash[pad] -= dt
            if self.pad_flash[pad] <= 0:
                del self.pad_flash[pad]
        question = self.current_question()
        if self.phase == "observe":
            if question["type"] == "sequence":
                if self.playback_active:
                    self.update_playback(dt)
            else:
                self.timer -= dt
                if self.timer <= 0:
                    self.begin_blackout()
        elif self.phase == "blackout":
            self.timer -= dt
            if self.timer <= 0:
                self.begin_answer()
        elif self.phase == "answer":
            if self.playback_active:                 # timer is paused during a hint replay
                self.update_playback(dt)
            else:
                self.timer -= dt
                if self.timer <= 0:
                    self.timer = 0.0
                    self.finish_question(False, timed_out=True)

    # --- input
    def pad_at(self, pos, pad_count):
        for index, center in enumerate(pad_centers(pad_count)):
            if math.hypot(pos[0] - center[0], pos[1] - center[1]) <= PAD_RADIUS + 6:
                return index
        return None

    def click_play(self, pos):
        if self.phase != "answer" or self.playback_active:
            return
        question = self.current_question()
        if question["type"] == "sequence":
            pad = self.pad_at(pos, question["pad_count"])
            if pad is not None and len(self.entered_sequence) < len(question["sequence"]):
                self.entered_sequence.append(pad)
                self.pad_flash[pad] = 0.25
            return
        for index, card in enumerate(self.cards):
            if card["clickable"] and not card["disabled"] and card["rect"].collidepoint(pos):
                self.selected_index = index
                return

    def key_play(self, event):
        key = event.key
        if key == pygame.K_h:
            self.use_hint()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.phase == "answer":
                self.submit_answer()
            elif self.phase == "feedback":
                self.continue_after_feedback()
        elif key == pygame.K_SPACE:
            if self.phase == "observe" and self.current_question()["type"] != "sequence":
                self.begin_blackout()
            elif self.phase == "feedback":
                self.continue_after_feedback()
        elif key == pygame.K_BACKSPACE:
            if self.phase == "answer" and not self.playback_active and self.entered_sequence:
                self.entered_sequence.pop()

    def clear_sequence(self):
        if self.phase == "answer" and not self.playback_active:
            self.entered_sequence = []

    def can_submit(self):
        if self.phase != "answer" or self.playback_active:
            return False
        question = self.current_question()
        if question["type"] == "sequence":
            return len(self.entered_sequence) == len(question["sequence"])
        return self.selected_index is not None

    def hint_candidates(self):
        """Cards a hint is allowed to switch off (never the correct one)."""
        question = self.current_question()
        if question["type"] == "choice":
            return [c for c in self.cards if c["role"] == "choice" and c["name"] != question["answer"]
                    and not c["disabled"]]
        if question["type"] == "room_click":
            return [c for c in self.cards if c["clickable"] and c["slot"] != question["answer"]
                    and not c["disabled"]]
        return []

    def can_use_hint(self):
        if self.phase != "answer" or self.hint_used or self.playback_active:
            return False
        if self.current_question()["type"] == "sequence":
            return True
        return len(self.hint_candidates()) > 0

    def use_hint(self):
        if not self.can_use_hint():
            return
        question = self.current_question()
        if question["type"] == "sequence":
            self.start_playback()                      # replay the pattern
        else:
            card = random.choice(self.hint_candidates())
            card["disabled"] = True
            if self.selected_index is not None and self.cards[self.selected_index] is card:
                self.selected_index = None
        self.hint_used = True

    def submit_answer(self):
        if not self.can_submit():
            return
        question = self.current_question()
        if question["type"] == "sequence":
            correct = self.entered_sequence == question["sequence"]
        else:
            card = self.cards[self.selected_index]
            if question["type"] == "choice":
                correct = card["name"] == question["answer"]
            else:
                correct = card["slot"] == question["answer"]
        self.finish_question(correct, timed_out=False)

    # --- scoring
    def finish_question(self, correct, timed_out):
        """Score one question exactly once, adjust difficulty, then show feedback."""
        question = self.current_question()
        fraction = 0.0 if timed_out else clamp(self.timer / self.timer_limit, 0.0, 1.0)
        points = POINTS_CORRECT if correct else 0
        bonus = int(round(TIME_BONUS_MAX * fraction)) if correct else 0
        hints = 1 if self.hint_used else 0
        penalty = HINT_PENALTY * hints
        self.question_results.append({"label": question["label"], "correct": correct,
                                      "timed_out": timed_out, "points": points, "bonus": bonus,
                                      "hints": hints, "penalty": penalty})
        self.player.register_question(correct)
        self.player.difficulty_offset = LevelManager.update_offset(
            self.player.difficulty_offset, correct, hints, fraction)
        self.db.save_player(self.player)

        # Mark cards so the player sees the right answer
        for index, card in enumerate(self.cards):
            if question["type"] == "choice" and card["role"] != "choice":
                continue
            if question["type"] == "room_click" and card["role"] != "room":
                continue
            is_answer = (card["name"] == question["answer"]) if question["type"] == "choice" \
                else (card["slot"] == question["answer"])
            if is_answer:
                card["state"] = "correct"
            elif index == self.selected_index:
                card["state"] = "wrong"

        self.phase = "feedback"
        self.feedback_correct = correct
        if correct:
            self.feedback_headline = "Correct!  +%d points" % (points + bonus)
        elif timed_out:
            self.feedback_headline = "Time ran out."
        else:
            self.feedback_headline = "Incorrect."
        self.feedback_detail = question["explanation"]

    def attempt_score(self):
        """Score of the current attempt so far (never negative)."""
        total = sum(r["points"] + r["bonus"] - r["penalty"] for r in self.question_results)
        if self.hint_used and self.phase != "feedback":
            total -= HINT_PENALTY
        return max(0, total)

    def continue_after_feedback(self):
        if self.phase != "feedback":
            return
        if self.question_index + 1 < len(self.puzzle["questions"]):
            self.enter_question(self.question_index + 1)
        else:
            self.finish_level()

    def finish_level(self):
        results = self.question_results
        correct_count = sum(1 for r in results if r["correct"])
        passed = correct_count >= self.puzzle["pass_required"]
        answer_points = sum(r["points"] for r in results)
        time_bonus = sum(r["bonus"] for r in results)
        hint_penalty = sum(r["penalty"] for r in results)
        completion = COMPLETION_BONUS if passed else 0
        level_score = max(0, answer_points + time_bonus - hint_penalty + completion)
        number = self.level_number
        previous_best = self.player.levels[number]["best_score"]
        unlocked_before = self.player.unlocked_level
        self.player.register_level_result(number, level_score, passed)
        self.db.save_player(self.player)
        self.last_result = {
            "level": number, "passed": passed, "correct_count": correct_count,
            "total_questions": len(results), "questions": list(results),
            "answer_points": answer_points, "time_bonus": time_bonus,
            "hint_penalty": hint_penalty, "completion": completion, "level_score": level_score,
            "previous_best": previous_best, "new_best": level_score > previous_best,
            "offset_before": self.level_start_offset, "offset_after": self.player.difficulty_offset,
            "newly_unlocked": self.player.unlocked_level if self.player.unlocked_level > unlocked_before else None}
        self.set_state("result")

    # --- drawing the play screen
    def timer_text(self):
        question = self.current_question()
        if self.phase == "observe":
            if question["type"] == "sequence":
                return "Watch..."
            return "Observe: %ds" % int(math.ceil(max(0.0, self.timer)))
        if self.phase == "answer":
            if self.playback_active:
                return "Replay..."
            return "Time: %.1fs" % max(0.0, self.timer)
        if self.phase == "blackout":
            return "..."
        return "Done"

    def draw_play(self):
        surf = self.screen
        question = self.current_question()
        # header bar
        pygame.draw.rect(surf, (12, 8, 26), pygame.Rect(0, 0, WIDTH, 58))
        pygame.draw.line(surf, COL_PANEL_EDGE, (0, 58), (WIDTH, 58), 2)
        title = "LEVEL %d: %s" % (self.level_number, LevelManager.TITLES[self.level_number].upper())
        draw_text(surf, title, self.f_h3, COL_LAVENDER, (20, 29), "midleft")
        draw_text(surf, "Score %d   |   Total %d" % (self.attempt_score(), self.player.total_score()),
                  self.f_h3, COL_TEXT, (610, 29), "center")
        timer_color = COL_TEXT
        use_bar = self.phase == "answer" and not self.playback_active or \
            (self.phase == "observe" and question["type"] != "sequence")
        fraction = clamp(self.timer / self.timer_limit, 0.0, 1.0) if use_bar and self.timer_limit > 0 else 0.0
        if use_bar and fraction < 0.25:
            timer_color = COL_BAD
        draw_text(surf, self.timer_text(), self.f_h3, timer_color, (WIDTH - 20, 29), "midright")
        if use_bar:
            bar_color = COL_BAD if fraction < 0.25 else COL_ACCENT
            pygame.draw.rect(surf, bar_color, pygame.Rect(0, 59, int(WIDTH * fraction), 4))

        # instruction or feedback text
        if self.phase == "feedback":
            color = COL_GOOD if self.feedback_correct else COL_BAD
            draw_text(surf, self.feedback_headline, self.f_h2, color, (WIDTH // 2, 62), "midtop")
            draw_text(surf, fit_line(self.feedback_detail, self.f_body, 900), self.f_body, COL_TEXT,
                      (WIDTH // 2, 100), "midtop")
        else:
            draw_wrapped(surf, self.instruction_text(question), self.f_body, COL_TEXT,
                         WIDTH // 2, 70, 900, 26, "center")
            if self.phase == "answer":
                draw_text(surf, "Difficulty: %s" % LevelManager.difficulty_name(self.player.difficulty_offset),
                          self.f_small, COL_MUTED, (WIDTH - 24, 106), "topright")

        # room panel
        draw_panel(surf, ROOM_RECT, (16, 9, 32))
        mouse = pygame.mouse.get_pos()
        if self.phase == "blackout":
            pygame.draw.rect(surf, (5, 2, 12), ROOM_RECT.inflate(-8, -8), border_radius=14)
            flicker = 0.5 + 0.5 * math.sin(self.now * 14)
            draw_text(surf, "The lights flicker...", self.f_h2,
                      lerp_color((60, 44, 96), COL_LAVENDER, flicker), ROOM_RECT.center, "center")
        elif question["type"] == "sequence":
            self.draw_pads(question, mouse)
        else:
            if self.puzzle["show_slots"]:
                for rect in slot_rects(8):
                    pygame.draw.rect(surf, (48, 34, 84), rect, 2, border_radius=14)
            for index, card in enumerate(self.cards):
                if card["role"] == "room":
                    draw_card(surf, card["rect"], card["name"], self.f_small, self.card_state(index, card, mouse))
        self.draw_play_lower(question, mouse)

    def instruction_text(self, question):
        if self.phase == "observe":
            text = question["observe_prompt"] if question["type"] == "sequence" \
                else self.puzzle["observe_prompt"]
        elif self.phase == "blackout":
            text = "Something in the room is changing..."
        else:
            text = question["prompt"]
        if len(self.puzzle["questions"]) > 1 and self.phase in ("answer", "observe") \
                and (self.phase == "answer" or question["type"] == "sequence"):
            text = "[Stage %d of %d]  %s" % (self.question_index + 1, len(self.puzzle["questions"]), text)
        return text

    def card_state(self, index, card, mouse):
        if card["state"] in ("correct", "wrong"):
            return card["state"]
        if card["disabled"]:
            return "disabled"
        if self.phase == "answer" and index == self.selected_index:
            return "selected"
        if self.phase == "answer" and card["clickable"] and card["rect"].collidepoint(mouse):
            return "hover"
        return "normal"

    def draw_pads(self, question, mouse):
        highlighted = self.highlighted_pad()
        for index, center in enumerate(pad_centers(question["pad_count"])):
            kind, color, _ = PAD_STYLES[index]
            active = (highlighted == index) or (index in self.pad_flash)
            hover = self.phase == "answer" and not self.playback_active and \
                math.hypot(mouse[0] - center[0], mouse[1] - center[1]) <= PAD_RADIUS + 6
            draw_pad(self.screen, center, kind, color, active, hover)

    def draw_symbol_row(self, pads, total, center_y, radius, compare=None):
        spacing = radius * 2 + 18
        start_x = WIDTH / 2 - (total - 1) * spacing / 2
        for i in range(total):
            center = (int(start_x + i * spacing), center_y)
            pygame.draw.circle(self.screen, (22, 14, 40), center, radius)
            if i < len(pads):
                kind, color, _ = PAD_STYLES[pads[i]]
                border = color
                if compare is not None:
                    border = COL_GOOD if i < len(compare) and compare[i] == pads[i] else COL_BAD
                pygame.draw.circle(self.screen, border, center, radius, 3)
                draw_symbol(self.screen, kind, center, int(radius * 0.55), color)
            else:
                pygame.draw.circle(self.screen, COL_PANEL_EDGE, center, radius, 2)

    def draw_play_lower(self, question, mouse):
        surf = self.screen
        kind = question["type"]
        if self.phase == "observe" and kind != "sequence":
            draw_text(surf, str(int(math.ceil(max(0.0, self.timer)))), self.f_big, COL_LAVENDER,
                      (WIDTH // 2, 410), "midtop")
            draw_text(surf, "Press I'm Ready when you have memorized the room.", self.f_body, COL_MUTED,
                      (WIDTH // 2, 495), "midtop")
        elif self.phase == "observe":
            total = len(question["sequence"])
            shown = 0
            if self.playback_active and self.playback_time > 0:
                shown = min(total, int(self.playback_time // (question["show_on"] + question["show_gap"])) + 1)
            draw_text(surf, "Watch the pattern", self.f_h2, COL_LAVENDER, (WIDTH // 2, 430), "midtop")
            self.draw_symbol_row([], total, 500, 12)
            for i in range(shown):
                pygame.draw.circle(surf, COL_ACCENT, (int(WIDTH / 2 - (total - 1) * 15 + i * 30), 500), 9)
        elif self.phase == "blackout":
            draw_text(surf, "Memories are shifting. Get ready to answer.", self.f_body, COL_MUTED,
                      (WIDTH // 2, 450), "midtop")
        elif kind == "choice":
            draw_text(surf, "Choose your answer:" if self.phase == "answer" else "The answer:",
                      self.f_body, COL_MUTED, (WIDTH // 2, 398), "midtop")
            for index, card in enumerate(self.cards):
                if card["role"] == "choice":
                    draw_card(surf, card["rect"], card["name"], self.f_small, self.card_state(index, card, mouse))
        elif kind == "sequence":
            total = len(question["sequence"])
            if self.phase == "answer":
                draw_text(surf, "Your sequence", self.f_body, COL_MUTED, (WIDTH // 2, 408), "midtop")
                self.draw_symbol_row(self.entered_sequence, total, 468, 24)
                message = "Watch the replay..." if self.playback_active else \
                    "Click the symbols in order. Use Clear or Backspace to fix mistakes."
                draw_text(surf, message, self.f_small, COL_MUTED, (WIDTH // 2, 520), "midtop")
            else:
                draw_text(surf, "Correct order", self.f_small, COL_MUTED, (WIDTH // 2, 404), "midtop")
                self.draw_symbol_row(question["sequence"], total, 448, 20)
                draw_text(surf, "Your order", self.f_small, COL_MUTED, (WIDTH // 2, 482), "midtop")
                self.draw_symbol_row(self.entered_sequence, total, 534, 20, compare=question["sequence"])
        else:   # room_click
            if self.phase == "answer":
                if self.selected_index is not None:
                    text = "Selected: %s" % self.cards[self.selected_index]["name"]
                    draw_text(surf, text, self.f_h2, COL_LAVENDER, (WIDTH // 2, 430), "midtop")
                else:
                    draw_text(surf, "Click an object in the room to select it.", self.f_body, COL_MUTED,
                              (WIDTH // 2, 435), "midtop")
                if self.player.difficulty_offset < 0 and not self.hint_used:
                    draw_text(surf, "The room is going easy on you. A hint can help.", self.f_small,
                              COL_GOLD, (WIDTH // 2, 500), "midtop")
            else:
                draw_text(surf, "Green marks the correct object.", self.f_body, COL_MUTED,
                          (WIDTH // 2, 440), "midtop")

    # ================================================================== RESULT
    def build_result(self):
        result = self.last_result
        number = result["level"]
        x0, w, gap = 60, 205, 20
        self.buttons = [
            Button((x0, 548, w, 52),
                   "Next Level" if number < TOTAL_LEVELS else "See Ending",
                   (lambda: self.start_level(number + 1)) if number < TOTAL_LEVELS
                   else (lambda: self.set_state("ending")),
                   enabled_check=lambda: result["passed"]),
            Button((x0 + (w + gap), 548, w, 52), "Retry", lambda: self.start_level(number), "secondary"),
            Button((x0 + 2 * (w + gap), 548, w, 52), "Level Select",
                   lambda: self.set_state("level_select"), "secondary"),
            Button((x0 + 3 * (w + gap), 548, w, 52), "Main Menu",
                   lambda: self.set_state("splash"), "secondary"),
        ]

    def draw_result(self):
        surf = self.screen
        r = self.last_result
        single = r["total_questions"] == 1
        if r["passed"]:
            headline = "CORRECT!" if single else "ESCAPE SUCCESSFUL"
            color = COL_GOOD
        else:
            headline = "INCORRECT" if single else "THE ROOM HOLDS YOU"
            color = COL_BAD
        draw_text(surf, headline, self.f_h1, color, (WIDTH // 2, 18), "midtop")
        draw_text(surf, "Level %d: %s" % (r["level"], LevelManager.TITLES[r["level"]]), self.f_body,
                  COL_MUTED, (WIDTH // 2, 74), "midtop")
        panel = pygame.Rect(60, 108, 880, 424)
        draw_panel(surf, panel)
        # left column: questions + score breakdown
        x, y = panel.x + 28, panel.y + 18
        draw_text(surf, "Your answers", self.f_h3, COL_ACCENT, (x, y))
        y += 32
        for q in r["questions"]:
            if q["correct"]:
                text, col = "Correct  (+%d)" % (q["points"] + q["bonus"]), COL_GOOD
            elif q["timed_out"]:
                text, col = "Time ran out", COL_BAD
            else:
                text, col = "Incorrect", COL_BAD
            draw_text(surf, q["label"] + ":", self.f_body, COL_TEXT, (x, y))
            draw_text(surf, text, self.f_body, col, (x + 190, y))
            y += 28
        y += 14
        draw_text(surf, "Score breakdown", self.f_h3, COL_ACCENT, (x, y))
        y += 32
        rows = [("Answer points", "+%d" % r["answer_points"], COL_TEXT),
                ("Time bonus", "+%d" % r["time_bonus"], COL_TEXT),
                ("Hint penalty", "-%d" % r["hint_penalty"], COL_BAD if r["hint_penalty"] else COL_TEXT),
                ("Level completion", "+%d" % r["completion"], COL_TEXT)]
        for label, value, col in rows:
            draw_text(surf, label, self.f_body, COL_MUTED, (x, y))
            draw_text(surf, value, self.f_body, col, (x + 300, y), "topright")
            y += 27
        pygame.draw.line(surf, COL_PANEL_EDGE, (x, y + 3), (x + 300, y + 3), 2)
        y += 12
        draw_text(surf, "LEVEL SCORE", self.f_h3, COL_GOLD, (x, y))
        draw_text(surf, str(r["level_score"]), self.f_h2, COL_GOLD, (x + 300, y - 3), "topright")
        # right column: statistics
        x2, y2 = panel.x + 470, panel.y + 18
        draw_text(surf, "Performance", self.f_h3, COL_ACCENT, (x2, y2))
        y2 += 34
        pct = int(round(100.0 * r["correct_count"] / r["total_questions"])) if r["total_questions"] else 0
        stats = [("Accuracy this attempt", "%d / %d  (%d%%)" % (r["correct_count"], r["total_questions"], pct)),
                 ("Overall accuracy", "%d%%" % self.player.accuracy_percent()),
                 ("Best score on this level", str(self.player.levels[r["level"]]["best_score"])),
                 ("Total score", str(self.player.total_score())),
                 ("Levels completed", "%d / %d" % (self.player.completed_count(), TOTAL_LEVELS))]
        for label, value in stats:
            draw_text(surf, label, self.f_body, COL_MUTED, (x2, y2))
            draw_text(surf, value, self.f_body, COL_TEXT, (x2 + 390, y2), "topright")
            y2 += 30
        y2 += 12
        if r["new_best"] and r["level_score"] > 0:
            draw_text(surf, "New best score for this level!", self.f_body, COL_GOLD, (x2, y2))
            y2 += 28
        if r["newly_unlocked"]:
            draw_text(surf, "Level %d unlocked!" % r["newly_unlocked"], self.f_body, COL_GOOD, (x2, y2))
            y2 += 28
        before = LevelManager.difficulty_name(r["offset_before"])
        after = LevelManager.difficulty_name(r["offset_after"])
        if r["offset_before"] == r["offset_after"]:
            note = "Difficulty stays %s." % after
        elif r["offset_after"] > r["offset_before"]:
            note = "Strong memory! Difficulty rises: %s to %s." % (before, after)
        else:
            note = "The rooms ease up: %s to %s." % (before, after)
        y2 = draw_wrapped(surf, note, self.f_body, COL_LAVENDER, x2, y2, 390, 25)
        if not r["passed"]:
            draw_wrapped(surf, "Press Retry to try again with a fresh puzzle.", self.f_body, COL_MUTED,
                         x2, y2 + 6, 390, 25)

    # ================================================================== ENDING
    def ending_info(self):
        accuracy = self.player.accuracy_percent()
        if accuracy >= 80:
            return ("THE AWAKENING", "Rating: Sharp Mind", COL_GOOD,
                    "The final door opens and daylight floods the corridor. Every object you remembered "
                    "falls into place, and so does the name you almost lost.\n\n"
                    "You step outside as someone who remembers. The building lets you go, and it has "
                    "nothing left to hide from you.")
        if accuracy >= 55:
            return ("THE ECHO", "Rating: Fading Mind", COL_GOLD,
                    "The exit opens, but the light beyond is dim. You escape carrying fragments of what "
                    "you saw and echoes of what you only think you saw.\n\n"
                    "Some details stay blurred. You wonder whether the building released you, or only "
                    "lent you a little more time.")
        return ("THE LOOP", "Rating: Lost Mind", COL_BAD,
                "The door opens, yet the corridor beyond looks strangely familiar. You walk into a room "
                "you have seen before, with the same objects and the same silence.\n\n"
                "You escaped, but memory slipped through your fingers. The building remembers you better "
                "than you remember yourself. Play again and try to remember more.")

    def build_ending(self):
        self.buttons = [
            Button((60, 566, 250, 52), "Dashboard", self.open_dashboard, "secondary"),
            Button((375, 566, 250, 52), "Restart Game", self.restart_game),
            Button((690, 566, 250, 52), "Main Menu", lambda: self.set_state("splash"), "secondary"),
        ]

    def restart_game(self):
        """Erase this player's progress and begin again with the same name."""
        self.player = self.db.create_player(self.player.name)
        self.set_state("level_select")
        self.show_toast("Progress reset. A new attempt begins.")

    def draw_ending(self):
        surf = self.screen
        title, rating, color, text = self.ending_info()
        blit_glow(surf, (WIDTH // 2, 110), 230, color, 60)
        draw_text(surf, "ENDING", self.f_small, COL_MUTED, (WIDTH // 2, 24), "midtop")
        draw_text(surf, title, self.f_h1, color, (WIDTH // 2, 50), "midtop")
        draw_text(surf, rating, self.f_h3, COL_LAVENDER, (WIDTH // 2, 112), "midtop")
        panel = pygame.Rect(120, 146, 760, 322)
        draw_panel(surf, panel)
        draw_wrapped(surf, text, self.f_story, COL_TEXT, panel.x + 36, panel.y + 22, 690, 29)
        draw_text(surf, "Final score: %d     Accuracy: %d%%     Levels cleared: %d / %d"
                  % (self.player.total_score(), self.player.accuracy_percent(),
                     self.player.completed_count(), TOTAL_LEVELS),
                  self.f_h3, COL_GOLD, (WIDTH // 2, 484), "midtop")
        draw_text(surf, "Restart Game erases your saved progress and starts a new attempt.",
                  self.f_small, COL_MUTED, (WIDTH // 2, 526), "midtop")

    # =============================================================== DASHBOARD
    def build_dashboard(self):
        self.buttons = [Button(((WIDTH - 220) // 2, 566, 220, 52), "Back", self.go_back, "secondary")]

    def draw_dashboard(self):
        surf = self.screen
        p = self.player
        draw_text(surf, "Player Dashboard", self.f_h1, COL_LAVENDER, (WIDTH // 2, 18), "midtop")
        draw_text(surf, p.name, self.f_body, COL_MUTED, (WIDTH // 2, 74), "midtop")
        left = pygame.Rect(50, 108, 410, 440)
        right = pygame.Rect(480, 108, 470, 440)
        draw_panel(surf, left)
        draw_panel(surf, right)
        x, y = left.x + 28, left.y + 22
        draw_text(surf, "TOTAL SCORE", self.f_small, COL_MUTED, (x, y))
        draw_text(surf, str(p.total_score()), self.f_big, COL_GOLD, (x, y + 20))
        y += 108
        draw_text(surf, "Completed levels", self.f_small, COL_MUTED, (x, y))
        draw_text(surf, "%d / %d" % (p.completed_count(), TOTAL_LEVELS), self.f_h2, COL_TEXT, (x, y + 20))
        y += 70
        draw_text(surf, "Accuracy", self.f_small, COL_MUTED, (x, y))
        draw_text(surf, "%d%%   (%d of %d questions)" % (p.accuracy_percent(), p.total_correct, p.total_questions),
                  self.f_h3, COL_TEXT, (x, y + 20))
        bar = pygame.Rect(x, y + 52, 350, 14)
        pygame.draw.rect(surf, (12, 7, 26), bar, border_radius=7)
        fill = pygame.Rect(bar.x, bar.y, int(bar.width * p.accuracy_percent() / 100.0), bar.height)
        if fill.width > 0:
            pygame.draw.rect(surf, COL_ACCENT, fill, border_radius=7)
        pygame.draw.rect(surf, COL_PANEL_EDGE, bar, 2, border_radius=7)
        y += 92
        draw_text(surf, "Best performance", self.f_small, COL_MUTED, (x, y))
        if p.best_level_score() > 0:
            best_text = "Level %d  -  %d points" % (p.best_level_number(), p.best_level_score())
        else:
            best_text = "No score yet"
        draw_text(surf, best_text, self.f_h3, COL_TEXT, (x, y + 20))
        y += 64
        draw_text(surf, "Current difficulty", self.f_small, COL_MUTED, (x, y))
        draw_text(surf, LevelManager.difficulty_name(p.difficulty_offset), self.f_h3, COL_TEXT, (x, y + 20))
        # right: table
        rx, ry = right.x + 20, right.y + 18
        draw_text(surf, "Level", self.f_small, COL_MUTED, (rx, ry))
        draw_text(surf, "Status", self.f_small, COL_MUTED, (rx + 272, ry))
        draw_text(surf, "Best", self.f_small, COL_MUTED, (rx + 366, ry))
        draw_text(surf, "Tries", self.f_small, COL_MUTED, (rx + 412, ry))
        ry += 32
        for number in range(1, TOTAL_LEVELS + 1):
            record = p.levels[number]
            row = pygame.Rect(right.x + 12, ry, right.width - 24, 62)
            pygame.draw.rect(surf, (28, 18, 50), row, border_radius=10)
            draw_text(surf, "%d. %s" % (number, LevelManager.TITLES[number]), self.f_body, COL_TEXT,
                      (rx, row.centery), "midleft")
            if record["completed"]:
                status, col = "Done", COL_GOOD
            elif p.is_unlocked(number):
                status, col = "Open", COL_ACCENT
            else:
                status, col = "Locked", (110, 98, 146)
            draw_text(surf, status, self.f_body, col, (rx + 272, row.centery), "midleft")
            draw_text(surf, str(record["best_score"]), self.f_body, COL_TEXT, (rx + 366, row.centery), "midleft")
            draw_text(surf, str(record["attempts"]), self.f_body, COL_TEXT, (rx + 412, row.centery), "midleft")
            ry += 72


def main():
    game = None
    try:
        game = Game()
        game.run()
    finally:
        if game is not None:
            game.db.close()
        pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
