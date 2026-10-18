#!/usr/bin/env python3
"""JARVIS HUD skin spec for MRiscoC ProUI on the Voxelab Aquila X2 (DWIN T5UIC1, 272x480 portrait).

Data shared by the skin tools in this folder:
  PALETTE  C11 slot 2..20 -> (R, G, B) as RGB565 components (R 0-31, G 0-63, B 0-31), the same
           values as the JARVIS_PALETTE defaults in Marlin/src/lcd/dwin/proui/dwin_defines.h
  SLOTS    C11 slot -> (Def_<name>_Color name, label of the slot in the Select Colors menu)
  JV       named accents, the same values as the JV_* macros in dwin_defines.h
  ICONS    icon id -> (W, H, class)
  LAYOUT   firmware screen coordinates in pixels
  write_theme(path) writes the C11 theme G-code

`python3 -I buildroot/share/dwin/jarvis/jarvis_spec.py` writes themes/jarvis_theme.gcode, re-reads
it and asserts its format and values, then asserts that dwin_defines.h still matches PALETTE and JV.
Standard library only. `python3 -I` does not put this folder on sys.path, so other tools add it
themselves (sys.path.insert(0, <this folder>)) before `import jarvis_spec`.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
THEME = os.path.join(ROOT, 'themes', 'jarvis_theme.gcode')
DEFINES = os.path.join(ROOT, 'Marlin', 'src', 'lcd', 'dwin', 'proui', 'dwin_defines.h')

# Named accents; dwin_defines.h has them as JV_CYAN, JV_TEAL, JV_ICE and JV_AMBER
JV = {
    'CYAN':  (0, 57, 31),
    'TEAL':  (0, 44, 22),
    'ICE':   (25, 59, 31),
    'AMBER': (31, 44, 0),
}

# C11 slot -> (Def_<name>_Color, Select Colors menu label), as DWIN_ApplyColor(element) in dwin.cpp
# maps them. C11 E0 redraws the screen and C11 E1 restores the firmware defaults.
SLOTS = {
    2:  ('Background', 'Screen Background'),
    3:  ('Cursor', 'Cursor'),
    4:  ('TitleBg', 'Title Background'),
    5:  ('TitleTxt', 'Title Text'),
    6:  ('Text', 'Text'),
    7:  ('Selected', 'Selected'),
    8:  ('SplitLine', 'Split Line'),
    9:  ('Highlight', 'Highlight'),
    10: ('StatusBg', 'Status Background'),
    11: ('StatusTxt', 'Status Text'),
    12: ('PopupBg', 'Popup Background'),
    13: ('PopupTxt', 'Popup Text'),
    14: ('AlertBg', 'Alert Background'),
    15: ('AlertTxt', 'Alert Text'),
    16: ('PercentTxt', 'Percent Text'),
    17: ('Barfill', 'Bar Fill'),
    18: ('Indicator', 'Indicator value'),
    19: ('Coordinate', 'Coordinate value'),
    20: ('Bottom', 'Bottom Line'),
}

PALETTE = {
    2:  (0, 0, 0),      # pure black: Draw_IconWB paints the icons' black background
    3:  JV['CYAN'],     # selection frames
    4:  (0, 14, 11),    # popup buttons (the title bar becomes an icon)
    5:  (20, 63, 31),
    6:  JV['ICE'],
    7:  (0, 20, 10),
    8:  (0, 18, 12),
    9:  JV['TEAL'],     # popup frame
    10: (0, 6, 6),
    11: (15, 58, 31),
    12: (0, 6, 6),
    13: JV['ICE'],
    14: (8, 6, 0),
    15: JV['AMBER'],
    16: JV['CYAN'],
    17: (0, 8, 6),      # unlit part of the progress bar
    18: JV['CYAN'],
    19: JV['ICE'],
    20: (0, 30, 18),
}

ICONS = {}  # filled by Task 5

# Screen coordinates of the ProUI firmware (tag 2.1.3h-7-HC32, PROUI_EX with the toolbar), in pixels
# from the top left corner: positions (x, y) are top-left corners, boxes (x1, y1, x2, y2) are
# inclusive, sizes and fonts are (w, h). The 'jv_*' entries are where the JARVIS_* switches draw.
LAYOUT = {
    'screen': (272, 480),
    'font': {'menu': (8, 16), 'head': (10, 20), 'stat': (10, 20), 'boot': (12, 24), 'mesh': (6, 12)},
    'title': {
        'box': (0, 0, 271, 29),             # TITLE_HEIGHT 30, TitleBg
        'text_y': 4,                        # caption 10x20 centered, TitleTxt
        'jv_icon': (0, 0),                  # JARVIS_TITLE: icon 130 (272x30) instead of the box
    },
    'main_area': (0, 30, 271, 353),
    'status': {'box': (0, 354, 271, 374), 'text_y': 356, 'chars': 34},  # STATUS_Y 354, 8x16 text
    'menu': {                               # row L: MYPOS(L) = 30 + 53 * L, MBASE(L) = MYPOS(L) + 18
        'mypos0': 30, 'mline': 53, 'mbase_dy': 18,
        'trows': 6, 'mrows': 5,             # rows per page, rows besides Back
        'icon_x': 26, 'icon_dy': 15,        # 20x20 icon at (26, MBASE(L) - 3)
        'label_x': 55, 'label_dy': 17,      # 8x16 label at (55, MBASE(L) - 1)
        'value_x': 210,                     # value at (210, MBASE(L) - 1), Selected background while edited
        'more_x': 226, 'more_icon': 26,     # at (226, MBASE(L) - 3)
        'split_x': 16, 'split_w': 240,      # SplitLine at y = MYPOS(L + 1)
        'cursor_x': 0, 'cursor_size': (15, 52),  # Cursor box at (0, MYPOS(L))
        'jv_cursor_icon': 77,               # JARVIS_CURSOR: icon 77 (14x52) at (0, MYPOS(L))
    },
    'main_menu': {
        'logo': (71, 52), 'logo_icon': 0,   # 130x26
        'buttons': {'print': (17, 90), 'prepare': (145, 90), 'control': (17, 206), 'level': (145, 206)},
        'button_icons': {'print': 1, 'prepare': 3, 'control': 5, 'level': 7},
        'button_size': (110, 100),          # selected: icon id + 1 and a double Cursor frame
        'caption_dy': 72,                   # caption 8x16 centered on the button at y + 72
    },
    'toolbar': {'y': 321, 'h': 28, 'item_y': 326, 'x0': 76, 'dx': 24},  # 5 items 20x20 at x0 + dx * i, no caption shown
    'print': {
        'filename_y': 60,                   # 8x16 centered
        'bar': (15, 93), 'bar_icon': 25, 'bar_size': (242, 20),  # Barfill from x 15 + pct * 242 // 100 to 257
        'percent': (117, 133),              # PercentTxt
        'time_icons': ((15, 171), (150, 171)),  # icons 15 / 16 (24x24): elapsed / remaining
        'time_labels': ((46, 173), (181, 173)),
        'time_values': ((45, 192), (181, 192)),
        'buttons': {'tune': (8, 232), 'pause': (96, 232), 'stop': (184, 232)},  # resume uses the pause slot
        'button_icons': {'tune': 17, 'pause': 19, 'resume': 21, 'stop': 23},    # selected: id + 1
        'button_size': (80, 100),
    },
    'dashboard': {                          # numbers 10x20 in Indicator color
        'box': (0, 375, 271, 479),
        'value_y': (384, 417),              # rows 1 and 2, whose icons are at y 383 and 416
        'hotend_icon': (9, 383), 'bed_icon': (9, 416),      # icons 9 / 47
        'temp_x': 28, 'slash_x': 60, 'target_x': 71, 'degree_x': 104,
        'speed_icon': (113, 383), 'flow_icon': (113, 416),  # icons 11 / 74
        'pct_value_x': 136, 'pct_x': 168,
        'fan_icon': (187, 383), 'fan_x': 215,               # icon 48
        'zoffset_icon': (187, 416), 'zoffset': (204, 417),  # icon 12 (76 with leveling on), signed value
        'rules_y': ((449, 450), (478, 479)),                # full width, Bottom color
        'xyz_icons': ((10, 454), (95, 454), (180, 454)),    # icons 59 / 60 / 61
        'xyz_values': ((27, 457), (112, 457), (197, 457)),  # 8x16, Coordinate color
        'jv_frame': (0, 375),               # JARVIS_DASH_FRAME: icon 131 (272x105) at STATUS_Y + 21
        'jv_gauges': ((4, 381), (4, 414)),  # JARVIS_GAUGES: hotend 110 + level, bed 120 + level (24x24)
    },
    'popup': {
        'box': (14, 60, 258, 330),          # PopupBg, Highlight frame
        'icon_110x100': (81, 90), 'icon_80x100': (96, 90), 'icon_73x66': (100, 107),
        'text_y': (210, 240),               # 8x16 centered, PopupTxt
        'button_size': (100, 38),           # TitleBg, Text caption; selected: 2 px Cursor frame outside
        'button': (86, 280),                # one button
        'buttons': ((26, 280), (146, 280)), # Confirm / Cancel
    },
    'boot': {                               # the display shows 0_start.jpg on its own first
        'name_y': 220,                      # MACHINE_NAME 12x24 centered (HMI_Init)
        'bar': (15, 260), 'bar_steps': 23,  # icon 25 revealed in 23 steps
        'frame': (20, 220, 251, 334),       # Init(): growing frame, then the texts
        'text_y': (230, 260, 280, 305),
        'jv_spinner': (96, 90),             # JARVIS_BOOT: icons 100-107 (80x80)
        'jv_text_y': (220, 296, 318),       # JARVIS_BOOT: name 12x24 CYAN, ProUI-EX 8x16 ICE, version 6x12 TEAL
    },
}


def theme_text():
    """The theme G-code in the format of themes/blue_theme.gcode (comments from column 21)."""
    rule = ';' + '-' * 53
    lines = [
        '; JARVIS theme file',
        '; Professional Firmware Theme File',
        '; Generated by buildroot/share/dwin/jarvis/jarvis_spec.py',
        ';' + '=' * 53,
        '%-21s; Mark as a configuration/theme file' % 'C10',
        rule,
    ]
    for slot in sorted(PALETTE):
        lines.append('%-21s;%s' % ('C11 E%-3dR%d G%d B%d' % ((slot,) + PALETTE[slot]), SLOTS[slot][1]))
    lines += [
        ';',
        'C11 E0  ;Preview changes',
        rule,
        '%-21s; Wait a second' % 'G4 S1',
        '%-21s; Beep' % 'M300 P200',
        'M117 JARVIS theme',
        '%-21s; Uncomment to keep the colors after a restart' % ';M500',
    ]
    return '\n'.join(lines) + '\n'


def write_theme(path):
    with open(path, 'w', encoding='ascii', newline='\n') as f:
        f.write(theme_text())


def check_theme(path):
    """Re-read a theme file and assert what the firmware needs; AssertionError on the first problem."""
    with open(path, 'rb') as f:
        data = f.read()
    assert data.isascii(), 'non-ASCII byte'
    assert b'\r' not in data and data.endswith(b'\n'), 'not LF line endings with a final newline'
    lines = data.decode('ascii').split('\n')
    cmds = [ln.split(';', 1)[0].split() for ln in lines]
    cmds = [c for c in cmds if c]                       # active commands, comments dropped
    assert cmds[0] == ['C10'], 'the first command is not C10'
    slots, e0 = {}, []
    for i, words in enumerate(cmds):
        if words[0] != 'C11':
            continue
        args = {w[0]: int(w[1:]) for w in words[1:]}
        assert 'E' in args, 'C11 without E'
        e = args['E']
        assert e != 1, 'C11 E1 would restore the firmware defaults'
        if e == 0:
            e0.append(i)
            continue
        assert 2 <= e <= 20 and e not in slots, 'C11 E%d unknown or repeated' % e
        assert sorted(args) == ['B', 'E', 'G', 'R'], 'C11 E%d needs exactly R, G and B' % e
        rgb = (args['R'], args['G'], args['B'])
        assert rgb[0] <= 31 and rgb[1] <= 63 and rgb[2] <= 31 and min(rgb) >= 0, 'C11 E%d out of range' % e
        slots[e] = (i, rgb)
    assert sorted(slots) == list(range(2, 21)), 'E2..E20 must each appear exactly once'
    assert len(e0) == 1 and e0[0] > max(i for i, _ in slots.values()), 'need one C11 E0 after the slots'
    assert {e: rgb for e, (_, rgb) in slots.items()} == PALETTE, 'values differ from PALETTE'
    assert ['M500'] not in cmds and any(ln.startswith(';M500') for ln in lines), 'M500 must be commented out'


def check_defines(path):
    """Assert that dwin_defines.h has JV and, in its JARVIS_PALETTE branch, PALETTE."""
    with open(path, encoding='ascii') as f:
        src = f.read()
    rgb = r'\(RGB\(\s*(\d+),\s*(\d+),\s*(\d+)\)\)'
    jv = {m.group(1): tuple(map(int, m.groups()[1:]))
          for m in re.finditer(r'^\s*#define\s+JV_(\w+)\s+' + rgb, src, re.M)}
    assert jv == JV, 'JV_* macros %s differ from JV' % jv
    branch = re.search(r'^#if ENABLED\(JARVIS_PALETTE\)[ \t]*(?://[^\n]*)?\n(.*?)^#else', src, re.M | re.S)
    assert branch, 'no #if ENABLED(JARVIS_PALETTE) ... #else block in ' + path
    for slot, (name, _) in sorted(SLOTS.items()):
        m = re.search(r'^\s*#define\s+Def_%s_Color\s+(?:%s|JV_(\w+)\b)' % (name, rgb), branch.group(1), re.M)
        assert m, 'Def_%s_Color missing from the JARVIS_PALETTE branch' % name
        val = tuple(map(int, m.groups()[:3])) if m.group(1) else JV.get(m.group(4))
        assert val == PALETTE[slot], 'Def_%s_Color is %s, PALETTE[%d] is %s' % (name, val, slot, PALETTE[slot])


if __name__ == '__main__':
    write_theme(THEME)
    check_theme(THEME)
    print('theme OK: %s (C10, C11 E2..E20, C11 E0)' % os.path.relpath(THEME, ROOT))
    check_defines(DEFINES)
    print('defines OK: %s matches PALETTE and JV' % os.path.relpath(DEFINES, ROOT))
