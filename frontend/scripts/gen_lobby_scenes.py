from math import sqrt
from pathlib import Path

W, H = 1600, 1000
OUT = Path(__file__).resolve().parent.parent / 'public' / 'images' / 'lobby'

def r(x, y, w, h, fill, op=None):
    o = f' opacity="{op}"' if op is not None else ''
    return f'<rect x="{round(x)}" y="{round(y)}" width="{round(w)}" height="{round(h)}" fill="{fill}"{o}/>'

def star(x, y, size, fill, op):
    if size <= 2:
        return r(x, y, 2, 2, fill, op)
    return (r(x, y + 2, size, size - 2, fill, op)
            + r(x + 2, y, size - 2, size, fill, op))

def cloud(x, y, scale, fill, shade, op, rim=None):
    blocks = [
        (0, 20, 132, 24), (22, 8, 62, 16), (54, 0, 54, 18),
        (96, 10, 58, 18), (134, 24, 34, 20),
    ]
    out = []
    for bx, by, bw, bh in blocks:
        out.append(r(x + bx * scale, y + (by + 10) * scale, bw * scale, bh * scale, shade, op * 0.72))
    for bx, by, bw, bh in blocks:
        out.append(r(x + bx * scale, y + by * scale, bw * scale, bh * scale, fill, op))
    if rim:
        out.append(r(x + 54 * scale, y - 4 * scale, 54 * scale, 4 * scale, rim, op * 0.75))
        out.append(r(x + 22 * scale, y + 4 * scale, 62 * scale, 4 * scale, rim, op * 0.5))
    return ''.join(out)

def tree(x, y, scale, p):
    out = []
    out.append(r(x + 14 * scale, y + 34 * scale, 8 * scale, 32 * scale, p['trunk']))
    out.append(r(x + 2 * scale, y + 22 * scale, 34 * scale, 14 * scale, p['tree_dark']))
    out.append(r(x + 8 * scale, y + 10 * scale, 42 * scale, 14 * scale, p['tree']))
    out.append(r(x + 18 * scale, y + 0 * scale, 26 * scale, 12 * scale, p['tree_dark']))
    out.append(r(x + 26 * scale, y + 4 * scale, 10 * scale, 6 * scale, p['tree_light']))
    return ''.join(out)

def house(x, y, scale, p):
    out = []
    out.append(r(x, y + 24 * scale, 52 * scale, 30 * scale, p['wall']))
    out.append(r(x - 6 * scale, y + 16 * scale, 64 * scale, 10 * scale, p['roof']))
    out.append(r(x + 2 * scale, y + 8 * scale, 48 * scale, 10 * scale, p['roof']))
    out.append(r(x + 14 * scale, y + 0 * scale, 24 * scale, 10 * scale, p['roof_dark']))
    out.append(r(x + 10 * scale, y + 33 * scale, 10 * scale, 10 * scale, p['window']))
    out.append(r(x + 34 * scale, y + 38 * scale, 9 * scale, 16 * scale, p['door']))
    out.append(r(x + 1 * scale, y + 36 * scale, 3 * scale, 18 * scale, p['outline'], .55))
    return ''.join(out)

def lantern(x, y, scale, p, op):
    return ''.join([
        r(x + 4 * scale, y, 2 * scale, 6 * scale, p['outline'], op),
        r(x, y + 6 * scale, 10 * scale, 13 * scale, p['window'], op),
        r(x + 2 * scale, y + 8 * scale, 6 * scale, 4 * scale, '#fff8e8', op * .75),
    ])

def island(x, y, w, p, op, flip=False):
    out = []
    # grass cap
    out.append(r(x - 12, y, w + 24, 12, p['grass_light'], op))
    out.append(r(x + 14, y + 12, w - 28, 9, p['grass'], op))
    # dirt body, stepping inward
    levels = [(21, 18, 0), (39, 20, 15), (59, 24, 45), (83, 28, 95), (111, 34, 165)]
    for dy, dh, inset in levels:
        out.append(r(x + inset, y + dy, w - inset * 2, dh, p['dirt'], op))
        out.append(r(x + inset, y + dy + dh - 3, w - inset * 2, 3, p['outline'], op * .55))
    # side highlights and roots
    out.append(r(x + 14, y + 12, 5, 76, p['grass_light'], op * .5))
    for i, rx in enumerate((0.18, 0.42, 0.72)):
        depth = (30, 48, 26)[i]
        out.append(r(x + w * rx, y + 130, 4, depth, p['outline'], op * .4))
        out.append(r(x + w * rx + 7, y + 118, 3, depth * .7, p['outline'], op * .28))
    # flora / dwelling
    out.append(tree(x + (w - 150 if flip else 26), y - 48, 1.0, p))
    out.append(house(x + (22 if flip else w - 96), y - 66, 1.0, p))
    out.append(lantern(x + (w - 40 if flip else 30), y + 2, 1.0, p, op))
    # little stones
    out.append(r(x + 60, y + 20, 14, 5, p['grass_light'], op * .8))
    out.append(r(x + w - 96, y + 18, 20, 5, p['grass_light'], op * .7))
    return ''.join(out)

