#!/usr/bin/env python3
"""Mockups of the JARVIS HUD skin for ProUI on the Voxelab Aquila X2 (DWIN T5UIC1, 272x480 portrait).

python3 -I buildroot/share/dwin/jarvis/mockup.py

Writes mockups/<name>.png and mockups/<name>@2x.png (nearest neighbour); every screen is 272x480:
  boot        0_start.jpg as the display shows it at power-on, HMI_Init's machine name and full boot
              bar, and the JARVIS_BOOT texts and spinner frame 0: both boot phases in one picture (with
              JARVIS_BOOT_JPG, DWIN_InitScreen() shows the splash again, which wipes the bar)
  boot_black  the JARVIS_BOOT phase with JARVIS_BOOT_JPG off, the X2-JARVIS default (black screen)
  main        main menu with Print selected, toolbar, status line and dashboard
  print       printing at 63 % with Pause selected
  menu        Prepare, cursor on row 1
  popup       the Pause confirmation over the print screen, Cancel chosen (as Goto_Popup leaves it)
  alert       the File menu without SD card (AlertBg box)
  main_stock  the main screen with Icon Packs/Original Icons, the stock palette (ALT_COLOR_MENU 0, as
              configurations/.../MM) and no JARVIS_* switch: the "before"
  contact     every id of jarvis_spec.ICONS on Background and on PopupBg (a sheet, not a screen)
The screens follow the firmware's drawing order (dwin.cpp, menus.cpp, dwinui.*, dwin_popup.*,
toolbar.cpp, ToolBarClass::draw() of the closed libproui.a, and the Tasks 7-8 plan for the JARVIS_*
code), with the coordinates of jarvis_spec.LAYOUT.

Emulation: text uses the display's own glyphs from 0T5UIC1.HZK; a string drawn with bShow = false
paints only the set bits, Draw_Int / Draw_Float / the Draw_String overloads with a background color
also paint each character cell. Draw_Icon (IBD = 0, BFI = 1) drops the pixels whose channels are all
<= check_dwin_set.BLACK (12; the display's own threshold is unknown) and Draw_IconWB pastes the decoded
JPEG as is. RGB565 colors are widened with gen_icons.rgb888. Asserts: every icon drawn is in
jarvis_spec.ICONS with that size and its JPEG is in the pack; every screen is 272x480; mockups/ ends
with exactly the files written. Standard library and Pillow. `python3 -I` does not put this folder
on sys.path, so it is added here.
"""
import os
import sys

from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_dwin_set as chk  # noqa: E402  (BLACK)
import gen_icons as gen  # noqa: E402  (rgb888, icon_name, asset paths, JV colors in 8 bit)
import jarvis_spec as spec  # noqa: E402

OUT = os.path.join(HERE, 'mockups')
ORIGINAL = os.path.join(gen.ASSETS, 'Icon Packs', 'Original Icons')
SPLASH = os.path.join(gen.DWIN_SET, '0_start.jpg')
HZK = os.path.join(gen.ASSETS, 'DWIN Font (Original)', '0T5UIC1.HZK')
L = spec.LAYOUT
W, H = L['screen']
F6, F8, F10, F12 = (L['font'][k] for k in ('mesh', 'menu', 'head', 'boot'))  # font6x12 .. font12x24

# 0T5UIC1.HZK: per size, 128 glyphs (index = ASCII code) of ceil(w / 8) * h bytes, 1 bit per pixel,
# rows MSB first; byte offset of each size block (the blocks follow each other)
HZK_BLOCKS = {(6, 12): 0, (8, 16): 1536, (10, 20): 3584, (12, 24): 8704}

