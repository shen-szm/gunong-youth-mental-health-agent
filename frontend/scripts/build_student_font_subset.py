#!/usr/bin/env python3
"""Build the student pixel-font subset from the installed Fusion Pixel package."""
from pathlib import Path

from fontTools import subset

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'node_modules/@fontsource/fusion-pixel-12px-proportional-sc/files/fusion-pixel-12px-proportional-sc-latin-400-normal.woff2'
OUT = ROOT / 'src/assets/fonts/fusion-pixel-sc-student.woff2'

SOURCES = [
    'src/App.vue',
    *[f'src/views/{name}.vue' for name in ('RoomHomeView', 'StudentChatView', 'TrendView', 'ProfileView', 'TreeHoleView', 'HealingView')],
    *[f'src/components/{name}.vue' for name in ('RoomActionBar', 'StudentAgentRail', 'StudentLeisureHub', 'StudentScreeningCard', 'StudentWellbeingAssessment', 'MusicListeningShelf')],
    *[str(p.relative_to(ROOT)) for p in sorted((ROOT / 'src/components/student').glob('*.vue'))],
    *[str(p.relative_to(ROOT)) for p in sorted((ROOT / 'src/components/island').glob('*.vue'))],
]

EXTRA = set('0123456789:.-/→×·…—，。：、？！（）「」『』【】；《》“”‘’')


def wanted(ch):
    code = ord(ch)
    return (
        0x20 <= code <= 0x7E
        or code in (0x00B7, 0x00D7)
        or 0x2013 <= code <= 0x2026
        or 0x2190 <= code <= 0x21FF
        or 0x3000 <= code <= 0x303F
        or 0x3400 <= code <= 0x9FFF
        or 0xFF00 <= code <= 0xFFEF
    )


chars = set(EXTRA)
for rel in SOURCES:
    chars.update(ch for ch in (ROOT / rel).read_text(encoding='utf-8') if wanted(ch))
chars -= {'\r', '\n', '\t'}

options = subset.Options()
options.flavor = 'woff2'
options.layout_features = ['*']
options.name_IDs = ['*']
options.name_languages = ['*']
options.notdef_outline = True
options.drop_tables += ['FFTM']

font = subset.load_font(str(SRC), options)
subsetter = subset.Subsetter(options=options)
subsetter.populate(unicodes={ord(ch) for ch in chars})
subsetter.subset(font)
OUT.parent.mkdir(parents=True, exist_ok=True)
subset.save_font(font, str(OUT), options)

print(f'student pixel subset: {len(chars)} chars -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)')