def boat(x, y, p, op):
    return ''.join([
        r(x, y + 10, 54, 8, p['boat'], op),
        r(x + 8, y + 18, 38, 5, p['outline'], op * .55),
        r(x + 24, y - 20, 3, 32, p['outline'], op * .6),
        r(x + 27, y - 18, 22, 22, p['sail'], op * .85),
        r(x + 6, y + 2, 9, 9, p['window'], op),
    ])

def hill(p, op):
    out = []
    # distant coastline
    out.append(r(0, 806, W, 18, p['hill_grass'], op * .35))
    out.append(r(0, 824, W, 26, p['hill_dark'], op * .55))
    # central mound growing to full width
    rows = [(846, 360), (866, 520), (886, 700), (906, 900), (926, 1120), (946, 1330), (966, 1480), (986, 1600)]
    for i, (y, w) in enumerate(rows):
        out.append(r(800 - w / 2, y, w, 22, p['hill'] if i < 6 else p['hill_dark'], op))
    out.append(r(800 - 185, 842, 370, 6, p['grass_light'], op * .9))
    out.append(r(800 - 265, 862, 530, 5, p['hill_grass'], op * .8))
    # grasses and pebbles
    for dx, dy, h in [(-160, 850, 14), (-96, 858, 10), (-38, 852, 16), (52, 856, 11), (118, 848, 15), (188, 860, 9)]:
        out.append(r(800 + dx, dy - h, 3, h, p['hill_grass'], op * .9))
        out.append(r(800 + dx + 6, dy - h + 4, 3, h - 4, p['grass_light'], op * .7))
    # side trees on the mound shoulders
    out.append(tree(360, 760, 0.9, p))
    out.append(tree(1160, 745, 1.0, p))
    out.append(tree(940, 780, 0.7, p))
    return ''.join(out)