# Stock colors for main_stock.png by C11 slot, as RGB565 words: DWIN_SetColorDefaults() for
# ALT_COLOR_MENU 0 (dwin.cpp:2111-2132) over the #else branch of dwin_defines.h and dwin_color.h
STOCK_565 = {2: 0x0841, 3: 0xFFFF, 4: 0xA804, 5: 0xFFFF, 6: 0xFFFF, 7: 0x8430, 8: 0xFFFF, 9: 0xFFFF,
             10: 0x0841, 11: 0xFF0F, 12: 0x31E8, 13: 0xD6BA, 14: 0xA804, 15: 0xFF0F, 16: 0xFFFF,
             17: 0x10E4, 18: 0xFFFF, 19: 0xFFFF, 20: 0xA804}

# Ids the firmware draws with Draw_IconWB (opaque): ICON_Button's 110x100 and 80x100 buttons, the
# print screen's bar, and the JARVIS cursor, spinner, gauges, title and dashboard frame (Tasks 7-8).
# The rest go through Draw_Icon; so do a popup's icon (dwin_popup.h:56) and HMI_Init's boot bar.
OPAQUE = set(range(1, 9)) | {90, 91, 93} | set(range(17, 26)) | {77} | set(range(100, 108)) | set(range(110, 132))

# What the screens show: X2-JARVIS strings as the firmware prints them, and a plausible machine state
MACHINE = 'Aquila X2 JARVIS'                    # CUSTOM_MACHINE_NAME
READY = MACHINE + ' Ready'                      # WELCOME_MSG (language_en.h:77)
BOOT_LINE = 'v2.1.3h-7  Oct 18 2026  ClassicRocker883'  # Task 7: "v%s  %s  ClassicRocker883"
FILE = 'benchy_0.2mm_PLA.gcode'                 # card.longest_filename(): print header and status
PCT, ELAPSED, REMAIN = 63, '02:05', '01:13'     # duration_t::toDigital() prints mm'ss under 1 h
DASH = {'hotend': (117, 210), 'bed': (60, 60), 'speed': 100, 'fan': 255, 'flow': 100, 'zoffset': -0.2,
        'xyz': (110.0, 110.0, 5.0),
        'gauges': (4, 8)}                       # jv_gauge_level(117, 210), (60, 60) of the Task 8 plan
TOOLBAR = (29, 31, 32, 33, 28)                  # home, preheat 1, preheat 2, cooldown, steppers off
MAIN_CAPTIONS = {'print': 'Print', 'prepare': 'Prepare', 'control': 'Control', 'level': 'Level'}
PRINT_CAPTIONS = {'tune': 'Tune', 'pause': 'Pause', 'stop': 'Stop'}
PREPARE = ((13, 'Back', False),                 # Draw_Prepare_Menu (dwin.cpp:3322-3351), first page:
           (254, 'Move Axis', True),            # (icon, label, "More" chevron of onDrawSubMenu)
           (29, 'Homing', True),                # INDIVIDUAL_AXIS_HOMING_SUBMENU is on
           (28, 'Disable Steppers', False),
           (31, 'Preheat PLA', False),
           (32, 'Preheat PETG', False))


def split565(v):
    """RGB565 word -> (R 0-31, G 0-63, B 0-31), the form of jarvis_spec.PALETTE."""
    return (v >> 11, v >> 5 & 63, v & 31)


