#!/usr/bin/env python3
"""Build the 960x540 pixel-art Heart Island map.

The layout intentionally mirrors the navigation grid in
src/game/island/islandState.js and islandNavigation.js: the cottage, greenhouse,
exchange tree, dock and lantern terrace all sit on their blocker footprints.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "images" / "island"
W, H = 960, 540
SEED = 20261101

# ── palette ──────────────────────────────────────────────────────────────
WATER_DEEP = (32, 100, 132)
WATER = (44, 124, 154)
WATER_MID = (58, 143, 168)
WATER_LIGHT = (86, 174, 190)
WATER_SKY = (132, 205, 208)
FOAM = (196, 236, 230)
FOAM_BRIGHT = (228, 248, 240)

SAND_DARK = (176, 142, 92)
SAND = (214, 180, 118)
SAND_LIGHT = (231, 202, 142)
SAND_PALE = (240, 217, 164)

GRASS_DARK = (66, 108, 54)
GRASS_DEEP = (82, 128, 61)
GRASS = (105, 152, 72)
GRASS_LIGHT = (128, 174, 86)
GRASS_PALE = (152, 193, 106)
GRASS_YELLOW = (172, 201, 112)

DIRT_DARK = (128, 90, 55)
DIRT = (168, 124, 76)
DIRT_LIGHT = (190, 148, 94)
DIRT_PALE = (208, 170, 114)

STONE_DARK = (94, 92, 85)
STONE = (130, 127, 118)
STONE_LIGHT = (160, 157, 145)
STONE_PALE = (188, 184, 168)
STONE_MOSS = (112, 136, 88)
STONE_BLUE = (104, 116, 118)

WOOD_DARK = (78, 49, 30)
WOOD = (112, 72, 42)
WOOD_LIGHT = (146, 99, 57)
WOOD_PALE = (174, 126, 78)

ROOF_DARK = (112, 46, 38)
ROOF = (157, 66, 48)
ROOF_LIGHT = (190, 92, 62)
ROOF_PALE = (214, 122, 82)

WALL_DARK = (132, 98, 64)
WALL = (219, 188, 138)
WALL_LIGHT = (238, 214, 169)
WALL_PALE = (247, 231, 194)

LEAF_DARK = (42, 78, 42)
LEAF_DEEP = (56, 96, 49)
LEAF = (72, 120, 58)
LEAF_LIGHT = (94, 143, 68)
LEAF_PALE = (124, 165, 84)
LEAF_YELLOW = (158, 185, 96)

GLASS_DARK = (74, 117, 112)
GLASS = (139, 190, 180)
GLASS_LIGHT = (184, 222, 210)
GLASS_PALE = (218, 240, 227)

GOLD_DARK = (154, 105, 48)
GOLD = (219, 172, 88)
GOLD_LIGHT = (247, 214, 136)
INK = (47, 35, 28)

SHADOW = (28, 54, 38, 92)
SOFT_SHADOW = (28, 54, 38, 52)

rng = random.Random(SEED)
image = Image.new("RGBA", (W, H), WATER_DEEP)
d = ImageDraw.Draw(image)


# ── tiny drawing helpers ────────────────────────────────────────────────
def rect(x0: int, y0: int, x1: int, y1: int, color) -> None:
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if x1 <= x0 or y1 <= y0:
        return
    d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=color)


def ellipse(x0: int, y0: int, x1: int, y1: int, color) -> None:
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if x1 <= x0 or y1 <= y0:
        return
    d.ellipse((x0, y0, x1 - 1, y1 - 1), fill=color)


def poly(points, color) -> None:
    d.polygon([(int(x), int(y)) for x, y in points], fill=color)


def line(points, color, width: int = 1) -> None:
    d.line([(int(x), int(y)) for x, y in points], fill=color, width=width)


def dot(x: int, y: int, color) -> None:
    d.point((int(x), int(y)), fill=color)


def dither(x0: int, y0: int, x1: int, y1: int, color, chance: float = 0.18, random_source=rng) -> None:
    for y in range(int(y0), int(y1)):
        for x in range(int(x0), int(x1)):
            if random_source.random() < chance:
                dot(x, y, color)


def shadow_ellipse(cx: int, cy: int, rx: int, ry: int, color=SHADOW) -> None:
    ellipse(cx - rx, cy - ry, cx + rx, cy + ry, color)


def outline_rect(x0: int, y0: int, x1: int, y1: int, fill, edge) -> None:
    rect(x0, y0, x1, y1, fill)
    rect(x0, y0, x1, y0 + 1, edge)
    rect(x0, y1 - 1, x1, y1, edge)
    rect(x0, y0, x0 + 1, y1, edge)
    rect(x1 - 1, y0, x1, y1, edge)


# ── water ───────────────────────────────────────────────────────────────
def build_water() -> None:
    rect(0, 0, W, H, WATER_DEEP)
    for y in range(0, H, 6):
        t = y / H
        base = WATER_DEEP if y < 170 else WATER
        rect(0, y, W, y + 6, base)
        if y % 24 == 0:
            dither(0, y, W, min(H, y + 12), WATER_MID, 0.05)

    # bands of quiet current
    for i in range(34):
        y = rng.randrange(18, H - 12)
        length = rng.randrange(18, 68)
        x = rng.randrange(0, W - length)
        shade = WATER_LIGHT if rng.random() < 0.5 else WATER_MID
        rect(x, y, x + length, y + 1, shade)
        if rng.random() < 0.45:
            rect(x + rng.randrange(2, max(3, length - 4)), y + 2, x + length - rng.randrange(0, 4), y + 3, shade)

    # little crests sprinkled around the shore
    for _ in range(90):
        x = rng.randrange(20, W - 20)
        y = rng.randrange(20, H - 14)
        if rng.random() < 0.5:
            rect(x, y, x + rng.randrange(2, 6), y + 1, FOAM)
        else:
            rect(x, y, x + 2, y + 1, WATER_SKY)


# ── island silhouette ───────────────────────────────────────────────────
LAND_POINTS = [
    (58, 158), (74, 114), (112, 82), (166, 60), (238, 45), (318, 36),
    (400, 32), (480, 31), (558, 36), (634, 44), (700, 58), (754, 80),
    (792, 112), (816, 154), (829, 204), (836, 258), (838, 310),
    (834, 360), (822, 406), (800, 444), (766, 470), (718, 490),
    (660, 502), (596, 510), (528, 515), (460, 516), (394, 512),
    (328, 505), (268, 495), (212, 480), (162, 460), (120, 431),
    (88, 392), (66, 346), (52, 296), (47, 246), (50, 200),
]

SAND_POINTS = [
    (54, 158), (69, 109), (107, 77), (162, 54), (235, 39), (315, 30),
    (400, 26), (481, 25), (560, 30), (637, 38), (706, 52), (762, 75),
    (801, 108), (826, 151), (839, 202), (846, 257), (848, 311),
    (844, 362), (831, 410), (808, 450), (772, 477), (722, 498),
    (662, 510), (596, 518), (528, 523), (460, 524), (392, 520),
    (324, 513), (263, 503), (206, 487), (155, 466), (112, 436),
    (80, 396), (58, 349), (44, 298), (39, 246), (42, 199),
]

GRASS_POINTS = [
    (70, 160), (86, 120), (124, 91), (176, 70), (246, 56), (324, 47),
    (402, 43), (480, 42), (556, 47), (630, 55), (692, 69), (744, 90),
    (780, 120), (803, 160), (816, 208), (822, 258), (824, 306),
    (820, 354), (808, 396), (788, 430), (754, 454), (708, 474),
    (652, 486), (590, 494), (524, 499), (460, 500), (396, 496),
    (332, 489), (274, 479), (220, 464), (172, 445), (134, 418),
    (105, 380), (86, 338), (73, 292), (69, 246), (71, 201),
]


def build_land() -> None:
    # deep water halo so the island reads as a rounded shelf
    poly([(x + 3, y + 5) for x, y in SAND_POINTS], (30, 86, 108, 255))
    poly(SAND_POINTS, SAND)
    # wet sand rim and dry sand band
    poly([(x, y) for x, y in SAND_POINTS], SAND)
    inner_sand = [(x + 3, y + 3) for x, y in SAND_POINTS]
    poly(inner_sand, SAND_LIGHT)
    # foam dashes just outside the sand
    for index, (x, y) in enumerate(SAND_POINTS):
        nx, ny = SAND_POINTS[(index + 1) % len(SAND_POINTS)]
        steps = max(2, int(math.hypot(nx - x, ny - y) / 6))
        for step in range(steps):
            t = step / steps
            fx, fy = int(x + (nx - x) * t), int(y + (ny - y) * t)
            if (step + index) % 3 == 0:
                rect(fx - 3, fy - 2, fx + 4, fy, FOAM)
            elif (step + index) % 3 == 1:
                rect(fx - 1, fy - 3, fx + 2, fy - 1, FOAM_BRIGHT)

    # grass layer masked by the organic silhouette
    grass_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grass_layer)
    gd.polygon([(x, y) for x, y in GRASS_POINTS], fill=GRASS)
    # broad tonal patches
    for _ in range(150):
        cx = rng.randrange(70, 830)
        cy = rng.randrange(50, 505)
        rx = rng.randrange(14, 52)
        ry = rng.randrange(8, 28)
        color = rng.choice([GRASS_DARK, GRASS_DEEP, GRASS_LIGHT, GRASS_PALE])
        gd.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=color)
    # fine pixel mottle
    for _ in range(5200):
        x = rng.randrange(55, 840)
        y = rng.randrange(40, 515)
        gd.point((x, y), fill=rng.choice([GRASS_DARK, GRASS_DEEP, GRASS_LIGHT, GRASS_PALE]))
    # sunny southern meadow
    for _ in range(900):
        x = rng.randrange(130, 800)
        y = rng.randrange(320, 505)
        gd.point((x, y), fill=rng.choice([GRASS_PALE, GRASS_YELLOW]))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(x, y) for x, y in GRASS_POINTS], fill=255)
    image.paste(grass_layer, (0, 0), mask)

    # sandy beach wedge on the east and south
    beach = [(806, 280), (846, 288), (848, 360), (838, 404), (816, 438), (780, 456), (744, 468),
             (742, 430), (768, 394), (792, 352), (802, 316)]
    poly(beach, SAND)
    for _ in range(240):
        x = rng.randrange(744, 848)
        y = rng.randrange(280, 468)
        if image.getpixel((x, y))[0] > 150 and image.getpixel((x, y))[1] > 120 and image.getpixel((x, y))[2] < 190:
            dot(x, y, rng.choice([SAND_LIGHT, SAND_DARK, SAND_PALE]))
    # southern beach strip
    poly([(300, 505), (500, 516), (700, 500), (760, 476), (700, 492), (560, 504), (420, 505), (330, 499)], SAND)


# ── shoreline foam & rocks ──────────────────────────────────────────────
def build_shore() -> None:
    # soft inner shadow on the south-east sand
    for i in range(28):
        x = rng.randrange(300, 840)
        y = rng.randrange(492, 520)
        rect(x, y, x + rng.randrange(2, 9), y + 1, (196, 160, 104))

    # scattered shore rocks
    rocks = [(96, 424, 9), (118, 432, 6), (152, 470, 7), (236, 492, 8), (520, 514, 6),
             (612, 508, 8), (748, 474, 7), (806, 430, 9), (838, 392, 6), (842, 246, 7),
             (828, 148, 8), (760, 96, 6)]
    for cx, cy, size in rocks:
        shadow_ellipse(cx + 2, cy + 2, size + 3, 3, SOFT_SHADOW)
        ellipse(cx - size, cy - size // 2, cx + size, cy + size // 2, STONE_DARK)
        ellipse(cx - size + 2, cy - size // 2 + 1, cx + size - 1, cy + size // 2 - 1, STONE)
        rect(cx - size + 3, cy - 2, cx - 1, cy, STONE_LIGHT)


# ── cliffs ──────────────────────────────────────────────────────────────
def draw_rock_wall(points, face_points, seed: int = 1) -> None:
    local = random.Random(seed)
    poly(points, STONE_DARK)
    poly(face_points, STONE)
    # strata
    for y in range(int(min(p[1] for p in face_points)) + 4, int(max(p[1] for p in face_points)), 7):
        line([(40, y), (900, y)], (112, 110, 100), 1)
    # cracks / highlights
    for _ in range(90):
        x = local.randrange(560, 850)
        y = local.randrange(80, 330)
        if image.getpixel((x, y))[0] > 90 and image.getpixel((x, y))[1] > 85:
            w = local.randrange(2, 8)
            rect(x, y, x + w, y + 1, local.choice([STONE_DARK, STONE_LIGHT]))


def build_cliffs() -> None:
    # jagged ridge peeking out behind the greenhouse
    poly([(266, 60), (272, 42), (294, 28), (318, 34), (342, 22), (368, 30), (392, 18),
          (420, 26), (446, 16), (474, 24), (500, 28), (522, 20), (548, 30), (566, 42),
          (572, 58), (540, 62), (500, 54), (458, 60), (412, 52), (366, 62), (318, 56),
          (286, 66)], STONE_DARK)
    poly([(274, 52), (284, 38), (306, 32), (330, 38), (350, 28), (374, 34), (398, 26),
          (422, 32), (448, 24), (476, 30), (502, 34), (526, 28), (548, 36), (560, 46),
          (532, 50), (500, 44), (462, 50), (416, 44), (370, 52), (322, 46), (290, 56)], STONE)
    for x in range(282, 560, 24):
        rect(x, 32 + (x % 9), x + 10, 36 + (x % 9), STONE_LIGHT)
        rect(x + 4, 46 + (x % 11), x + 16, 49 + (x % 11), STONE_DARK)
    for x in range(280, 566, 4):
        if rng.random() < 0.55:
            rect(x, 28 + rng.randrange(0, 5), x + 2, 31 + rng.randrange(0, 5), rng.choice([GRASS_DEEP, LEAF_DARK]))
    for cx, cy, size in [(306, 30, 11), (478, 26, 12)]:
        for layer in range(3):
            yy = cy - layer * 5
            poly([(cx - size + layer * 3, yy), (cx + size - layer * 3, yy), (cx, yy - 16 + layer * 3)], LEAF_DARK)
            poly([(cx - size + layer * 3 + 2, yy - 2), (cx + size - layer * 3 - 2, yy - 2), (cx, yy - 13 + layer * 3)], LEAF_DEEP)

    # north-east crag (islandNavigation blocker) — a stepped rock outcrop, not a boulder
    crag = [(558, 144), (554, 124), (560, 104), (554, 86), (566, 68), (580, 52),
            (598, 40), (618, 32), (640, 30), (662, 38), (674, 52), (684, 72),
            (688, 96), (684, 116), (690, 134), (678, 148), (650, 152), (620, 148),
            (588, 150)]
    poly(crag, STONE_DARK)
    poly([(566, 136), (562, 116), (568, 96), (564, 80), (576, 64), (590, 50),
          (608, 42), (624, 38), (646, 44), (660, 56), (670, 74), (676, 96),
          (672, 114), (680, 128), (666, 141), (642, 145), (610, 140), (582, 142)], STONE)
    # rock courses
    for y in range(58, 140, 7):
        line([(566 + (y % 15), y), (676 - (y % 19), y)], STONE_DARK if y % 21 else (116, 112, 102), 1)
    for x0, y0, w in [(582, 58, 26), (594, 72, 18), (620, 80, 30), (576, 92, 22),
                      (604, 106, 26), (646, 100, 20), (586, 120, 18), (632, 124, 24)]:
        rect(x0, y0, x0 + w, y0 + 2, STONE_LIGHT)
        rect(x0 + 2, y0 + 5, x0 + w - 4, y0 + 6, STONE_DARK)
    # mossy crown with fern overhang
    for _ in range(70):
        x = rng.randrange(560, 690)
        y = rng.randrange(36, 66)
        if 600 < x < 660 and y < 44:
            continue
        rect(x, y, x + rng.randrange(2, 6), y + 2, rng.choice([LEAF_DARK, LEAF_DEEP, GRASS_DEEP]))
    for x in range(562, 688, 9):
        if rng.random() < 0.6:
            line([(x, 66), (x + rng.randrange(-2, 3), 66 + rng.randrange(6, 16))], rng.choice([LEAF_DARK, LEAF]), 1)
    # little star cave — an arched recess cut into the crag, framed by stones
    poly([(606, 132), (604, 118), (608, 106), (614, 98), (622, 93),
          (631, 94), (638, 100), (643, 110), (645, 121), (643, 132)], (52, 40, 36))
    poly([(610, 132), (609, 120), (612, 110), (617, 102), (624, 98),
          (632, 100), (638, 107), (641, 116), (641, 132)], (30, 25, 28))
    poly([(616, 132), (615, 120), (618, 111), (623, 105), (630, 106),
          (635, 112), (636, 121), (636, 132)], (16, 14, 20))
    for sx, sy, sw in [(602, 108, 7), (604, 100, 6), (610, 94, 8), (618, 91, 7),
                       (626, 90, 8), (634, 94, 7), (641, 100, 6), (645, 108, 6), (646, 119, 5)]:
        rect(sx, sy, sx + sw, sy + 4, STONE_LIGHT)
        rect(sx + 1, sy + 4, sx + sw - 1, sy + 6, STONE_DARK)
        if rng.random() < 0.6:
            dot(sx + rng.randrange(1, max(2, sw - 1)), sy - 1, rng.choice([LEAF_DARK, LEAF]))
    for tx, ty, th in [(611, 107, 5), (616, 103, 7), (622, 101, 6), (629, 101, 8), (635, 105, 5), (639, 109, 4)]:
        poly([(tx, ty), (tx + 3, ty), (tx + 1, ty + th)], (20, 17, 22))
    for cx, cy in [(619, 121), (628, 114), (624, 124)]:
        dot(cx, cy, (118, 198, 196))
        dot(cx + 1, cy, (188, 238, 218))
    # stepping stones leading to the mouth
    for sx, sy in [(606, 140), (620, 144), (634, 141)]:
        rect(sx - 4, sy, sx + 4, sy + 3, STONE)
        rect(sx - 3, sy, sx + 3, sy + 1, STONE_LIGHT)
    # pines on the crown
    for cx, cy, size in [(590, 40, 12), (648, 34, 14), (672, 48, 9)]:
        rect(cx - 1, cy + 4, cx + 2, cy + 18, WOOD_DARK)
        for layer in range(3):
            yy = cy + layer * 6
            poly([(cx - size + layer * 4, yy + 6), (cx + size - layer * 4, yy + 6), (cx, yy - 12 + layer * 3)], LEAF_DARK)
            poly([(cx - size + layer * 4 + 2, yy + 4), (cx + size - layer * 4 - 2, yy + 4), (cx, yy - 9 + layer * 3)], LEAF_DEEP)

    # east headland with a small beacon, jagged against the water
    head = [(806, 304), (800, 280), (808, 258), (800, 236), (808, 212), (802, 188),
            (810, 162), (822, 144), (838, 140), (848, 154), (842, 174), (850, 194),
            (846, 218), (852, 240), (846, 264), (840, 286), (832, 304), (818, 310)]
    poly(head, STONE_DARK)
    poly([(816, 296), (810, 276), (818, 256), (812, 236), (820, 214), (814, 190),
          (822, 166), (832, 154), (840, 158), (834, 180), (842, 198), (838, 220),
          (844, 242), (838, 262), (832, 282), (824, 298)], STONE)
    for y in range(162, 300, 8):
        line([(812 + (y % 11), y), (846 - (y % 13), y)], STONE_DARK, 1)
        if y % 24 == 0:
            rect(820, y, 834, y + 2, STONE_LIGHT)
    for _ in range(40):
        x = rng.randrange(806, 850)
        y = rng.randrange(144, 306)
        dot(x, y, rng.choice([STONE_MOSS, LEAF_DARK]))
    # beacon
    rect(824, 158, 842, 176, STONE_DARK)
    rect(826, 160, 840, 174, STONE)
    rect(828, 156, 838, 166, STONE_LIGHT)
    rect(830, 146, 836, 158, WOOD_DARK)
    rect(828, 140, 838, 148, WOOD)
    rect(830, 141, 836, 146, GOLD_LIGHT)
    dot(833, 138, GOLD)
    # grass tufts at the cliff bases
    for _ in range(24):
        x = rng.randrange(790, 850)
        y = rng.randrange(290, 330)
        if image.getpixel((x, y))[1] > 90:
            rect(x, y, x + 2, y + 3, rng.choice([LEAF_DARK, GRASS_DEEP]))


# ── paths ───────────────────────────────────────────────────────────────
def draw_path(points, width: int, seed: int) -> None:
    local = random.Random(seed)
    # dirt shoulder, kept thin so the trail does not read as an asphalt road
    line(points, DIRT_DARK, width + 2)
    line(points, DIRT, width)
    line([(x, y) for x, y in points], DIRT_LIGHT, max(2, width - 12))
    # nibble the edges with grass and gravel so the border is irregular
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dx, dy = x1 - x0, y1 - y0
        length = max(1, math.hypot(dx, dy))
        nx, ny = -dy / length, dx / length
        steps = max(2, int(length / 5))
        for step in range(steps):
            t = step / steps
            bx, by = x0 + dx * t, y0 + dy * t
            for side in (-1, 1):
                if local.random() < 0.22:
                    continue
                ox = int(bx + nx * side * (width / 2 + local.randrange(-1, 3)))
                oy = int(by + ny * side * (width / 2 + local.randrange(-1, 3)))
                if local.random() < 0.45:
                    rect(ox - 1, oy - 1, ox + 2, oy + 1, local.choice([GRASS_DEEP, GRASS_DARK, DIRT]))
                else:
                    rect(ox, oy, ox + 1 + local.randrange(0, 3), oy + 1, local.choice([DIRT_DARK, DIRT_PALE]))
    # speckled surface + light centre
    for _ in range(width * len(points)):
        x = local.randrange(max(0, int(min(p[0] for p in points)) - width), min(W - 1, int(max(p[0] for p in points)) + width))
        y = local.randrange(max(0, int(min(p[1] for p in points)) - width), min(H - 1, int(max(p[1] for p in points)) + width))
        if image.getpixel((x, y))[0] > 120 and image.getpixel((x, y))[1] > 90 and image.getpixel((x, y))[2] < 160:
            color = local.choice([DIRT, DIRT_PALE, DIRT_DARK, (150, 112, 74)])
            if local.random() < 0.18:
                rect(x, y, x + 2, y + 1, color)
            else:
                dot(x, y, color)
    # little border stones
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dx, dy = x1 - x0, y1 - y0
        length = max(1, math.hypot(dx, dy))
        nx, ny = -dy / length, dx / length
        for t in (0.12, 0.38, 0.66, 0.88):
            if local.random() < 0.7:
                continue
            bx, by = int(x0 + dx * t + nx * (width / 2 + 3)), int(y0 + dy * t + ny * (width / 2 + 3))
            ellipse(bx - 2, by - 1, bx + 3, by + 2, STONE)


def build_paths() -> None:
    # south plaza to cottage front door
    draw_path([(480, 512), (480, 492), (482, 452), (484, 412), (488, 382), (486, 356)], 30, 11)
    # exchange tree branch
    draw_path([(464, 446), (416, 430), (362, 416), (312, 400), (276, 386), (252, 374)], 22, 12)
    # dock branch
    draw_path([(512, 446), (566, 424), (620, 402), (674, 382), (720, 360), (756, 346), (790, 342)], 22, 13)
    # greenhouse branch (east side of the cottage)
    draw_path([(584, 356), (606, 320), (616, 282), (620, 244), (606, 208), (590, 184)], 20, 14)
    # lantern terrace spur
    draw_path([(640, 300), (664, 268), (682, 236), (694, 208), (702, 188)], 18, 15)
    # garden through the greenhouse door
    draw_path([(590, 184), (576, 168)], 18, 16)
    # little path from exchange to west meadow
    draw_path([(252, 374), (214, 394), (176, 410), (142, 418)], 16, 17)

    # plaza flagstones
    cx, cy = 480, 484
    ellipse(cx - 46, cy - 30, cx + 46, cy + 32, DIRT_DARK)
    ellipse(cx - 42, cy - 27, cx + 42, cy + 29, STONE)
    for ring, radius in enumerate([12, 24, 36]):
        for angle in range(0, 360, 30):
            rad = math.radians(angle + ring * 8)
            sx = int(cx + math.cos(rad) * radius)
            sy = int(cy + math.sin(rad) * radius * 0.62)
            rect(sx - 3, sy - 2, sx + 4, sy + 2, STONE_LIGHT if (angle // 30) % 2 else STONE_PALE)
    # compass mosaic
    for angle in (0, 90, 180, 270):
        rad = math.radians(angle)
        poly([(cx, cy - 4), (cx + math.cos(rad) * 9, cy + math.sin(rad) * 6),
              (cx + math.cos(rad + 0.5) * 14, cy + math.sin(rad + 0.5) * 8)], STONE_PALE)
    ellipse(cx - 5, cy - 4, cx + 5, cy + 4, GOLD)


# ── cottage ─────────────────────────────────────────────────────────────
def build_cottage() -> None:
    # yard shadow + fence
    shadow_ellipse(482, 356, 126, 20)
    # stone foundation
    outline_rect(392, 342, 572, 362, STONE, STONE_DARK)
    for x in range(398, 568, 12):
        rect(x, 344, x + 8, 348, STONE_LIGHT)
        rect(x + 3, 354, x + 9, 358, STONE_DARK)

    # walls
    outline_rect(396, 286, 568, 356, WALL, WALL_DARK)
    for y in range(292, 352, 8):
        rect(400, y, 564, y + 1, (211, 180, 133))
    # timber frame
    rect(396, 286, 402, 356, WOOD_DARK)
    rect(562, 286, 568, 356, WOOD_DARK)
    rect(396, 286, 568, 291, WOOD_DARK)
    rect(396, 350, 568, 356, WOOD_DARK)
    rect(474, 291, 480, 350, WOOD)
    # diagonal braces
    line([(402, 292), (420, 310)], WOOD_DARK, 2)
    line([(562, 292), (544, 310)], WOOD_DARK, 2)

    # windows
    for wx in (420, 512):
        outline_rect(wx, 304, wx + 32, 334, GOLD_LIGHT, WOOD_DARK)
        rect(wx + 2, 306, wx + 30, 332, GOLD)
        rect(wx + 3, 307, wx + 29, 313, (255, 232, 164))
        rect(wx + 15, 306, wx + 18, 332, WOOD_DARK)
        rect(wx + 2, 319, wx + 30, 321, WOOD_DARK)
        # flower box
        rect(wx - 2, 334, wx + 34, 339, WOOD)
        for fx in range(wx + 1, wx + 33, 6):
            rect(fx, 331, fx + 2, 335, rng.choice([ROOF_LIGHT, GOLD_LIGHT, LEAF_LIGHT]))
    # door
    outline_rect(466, 306, 498, 352, WOOD_DARK, (63, 38, 24))
    rect(468, 310, 496, 352, WOOD)
    for x in range(472, 496, 6):
        rect(x, 312, x + 1, 350, WOOD_DARK)
    ellipse(470, 306, 494, 318, WOOD)
    ellipse(473, 308, 491, 317, WOOD_LIGHT)
    rect(472, 320, 492, 324, GOLD_LIGHT)
    dot(490, 338, GOLD_LIGHT)
    # porch lamp
    for lx in (454, 510):
        rect(lx, 332, lx + 3, 344, WOOD_DARK)
        rect(lx - 3, 326, lx + 6, 336, WOOD_DARK)
        rect(lx - 1, 328, lx + 4, 334, GOLD_LIGHT)

    # steps
    rect(450, 352, 478, 356, STONE_LIGHT)
    rect(446, 356, 484, 360, STONE)
    rect(442, 360, 488, 365, STONE_DARK)
    rect(448, 353, 480, 355, STONE_PALE)

    # roof
    ridge_y, eave_y = 200, 286
    for y in range(ridge_y, eave_y):
        t = (y - ridge_y) / (eave_y - ridge_y)
        half = int(20 + 106 * t)
        rect(482 - half, y, 482 + half, y + 1, ROOF if y % 12 < 7 else (150, 62, 45))
    # shingle rows
    for row_y in range(ridge_y + 7, eave_y, 7):
        t = (row_y - ridge_y) / (eave_y - ridge_y)
        half = int(20 + 106 * t)
        rect(482 - half + 2, row_y, 482 + half - 1, row_y + 1, ROOF_DARK)
        for sx in range(482 - half + 5 + (row_y // 7 % 2) * 4, 482 + half - 5, 11):
            dot(sx, row_y - 1, ROOF_PALE)
    # roof edge outline
    for y in range(ridge_y, eave_y):
        t = (y - ridge_y) / (eave_y - ridge_y)
        half = int(20 + 106 * t)
        dot(482 - half - 1, y, INK)
        dot(482 + half, y, INK)
    rect(482 - 121, eave_y - 2, 482 + 121, eave_y + 2, WOOD_DARK)
    rect(482 - 118, eave_y + 2, 482 + 118, eave_y + 4, ROOF_DARK)
    # ridge cap
    rect(462, 196, 502, 202, ROOF_DARK)
    rect(468, 193, 496, 198, ROOF_LIGHT)
    # chimney
    rect(532, 184, 558, 222, (126, 86, 64))
    rect(536, 188, 554, 218, (154, 100, 72))
    for y in range(192, 216, 7):
        rect(536, y, 554, y + 1, (118, 76, 58))
        dot(542 + (y % 9), y - 1, (180, 122, 88))
    rect(530, 180, 560, 186, STONE_DARK)
    rect(534, 178, 556, 182, STONE_LIGHT)

    # attic window
    outline_rect(470, 230, 494, 254, GOLD_LIGHT, WOOD_DARK)
    rect(472, 232, 492, 252, GOLD)
    rect(479, 232, 482, 252, WOOD_DARK)
    rect(472, 240, 492, 242, WOOD_DARK)
    # hanging sign
    rect(500, 296, 524, 302, WOOD_DARK)
    rect(502, 302, 522, 314, WOOD_LIGHT)
    rect(505, 305, 519, 311, WALL_PALE)
    poly([(509, 306), (512, 310), (515, 306), (514, 313), (510, 313)], ROOF_LIGHT)
    rect(508, 292, 509, 302, WOOD_DARK)
    rect(516, 292, 517, 302, WOOD_DARK)

    # flower beds along the front
    for x in range(402, 562, 10):
        if 450 < x < 486:
            continue
        y = 358 + rng.randrange(-1, 3)
        rect(x, y, x + 6, y + 3, LEAF_DEEP)
        rect(x + 2, y - 2, x + 4, y + 1, rng.choice([ROOF_LIGHT, GOLD, LEAF_LIGHT, WALL_PALE]))
    # bench + mailbox
    rect(586, 330, 606, 334, WOOD)
    rect(588, 334, 590, 344, WOOD_DARK)
    rect(602, 334, 604, 344, WOOD_DARK)
    rect(586, 324, 606, 328, WOOD_LIGHT)
    rect(352, 332, 366, 350, WOOD_DARK)
    rect(349, 326, 369, 336, ROOF)
    rect(352, 330, 366, 333, ROOF_LIGHT)
    rect(365, 331, 369, 334, GOLD_LIGHT)
    rect(357, 350, 360, 362, WOOD_DARK)


# ── greenhouse ──────────────────────────────────────────────────────────
def build_greenhouse() -> None:
    shadow_ellipse(430, 158, 132, 14)
    # stone footing
    outline_rect(312, 142, 550, 164, STONE, STONE_DARK)
    for x in range(318, 546, 14):
        rect(x, 146, x + 9, 150, STONE_LIGHT)
        rect(x + 3, 155, x + 11, 160, STONE_DARK)
    # glass body
    outline_rect(320, 82, 542, 150, GLASS, GLASS_DARK)
    rect(322, 84, 540, 148, (176, 214, 199))
    # raised soil beds seen through the glass
    rect(324, 140, 406, 147, (108, 78, 52))
    rect(326, 139, 404, 142, (128, 94, 60))
    rect(454, 140, 538, 147, (108, 78, 52))
    rect(456, 139, 536, 142, (128, 94, 60))
    for bx in range(330, 402, 12):
        rect(bx, 137, bx + 5, 140, rng.choice([LEAF_DEEP, LEAF]))
    for bx in range(460, 534, 12):
        rect(bx, 137, bx + 5, 140, rng.choice([LEAF_DEEP, LEAF]))
    # plants behind the glass
    for px, py, ph in [(342, 146, 20), (372, 146, 27), (402, 146, 18), (470, 146, 26),
                       (500, 146, 20), (526, 146, 16), (352, 146, 13), (484, 146, 13)]:
        ellipse(px - 8, py - ph, px + 8, py, LEAF_DEEP)
        ellipse(px - 5, py - ph + 2, px + 5, py - 2, LEAF)
        ellipse(px - 3, py - ph + 3, px + 1, py - ph + 7, LEAF_LIGHT)
        rect(px, py - ph + 4, px + 1, py, WOOD_DARK)
        if rng.random() < 0.5:
            dot(px - 3, py - ph + 5, GOLD_LIGHT)
        if rng.random() < 0.35:
            dot(px + 3, py - ph + 8, ROOF_LIGHT)
    # hanging planters from the glass roof
    for hx in (334, 386, 462, 516):
        rect(hx, 86, hx + 1, 96, WOOD_DARK)
        rect(hx - 3, 96, hx + 5, 101, (166, 104, 68))
        ellipse(hx - 5, 98, hx + 7, 106, LEAF)
        dot(hx, 97, rng.choice([ROOF_LIGHT, GOLD_LIGHT, WATER_SKY]))
    # warm lanterns warming the glasshouse
    for lx, ly in [(420, 100), (444, 100)]:
        rect(lx, ly, lx + 4, ly + 6, GOLD_LIGHT)
        dot(lx + 1, ly + 1, (255, 238, 178))
    # glass reflections
    for offset in range(0, 176, 28):
        line([(330 + offset, 146), (362 + offset, 90)], (210, 238, 226), 1)
    # mullions
    for x in range(320, 543, 28):
        rect(x, 82, x + 2, 150, STONE_PALE)
    for y in (96, 116, 136):
        rect(320, y, 542, y + 1, STONE_PALE)
    # door
    outline_rect(412, 108, 448, 150, GLASS_PALE, GLASS_DARK)
    rect(414, 110, 446, 148, (176, 215, 200))
    rect(428, 110, 431, 148, WOOD)
    rect(414, 126, 446, 128, WOOD)
    dot(440, 138, GOLD_DARK)
    # roof
    ridge_y, eave_y = 38, 84
    for y in range(ridge_y, eave_y):
        t = (y - ridge_y) / (eave_y - ridge_y)
        half = int(10 + 112 * t)
        rect(431 - half, y, 431 + half, y + 1, GLASS_LIGHT if y % 10 < 6 else GLASS)
    for y in range(ridge_y, eave_y):
        t = (y - ridge_y) / (eave_y - ridge_y)
        half = int(10 + 112 * t)
        if y % 9 == 0:
            rect(431 - half + 2, y, 431 + half - 1, y + 1, STONE_PALE)
        dot(431 - half - 1, y, GLASS_DARK)
        dot(431 + half, y, GLASS_DARK)
    # roof ribs
    for x in range(-100, 104, 24):
        if x % 48 == 0:
            line([(431 + x, 40), (431 + x, 84)], STONE_PALE, 1)
        else:
            line([(431 + x, 40), (431 + x, 84)], (158, 198, 186), 1)
    rect(415, 36, 447, 41, STONE_LIGHT)
    rect(423, 32, 439, 37, STONE_PALE)
    # door canopy
    rect(406, 104, 454, 109, STONE_PALE)
    # potbelly stove pipe on the glass roof
    rect(474, 48, 488, 72, (72, 76, 78))
    rect(476, 50, 486, 70, (108, 112, 114))
    rect(476, 50, 479, 70, (146, 148, 148))
    for py in range(53, 68, 6):
        rect(475, py, 487, py + 1, (66, 70, 72))
    rect(470, 42, 492, 48, (66, 70, 72))
    rect(472, 40, 490, 43, (130, 134, 136))
    # flower pots & tools
    for px, py in [(330, 170), (350, 169), (520, 170), (536, 168)]:
        rect(px, py, px + 12, py + 9, (166, 104, 68))
        rect(px + 1, py + 1, px + 11, py + 3, (194, 128, 82))
        ellipse(px + 2, py - 8, px + 10, py + 2, LEAF)
        dot(px + 6, py - 6, rng.choice([ROOF_LIGHT, GOLD_LIGHT, WATER_SKY]))
    # watering can + crate
    rect(552, 152, 570, 166, (150, 154, 146))
    rect(556, 146, 565, 153, (172, 176, 164))
    rect(568, 150, 580, 154, (150, 154, 146))
    rect(300, 154, 320, 170, WOOD)
    rect(302, 156, 318, 158, WOOD_LIGHT)
    # garden bed in front
    rect(306, 174, 402, 196, DIRT_DARK)
    rect(308, 176, 400, 194, DIRT)
    for x in range(314, 398, 12):
        rect(x, 180, x + 2, 190, LEAF_DEEP)
        ellipse(x - 3, 176, x + 6, 184, rng.choice([LEAF, LEAF_LIGHT]))
        if rng.random() < 0.5:
            dot(x + 1, 176, GOLD_LIGHT)


# ── exchange tree ───────────────────────────────────────────────────────
def build_exchange_tree() -> None:
    shadow_ellipse(190, 322, 118, 20)
    # trunk with roots
    poly([(164, 330), (158, 300), (164, 264), (176, 238), (196, 238), (208, 264), (214, 300), (216, 330)], WOOD_DARK)
    poly([(170, 326), (168, 298), (174, 266), (182, 246), (196, 246), (204, 268), (206, 300), (208, 326)], WOOD)
    for y in range(252, 322, 9):
        rect(178 + (y % 7), y, 180 + (y % 7), y + 5, WOOD_DARK)
        rect(192 - (y % 5), y + 2, 194 - (y % 5), y + 6, WOOD_LIGHT)
    # roots
    line([(166, 326), (146, 334), (128, 336)], WOOD_DARK, 3)
    line([(208, 326), (228, 334), (242, 337)], WOOD_DARK, 3)
    # branches
    line([(180, 250), (150, 214), (120, 194)], WOOD_DARK, 4)
    line([(200, 248), (232, 212), (264, 190)], WOOD_DARK, 4)
    line([(190, 242), (192, 206), (190, 178)], WOOD, 3)
    # canopy in clusters
    clusters = [
        (96, 132, 36, 30), (128, 105, 30, 26), (168, 92, 34, 28), (208, 100, 30, 24),
        (246, 120, 32, 26), (276, 150, 26, 22), (86, 170, 26, 22), (118, 158, 28, 24),
        (158, 140, 32, 26), (196, 138, 30, 24), (230, 160, 28, 22), (262, 184, 22, 18),
        (142, 190, 24, 18), (104, 202, 20, 16), (222, 200, 20, 16),
    ]
    for cx, cy, rx, ry in clusters:
        ellipse(cx - rx, cy - ry, cx + rx, cy + ry, LEAF_DARK)
    for cx, cy, rx, ry in clusters:
        ellipse(cx - rx + 3, cy - ry + 2, cx + rx - 4, cy + ry - 4, LEAF_DEEP)
    for cx, cy, rx, ry in clusters:
        ellipse(cx - rx + 8, cy - ry + 4, cx + rx - 12, cy + ry - 10, LEAF)
    for cx, cy, rx, ry in clusters:
        if rx > 24:
            ellipse(cx - rx + 14, cy - ry + 6, cx + rx - 20, cy + ry - 18, LEAF_LIGHT)
            for _ in range(10):
                dot(cx + rng.randrange(-rx + 8, rx - 8), cy + rng.randrange(-ry + 6, ry - 10), LEAF_PALE)
    # canopy outline fluff
    for _ in range(90):
        angle = rng.random() * math.tau
        cx, cy = 186 + math.cos(angle) * rng.randrange(80, 102), 146 + math.sin(angle) * rng.randrange(56, 72)
        rect(int(cx), int(cy), int(cx) + 3, int(cy) + 2, rng.choice([LEAF_DARK, LEAF_DEEP]))
    # hanging wish tags
    for tx, ty in [(120, 196), (164, 214), (214, 198), (256, 214)]:
        rect(tx, ty, tx + 1, ty + 12, (204, 184, 142))
        rect(tx - 4, ty + 12, tx + 5, ty + 23, WALL_PALE)
        rect(tx - 3, ty + 13, tx + 4, ty + 22, (244, 226, 184))
        poly([(tx - 1, ty + 16), (tx, ty + 18), (tx + 2, ty + 16), (tx + 1, ty + 20)], ROOF_LIGHT)
    # swing
    line([(118, 196), (110, 254)], WOOD_DARK, 1)
    line([(146, 200), (144, 254)], WOOD_DARK, 1)
    rect(106, 254, 148, 258, WOOD_LIGHT)
    rect(108, 258, 146, 260, WOOD_DARK)
    # bench and sign
    rect(238, 316, 274, 321, WOOD)
    rect(240, 321, 243, 333, WOOD_DARK)
    rect(270, 321, 273, 333, WOOD_DARK)
    rect(238, 310, 274, 315, WOOD_LIGHT)
    # mushrooms & fallen leaves
    for mx, my in [(92, 286), (108, 304), (270, 292), (286, 314), (150, 338), (222, 340)]:
        rect(mx, my, mx + 2, my + 5, WALL_PALE)
        ellipse(mx - 4, my - 3, mx + 6, my + 3, ROOF_LIGHT)
        dot(mx - 1, my - 1, WALL_PALE)
        dot(mx + 3, my, WALL_PALE)
    for _ in range(70):
        x = rng.randrange(76, 306)
        y = rng.randrange(250, 350)
        if image.getpixel((x, y))[1] > 90:
            rect(x, y, x + rng.randrange(1, 4), y + 1, rng.choice([LEAF_YELLOW, GOLD_DARK, ROOF_PALE]))


# ── lantern terrace ─────────────────────────────────────────────────────
def build_terrace() -> None:
    cx, cy = 704, 168
    shadow_ellipse(cx, cy + 18, 62, 16)
    # mossy stone footing under a warm wooden deck
    ellipse(cx - 60, cy - 40, cx + 60, cy + 48, STONE_DARK)
    ellipse(cx - 56, cy - 36, cx + 56, cy + 44, STONE)
    ellipse(cx - 51, cy - 32, cx + 51, cy + 39, WOOD_DARK)
    for gy in range(cy - 30, cy + 36, 6):
        for gx in range(cx - 48, cx + 50, 2):
            nx = (gx - cx) / 46
            ny = (gy - cy) / 27
            if nx * nx + ny * ny > 1:
                continue
            rect(gx, gy, gx + 2, gy + 5, WOOD_LIGHT if gy % 12 else WOOD)
        rect(cx - 46, gy + 4, cx + 46, gy + 5, WOOD_DARK)
    for gx in range(cx - 46, cx + 48, 16):
        rect(gx, cy - 29, gx + 1, cy + 34, (98, 62, 38))
        dot(gx + 1, cy - 20, WOOD_PALE)
        dot(gx + 1, cy + 12, WOOD_PALE)
    # uneven stone rim
    for angle in range(0, 360, 24):
        rad = math.radians(angle)
        x = int(cx + math.cos(rad) * 54)
        y = int(cy + math.sin(rad) * 40)
        w = 8 if angle % 48 else 11
        rect(x - w // 2, y - 2, x + w // 2, y + 4, STONE_LIGHT if angle % 48 else STONE_PALE)
        rect(x - w // 2, y + 3, x + w // 2, y + 5, STONE_DARK)
    dither(cx - 48, cy - 27, cx + 48, cy + 34, STONE_MOSS, 0.015)
    # central stone fire ring, coals and a kettle
    ellipse(cx - 15, cy - 10, cx + 15, cy + 11, STONE_DARK)
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        sx, sy = int(cx + math.cos(rad) * 13), int(cy + math.sin(rad) * 9)
        rect(sx - 3, sy - 2, sx + 4, sy + 3, STONE_LIGHT if angle % 60 else STONE_PALE)
        rect(sx - 2, sy - 3, sx + 3, sy - 1, STONE)
    ellipse(cx - 10, cy - 6, cx + 10, cy + 7, (66, 58, 54))
    for dx, dy, c in [(-5, 0, GOLD_DARK), (1, -2, GOLD), (5, 1, GOLD_DARK), (-1, 3, GOLD_LIGHT), (-3, -3, (204, 108, 62))]:
        rect(cx + dx - 2, cy + dy, cx + dx + 2, cy + dy + 2, c)
    # log seats with cushions
    for ox, oy, color in [(-36, 2, ROOF), (31, -4, (88, 118, 142)), (12, 24, LEAF_DEEP)]:
        rect(cx + ox - 9, cy + oy + 3, cx + ox + 9, cy + oy + 8, WOOD_DARK)
        rect(cx + ox - 8, cy + oy + 2, cx + ox + 8, cy + oy + 6, WOOD_LIGHT)
        rect(cx + ox - 7, cy + oy - 4, cx + ox + 7, cy + oy + 3, color)
        rect(cx + ox - 7, cy + oy - 4, cx + ox + 7, cy + oy - 2, tuple(min(255, c + 26) for c in color))
        rect(cx + ox - 5, cy + oy + 1, cx + ox + 5, cy + oy + 2, tuple(max(0, c - 22) for c in color))
    # kettle
    ellipse(cx - 5, cy - 14, cx + 5, cy - 8, (90, 92, 96))
    rect(cx - 3, cy - 18, cx + 3, cy - 13, (114, 116, 120))
    rect(cx + 4, cy - 13, cx + 8, cy - 11, (90, 92, 96))
    dot(cx, cy - 19, (168, 170, 172))
    rect(cx + 20, cy + 17, cx + 30, cy + 21, WALL_PALE)
    rect(cx + 21, cy + 18, cx + 29, cy + 20, WATER_SKY)
    # low stone wall along the south rim with wildflowers
    for x in range(cx - 44, cx + 48, 10):
        y = cy + 38 + int(math.sin((x - cx) / 18) * 2)
        rect(x, y, x + 8, y + 5, STONE_LIGHT)
        rect(x, y + 4, x + 8, y + 6, STONE_DARK)
        if x % 20 == 0:
            dot(x + 4, y + 2, STONE_MOSS)
    # steps down to path
    for i, (w, yy) in enumerate([(34, 214), (42, 220), (50, 227)]):
        rect(cx - w // 2, yy, cx + w // 2, yy + 5, STONE_LIGHT if i % 2 == 0 else STONE)
        rect(cx - w // 2, yy + 4, cx + w // 2, yy + 6, STONE_DARK)
    # telescope aimed at the bay
    line([(736, 170), (752, 146)], WOOD_DARK, 2)
    rect(746, 138, 762, 145, (86, 96, 110))
    rect(760, 140, 768, 144, GOLD_LIGHT)
    rect(733, 168, 739, 180, WOOD_DARK)
    # bunting of little stars
    for x in range(646, 762, 16):
        y = 124 + int(math.sin(x / 21) * 7)
        rect(x, y, x + 1, y + 1, (220, 202, 158))
        poly([(x + 2, y + 4), (x + 4, y + 1), (x + 6, y + 4), (x + 4, y + 7)], GOLD if x % 32 else GLASS_PALE)
    # lantern posts
    for lx, ly in [(648, 134), (758, 202)]:
        rect(lx - 1, ly, lx + 2, ly + 20, WOOD_DARK)
        rect(lx - 4, ly - 6, lx + 5, ly + 3, WOOD_DARK)
        rect(lx - 2, ly - 4, lx + 3, ly + 1, GOLD_LIGHT)
    # wildflowers around terrace
    for _ in range(30):
        angle = rng.random() * math.tau
        dist = rng.randrange(62, 80)
        x = int(cx + math.cos(angle) * dist)
        y = int(cy + math.sin(angle) * dist * 0.72)
        if image.getpixel((x, y))[1] > 90:
            rect(x, y, x + 1, y + 4, LEAF_DEEP)
            dot(x, y - 1, rng.choice([WALL_PALE, GOLD_LIGHT, (214, 168, 194)]))


# ── dock & bay ──────────────────────────────────────────────────────────
def build_dock() -> None:
    # wet sand around the pier
    poly([(758, 320), (836, 322), (842, 368), (826, 404), (780, 396), (756, 372)], (196, 166, 112))
    for _ in range(80):
        x = rng.randrange(760, 840)
        y = rng.randrange(322, 400)
        dot(x, y, rng.choice([SAND_DARK, SAND_LIGHT, (206, 188, 146)]))

    # pier planks
    rect(742, 330, 906, 366, WOOD_DARK)
    rect(744, 332, 902, 362, WOOD)
    for x in range(748, 900, 10):
        rect(x, 332, x + 8, 360, WOOD_LIGHT if (x // 10) % 3 else (132, 88, 52))
        rect(x + 1, 335, x + 6, 336, WOOD_PALE)
        rect(x + 2, 352, x + 7, 353, WOOD_DARK)
    # plank nails
    for x in range(752, 898, 20):
        dot(x, 338, WOOD_DARK)
        dot(x + 4, 354, WOOD_DARK)
    # posts and rails
    for x in (746, 786, 826, 866, 898):
        rect(x, 318, x + 6, 374, WOOD_DARK)
        rect(x + 1, 320, x + 5, 372, WOOD)
        rect(x - 2, 314, x + 8, 320, WOOD_LIGHT)
        rect(x - 1, 314, x + 7, 316, WOOD_PALE)
    for x0, x1 in [(752, 786), (792, 826), (832, 866), (872, 898)]:
        for offset, sag in ((0, 5), (8, 7)):
            mid_x = (x0 + x1) // 2
            line([(x0, 322 + offset), (mid_x, 322 + offset + sag), (x1, 322 + offset)], (196, 164, 112), 1)
    # hanging lanterns
    for lx in (800, 856):
        rect(lx, 322, lx + 1, 332, WOOD_DARK)
        rect(lx - 4, 332, lx + 5, 342, WOOD_DARK)
        rect(lx - 2, 334, lx + 3, 340, GOLD_LIGHT)
    # crates and barrel at the land end
    rect(730, 342, 746, 360, WOOD)
    rect(732, 344, 744, 358, WOOD_LIGHT)
    rect(744, 344, 748, 362, WOOD_DARK)
    rect(720, 350, 728, 364, WOOD_DARK)
    rect(722, 352, 727, 360, WOOD_LIGHT)
    # rowboat
    poly([(856, 392), (900, 386), (908, 400), (888, 410), (862, 408)], WOOD_DARK)
    poly([(860, 393), (898, 389), (903, 399), (886, 405), (864, 403)], WOOD_LIGHT)
    rect(870, 394, 888, 397, WOOD_PALE)
    line([(898, 392), (916, 376)], WOOD, 2)
    # fishing rod leaning on crates
    line([(728, 340), (742, 312)], (114, 82, 48), 1)
    line([(742, 312), (748, 322)], (204, 204, 190), 1)
    # gull
    rect(884, 306, 888, 308, WALL_PALE)
    rect(890, 308, 894, 310, WALL_PALE)
    dot(885, 305, GOLD_LIGHT)


# ── plaza & spawn ───────────────────────────────────────────────────────
def build_plaza_details() -> None:
    # direction signpost
    rect(438, 436, 463, 468, WOOD_DARK)
    rect(440, 438, 461, 466, WOOD)
    for y, direction, color in [(442, -1, ROOF_LIGHT), (452, 1, GOLD_LIGHT), (462, -1, WATER_SKY)]:
        x0, x1 = (410, 440) if direction < 0 else (460, 490)
        rect(x0, y, x1, y + 7, WOOD_DARK)
        rect(x0 + 1, y + 1, x1 - 1, y + 6, color)
        poly([(x0, y), (x0 - 5, y + 3), (x0, y + 7)], WOOD_DARK)
    rect(436, 442, 470, 445, WOOD_DARK)
    rect(436, 458, 470, 461, WOOD_DARK)
    # bell / heart topiary
    rect(510, 442, 522, 462, WOOD_DARK)
    rect(507, 436, 525, 446, ROOF)
    rect(508, 437, 524, 440, ROOF_LIGHT)
    rect(512, 462, 520, 468, WOOD)
    # planters
    for px, py in [(420, 468), (526, 464)]:
        rect(px, py, px + 20, py + 12, WOOD_DARK)
        rect(px + 1, py + 1, px + 19, py + 4, WOOD_LIGHT)
        for fx in range(px + 3, px + 19, 5):
            rect(fx, py - 4, fx + 1, py + 2, LEAF_DEEP)
            dot(fx, py - 5, rng.choice([ROOF_LIGHT, GOLD, WALL_PALE]))
    # bunting across the plaza
    for x in range(396, 564, 12):
        y = 412 + int(math.sin((x - 396) / 34) * 5)
        rect(x, y, x + 1, y + 1, (220, 200, 160))
        poly([(x + 1, y + 1), (x + 6, y + 1), (x + 3, y + 6)], rng.choice([ROOF_LIGHT, GOLD, WATER_SKY, LEAF_LIGHT]))
    # lily pond at the south-west edge (outside the walkable grid)
    cx, cy = 92, 510
    ellipse(cx - 42, cy - 16, cx + 42, cy + 14, (44, 112, 116))
    ellipse(cx - 38, cy - 13, cx + 38, cy + 12, WATER_MID)
    for lx, ly in [(-20, -4), (4, 2), (22, -6)]:
        ellipse(cx + lx - 6, cy + ly - 3, cx + lx + 6, cy + ly + 3, LEAF)
        dot(cx + lx + 2, cy + ly - 1, (224, 170, 196))
    for _ in range(8):
        x = rng.randrange(cx - 32, cx + 32)
        y = rng.randrange(cy - 9, cy + 8)
        rect(x, y, x + 1, y + 4, LEAF_DARK)
    # flowers around spawn
    for _ in range(42):
        x = rng.randrange(336, 626)
        y = rng.randrange(448, 516)
        if abs(x - 480) < 44 and y > 450:
            continue
        if image.getpixel((x, y))[1] < 90:
            continue
        rect(x, y, x + 1, y + 3, LEAF_DEEP)
        dot(x, y - 1, rng.choice([WALL_PALE, GOLD_LIGHT, ROOF_PALE, (204, 174, 216)]))


# ── lamps, fences, trees, props ─────────────────────────────────────────
LAMP_POINTS = [(137, 352), (252, 387), (365, 405), (472, 385), (574, 330), (668, 275),
               (748, 242), (721, 158), (602, 138), (532, 184), (335, 280), (190, 292)]


def build_lamps() -> None:
    for x, y in LAMP_POINTS:
        shadow_ellipse(x + 2, y + 1, 7, 3, SOFT_SHADOW)
        rect(x - 2, y - 3, x + 2, y + 2, STONE_DARK)
        rect(x - 1, y - 24, x + 1, y - 2, WOOD_DARK)
        rect(x, y - 24, x + 2, y - 2, WOOD)
        # arm
        rect(x - 3, y - 26, x + 4, y - 24, WOOD_DARK)
        # lantern
        rect(x - 5, y - 37, x + 5, y - 25, WOOD_DARK)
        rect(x - 4, y - 35, x + 4, y - 27, GOLD)
        rect(x - 3, y - 34, x + 2, y - 32, GOLD_LIGHT)
        rect(x - 6, y - 39, x + 6, y - 36, WOOD_DARK)
        rect(x - 7, y - 40, x + 7, y - 38, WOOD)
        dot(x, y - 41, WOOD_LIGHT)
        rect(x - 4, y - 25, x + 4, y - 24, WOOD_DARK)


def build_fences() -> None:
    # split-rail fence along the cottage west yard
    fence_x = [330, 352, 374, 396]
    for x in fence_x:
        rect(x, 300, x + 3, 322, WOOD_DARK)
        rect(x + 1, 301, x + 2, 320, WOOD)
        rect(x - 1, 298, x + 5, 301, WOOD_LIGHT)
    for y in (304, 312):
        rect(330, y, 399, y + 2, WOOD)
        rect(330, y + 2, 399, y + 3, WOOD_DARK)
    # fence along the greenhouse east side
    for x in (556, 578, 600):
        rect(x, 156, x + 3, 178, WOOD_DARK)
        rect(x + 1, 157, x + 2, 176, WOOD)
        rect(x - 1, 154, x + 5, 157, WOOD_LIGHT)
    for y in (160, 168):
        rect(556, y, 604, y + 2, WOOD)
    # low stone wall by the terrace
    for x in range(630, 682, 10):
        rect(x, 198, x + 8, 208, STONE)
        rect(x + 1, 200, x + 7, 203, STONE_LIGHT)
        rect(x + 2, 206, x + 8, 209, STONE_DARK)
    dither(630, 198, 682, 210, STONE_MOSS, 0.15)


def build_small_tree(cx: int, cy: int, scale: float = 1.0, pine: bool = False) -> None:
    shadow_ellipse(cx + 2, cy + 14, int(30 * scale), int(8 * scale), SOFT_SHADOW)
    if pine:
        rect(cx - 2, cy - 6, cx + 3, cy + 14, WOOD_DARK)
        tiers = 4
        for tier in range(tiers):
            half = int((18 - tier * 3) * scale)
            top = cy - 30 + tier * 8
            poly([(cx - half, top + 14), (cx + half, top + 14), (cx, top)], LEAF_DARK)
            poly([(cx - half + 2, top + 13), (cx + half - 2, top + 13), (cx, top + 2)], LEAF_DEEP)
            rect(cx - half + 4, top + 8, cx - 2, top + 9, LEAF)
        return
    rect(cx - 3, cy - 6, cx + 3, cy + 14, WOOD_DARK)
    rect(cx - 2, cy - 6, cx + 1, cy + 12, WOOD)
    for ox, oy, rx, ry, color in [
        (-10, -18, 18, 14, LEAF_DARK), (8, -20, 17, 14, LEAF_DARK),
        (0, -30, 18, 15, LEAF_DEEP), (-14, -8, 14, 11, LEAF_DEEP), (12, -9, 13, 10, LEAF_DEEP),
    ]:
        ellipse(cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry, color)
    for ox, oy, rx, ry in [(-8, -19, 12, 8), (8, -22, 12, 8), (0, -30, 12, 9), (-12, -9, 8, 6), (12, -10, 8, 6)]:
        ellipse(cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry, LEAF)
    for ox, oy in [(-6, -22), (10, -26), (0, -33), (-14, -10), (14, -12), (4, -16)]:
        rect(cx + ox, cy + oy, cx + ox + 3, cy + oy + 2, LEAF_LIGHT)


def build_props() -> None:
    # a few pines and round trees framing the island edges
    for cx, cy, sc, pine in [(80, 120, 1.1, True), (806, 110, 1.0, True), (786, 454, 0.9, False),
                             (170, 470, 0.9, False), (712, 470, 0.8, False), (300, 90, 0.9, False)]:
        build_small_tree(cx, cy, sc, pine)

    # bushes
    for cx, cy, size in [(318, 190, 14), (630, 186, 12), (300, 360, 13), (650, 370, 14),
                         (104, 300, 16), (846, 326, 10), (410, 510, 12), (670, 448, 12)]:
        shadow_ellipse(cx + 2, cy + 5, size + 4, 5, SOFT_SHADOW)
        ellipse(cx - size, cy - size // 2, cx + size, cy + size // 2, LEAF_DARK)
        ellipse(cx - size + 2, cy - size // 2 - 2, cx + size - 3, cy + size // 2 - 2, LEAF_DEEP)
        for _ in range(8):
            bx = cx + rng.randrange(-size + 3, size - 4)
            by = cy + rng.randrange(-size // 2, size // 2 - 3)
            rect(bx, by, bx + 2, by + 2, rng.choice([LEAF, LEAF_LIGHT]))
        for _ in range(3):
            dot(cx + rng.randrange(-size, size), cy + rng.randrange(-4, 5), rng.choice([WALL_PALE, GOLD_LIGHT]))

    # grass tufts spread across open ground
    for _ in range(260):
        x = rng.randrange(70, 840)
        y = rng.randrange(60, 510)
        if image.getpixel((x, y))[1] < 92:
            continue
        if rng.random() < 0.55:
            line([(x, y), (x - 2, y - 4)], GRASS_DEEP, 1)
            line([(x + 1, y), (x + 1, y - 5)], GRASS_DARK, 1)
            line([(x + 2, y), (x + 4, y - 3)], GRASS_DEEP, 1)
        else:
            rect(x, y, x + 2, y + 1, GRASS_PALE)

    # flowers in clusters near paths and buildings
    flower_spots = [(360, 300), (610, 352), (330, 425), (640, 300), (520, 200),
                    (250, 330), (760, 300), (410, 470), (560, 470), (120, 210),
                    (780, 240), (300, 160), (660, 130), (860, 330)]
    for sx, sy in flower_spots:
        for _ in range(5):
            x = sx + rng.randrange(-16, 17)
            y = sy + rng.randrange(-10, 11)
            if image.getpixel((x, y))[1] < 92:
                continue
            rect(x, y, x + 1, y + 3, LEAF_DEEP)
            petal = rng.choice([WALL_PALE, GOLD_LIGHT, ROOF_PALE, (212, 166, 196), (196, 216, 236)])
            dot(x, y - 1, petal)
            if rng.random() < 0.5:
                dot(x - 1, y - 1, petal)
                dot(x + 1, y, petal)
            if rng.random() < 0.4:
                dot(x, y - 2, GOLD_LIGHT)

    # stones & pebbles
    for _ in range(40):
        x = rng.randrange(90, 830)
        y = rng.randrange(70, 505)
        if image.getpixel((x, y))[1] < 92:
            continue
        w = rng.randrange(2, 6)
        rect(x, y, x + w, y + 2, STONE_DARK)
        rect(x + 1, y, x + w - 1, y + 1, STONE_LIGHT)

    # tiny critters: butterflies / dots near flowers will be animated in Phaser;
    # here we add dragonflies resting on the dock and a snail by the tree.
    for bx, by in [(624, 330), (586, 228), (340, 450)]:
        rect(bx, by, bx + 3, by + 1, (230, 214, 170))
        rect(bx - 2, by - 2, bx + 1, by, (216, 236, 240))
        rect(bx + 2, by - 2, bx + 5, by, (216, 236, 240))

    # faint sunlit patches
    for _ in range(90):
        x = rng.randrange(110, 800)
        y = rng.randrange(90, 500)
        if image.getpixel((x, y))[1] > 120:
            rect(x, y, x + rng.randrange(2, 6), y + 1, GRASS_YELLOW)


def build_meadows() -> None:
    # village well west of the cottage
    cx, cy = 328, 344
    shadow_ellipse(cx, cy + 8, 24, 7, SOFT_SHADOW)
    rect(cx - 19, cy - 8, cx + 19, cy + 7, STONE_DARK)
    rect(cx - 17, cy - 10, cx + 17, cy + 5, STONE)
    ellipse(cx - 17, cy - 15, cx + 17, cy - 1, STONE_LIGHT)
    ellipse(cx - 13, cy - 12, cx + 13, cy - 3, (58, 92, 94))
    rect(cx - 13, cy - 8, cx + 13, cy - 6, (78, 122, 118))
    for x in range(cx - 16, cx + 16, 7):
        rect(x, cy - 3, x + 4, cy + 3, STONE_LIGHT if (x // 7) % 2 else STONE_PALE)
    # posts + shingled roof
    rect(cx - 16, cy - 30, cx - 13, cy - 6, WOOD_DARK)
    rect(cx + 13, cy - 30, cx + 16, cy - 6, WOOD_DARK)
    poly([(cx - 23, cy - 28), (cx, cy - 42), (cx + 23, cy - 28), (cx + 20, cy - 24), (cx - 20, cy - 24)], ROOF_DARK)
    poly([(cx - 19, cy - 28), (cx, cy - 38), (cx + 19, cy - 28), (cx + 16, cy - 25), (cx - 16, cy - 25)], ROOF)
    for x in range(cx - 16, cx + 17, 5):
        rect(x, cy - 31, x + 3, cy - 29, ROOF_LIGHT)
    dot(cx, cy - 43, GOLD_LIGHT)
    # rope + bucket
    rect(cx, cy - 24, cx + 1, cy - 6, (196, 174, 128))
    rect(cx - 4, cy - 9, cx + 6, cy - 2, WOOD_DARK)
    rect(cx - 3, cy - 8, cx + 5, cy - 3, WOOD_LIGHT)
    rect(cx - 3, cy - 9, cx + 5, cy - 8, STONE)
    # daisies at the base
    for _ in range(8):
        x, y = cx + rng.randrange(-28, 30), cy + rng.randrange(8, 18)
        rect(x, y, x + 1, y + 3, LEAF_DEEP)
        dot(x, y - 1, WALL_PALE)

    # fenced vegetable garden south-east of the dock path
    gx, gy = 650, 428
    for x in (gx - 4, gx + 32, gx + 68):
        rect(x, gy - 2, x + 3, gy + 42, WOOD_DARK)
        rect(x + 1, gy, x + 2, gy + 40, WOOD)
        rect(x - 1, gy - 5, x + 5, gy - 1, WOOD_LIGHT)
    for y in (gy + 2, gy + 22, gy + 40):
        rect(gx - 4, y, gx + 71, y + 2, WOOD)
        rect(gx - 4, y + 1, gx + 71, y + 2, WOOD_DARK)
    for row in range(3):
        y = gy + 6 + row * 15
        rect(gx, y, gx + 64, y + 9, DIRT_DARK)
        rect(gx + 1, y + 1, gx + 63, y + 8, DIRT)
        for col in range(7):
            x = gx + 4 + col * 9
            if row == 0:
                rect(x, y + 2, x + 1, y + 7, LEAF_DEEP)
                rect(x - 2, y + 2, x - 1, y + 5, LEAF)
                rect(x + 2, y + 2, x + 3, y + 5, LEAF)
                dot(x, y + 7, (210, 124, 58))
            elif row == 1:
                ellipse(x - 3, y + 1, x + 4, y + 7, LEAF_DEEP)
                ellipse(x - 2, y + 2, x + 3, y + 6, LEAF_LIGHT)
                dot(x, y + 5, (196, 226, 176))
            else:
                rect(x, y + 1, x + 1, y + 8, LEAF_DEEP)
                ellipse(x - 2, y, x + 3, y + 6, GOLD_LIGHT)
                dot(x, y + 3, GOLD_DARK)
    # scarecrow
    sx, sy = 730, 408
    rect(sx, sy, sx + 2, sy + 34, WOOD_DARK)
    rect(sx - 12, sy + 8, sx + 14, sy + 10, WOOD)
    rect(sx - 13, sy + 11, sx - 1, sy + 24, (116, 88, 108))
    rect(sx + 1, sy + 11, sx + 13, sy + 24, (116, 88, 108))
    rect(sx - 4, sy + 13, sx + 6, sy + 22, WALL_PALE)
    rect(sx - 3, sy + 14, sx + 2, sy + 16, ROOF_LIGHT)
    ellipse(sx - 7, sy + 2, sx + 8, sy + 13, (224, 194, 136))
    dot(sx - 3, sy + 6, INK)
    dot(sx + 3, sy + 6, INK)
    rect(sx - 2, sy + 9, sx + 3, sy + 10, INK)
    rect(sx - 11, sy - 4, sx + 11, sy + 2, (152, 120, 66))
    rect(sx - 6, sy - 9, sx + 6, sy - 2, (180, 144, 78))
    rect(sx - 12, sy - 1, sx + 12, sy + 1, (128, 98, 54))
    # watering can + basket
    rect(gx + 72, gy + 30, gx + 84, gy + 40, (128, 146, 140))
    rect(gx + 75, gy + 25, gx + 81, gy + 31, (150, 168, 158))
    rect(gx + 83, gy + 27, gx + 91, gy + 30, (128, 146, 140))
    rect(gx - 18, gy + 28, gx - 2, gy + 40, WOOD_DARK)
    rect(gx - 16, gy + 30, gx - 4, gy + 38, WOOD_LIGHT)
    ellipse(gx - 14, gy + 26, gx - 6, gy + 32, ROOF_LIGHT)
    ellipse(gx - 8, gy + 27, gx, gy + 33, GOLD_LIGHT)

    # picnic blanket west of the garden
    px, py = 574, 468
    shadow_ellipse(px + 18, py + 9, 34, 8, SOFT_SHADOW)
    rect(px, py, px + 52, py + 22, (196, 96, 82))
    for i in range(0, 52, 8):
        rect(px + i, py, px + i + 4, py + 22, (238, 214, 176))
    for i in range(0, 22, 8):
        rect(px, py + i, px + 52, py + i + 4, (238, 214, 176))
    rect(px + 2, py + 2, px + 50, py + 3, (170, 74, 66))
    # basket and food
    rect(px + 30, py + 5, px + 44, py + 16, WOOD_DARK)
    rect(px + 31, py + 6, px + 43, py + 14, WOOD_LIGHT)
    rect(px + 34, py + 3, px + 40, py + 7, WOOD)
    rect(px + 32, py + 2, px + 36, py + 4, GOLD_LIGHT)
    rect(px + 39, py + 3, px + 43, py + 5, ROOF_LIGHT)
    rect(px + 10, py + 8, px + 18, py + 13, WALL_PALE)
    rect(px + 12, py + 9, px + 16, py + 11, GOLD)
    rect(px + 15, py + 15, px + 19, py + 19, WATER_SKY)
    # little dog beside the blanket
    dx, dy = px + 58, py + 14
    rect(dx, dy, dx + 10, dy + 6, (204, 160, 100))
    rect(dx + 3, dy - 3, dx + 9, dy + 1, (204, 160, 100))
    rect(dx + 2, dy - 2, dx + 9, dy + 1, (222, 180, 114))
    dot(dx + 6, dy - 1, INK)
    dot(dx + 8, dy, INK)
    rect(dx + 9, dy - 1, dx + 12, dy + 1, (222, 180, 114))
    dot(dx + 11, dy, INK)
    rect(dx - 1, dy + 6, dx + 3, dy + 10, (188, 144, 88))
    rect(dx + 7, dy + 6, dx + 11, dy + 10, (188, 144, 88))
    rect(dx + 10, dy + 1, dx + 15, dy + 3, (204, 160, 100))

    # orchard + apiary in the south-west meadow
    for tx, ty in [(154, 438), (208, 446)]:
        build_small_tree(tx, ty, 0.72)
        for _ in range(5):
            dot(tx + rng.randrange(-16, 17), ty + rng.randrange(-34, -3), rng.choice([ROOF_LIGHT, GOLD, ROOF_PALE]))
    # beehives
    for hx, hy in [(118, 450), (130, 466)]:
        rect(hx - 1, hy + 10, hx + 12, hy + 13, WOOD_DARK)
        rect(hx, hy - 2, hx + 11, hy + 11, (196, 152, 86))
        for line_y in range(hy, hy + 11, 3):
            rect(hx, line_y, hx + 11, line_y + 1, (160, 116, 62))
        rect(hx + 2, hy + 5, hx + 9, hy + 8, (64, 48, 34))
        dot(hx + 4, hy + 6, GOLD_LIGHT)
        dot(hx + 7, hy + 7, GOLD_LIGHT)
    for _ in range(10):
        bx, by = rng.randrange(112, 148), rng.randrange(436, 476)
        dot(bx, by, GOLD_LIGHT)
    # split rail gate at the end of the west path
    rect(142, 408, 146, 428, WOOD_DARK)
    rect(166, 408, 170, 428, WOOD_DARK)
    for y in (414, 422):
        rect(140, y, 172, y + 2, WOOD)
        rect(140, y + 2, 172, y + 3, WOOD_DARK)
    rect(152, 410, 160, 426, WOOD_LIGHT)
    line([(152, 410), (160, 426)], WOOD_DARK, 1)
    line([(160, 410), (152, 426)], WOOD_DARK, 1)

    # sleepy cat on the cottage bench
    rect(588, 324, 604, 328, (204, 132, 74))
    rect(588, 322, 594, 326, (216, 146, 84))
    ellipse(590, 318, 600, 326, (216, 146, 84))
    poly([(590, 318), (592, 312), (595, 317)], (216, 146, 84))
    poly([(596, 317), (599, 312), (601, 319)], (216, 146, 84))
    rect(600, 326, 608, 328, (204, 132, 74))

    # a little south-shore jetty beyond the walkable area
    rect(596, 518, 672, 526, WOOD_DARK)
    rect(598, 519, 670, 524, WOOD)
    for x in range(600, 670, 12):
        rect(x, 516, x + 4, 530, WOOD_DARK)
        rect(x + 1, 517, x + 3, 529, WOOD_LIGHT)
    for x in range(602, 668, 10):
        rect(x, 520, x + 7, 523, WOOD_LIGHT)
    poly([(674, 518), (706, 514), (712, 526), (696, 534), (678, 530)], WOOD_DARK)
    poly([(678, 519), (704, 516), (708, 524), (694, 529), (680, 527)], WOOD_LIGHT)
    line([(704, 516), (718, 502)], WOOD, 2)

    # distant islets and a sailboat for depth
    for ix, iy, size in [(24, 54, 1.0), (922, 92, 0.8), (918, 496, 0.9)]:
        ellipse(ix - int(26 * size), iy + 8 - int(8 * size), ix + int(26 * size), iy + 16, (30, 86, 104))
        ellipse(ix - int(22 * size), iy + 2 - int(8 * size), ix + int(22 * size), iy + 12, SAND_DARK)
        ellipse(ix - int(18 * size), iy - int(2 * size), ix + int(18 * size), iy + 10, GRASS)
        build_small_tree(ix, iy - int(2 * size), 0.55 * size, pine=size > 0.85)
    # sailboat
    sx, sy = 902, 246
    rect(sx - 2, sy + 6, sx + 20, sy + 10, WOOD_DARK)
    rect(sx, sy + 7, sx + 18, sy + 9, WOOD_LIGHT)
    rect(sx + 8, sy - 18, sx + 9, sy + 7, WOOD_DARK)
    poly([(sx + 9, sy - 17), (sx + 9, sy + 3), (sx + 20, sy + 3)], WALL_PALE)
    poly([(sx + 7, sy - 12), (sx + 7, sy + 3), (sx - 2, sy + 3)], (226, 212, 174))
    dot(sx + 8, sy - 19, GOLD_LIGHT)

    # duck at the lily pond
    rect(104, 502, 112, 506, WALL_PALE)
    rect(108, 499, 115, 503, WALL_PALE)
    rect(114, 500, 119, 502, GOLD)
    dot(110, 500, INK)


def build_labels() -> None:
    """Tiny in-world signposts. Names stay in the Phaser labels."""
    signs = [
        (500, 382, 'home'), (580, 176, 'garden'), (244, 362, 'exchange'),
        (704, 186, 'rest'), (793, 354, 'dock'),
    ]
    for x, y, kind in signs:
        rect(x - 1, y, x + 1, y + 13, WOOD_DARK)
        rect(x - 11, y - 9, x + 11, y + 2, WOOD_DARK)
        rect(x - 10, y - 8, x + 10, y + 1, WOOD_LIGHT)
        rect(x - 8, y - 6, x + 8, y - 1, WALL_PALE)
        if kind == 'home':
            poly([(x - 3, y - 4), (x, y - 6), (x + 3, y - 4), (x + 2, y - 2), (x, y - 1), (x - 2, y - 2)], ROOF)
        elif kind == 'garden':
            rect(x - 3, y - 4, x - 2, y - 1, LEAF_DEEP)
            rect(x - 1, y - 5, x + 2, y - 1, LEAF)
        elif kind == 'exchange':
            poly([(x - 2, y - 5), (x, y - 3), (x + 2, y - 5), (x + 2, y - 2), (x, y - 1), (x - 2, y - 2)], WATER_SKY)
        elif kind == 'rest':
            dot(x, y - 4, GOLD)
            dot(x, y - 5, GOLD_LIGHT)
        else:
            rect(x - 3, y - 4, x + 3, y - 3, (92, 134, 146))
            poly([(x + 3, y - 4), (x + 6, y - 2), (x + 3, y - 1)], (92, 134, 146))
            dot(x - 2, y - 3, WALL_PALE)


# ── post-processing ─────────────────────────────────────────────────────
def finish() -> None:
    # soft warm vignette to keep the eye on the island
    vignette = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vignette)
    vd.rectangle((0, 0, W, H), fill=20)
    vd.rectangle((34, 26, W - 34, H - 26), fill=0)
    vignette = vignette.filter(ImageFilter.GaussianBlur(46))
    warm = Image.new("RGBA", (W, H), (18, 34, 44, 0))
    alpha = vignette.point(lambda value: int(value * 1.8))
    warm.putalpha(alpha)
    image.alpha_composite(warm)

    # light dither across the water so it does not band
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for _ in range(1400):
        x = rng.randrange(0, W)
        y = rng.randrange(0, H)
        if image.getpixel((x, y))[2] > 150 and image.getpixel((x, y))[0] < 120:
            od.point((x, y), fill=(112, 200, 204, 46))
    image.alpha_composite(overlay)


def main() -> None:
    build_water()
    build_land()
    build_shore()
    build_cliffs()
    build_paths()
    build_cottage()
    build_greenhouse()
    build_exchange_tree()
    build_terrace()
    build_dock()
    build_plaza_details()
    build_fences()
    build_props()
    build_meadows()
    build_lamps()
    build_labels()
    # labels are drawn before the lamps so lamp glows sit above the sign tops
    finish()

    PUBLIC.mkdir(parents=True, exist_ok=True)
    out_png = PUBLIC / "heart-island-base.png"
    out_webp = PUBLIC / "heart-island-base.webp"
    image.convert("RGB").save(out_png, optimize=True)
    image.convert("RGB").save(out_webp, "WEBP", quality=88, method=6)
    print(f"wrote {out_png.relative_to(ROOT)} ({out_png.stat().st_size} bytes)")
    print(f"wrote {out_webp.relative_to(ROOT)} ({out_webp.stat().st_size} bytes)")
    preview = Path("/tmp/shengyu-shots/island-pixel-preview.png")
    preview.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(preview)


if __name__ == "__main__":
    main()