def scene(theme):
    palettes = {
        'day': dict(
            halo='#ecc987', halo_op=.5,
            cloud='#fffaf0', cloud_shade='#e7d5ba', cloud_op=.75, rim='#fffdf8',
            star='#d7b07c', star_op=.22, star_count=10,
            grass_light='#cfdbb7', grass='#b6c7a0', dirt='#c9a77b', outline='#8d6a45',
            tree='#9db786', tree_dark='#7f9a6a', tree_light='#b5c99c', trunk='#8c6a45',
            wall='#f4e7cf', roof='#b98a5a', roof_dark='#9a6d42', window='#ffdb91', door='#8d6a45',
            sea='#cfdcc9', ripple='#a9bda2', hill='#ddcbae', hill_dark='#cdb898', hill_grass='#b6c7a0',
            boat='#b98555', sail='#fff6e5', firefly='#d8a95e', firefly_op=0, birds='#9b7a55',
        ),
        'evening': dict(
            halo='#e3b46d', halo_op=.42,
            cloud='#5d4437', cloud_shade='#3e2e25', cloud_op=.9, rim='#c49a63',
            star='#f0d9a8', star_op=.45, star_count=22,
            grass_light='#5c6646', grass='#4a5338', dirt='#3a2b22', outline='#1e1611',
            tree='#46503a', tree_dark='#333d2c', tree_light='#5b6644', trunk='#6b4c33',
            wall='#4a382c', roof='#7a553b', roof_dark='#5e4029', window='#ffd486', door='#2b1f18',
            sea='#2c241e', ripple='#6d563a', hill='#2b1f19', hill_dark='#211814', hill_grass='#3d4633',
            boat='#7a573b', sail='#e8d3ad', firefly='#ffd486', firefly_op=.8, birds='#a98858',
        ),
        'night': dict(
            halo='#e3c27d', halo_op=.3,
            cloud='#251d18', cloud_shade='#191411', cloud_op=.92, rim='#6f5a3a',
            star='#f5e8cb', star_op=.62, star_count=38,
            grass_light='#39442f', grass='#2c3427', dirt='#221a15', outline='#0d0a08',
            tree='#293226', tree_dark='#1c241b', tree_light='#3a4632', trunk='#5a402c',
            wall='#2a211a', roof='#4e3828', roof_dark='#38271c', window='#ffd88f', door='#17110d',
            sea='#14110e', ripple='#5c4a33', hill='#110e0c', hill_dark='#0c0a08', hill_grass='#252a20',
            boat='#54402f', sail='#c9b48e', firefly='#ffd88f', firefly_op=.9, birds='#6f5a3a',
        ),
    }
    p = palettes[theme]
    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" shape-rendering="crispEdges" role="img" aria-label="像素心岛背景">')
    parts.append('<defs>')
    parts.append(f'<radialGradient id="halo" cx="50%" cy="34%" r="52%"><stop offset="0%" stop-color="{p["halo"]}" stop-opacity="{p["halo_op"]}"/><stop offset="58%" stop-color="{p["halo"]}" stop-opacity="{p["halo_op"] * .38:.3f}"/><stop offset="100%" stop-color="{p["halo"]}" stop-opacity="0"/></radialGradient>')
    parts.append(f'<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{p["sea"]}" stop-opacity="0"/><stop offset="100%" stop-color="{p["sea"]}" stop-opacity=".85"/></linearGradient>')
    parts.append('</defs>')

    parts.append('<ellipse cx="800" cy="310" rx="470" ry="380" fill="url(#halo)"/>')

    # 日月由首页动态天象层绘制，场景只保留光晕与岛屿。

    # stars / dust
    stars = [
        (240, 130, 3), (340, 220, 2), (520, 118, 2), (640, 196, 3), (940, 120, 2),
        (1080, 210, 3), (1210, 122, 2), (1330, 238, 3), (1470, 158, 2), (160, 318, 2),
        (300, 386, 3), (500, 300, 2), (700, 108, 2), (880, 370, 2), (1030, 310, 3),
        (1160, 400, 2), (1300, 340, 2), (1430, 430, 3), (90, 180, 2), (1510, 300, 2),
        (420, 460, 2), (630, 420, 2), (980, 460, 2), (1380, 500, 2),
    ]
    for i, (sx, sy, ss) in enumerate(stars):
        if i < p['star_count']:
            parts.append(star(sx, sy, ss, p['star'], p['star_op']))

    # clouds
    parts.append(cloud(150, 250, 1.2, p['cloud'], p['cloud_shade'], p['cloud_op'], p.get('rim')))
    parts.append(cloud(1200, 232, 1.0, p['cloud'], p['cloud_shade'], p['cloud_op'] * .95, p.get('rim')))
    parts.append(cloud(330, 520, .8, p['cloud'], p['cloud_shade'], p['cloud_op'] * .7, p.get('rim')))
    parts.append(cloud(1080, 560, .7, p['cloud'], p['cloud_shade'], p['cloud_op'] * .65, p.get('rim')))

    # birds
    for bx, by in ((1040, 256), (1090, 230), (1140, 270)):
        parts.append(r(bx, by, 8, 3, p['birds'], .55))
        parts.append(r(bx + 8, by - 3, 8, 3, p['birds'], .55))
        parts.append(r(bx + 16, by, 8, 3, p['birds'], .55))

    # floating islands
    parts.append(island(96, 564, 320, p, .92))
    parts.append(island(1216, 500, 300, p, .9, flip=True))

    # sea
    parts.append(r(0, 768, W, 58, 'url(#sea)'))
    for i, (rx, ry, rw) in enumerate(((90, 790, 150), (310, 806, 90), (600, 792, 180), (860, 812, 120), (1120, 796, 160), (1360, 810, 110), (1470, 786, 70))):
        parts.append(r(rx, ry, rw, 3, p['ripple'], .5))
    parts.append(boat(980, 782, p, .9))

    # foreground hill
    parts.append(hill(p, .98))

    # fireflies
    if p['firefly_op']:
        for fx, fy in ((420, 760), (560, 700), (690, 752), (900, 720), (1040, 758), (1230, 690), (1360, 748), (760, 810), (300, 800), (1470, 800)):
            parts.append(r(fx, fy, 4, 4, p['firefly'], p['firefly_op']))
            parts.append(r(fx + 1, fy + 1, 2, 2, '#fff6dc', p['firefly_op']))

    parts.append('</svg>')
    (OUT / f'lobby-scene-{theme}.svg').write_text(''.join(parts), encoding='utf-8')
    print(theme, len(''.join(parts).encode('utf-8')))

for theme in ('day', 'evening', 'night'):
    scene(theme)