def load_fonts(path):
    """{(w, h): [128 glyph masks, mode 1]} from the HZK file."""
    with open(path, 'rb') as f:
        data = f.read()
    fonts, end = {}, 0
    for (w, h), off in sorted(HZK_BLOCKS.items(), key=lambda kv: kv[1]):
        assert off == end, 'HZK block %dx%d at %d, expected %d' % (w, h, off, end)
        n = (w + 7) // 8 * h
        fonts[(w, h)] = [Image.frombytes('1', ((w + 7) // 8 * 8, h), data[off + n * c:off + n * c + n])
                         .crop((0, 0, w, h)) for c in range(128)]
        end = off + 128 * n
    return fonts


FONTS = load_fonts(HZK)


class Theme:
    """An icon pack, a C11 palette and whether the JARVIS_* drawing switches are on."""

    def __init__(self, pack, palette, jarvis):
        assert sorted(palette) == sorted(spec.SLOTS), 'palette needs slots 2..20'
        self.pack, self.jarvis, self.cache = pack, jarvis, {}
        self.c = {spec.SLOTS[slot][0]: gen.rgb888(rgb) for slot, rgb in palette.items()}

    def icon(self, i):
        """(image, Draw_Icon mask) of icon i."""
        if i not in self.cache:
            assert i in spec.ICONS, 'icon %d is not in jarvis_spec.ICONS' % i
            path = os.path.join(self.pack, '%03d-ICON_%s.jpg' % (i, gen.icon_name(i)))
            assert os.path.isfile(path), 'missing ' + path
            with Image.open(path) as f:
                im = f.convert('RGB')
            assert im.size == spec.ICONS[i][:2], '%s is %dx%d' % ((path,) + im.size)
            r, g, b = im.split()
            mask = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > chk.BLACK else 0)
            self.cache[i] = (im, mask)
        return self.cache[i]


class Screen:
    """A frame buffer with the DWIN calls ProUI makes; boxes are (x1, y1, x2, y2), inclusive."""

    def __init__(self, theme, size=(W, H), bg=(0, 0, 0)):
        self.t, self.c, self.icons = theme, theme.c, set()
        self.im = Image.new('RGB', size, bg)
        self.d = ImageDraw.Draw(self.im)

    def rect(self, mode, color, x1, y1, x2, y2):    # DWIN_Draw_Rectangle: mode 0 frame, 1 fill
        self.d.rectangle((x1, y1, x2, y2), fill=color if mode else None, outline=None if mode else color)

    def box(self, mode, color, x, y, w, h):         # DWIN_Draw_Box
        self.rect(mode, color, x, y, x + w - 1, y + h - 1)

    def hline(self, color, x, y, n):                # DWIN_Draw_HLine
        self.d.line((x, y, x + n - 1, y), fill=color)

    def degree(self, color, x, y):                  # DWIN_Draw_DegreeSymbol (dwin_api.cpp:264-273)
        for dx, dy in ((1, 0), (2, 0), (0, 1), (3, 1), (0, 2), (3, 2), (1, 3), (2, 3)):
            self.im.putpixel((x + dx, y + dy), color)

    def icon(self, i, x, y, wb=False):              # Draw_Icon, or Draw_IconWB when wb
        im, mask = self.t.icon(i)
        assert x >= 0 and y >= 0 and x + im.width <= self.im.width and y + im.height <= self.im.height, \
            'icon %d at (%d, %d) leaves the image' % (i, x, y)
        self.im.paste(im, (x, y), None if wb else mask)
        self.icons.add(i)

    def text(self, font, color, x, y, s, bg=None):  # DWIN_Draw_String; bg: bShow with that color
        w, h = font
        assert s.isascii() and x >= 0 and x + w * len(s) <= self.im.width, 'text %r at x %d' % (s, x)
        if bg is not None:
            self.box(1, bg, x, y, w * len(s), h)
        for k, ch in enumerate(s):
            self.im.paste(color, (x + w * k, y), FONTS[font][ord(ch)])

    def centered(self, font, color, y, s, x1=0, x2=W):  # Draw_CenteredString (dwinui.cpp:124-127)
        self.text(font, color, (x1 + x2 - len(s) * font[0]) // 2 - 1, y, s)


def title(s, caption):                              # Draw_Title (menus.cpp:39-46)
    T = L['title']
    if s.t.jarvis:
        s.icon(130, *T['jv_icon'], wb=True)         # JARVIS_TITLE: ICON_JV_Title instead of the box
    else:
        s.rect(1, s.c['TitleBg'], *T['box'])
    s.centered(F10, s.c['TitleTxt'], T['text_y'], caption)


def clear_main(s):                                  # DWINUI::ClearMainArea (dwinui.cpp:288-290)
    s.rect(1, s.c['Background'], *L['main_area'])


def status(s, text):                                # DWIN_DrawStatusLine (dwin.cpp:439-442)
    S = L['status']
    assert len(text) <= S['chars'], text
    s.rect(1, s.c['StatusBg'], *S['box'])
    s.centered(F8, s.c['StatusTxt'], S['text_y'], text)


def dashboard(s):
    """DWIN_Draw_Dashboard (dwin.cpp:1095-1141) with Task 8's JARVIS_DASH_FRAME and JARVIS_GAUGES; the
    stock temperature icons are the ones update_variable keeps while heating (dwin.cpp:827-855)."""
    D, c, jv = L['dashboard'], s.c, s.t.jarvis
    ind, bg = c['Indicator'], c['Background']
    if jv:
        s.icon(131, *D['jv_frame'], wb=True)        # ICON_JV_Dash, rules included (replaces 1096-1097, 1104)
    else:
        s.rect(1, bg, *D['box'])
        for ya, yb in D['rules_y']:
            s.rect(1, c['Bottom'], 0, ya, W, yb)
    for k in range(3):                              # ICON_MaxSpeedX/Y/Z, Draw_Signed_Float(3, 2)
        s.icon(59 + k, *D['xyz_icons'][k])
        s.text(F8, c['Coordinate'], *D['xyz_values'][k], '%7.2f' % DASH['xyz'][k], bg)
    for row, (cur, tgt) in enumerate((DASH['hotend'], DASH['bed'])):
        y = D['value_y'][row]
        if jv:                                      # ICON_JV_HotG0 / ICON_JV_BedG0 + level
            s.icon((110, 120)[row] + DASH['gauges'][row], *D['jv_gauges'][row], wb=True)
        else:                                       # ICON_SetEndTemp (heating), ICON_BedTemp (hot)
            s.icon((46, 10)[row], *(D['hotend_icon'], D['bed_icon'])[row])
        s.text(F10, ind, D['temp_x'], y, '%3d' % cur, bg)
        s.text(F10, ind, D['slash_x'], y, '/', bg)
        s.text(F10, ind, D['target_x'], y, '%3d' % tgt, bg)
        s.degree(ind, D['degree_x'], y)
    for row, (i, xy, value) in enumerate(((11, D['speed_icon'], DASH['speed']), (74, D['flow_icon'], DASH['flow']))):
        s.icon(i, *xy)
        s.text(F10, ind, D['pct_value_x'], D['value_y'][row], '%3d' % value, bg)
        s.text(F10, ind, D['pct_x'], D['value_y'][row], '%', bg)
    s.icon(48, *D['fan_icon'])
    s.text(F10, ind, D['fan_x'], D['value_y'][0], '%3d' % DASH['fan'], bg)
    s.icon(12, *D['zoffset_icon'])                  # ICON_Zoffset (leveling off)
    s.text(F10, ind, *D['zoffset'], '%6.2f' % DASH['zoffset'], bg)  # Draw_Signed_Float(2, 2)


def icon_button(s, sel, icon, xy, size, caption):
    """ICON_Button (dwin.cpp:334-343): icon (+1 when selected) opaque; selected: two Cursor frames at
    the icon's outer 2 px (ReduceFrame(ico, 1)); caption centered at y + h - 20 - 8."""
    (x, y), (w, h) = xy, size
    s.icon(icon + sel, x, y, wb=True)
    if sel:
        s.box(0, s.c['Cursor'], x, y, w, h)
        s.box(0, s.c['Cursor'], x + 1, y + 1, w - 2, h - 2)
    s.text(F8, s.c['Text'], x + (w - len(caption) * F8[0]) // 2, y + h - 20 - F8[1] // 2, caption)


def toolbar(s, icons):
    """ToolBarClass::draw() (libproui.a: DWIN_Draw_Box(1, 0x0841, 0, 321, 272, 28), then the items) and
    onDrawTBItem unfocused (toolbar.cpp:39-48)."""
    T = L['toolbar']
    assert len(icons) * T['dx'] + 2 * T['x0'] == W, 'x0 is for 5 items'
    s.box(1, gen.rgb888(split565(T['band_565'])), 0, T['y'], W, T['h'])
    for k, i in enumerate(icons):
        s.icon(i, T['x0'] + T['dx'] * k, T['item_y'])


def mypos(line):                                    # MYPOS(L)
    return L['menu']['mypos0'] + L['menu']['mline'] * line


def menu_line(s, line, icon, label, more):          # onDrawMenuItem / onDrawSubMenu (menus.cpp:93-104)
    M, y = L['menu'], mypos(line)
    s.icon(icon, M['icon_x'], y + M['icon_dy'])
    s.text(F8, s.c['Text'], M['label_x'], y + M['label_dy'], label)
    s.hline(s.c['SplitLine'], M['split_x'], mypos(line + 1), M['split_w'])
    if more:
        s.icon(M['more_icon'], M['more_x'], y + M['icon_dy'])


def menu_cursor(s, line):                           # Draw_Menu_Cursor (menus.cpp:48-51)
    M = L['menu']
    if s.t.jarvis:                                  # JARVIS_CURSOR: ICON_Rectangle opaque
        s.icon(M['jv_cursor_icon'], M['cursor_x'], mypos(line), wb=True)
    else:
        s.box(1, s.c['Cursor'], M['cursor_x'], mypos(line), *M['cursor_size'])


def button(s, caption, x, y):                       # DWINUI::Draw_Button(caption, x, y) (dwinui.cpp:220-223)
    w, h = L['popup']['button_size']
    s.box(1, s.c['TitleBg'], x, y, w, h)
    s.centered(F8, s.c['Text'], (2 * y + h - 1 - F8[1]) // 2, caption, x, x + w - 1)


def select_highlight(s, sel):                       # Draw_Select_Highlight (dwin_popup.cpp:32-41)
    w, h = L['popup']['button_size']
    for k, (x, y) in enumerate(L['popup']['buttons']):
        color = s.c['Cursor'] if (k == 0) == sel else s.c['PopupBg']
        for d in (1, 2):
            s.rect(0, color, x - d, y - d, x + w - 1 + d, y + h - 1 + d)


def boot(t, jpg=True):
    """JARVIS_BOOT (Task 7). jpg: over the splash, with HMI_Init's name and full bar (dwin.cpp:1345-1352,
    name in JV_CYAN); else DWIN_InitScreen() starts with DWIN_Frame_Clear(Color_Black). Then the name 12x24 cyan,
    "MRiscoC ProUI-EX" 8x16 ice, the version line 6x12 teal and spinner frame 0 (Draw_IconWB)."""
    s, B = Screen(t), L['boot']
    if jpg:
        with Image.open(SPLASH) as f:                # stored landscape, turned with ROTATE_90
            splash = f.convert('RGB').transpose(Image.Transpose.ROTATE_270)
        assert splash.size == (W, H), 'splash is %dx%d' % splash.size
        s.im.paste(splash)
        s.icon(25, *B['bar'])                       # ICON_Bar after its 23 steps, Draw_Icon
    assert B['name_y'] == B['jv_text_y'][0]         # HMI_Init and DWIN_InitScreen() put the name at the same place
    for font, color, y, text in zip((F12, F8, F6), (gen.CYAN, gen.ICE, gen.TEAL), B['jv_text_y'],
                                    (MACHINE, 'MRiscoC ProUI-EX', BOOT_LINE)):
        s.centered(font, color, y, text)
    s.icon(100, *B['jv_spinner'], wb=True)          # ICON_JV_Spin0
    return s


def main_menu(t):
    s, M = Screen(t), L['main_menu']
    status(s, READY)                                # DWIN_InitScreen: status line, dashboard, then
    dashboard(s)                                    # Draw_Main_Menu (dwin.cpp:675-686)
    clear_main(s)
    title(s, MACHINE)
    s.icon(M['logo_icon'], *M['logo'])
    for key in ('print', 'prepare', 'control', 'level'):
        icon_button(s, key == 'print', M['button_icons'][key], M['buttons'][key], M['button_size'],
                    MAIN_CAPTIONS[key])
    toolbar(s, TOOLBAR)
    return s


def printing(t):
    s, P = Screen(t), L['print']
    status(s, FILE)                                 # cardreader.cpp:856 sets the file name as status
    dashboard(s)
    title(s, 'Printing...')                         # Draw_PrintProcess (dwin.cpp:592-613)
    clear_main(s)
    fy = P['filename_y']                            # DWIN_Print_Header (dwin.cpp:586-589)
    s.rect(1, s.c['Background'], 0, fy, W, fy + F8[1])
    s.centered(F8, s.c['Text'], fy, FILE)
    for xy, label in zip(P['time_labels'], ('Print Time', 'Remaining')):  # MSG_INFO_PRINT_TIME (wide)
        s.text(F8, s.c['Text'], *xy, label)
    for xy, i in zip(P['time_icons'], (15, 16)):
        s.icon(i, *xy)
    (bx, by), (bw, _) = P['bar'], P['bar_size']    # Draw_Print_ProgressBar (dwin.cpp:526-530)
    s.icon(P['bar_icon'], bx, by, wb=True)
    s.rect(1, s.c['Barfill'], bx + PCT * bw // 100, by, *P['barfill_end'])
    s.text(F8, s.c['PercentTxt'], *P['percent'], '%3d%%' % PCT, s.c['Background'])  # DWINUI::fontid 8x16
    for xy, value in zip(P['time_values'], (ELAPSED, REMAIN)):
        s.text(F8, s.c['Text'], *xy, value, s.c['Background'])
    for key in ('tune', 'pause', 'stop'):
        icon_button(s, key == 'pause', P['button_icons'][key], P['buttons'][key], P['button_size'],
                    PRINT_CAPTIONS[key])
    return s


def prepare(t):
    s = Screen(t)
    status(s, READY)                                # ui.reset_status(true) (dwin.cpp:3349)
    dashboard(s)
    title(s, 'Prepare')                             # MenuClass::draw (menus.cpp)
    clear_main(s)
    for line, row in enumerate(PREPARE):
        menu_line(s, line, *row)
    menu_cursor(s, 1)
    return s


def popup(t):
    s, P = printing(t), L['popup']                  # Popup_window_PauseOrStop from the print screen
    clear_main(s)                                   # DWIN_Draw_Popup (dwin_popup.h:46-60)
    s.rect(1, s.c['PopupBg'], *P['box'])
    s.rect(0, s.c['Highlight'], *P['box'])
    s.icon(20, *P['icon_80x100'])                   # ICON_Pause_1 with Draw_Icon
    for y, msg in zip(P['text_y'], ('Please confirm', 'Pause Print')):  # Popup_ConfirmCancel
        s.centered(F8, s.c['PopupTxt'], y, msg)
    for (x, y), caption in zip(P['buttons'], ('Confirm', 'Cancel')):
        button(s, caption, x, y)
    select_highlight(s, False)                      # Goto_Popup clears select_flag: Cancel
    return s


def alert(t):
    s, A = Screen(t), L['alert']
    status(s, READY)
    dashboard(s)
    title(s, 'Select from SD Card')                 # Draw_Print_File_Menu without media (dwin.cpp:1070-1076)
    clear_main(s)
    menu_line(s, 0, *PREPARE[0])                    # BACK_ITEM
    menu_cursor(s, 0)
    s.rect(1, s.c['AlertBg'], *A['box'])
    s.centered(F12, s.c['AlertTxt'], A['text_y'], 'SD Card Not Inserted')
    return s


def contact(t):
    """Every id of ICONS by size, on Background and again on PopupBg. On Background the OPAQUE ids are
    drawn with Draw_IconWB (id in amber), the others with Draw_Icon (id in ice); on PopupBg every id goes
    through Draw_Icon, as a popup draws its icon (dwin_popup.h:56): nothing is opaque there."""
    pw, gap, top = 560, 6, 36
    pos, x, y, row = {}, gap, top, 0
    for i in sorted(spec.ICONS, key=lambda i: (-spec.ICONS[i][1], -spec.ICONS[i][0], i)):
        w, h = spec.ICONS[i][:2]
        cw = max(w, 3 * F6[0])
        if x + cw > pw - gap:
            x, y, row = gap, y + row + F6[1] + 1 + gap, 0
        pos[i], x, row = (x, y), x + cw + gap, max(row, h)
    sheet = Image.new('RGB', (2 * pw, y + row + F6[1] + 1 + gap))
    legend = ('id in amber: Draw_IconWB (opaque); in ice: Draw_Icon (all channels <= %d dropped)',
              'every id with Draw_Icon (all channels <= %d dropped), as popups draw (dwin_popup.h:56)')
    for k, slot in enumerate(('Background', 'PopupBg')):
        s = Screen(t, (pw, sheet.height), t.c[slot])
        s.text(F8, gen.ICE, gap, 4, 'on %s %s' % (slot, t.c[slot]))
        s.text(F6, gen.ICE, gap, 22, legend[k] % chk.BLACK)
        for i, (x, y) in pos.items():
            wb = k == 0 and i in OPAQUE
            s.icon(i, x, y, wb=wb)
            s.text(F6, gen.AMBER if wb else gen.ICE, x, y + spec.ICONS[i][1] + 1, str(i))
        sheet.paste(s.im, (k * pw, 0))
    return sheet


def save(name, im, written):
    for suffix, img in (('', im), ('@2x', im.resize((2 * im.width, 2 * im.height), Image.Resampling.NEAREST))):
        img.save(os.path.join(OUT, name + suffix + '.png'), optimize=True)
        written.append(name + suffix + '.png')


def main():
    assert OPAQUE <= set(spec.ICONS), sorted(OPAQUE - set(spec.ICONS))
    jarvis = Theme(gen.PACK, spec.PALETTE, True)
    stock = Theme(ORIGINAL, {slot: split565(v) for slot, v in STOCK_565.items()}, False)
    screens = (('boot', boot(jarvis)), ('boot_black', boot(jarvis, jpg=False)), ('main', main_menu(jarvis)),
               ('print', printing(jarvis)), ('menu', prepare(jarvis)), ('popup', popup(jarvis)),
               ('alert', alert(jarvis)), ('main_stock', main_menu(stock)))
    for name, s in screens:
        assert s.im.size == (W, H), '%s is %dx%d' % ((name,) + s.im.size)
    sheet = contact(jarvis)
    os.makedirs(OUT, exist_ok=True)                 # all drawn and checked: only now drop the old pictures
    for name in os.listdir(OUT):
        if name.endswith('.png'):
            os.remove(os.path.join(OUT, name))
    written = []
    for name, s in screens:
        save(name, s.im, written)
        print('%-10s %dx%d  icons %s' % (name, W, H, ' '.join(map(str, sorted(s.icons)))))
    save('contact', sheet, written)
    print('%-10s %dx%d  icons: all %d ids of jarvis_spec.ICONS, twice' % ('contact', sheet.width, sheet.height,
                                                                         len(spec.ICONS)))
    left = sorted(set(os.listdir(OUT)) - set(written))
    assert not left, 'unexpected files in %s: %s' % (OUT, left)
    print('mockups OK: %d PNGs in %s (each also @2x)' % (len(written), os.path.relpath(OUT, gen.ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
