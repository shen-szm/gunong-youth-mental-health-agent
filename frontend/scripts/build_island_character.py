#!/usr/bin/env python3
"""Draw the heart-island student sprite sheet.

Frames are 40x56, six per row: four walk frames then two idle frames.
Rows are down, up, side (side faces right; the scene mirrors it).

Design notes: chibi proportions with a chin-length bob, a soft sage hoodie,
denim jeans, cream sneakers and a tangerine backpack. The head is wider than
the body; arms sit outside a transparent 1px seam and legs keep a 2px inseam,
so the single derived outline separates every limb cleanly at 1x. Skin, cloth
and shoes use distinct values so hands and feet read at game scale.
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'public' / 'images' / 'island' / 'student-back.webp'
SHOT_DIR = Path('/tmp/shengyu-shots')
PREVIEW = SHOT_DIR / 'student-sprite-preview.png'
FRONT_PREVIEW = SHOT_DIR / 'student-front-preview.png'
BACK_PREVIEW = SHOT_DIR / 'student-back-preview.png'
SIDE_PREVIEW = SHOT_DIR / 'student-side-preview.png'
FRONT_WALK_PREVIEW = SHOT_DIR / 'student-front-walk-preview.png'
BACK_WALK_PREVIEW = SHOT_DIR / 'student-back-walk-preview.png'
SIDE_WALK_PREVIEW = SHOT_DIR / 'student-side-walk-preview.png'

W, H = 40, 56
COLS, ROWS = 6, 3

OUTLINE = (62, 45, 38, 255)
HAIR = (126, 82, 56, 255)
HAIR_DARK = (94, 58, 40, 255)
HAIR_LIGHT = (172, 120, 82, 255)
HAIR_SHINE = (210, 160, 112, 255)
SKIN = (250, 214, 176, 255)
SKIN_SHADE = (232, 184, 144, 255)
SKIN_DEEP = (212, 156, 118, 255)
BLUSH = (246, 172, 158, 255)
MOUTH = (196, 112, 100, 255)
EYE = (48, 36, 32, 255)
EYE_SOFT = (96, 66, 56, 255)
WHITE = (255, 252, 246, 255)
HOODIE = (176, 202, 166, 255)
HOODIE_SHADE = (146, 176, 138, 255)
HOODIE_DARK = (112, 144, 112, 255)
HOODIE_LIGHT = (206, 228, 194, 255)
PANTS = (82, 106, 142, 255)
PANTS_DARK = (58, 78, 110, 255)
PANTS_FAR = (66, 88, 120, 255)
PANTS_LIGHT = (108, 134, 170, 255)
SHOE = (236, 226, 208, 255)
SHOE_LIGHT = (252, 246, 232, 255)
SHOE_DARK = (168, 142, 116, 255)
SHOE_LACE = (128, 100, 78, 255)
SHOE_FAR = (204, 188, 168, 255)
BAG = (216, 128, 62, 255)
BAG_DARK = (172, 92, 42, 255)
BAG_LIGHT = (242, 166, 96, 255)
GOLD = (244, 204, 112, 255)
GOLD_DARK = (208, 158, 72, 255)


def put(im, x, y, color):
    if 0 <= x < W and 0 <= y < H:
        im.putpixel((x, y), color)


def rect(im, x0, y0, x1, y1, color):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(im, x, y, color)


def hline(im, x0, x1, y, color):
    for x in range(x0, x1 + 1):
        put(im, x, y, color)


def vline(im, x, y0, y1, color):
    for y in range(y0, y1 + 1):
        put(im, x, y, color)


def span(im, y, x0, x1, color, dy=0):
    hline(im, x0, x1, y + dy, color)


def spans(im, rows, color, dy=0):
    for y, x0, x1 in rows:
        span(im, y, x0, x1, color, dy)


def putc(im, x, y, color, dy=0):
    put(im, x, y + dy, color)


# ---------------------------------------------------------------- heads ----

FRONT_HAIR = (
    [(4, 16, 23), (5, 14, 25), (6, 13, 26), (7, 12, 27), (8, 12, 27)]
    + [(y, 12, 27) for y in range(9, 21)]
    + [(21, 12, 15), (21, 24, 27),
       (22, 12, 14), (22, 25, 27),
       (23, 12, 13), (23, 26, 27)]
)

FRONT_FACE = (
    [(10, 14, 25)]
    + [(y, 14, 25) for y in range(11, 20)]
    + [(20, 15, 24), (21, 16, 23), (22, 17, 22)]
)


def draw_head_front(im, dy):
    spans(im, FRONT_HAIR, HAIR, dy)
    spans(im, FRONT_FACE, SKIN, dy)

    # side-swept fringe with a short forehead on one side
    spans(im, [(10, 14, 25), (11, 14, 25), (12, 14, 25),
               (13, 14, 24), (14, 14, 21)], HAIR, dy)
    putc(im, 24, 13, HAIR_DARK, dy)
    putc(im, 21, 14, HAIR_DARK, dy)

    # one top-left light source
    for x, y in ((18, 4), (17, 5), (18, 5), (16, 6), (17, 6),
                 (15, 7), (16, 7)):
        putc(im, x, y, HAIR_LIGHT, dy)
    putc(im, 17, 5, HAIR_SHINE, dy)
    vline(im, 12, 9 + dy, 12 + dy, HAIR_LIGHT)
    putc(im, 12, 9, HAIR_SHINE, dy)
    vline(im, 26, 15 + dy, 18 + dy, HAIR_DARK)

    # bob tips and inner lock shadows
    for x, y in ((13, 20), (12, 21), (13, 21), (14, 22),
                 (26, 19), (27, 19), (26, 20), (26, 21),
                 (25, 22), (26, 22), (26, 23)):
        putc(im, x, y, HAIR_DARK, dy)

    # gold barrette on the character's right temple
    rect(im, 13, 11 + dy, 14, 12 + dy, GOLD)
    put(im, 14, 12 + dy, GOLD_DARK)
    put(im, 13, 11 + dy, HOODIE_LIGHT)

    # cheek and jaw shading
    putc(im, 24, 20, SKIN_SHADE, dy)
    putc(im, 23, 21, SKIN_SHADE, dy)

    # eyes: 2x3 with one highlight pixel each
    for ex in (16, 22):
        put(im, ex, 15 + dy, WHITE)
        put(im, ex + 1, 15 + dy, EYE)
        put(im, ex, 16 + dy, EYE)
        put(im, ex + 1, 16 + dy, EYE)
        put(im, ex, 17 + dy, EYE)
        put(im, ex + 1, 17 + dy, EYE_SOFT)

    span(im, 19, 15, 16, BLUSH, dy)
    span(im, 19, 23, 24, BLUSH, dy)
    span(im, 20, 19, 20, MOUTH, dy)


BACK_HAIR = (
    [(4, 16, 23), (5, 14, 25), (6, 13, 26), (7, 12, 27), (8, 12, 27)]
    + [(y, 12, 27) for y in range(9, 24)]
    + [(24, 13, 17), (24, 22, 26)]
)


def draw_neck_back(im, dy):
    spans(im, [(y, 18, 21) for y in range(22, 25)], SKIN, dy)
    span(im, 24, 18, 21, SKIN_SHADE, dy)


def draw_head_back(im, dy):
    spans(im, BACK_HAIR, HAIR, dy)

    for x, y in ((18, 4), (17, 5), (18, 5), (16, 6), (17, 6),
                 (15, 7), (16, 7)):
        putc(im, x, y, HAIR_LIGHT, dy)
    putc(im, 17, 5, HAIR_SHINE, dy)
    vline(im, 12, 9 + dy, 12 + dy, HAIR_LIGHT)
    putc(im, 12, 9, HAIR_SHINE, dy)

    # soft shadow along the right contour and layered hair tips
    for x, y in ((26, 14), (26, 15), (26, 16), (26, 17), (26, 18),
                 (26, 19), (25, 19), (25, 20), (25, 21), (24, 21),
                 (24, 22), (23, 22), (23, 23), (14, 24), (17, 24),
                 (22, 24), (26, 24)):
        putc(im, x, y, HAIR_DARK, dy)


SIDE_FACE = (
    [(12, 20, 25)]
    + [(y, 20, 26) for y in range(13, 19)]
    + [(19, 20, 25), (20, 20, 24), (21, 20, 23)]
)

SIDE_HAIR = (
    [(4, 15, 21), (5, 14, 22), (6, 13, 23), (7, 12, 24),
     (8, 12, 25), (9, 12, 26), (10, 12, 26)]
    + [(y, 12, 20) for y in range(11, 24)]
    + [(24, 13, 20)]
)


def draw_head_side(im, dy):
    spans(im, SIDE_HAIR, HAIR, dy)
    spans(im, SIDE_FACE, SKIN, dy)

    # side-swept fringe covers the forehead and slopes back toward the ear
    spans(im, [(10, 21, 27), (11, 21, 27), (12, 20, 26),
               (13, 20, 25), (14, 20, 24), (15, 20, 23),
               (16, 20, 22), (17, 20, 21)], HAIR, dy)
    for x, y in ((27, 10), (26, 11), (26, 12), (25, 13), (24, 14),
                 (23, 15), (22, 16), (21, 17)):
        putc(im, x, y, HAIR_DARK, dy)

    # one top-left light source, plus the fold where the fringe meets the temple
    for x, y in ((16, 4), (17, 4), (15, 5), (16, 5), (15, 6)):
        putc(im, x, y, HAIR_LIGHT, dy)
    putc(im, 16, 5, HAIR_SHINE, dy)
    vline(im, 12, 9 + dy, 12 + dy, HAIR_LIGHT)
    putc(im, 12, 10, HAIR_SHINE, dy)
    for x, y in ((22, 13), (21, 14), (21, 15)):
        putc(im, x, y, HAIR_LIGHT, dy)
    for x, y in ((20, 21), (19, 22), (19, 23), (14, 24), (17, 24)):
        putc(im, x, y, HAIR_DARK, dy)

    # barrette on the near temple
    rect(im, 24, 11 + dy, 25, 12 + dy, GOLD)
    put(im, 25, 12 + dy, GOLD_DARK)
    put(im, 24, 11 + dy, HOODIE_LIGHT)

    # profile: eye on the front plane, cheek and chin read as soft shading
    put(im, 24, 15 + dy, WHITE)
    put(im, 25, 15 + dy, EYE)
    put(im, 24, 16 + dy, EYE)
    put(im, 25, 16 + dy, EYE)
    put(im, 24, 17 + dy, EYE)
    put(im, 25, 17 + dy, EYE_SOFT)
    putc(im, 24, 19, MOUTH, dy)
    putc(im, 22, 18, SKIN_SHADE, dy)
    putc(im, 21, 19, SKIN_SHADE, dy)
    putc(im, 23, 21, SKIN_SHADE, dy)


# ---------------------------------------------------------------- body ----

TORSO_FRONT = (
    [(25, 16, 23), (26, 15, 24)]
    + [(y, 15, 24) for y in range(27, 39)]
)


def draw_torso_front(im, dy):
    spans(im, TORSO_FRONT, HOODIE, dy)

    # collar, shoulder light and one shaded side
    span(im, 25, 17, 22, HOODIE_SHADE, dy)
    span(im, 26, 15, 16, HOODIE_LIGHT, dy)
    span(im, 27, 15, 16, HOODIE_LIGHT, dy)
    vline(im, 24, 28 + dy, 37 + dy, HOODIE_SHADE)

    # simple drawstrings and a straight pocket seam
    vline(im, 18, 26 + dy, 30 + dy, HOODIE_DARK)
    vline(im, 21, 26 + dy, 30 + dy, HOODIE_DARK)
    span(im, 35, 17, 22, HOODIE_SHADE, dy)
    span(im, 38, 15, 24, HOODIE_SHADE, dy)


def draw_arm_front(im, dy, left, drop):
    x0, x1 = (11, 13) if left else (26, 28)
    top = 27 + dy + drop
    span(im, top, 12 if left else 26, 13 if left else 27, HOODIE_SHADE)
    spans(im, [(y, x0, x1) for y in range(top + 1, top + 8)], HOODIE_SHADE)
    put(im, x0, top + 1, HOODIE_LIGHT)
    hline(im, x0, x1, top + 8, HOODIE_DARK)
    rect(im, x0, top + 9, x1, top + 10, SKIN)
    hline(im, x0, x1, top + 10, SKIN_SHADE)


def draw_torso_back(im, dy):
    spans(im, TORSO_FRONT, HOODIE, dy)

    # folded hood resting above the backpack
    span(im, 25, 16, 23, HOODIE_SHADE, dy)
    span(im, 26, 15, 24, HOODIE_SHADE, dy)
    span(im, 27, 17, 22, HOODIE_SHADE, dy)
    span(im, 25, 18, 21, HOODIE_DARK, dy)
    span(im, 27, 16, 17, HOODIE_LIGHT, dy)
    span(im, 27, 22, 23, HOODIE_LIGHT, dy)
    span(im, 38, 15, 24, HOODIE_SHADE, dy)


def draw_backpack_back(im, dy):
    spans(im, [(28, 17, 22)]
          + [(y, 16, 23) for y in range(29, 36)]
          + [(36, 17, 22), (37, 18, 21)], BAG, dy)

    span(im, 28, 17, 22, BAG_LIGHT, dy)
    span(im, 29, 16, 17, BAG_LIGHT, dy)
    span(im, 31, 16, 23, BAG_DARK, dy)
    vline(im, 17, 28 + dy, 30 + dy, BAG_DARK)
    vline(im, 22, 28 + dy, 30 + dy, BAG_DARK)
    vline(im, 23, 32 + dy, 36 + dy, BAG_DARK)
    span(im, 37, 18, 21, BAG_DARK, dy)


def draw_legs_front(im, left_lift, right_lift):
    spans(im, [(y, 14, 25) for y in range(39, 43)], PANTS)
    hline(im, 14, 25, 39, PANTS_DARK)
    hline(im, 19, 20, 42, PANTS_DARK)
    span(im, 40, 15, 16, PANTS_LIGHT)
    vline(im, 25, 40, 41, PANTS_DARK)

    def leg(x0, x1, left, lift):
        bottom = 51 - lift
        for y in range(43, bottom + 1):
            if y >= 49:
                lo, hi = (x0 + 1, x1) if left else (x0, x1 - 1)
            else:
                lo, hi = x0, x1
            span(im, y, lo, hi, PANTS)
            if left:
                put(im, lo, y, PANTS_LIGHT)
            else:
                put(im, hi, y, PANTS_LIGHT)
        span(im, bottom, x0 + 1 if left else x0,
             x1 if left else x1 - 1, PANTS_DARK)

        top = bottom + 1
        shoe_x0, shoe_x1 = (x0 - 1, x1) if left else (x0, x1 + 1)
        span(im, top, shoe_x0, shoe_x1, SHOE_LIGHT)
        span(im, top + 1, shoe_x0, shoe_x1, SHOE)
        span(im, top + 2, shoe_x0, shoe_x1, SHOE_DARK)
        lace_x = (shoe_x0 + shoe_x1) // 2
        put(im, lace_x, top + 1, SHOE_LACE)

    leg(14, 18, True, left_lift)
    leg(21, 25, False, right_lift)


def draw_legs_side(im, near_dx, near_lift, far_dx):
    spans(im, [(y, 14, 25) for y in range(39, 43)], PANTS)
    hline(im, 14, 25, 39, PANTS_DARK)
    span(im, 40, 15, 16, PANTS_LIGHT)

    def far_leg(dx):
        x0, x1 = 15 + dx, 20 + dx
        spans(im, [(y, x0, x1) for y in range(43, 52)], PANTS_FAR)
        vline(im, x1, 43, 50, PANTS_DARK)
        hline(im, x0, x1, 51, PANTS_DARK)
        span(im, 52, x0 + 1, x1 + 1, SHOE_FAR)
        span(im, 53, x0, x1 + 1, SHOE_FAR)
        span(im, 54, x0, x1 + 1, SHOE_DARK)
        put(im, x0 + 1, 53, SHOE_LACE)

    def near_leg(dx, lift):
        x0, x1 = 18 + dx, 23 + dx
        bottom = 51 - lift
        spans(im, [(y, x0, x1) for y in range(43, bottom + 1)], PANTS)
        vline(im, x0, 43, bottom, PANTS_LIGHT)
        vline(im, x1, 43, bottom, PANTS_DARK)
        hline(im, x0, x1, bottom, PANTS_DARK)
        top = bottom + 1
        span(im, top, x0 + 1, x1 + 1, SHOE_LIGHT)
        span(im, top + 1, x0, x1 + 1, SHOE)
        span(im, top + 2, x0, x1 + 1, SHOE_DARK)
        vline(im, x0, top, top + 1, SHOE_DARK)
        put(im, x0 + 1, top + 1, SHOE_LACE)

    far_leg(far_dx)
    near_leg(near_dx, near_lift)


def draw_neck_front(im, dy):
    spans(im, [(y, 18, 21) for y in range(22, 25)], SKIN, dy)
    vline(im, 21, 22 + dy, 24 + dy, SKIN_SHADE)
    span(im, 24, 18, 21, SKIN_SHADE, dy)


def draw_neck_side(im, dy):
    spans(im, [(22, 22, 25), (23, 22, 25)], SKIN, dy)
    vline(im, 22, 22 + dy, 23 + dy, SKIN_SHADE)
    span(im, 24, 22, 25, SKIN_SHADE, dy)


def draw_backpack_side(im, dy):
    spans(im, [(27, 13, 16), (28, 11, 16)]
          + [(y, 11, 16) for y in range(29, 37)]
          + [(37, 12, 16), (38, 13, 15)], BAG, dy)
    span(im, 27, 13, 16, BAG_LIGHT, dy)
    span(im, 28, 11, 16, BAG_LIGHT, dy)
    span(im, 29, 11, 12, BAG_LIGHT, dy)
    span(im, 30, 11, 16, BAG_DARK, dy)
    vline(im, 14, 27 + dy, 29 + dy, BAG_DARK)
    put(im, 14, 31 + dy, GOLD)
    vline(im, 16, 29 + dy, 36 + dy, BAG_DARK)
    span(im, 37, 12, 16, BAG_DARK, dy)
    span(im, 38, 13, 15, BAG_DARK, dy)


def draw_torso_side(im, dy):
    spans(im, [(25, 19, 25), (26, 18, 26), (27, 17, 26)]
          + [(y, 17, 26) for y in range(28, 38)]
          + [(38, 18, 25)], HOODIE, dy)

    span(im, 25, 20, 25, HOODIE_SHADE, dy)
    span(im, 26, 18, 20, HOODIE_SHADE, dy)
    span(im, 26, 18, 19, HOODIE_LIGHT, dy)
    span(im, 27, 18, 19, HOODIE_LIGHT, dy)
    vline(im, 26, 28 + dy, 37 + dy, HOODIE_SHADE)
    vline(im, 17, 28 + dy, 37 + dy, HOODIE_SHADE)
    span(im, 38, 18, 25, HOODIE_SHADE, dy)


def draw_arm_side(im, dy, drop, dx):
    x0, x1 = 22 + dx, 24 + dx
    top = 27 + dy + drop
    put(im, x0, top, HOODIE_LIGHT)
    spans(im, [(y, x0, x1) for y in range(top + 1, top + 8)], HOODIE_SHADE)
    vline(im, x0 - 1, top, top + 10, HOODIE_DARK)
    hline(im, x0, x1, top + 8, HOODIE_DARK)
    rect(im, x0, top + 9, x1, top + 10, SKIN)
    hline(im, x0, x1, top + 10, SKIN_SHADE)


# --------------------------------------------------------------- views ----

FRONT_POSES = {
    0: (0, -1, 0, 1, 1, -1),
    1: (-1, 0, 0, 0, 0, 0),
    2: (0, 1, 1, 0, -1, 1),
    3: (-1, 0, 0, 0, 0, 0),
    4: (0, 0, 0, 0, 0, 0),
    5: (1, 0, 0, 0, 0, 0),
}


def draw_front(im, pose):
    bob, sway, left_lift, right_lift, left_arm, right_arm = FRONT_POSES[pose]
    draw_legs_front(im, left_lift, right_lift)

    upper = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_torso_front(upper, bob)
    draw_arm_front(upper, bob, True, left_arm)
    draw_arm_front(upper, bob, False, right_arm)
    draw_neck_front(upper, bob)
    draw_head_front(upper, bob)
    im.alpha_composite(upper, dest=(sway, 0))


def draw_back(im, pose):
    bob, sway, left_lift, right_lift, left_arm, right_arm = FRONT_POSES[pose]
    draw_legs_front(im, left_lift, right_lift)

    upper = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_torso_back(upper, bob)
    draw_backpack_back(upper, bob)
    draw_arm_front(upper, bob, True, left_arm)
    draw_arm_front(upper, bob, False, right_arm)
    draw_neck_back(upper, bob)
    draw_head_back(upper, bob)
    im.alpha_composite(upper, dest=(sway, 0))


SIDE_POSES = {
    0: (0, 1, 0, -1, 1, -1),
    1: (-1, 0, 1, 0, 0, 0),
    2: (0, -1, 0, 1, -1, 1),
    3: (-1, 0, 1, 0, 0, 0),
    4: (0, 0, 0, 0, 0, 0),
    5: (1, 0, 0, 0, 0, 0),
}


def draw_side(im, pose):
    bob, near_dx, near_lift, far_dx, arm_drop, arm_dx = SIDE_POSES[pose]
    draw_legs_side(im, near_dx, near_lift, far_dx)

    upper = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_backpack_side(upper, bob)
    draw_torso_side(upper, bob)
    draw_arm_side(upper, bob, arm_drop, arm_dx)
    draw_neck_side(upper, bob)
    draw_head_side(upper, bob)
    im.alpha_composite(upper, dest=(0, 0))


# -------------------------------------------------------------- output ----

def outline_frame(frame):
    mask = frame.getchannel('A').point(lambda a: 255 if a else 0)
    ring = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(3)), mask)
    layer = Image.new('RGBA', frame.size, OUTLINE)
    layer.putalpha(ring)
    return Image.alpha_composite(layer, frame)


def build_sheet():
    sheet = Image.new('RGBA', (W * COLS, H * ROWS), (0, 0, 0, 0))
    for row, drawer in enumerate((draw_front, draw_back, draw_side)):
        for col in range(COLS):
            frame = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            drawer(frame, col)
            sheet.alpha_composite(outline_frame(frame), (col * W, row * H))
    return sheet


def checker(width, height, scale):
    bg = Image.new('RGBA', (width * scale, height * scale), (244, 234, 214, 255))
    for y in range(0, bg.height, 24):
        for x in range(0, bg.width, 24):
            if (x // 24 + y // 24) % 2 == 0:
                bg.paste((236, 224, 200, 255),
                         (x, y, min(x + 24, bg.width), min(y + 24, bg.height)))
    return bg


def build_preview(sheet, scale=7):
    gap = 10
    bg = checker(sheet.width, sheet.height, scale)
    enlarged = sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
    bg.alpha_composite(enlarged, (gap, gap))
    return bg.convert('RGB')


def build_frame_preview(sheet, col, row, scale=12):
    frame = sheet.crop((col * W, row * H, (col + 1) * W, (row + 1) * H))
    bg = checker(W, H, scale)
    bg.alpha_composite(frame.resize((W * scale, H * scale), Image.NEAREST), (0, 0))
    return bg.convert('RGB')


def build_walk_preview(sheet, row, scale=10):
    gap = 8
    frames = [sheet.crop((col * W, row * H, (col + 1) * W, (row + 1) * H))
              for col in range(4)]
    width = len(frames) * W * scale + gap * (len(frames) + 1)
    height = H * scale + gap * 2
    bg = Image.new('RGBA', (width, height), (244, 234, 214, 255))
    for y in range(0, height, 24):
        for x in range(0, width, 24):
            if (x // 24 + y // 24) % 2 == 0:
                bg.paste((236, 224, 200, 255),
                         (x, y, min(x + 24, width), min(y + 24, height)))
    for index, frame in enumerate(frames):
        bg.alpha_composite(frame.resize((W * scale, H * scale), Image.NEAREST),
                           (gap + index * (W * scale + gap), gap))
    return bg.convert('RGB')


def main():
    sheet = build_sheet()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, 'WEBP', lossless=True, method=6, quality=100)
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    build_preview(sheet).save(PREVIEW)
    build_frame_preview(sheet, 4, 0).save(FRONT_PREVIEW)
    build_frame_preview(sheet, 4, 1).save(BACK_PREVIEW)
    build_frame_preview(sheet, 4, 2).save(SIDE_PREVIEW)
    build_walk_preview(sheet, 0).save(FRONT_WALK_PREVIEW)
    build_walk_preview(sheet, 1).save(BACK_WALK_PREVIEW)
    build_walk_preview(sheet, 2).save(SIDE_WALK_PREVIEW)
    print(f'{OUT} {OUT.stat().st_size} bytes')
    for path in (PREVIEW, FRONT_PREVIEW, BACK_PREVIEW, SIDE_PREVIEW,
                 FRONT_WALK_PREVIEW, BACK_WALK_PREVIEW, SIDE_WALK_PREVIEW):
        print(path)


if __name__ == '__main__':
    main()
