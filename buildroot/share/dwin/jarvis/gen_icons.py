#!/usr/bin/env python3
"""Generate the JARVIS HUD icon pack and boot splash for ProUI on the Voxelab Aquila X2 (DWIN T5UIC1).

python3 -I buildroot/share/dwin/jarvis/gen_icons.py

Everything is drawn from code (no image or font files) and written to
  display assets/Aquila Display Firmware/Icon Packs/JARVIS/NNN-ICON_<Name>.jpg   one per id of
      jarvis_spec.ICONS, <Name> from DWIN_ICO._icon_names (stock ids) or JV_* (ids 100-131);
      first the stock ids, then the JARVIS ones (77, 100-131)
  display assets/Aquila Display Firmware/Firmware Sets/DWIN_SET (JARVIS)/9.ICO      by bin/makeIco.py
  display assets/Aquila Display Firmware/Firmware Sets/DWIN_SET (JARVIS)/0_start.jpg

Look: thin line art in the JV accents of jarvis_spec (cyan, teal, ice; amber for Stop, Error and HOT)
plus an art-only dim teal, on pure black. Each icon is drawn at 4x on two layers, `lit` (glows) and
`flat`, both reduced with LANCZOS; the glow is GaussianBlur(6) x 0.55 and GaussianBlur(2) x 0.9 of
`lit`, combined with ImageChops.lighter; then every channel below 10 becomes 0 and the areas the
firmware needs black (2-px margin, CAPTION_ROWS, DASH_KEEPOUT, SPLASH_KEEPOUT) are cleared. Text in
the art uses the stroke font FONT (polylines on a 4 x 6 grid).

JPEG: RGB, baseline, 4:4:4, optimize=True, no EXIF. Every budget class starts at quality 90; while
9.ICO would be over 215000 B the class with most bytes drops 2 points (not below 75). An icon is
raised above its class quality, 1 point at a time, while the JPEG noise lifts one of the areas that
must stay black above check_dwin_set.BLACK (12), measured with the validator's own code: in 20x20,
24x24 and 14x52 icons every 8x8 block holds border pixels, so most end up at q89-96. 0_start.jpg is
the 272x480 portrait design turned with transpose(ROTATE_90), from q90 down by 2 until <= 31744 B.
No clock and no randomness: two runs write the same bytes.
Check the result with check_dwin_set.py "<DWIN_SET (JARVIS)>" --profile jarvis.
"""
import io
import math
import os
import re
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
BIN = os.path.join(ROOT, 'buildroot', 'share', 'dwin', 'bin')
sys.path.insert(0, HERE)
sys.path.insert(0, BIN)
import DWIN_ICO  # noqa: E402  (stock icon names)
import check_dwin_set as chk  # noqa: E402  (its black-area measures pick the qualities)
import jarvis_spec as spec  # noqa: E402

ASSETS = os.path.join(ROOT, 'display assets', 'Aquila Display Firmware')
PACK = os.path.join(ASSETS, 'Icon Packs', 'JARVIS')
DWIN_SET = os.path.join(ASSETS, 'Firmware Sets', 'DWIN_SET (JARVIS)')
MAKEICO = os.path.join(BIN, 'makeIco.py')

ICO_TARGET, ICO_MAX, HEADER = 215000, 229376, 4096
Q_START, Q_MIN, Q_STEP = 90, 75, 2
START_FIT, START_QMIN = 31744, 60
SS = 4                                   # supersampling factor of the drawing


def rgb888(c):
    """RGB565 components (as in jarvis_spec) -> 8-bit RGB, the way the display widens them."""
    r, g, b = c
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))


CYAN, TEAL, ICE, AMBER = (rgb888(spec.JV[k]) for k in ('CYAN', 'TEAL', 'ICE', 'AMBER'))
DIM = (0x00, 0x3D, 0x42)                 # art only: tracks and idle lines (not a firmware color)
BLACK = (0, 0, 0)


def mix(c1, c2, k):
    """Color between c1 (k = 0) and c2 (k = 1)."""
    return tuple(int(a + (b - a) * k + 0.5) for a, b in zip(c1, c2))


AMBER_HI = mix(AMBER, (255, 255, 255), 0.55)
LUT_G6 = [int(v * 0.55 + 0.5) for v in range(256)] * 3
LUT_G2 = [int(v * 0.9 + 0.5) for v in range(256)] * 3
LUT_CLAMP = [0 if v < 10 else v for v in range(256)] * 3

# Stroke font: polylines on a grid 4 wide and 6 high (y down); advance 4 + tracking
_O = ((1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0))
_P = ((0, 6), (0, 0), (3, 0), (4, 1), (4, 2.2), (3, 3.2), (0, 3.2))
FONT = {
    ' ': (),
    'A': (((0, 6), (0, 1.2), (1.2, 0), (2.8, 0), (4, 1.2), (4, 6)), ((0, 3.6), (4, 3.6))),
    'B': (((0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)), ((0, 0), (3, 0), (4, 1), (4, 2), (3, 3))),
    'C': (((4, 0), (1, 0), (0, 1), (0, 5), (1, 6), (4, 6)),),
    'D': (((0, 0), (0, 6), (3, 6), (4, 5), (4, 1), (3, 0), (0, 0)),),
    'E': (((4, 0), (0, 0), (0, 6), (4, 6)), ((0, 3), (3, 3))),
    'F': (((4, 0), (0, 0), (0, 6)), ((0, 3), (3, 3))),
    'G': (((4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3.2), (2.2, 3.2)),),
    'H': (((0, 0), (0, 6)), ((4, 0), (4, 6)), ((0, 3), (4, 3))),
    'I': (((2, 0), (2, 6)), ((1, 0), (3, 0)), ((1, 6), (3, 6))),
    'J': (((4, 0), (4, 5), (3, 6), (1, 6), (0, 5)),),
    'K': (((0, 0), (0, 6)), ((4, 0), (0, 3.6)), ((1.5, 2.3), (4, 6))),
    'L': (((0, 0), (0, 6), (4, 6)),),
    'M': (((0, 6), (0, 0), (2, 3), (4, 0), (4, 6)),),
    'N': (((0, 6), (0, 0), (4, 6), (4, 0)),),
    'O': (_O,),
    'P': (_P,),
    'Q': (_O, ((2.4, 4.4), (4.2, 6.2))),
    'R': (_P, ((2.2, 3.2), (4, 6))),
    'S': (((4, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (0, 6)),),
    'T': (((0, 0), (4, 0)), ((2, 0), (2, 6))),
    'U': (((0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)),),
    'V': (((0, 0), (2, 6), (4, 0)),),
    'W': (((0, 0), (1, 6), (2, 2.5), (3, 6), (4, 0)),),
    'X': (((0, 0), (4, 6)), ((4, 0), (0, 6))),
    'Y': (((0, 0), (2, 3), (4, 0)), ((2, 3), (2, 6))),
    'Z': (((0, 0), (4, 0), (0, 6), (4, 6)),),
    '0': (_O, ((3, 1.8), (1, 4.2))),
    '1': (((1, 1), (2, 0), (2, 6)), ((1, 6), (3, 6))),
    '2': (((0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (0, 6), (4, 6)),),
    '3': (((0, 0), (4, 0), (1.5, 2.6), (3, 2.6), (4, 3.6), (4, 5), (3, 6), (1, 6), (0, 5)),),
    '4': (((3, 6), (3, 0), (0, 4), (4, 4)),),
    '5': (((4, 0), (0, 0), (0, 2.6), (3, 2.6), (4, 3.6), (4, 5), (3, 6), (0, 6)),),
    '6': (((4, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3.6), (3, 2.6), (0, 2.6)),),
    '7': (((0, 0), (4, 0), (1.5, 6)),),
    '8': (((1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (1, 3), (0, 4), (0, 5), (1, 6),
           (3, 6), (4, 5), (4, 4), (3, 3)),),
    '9': (((0, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0), (0, 1), (0, 2.4), (1, 3.4), (4, 3.4)),),
    '-': (((1, 3), (3, 3)),),
    '.': (((2, 5.6), (2, 6)),),
    '/': (((0.5, 6), (3.5, 0)),),
    ':': (((2, 1.6), (2, 2)), ((2, 4.6), (2, 5))),
    '>': (((1, 1), (3, 3), (1, 5)),),
    '<': (((3, 1), (1, 3), (3, 5)),),
}


def P(cx, cy, r, deg):
    """Point at radius r and angle deg (0 = right, 90 = down: clockwise on screen)."""
    t = math.radians(deg)
    return (cx + r * math.cos(t), cy + r * math.sin(t))


class Art:
    """One image drawn at SS x on two layers: `lit` (gets the glow) and `flat` (does not).
    Coordinates are image pixels as floats (pixel i spans i..i+1), shifted by the origin set with at()."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.layer = {lit: Image.new('RGB', (w * SS, h * SS)) for lit in (True, False)}
        self.pen = {lit: ImageDraw.Draw(im) for lit, im in self.layer.items()}
        self.ox = self.oy = 0.0

    def at(self, ox, oy):
        self.ox, self.oy = ox, oy
        return self

    def _p(self, x, y):
        return ((self.ox + x) * SS - 0.5, (self.oy + y) * SS - 0.5)

    def line(self, pts, w=1.4, c=CYAN, lit=True, closed=False):
        """Polyline with round joins and caps."""
        q = [self._p(x, y) for x, y in pts]
        if closed:
            q.append(q[0])
        width = max(1, int(round(w * SS)))
        pen = self.pen[lit]
        if len(q) > 1:
            pen.line(q, fill=c, width=width, joint='curve')
        r = width / 2.0
        for x, y in (q[0], q[-1]):
            pen.ellipse((x - r + 0.5, y - r + 0.5, x + r - 0.5, y + r - 0.5), fill=c)

    def arc(self, cx, cy, r, a0, a1, w=1.4, c=CYAN, lit=True):
        n = max(2, int(abs(a1 - a0) / 3) + 2)
        self.line([P(cx, cy, r, a0 + (a1 - a0) * k / (n - 1)) for k in range(n)], w, c, lit)

    def circle(self, cx, cy, r, w=1.4, c=CYAN, lit=True):
        self.arc(cx, cy, r, 0, 360, w, c, lit)

    def disc(self, cx, cy, r, c=CYAN, lit=True):
        x, y = self._p(cx, cy)
        r *= SS
        self.pen[lit].ellipse((x - r + 0.5, y - r + 0.5, x + r - 0.5, y + r - 0.5), fill=c)

    def fill(self, pts, c, lit=False):
        self.pen[lit].polygon([self._p(x, y) for x, y in pts], fill=c)

    def rect(self, x0, y0, x1, y1, c, lit=False):
        """Filled box covering pixels x0..x1-1, y0..y1-1 exactly."""
        x0, y0, x1, y1 = (int(round(v * SS)) for v in (self.ox + x0, self.oy + y0, self.ox + x1, self.oy + y1))
        self.pen[lit].rectangle((x0, y0, x1 - 1, y1 - 1), fill=c)

    def text(self, s, x, y, h, w=1.2, c=CYAN, lit=True, align='left', track=1.5):
        """Stroke-font text, cap height h, top at y; returns its width."""
        u = h / 6.0
        adv = (4 + track) * u
        width = len(s) * adv - track * u
        x0 = x - width / 2 if align == 'center' else x - width if align == 'right' else x
        for k, ch in enumerate(s):
            for poly in FONT[ch]:
                self.line([(x0 + k * adv + px * u, y + py * u) for px, py in poly], w, c, lit)
        return width

    def render(self, margin=(2, 2, 2, 2), black=()):
        """Reduce, add the glow, clamp to black below 10, clear margin (l, t, r, b) and boxes."""
        size = (self.w, self.h)
        lit = self.layer[True].resize(size, Image.Resampling.LANCZOS)
        flat = self.layer[False].resize(size, Image.Resampling.LANCZOS)
        glow = ImageChops.lighter(lit.filter(ImageFilter.GaussianBlur(6)).point(LUT_G6),
                                  lit.filter(ImageFilter.GaussianBlur(2)).point(LUT_G2))
        out = ImageChops.lighter(ImageChops.lighter(lit, flat), glow).point(LUT_CLAMP)
        pen = ImageDraw.Draw(out)
        w, h = size
        left, top, right, bottom = margin
        for box in ((0, 0, left - 1, h - 1), (0, 0, w - 1, top - 1),
                    (w - right, 0, w - 1, h - 1), (0, h - bottom, w - 1, h - 1)) + tuple(black):
            if box[2] >= box[0] and box[3] >= box[1]:
                pen.rectangle(box, fill=BLACK)
        return out


# ---------------------------------------------------------------- drawing helpers

def hexagon(cx, cy, r, flat=True):
    return [P(cx, cy, r, (0 if flat else 30) + 60 * k) for k in range(6)]


def arrowhead(a, tip, deg, size=2.6, w=1.4, c=CYAN, lit=True, spread=42):
    """Chevron at tip for a stroke travelling in direction deg."""
    a.line([P(tip[0], tip[1], size, deg + 180 - spread), tip, P(tip[0], tip[1], size, deg + 180 + spread)], w, c, lit)


def arrow(a, p0, p1, size=2.6, w=1.4, c=CYAN, lit=True):
    a.line([p0, p1], w, c, lit)
    arrowhead(a, p1, math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])), size, w, c, lit)


def arc_arrow(a, cx, cy, r, a0, a1, size=2.6, w=1.4, c=CYAN):
    a.arc(cx, cy, r, a0, a1, w, c)
    arrowhead(a, P(cx, cy, r, a1), a1 + (90 if a1 > a0 else -90), size, w, c)


def wave(a, p0, p1, amp, periods, w=1.1, c=TEAL, lit=True):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    n = max(8, int(math.hypot(dx, dy) * 2))
    nx, ny = -dy / math.hypot(dx, dy), dx / math.hypot(dx, dy)
    a.line([(x0 + dx * t + nx * amp * math.sin(2 * math.pi * periods * t),
             y0 + dy * t + ny * amp * math.sin(2 * math.pi * periods * t))
            for t in (k / n for k in range(n + 1))], w, c, lit)


def gear(cx, cy, n, r_in, r_out, phase=-90):
    pts, step = [], 360.0 / n
    for k in range(n):
        b = phase + k * step
        pts += [P(cx, cy, r_in, b - step * 0.31), P(cx, cy, r_out, b - step * 0.17),
                P(cx, cy, r_out, b + step * 0.17), P(cx, cy, r_in, b + step * 0.31)]
    return pts


def thermo(a, cx, top, length, tr, br, w=1.4, c=CYAN, level=0.6, core=ICE):
    """Thermometer: tube of half-width tr from y = top down to a bulb of radius br at y = top + length."""
    by = top + length
    j = math.degrees(math.acos(tr / br))
    pts = [P(cx, by, br, -j), (cx + tr, top)]
    pts += [P(cx, top, tr, -d) for d in range(0, 181, 15)]
    pts += [P(cx, by, br, 180 + j - d) for d in range(0, int(180 + 2 * j) + 1, 10)] + [P(cx, by, br, -j)]
    a.line(pts, w, c)
    a.line([(cx, top + (by - top) * (1 - level)), (cx, by)], w * 0.9, core)
    a.disc(cx, by, br * 0.5, core)


def stroke(a, pts, hi, w=1.8, c=CYAN, closed=False):
    """Main stroke of a button glyph; the selected variant (hi) gets a brighter core."""
    a.line(pts, w, c, closed=closed)
    if hi:
        a.line(pts, w * 0.45, AMBER_HI if c == AMBER else ICE, closed=closed)


def nozzle(a, cx, top, s, w, c, lit=True):
    """Heater block and nozzle, s = scale (1 = 8 px wide block)."""
    a.line([(cx - 4 * s, top), (cx + 4 * s, top), (cx + 4 * s, top + 5 * s), (cx - 4 * s, top + 5 * s)], w, c, lit, True)
    a.line([(cx - 2.6 * s, top + 5 * s), (cx - 0.7 * s, top + 9.2 * s), (cx + 0.7 * s, top + 9.2 * s),
            (cx + 2.6 * s, top + 5 * s)], w, c, lit)


# ---------------------------------------------------------------- 20x20 menu glyphs

GLYPHS = {}


def glyph(*ids):
    def reg(f):
        for i in ids:
            GLYPHS[i] = f
        return f
    return reg


@glyph(9, 46)
def g_nozzle(a, i):
    nozzle(a, 10, 3.5, 1.0, 1.4, CYAN)
    if i == 46:                                          # hot: heat waves at the sides
        for x in (3.6, 16.4):
            wave(a, (x, 4), (x, 13.5), 0.9, 1.5, 1.1, TEAL)
    a.line([(4, 16.5), (16, 16.5)], 1.1, DIM, lit=False)


@glyph(10, 47)
def g_bed(a, i):
    a.line([(3, 11), (17, 11), (17, 14), (3, 14)], 1.4, CYAN, closed=True)
    for x in (5.5, 14.5):
        a.line([(x, 14), (x, 16.5)], 1.2, TEAL)
    if i == 10:                                          # hot bed
        for x in (6, 10, 14):
            wave(a, (x, 3.2), (x, 8.8), 0.9, 1.25, 1.1, TEAL)


@glyph(11, 75)
def g_speed(a, i):
    a.arc(10, 11, 7, 150, 390, 1.4, CYAN)
    for d in (180, 270, 360):
        a.line([P(10, 11, 4.6, d), P(10, 11, 5.6, d)], 1.0, DIM, lit=False)
    a.line([(10, 11), P(10, 11, 5.4, 315 if i == 11 else 240)], 1.4, ICE)
    a.disc(10, 11, 1.4, CYAN)


@glyph(12, 76)
def g_zoffset(a, i):
    a.text('Z', 3.4, 4.5, 8, 1.3, CYAN)
    a.line([(14.2, 3.5), (14.2, 16.5)], 1.3, CYAN)
    arrowhead(a, (14.2, 3.5), -90, 2.4, 1.3)
    arrowhead(a, (14.2, 16.5), 90, 2.4, 1.3)
    if i == 12:
        a.line([(3, 16.2), (10, 16.2)], 1.1, TEAL)
    else:                                                # with the mesh active
        wave(a, (3, 16), (10.5, 16), 0.8, 1.5, 1.1, TEAL)


@glyph(13)
def g_back(a, i):
    a.line([(16, 15.5), (16, 10.5), (13, 7.5), (4.5, 7.5)], 1.5, CYAN)
    a.line([(8, 4), (4.5, 7.5), (8, 11)], 1.5, CYAN)


@glyph(14)
def g_file(a, i):
    a.line([(5, 3), (11.5, 3), (15, 6.5), (15, 17), (5, 17)], 1.3, CYAN, closed=True)
    a.line([(11.5, 3), (11.5, 6.5), (15, 6.5)], 1.0, TEAL)
    for y, x1 in ((10, 12.5), (12.6, 12.5), (15, 10.5)):
        a.line([(7.6, y), (x1, y)], 1.0, TEAL)


@glyph(26)
def g_more(a, i):
    a.line([(7.5, 4.5), (12.8, 10), (7.5, 15.5)], 1.7, CYAN)


@glyph(27, 249)
def g_axes(a, i):
    a.line([(10, 3.5), (10, 16.5)], 1.3)
    a.line([(3.5, 10), (16.5, 10)], 1.3)
    for tip, d in (((10, 3.5), -90), ((10, 16.5), 90), ((3.5, 10), 180), ((16.5, 10), 0)):
        arrowhead(a, tip, d, 2.3, 1.3)
    a.disc(10, 10, 1.2, ICE)


@glyph(28)
def g_motor(a, i):
    a.line([(4, 6), (12.5, 6), (12.5, 15), (4, 15)], 1.3, CYAN, closed=True)
    a.circle(8.25, 10.5, 2.2, 1.0, TEAL)
    a.line([(12.5, 10.5), (16.5, 10.5)], 1.6, CYAN)
    a.line([(3.2, 17), (16.8, 3.4)], 1.1, ICE)            # disabled


@glyph(29)
def g_home(a, i):
    a.line([(3.4, 10), (10, 3.6), (16.6, 10)], 1.4, CYAN)
    a.line([(5.6, 8.2), (5.6, 16.5), (14.4, 16.5), (14.4, 8.2)], 1.3, CYAN)
    a.line([(8.6, 16.5), (8.6, 12.4), (11.4, 12.4), (11.4, 16.5)], 1.0, TEAL)


@glyph(30)
def g_target(a, i):
    a.circle(10, 10, 5, 1.3, CYAN)
    for d in (0, 90, 180, 270):
        a.line([P(10, 10, 6.4, d), P(10, 10, 7.8, d)], 1.3, TEAL)
    a.disc(10, 10, 1.4, ICE)


@glyph(31, 32, 49, 50)
def g_preheat(a, i):
    a.text('PLA' if i in (31, 49) else 'ABS', 10, 4, 6, 1.2, CYAN, align='center', track=1)
    if i in (31, 32):
        a.line([(3.5, 14.5), (16.5, 14.5)], 1.1, TEAL)
    else:
        wave(a, (3.5, 14.5), (16.5, 14.5), 1.0, 2, 1.1, TEAL)


@glyph(33)
def g_snow(a, i):
    for d in (90, 30, 150):
        a.line([P(10, 10, 7, d), P(10, 10, 7, d + 180)], 1.2, CYAN)
    for d in range(30, 390, 60):
        a.line([P(10, 10, 4.6, d - 24), P(10, 10, 6.6, d), P(10, 10, 4.6, d + 24)], 1.0, TEAL)


@glyph(34)
def g_globe(a, i):
    a.circle(10, 10, 7, 1.3, CYAN)
    a.line([(10 + 3 * math.cos(math.radians(d)), 10 + 7 * math.sin(math.radians(d))) for d in range(0, 361, 10)],
           1.0, TEAL)
    a.line([(3, 10), (17, 10)], 1.0, TEAL)
    for y in (6.2, 13.8):
        hw = math.sqrt(49 - (y - 10) ** 2) - 0.6
        a.line([(10 - hw, y), (10 + hw, y)], 0.9, DIM, lit=False)


@glyph(35, 36, 37, 38)
def g_move(a, i):
    a.text('XYZE'[i - 35], 3, 6.5, 7, 1.3, CYAN)
    p0, p1 = {35: ((10.5, 10), (16.6, 10)), 36: ((10.6, 15.2), (16.2, 5)),
              37: ((13.6, 16.6), (13.6, 3.4)), 38: ((13.6, 3.4), (13.6, 16.6))}[i]
    arrow(a, p0, p1, 2.6, 1.3, ICE)


@glyph(40)
def g_temperature(a, i):
    thermo(a, 9, 4.2, 10.2, 1.6, 2.9, 1.3, CYAN, 0.65)
    for y in (5.5, 8.2, 10.9):
        a.line([(13, y), (15.6, y)], 1.0, TEAL)


@glyph(41)
def g_bolt(a, i):
    pts = [(11.8, 2.8), (5.8, 11.2), (9.6, 11.2), (8.2, 17.2), (14.2, 8.8), (10.4, 8.8)]
    a.fill(pts, mix(BLACK, CYAN, 0.22))
    a.line(pts, 1.2, CYAN, closed=True)


@glyph(42, 43)
def g_memory(a, i):
    a.line([(6, 10.5), (14, 10.5), (14, 16.6), (6, 16.6)], 1.3, CYAN, closed=True)   # memory chip
    for y in (12.4, 14.8):
        a.line([(3.6, y), (6, y)], 1.0, TEAL)
        a.line([(14, y), (16.4, y)], 1.0, TEAL)
    if i == 42:                                          # write: into the chip
        arrow(a, (10, 2.8), (10, 8.6), 2.4, 1.4, ICE)
    else:                                                # read: out of it
        arrow(a, (10, 8.6), (10, 2.8), 2.4, 1.4, ICE)


@glyph(44)
def g_reset(a, i):
    arc_arrow(a, 10, 10.5, 6, -55, 245, 2.6, 1.4, CYAN)


@glyph(45)
def g_info(a, i):
    a.disc(10, 4.6, 1.5, ICE)
    a.line([(8.4, 8.2), (10, 8.2), (10, 16.2)], 1.6, CYAN)
    a.line([(7.8, 16.4), (12.2, 16.4)], 1.4, CYAN)


@glyph(48)
def g_fan(a, i):
    a.circle(10, 10, 7.4, 1.0, TEAL)
    for k in range(3):
        t = -90 + 120 * k
        blade = [P(10, 10, 1.8, t - 28), P(10, 10, 6.0, t - 8), P(10, 10, 5.4, t + 30), P(10, 10, 2.4, t + 40)]
        a.fill(blade, mix(BLACK, CYAN, 0.25))
        a.line(blade, 1.1, CYAN, closed=True)
    a.disc(10, 10, 1.5, ICE)


def letter_gauge(a, letter, style):
    cx, cy, r = 9.6, 10.6, 6.8                           # right edge at x 17: the dashboard clips from 17
    if style == 'jerk':                                  # dashed dial
        for k in range(7):
            a.arc(cx, cy, r, 135 + 40 * k, 135 + 40 * k + 22, 1.3, TEAL)
    elif style == 'acc':                                 # dial with an arrow at its end
        arc_arrow(a, cx, cy, r, 135, 400, 2.3, 1.3, TEAL)
    else:
        a.arc(cx, cy, r, 135, 405, 1.3, TEAL)
    a.text(letter, cx, cy - 3.2, 6.4, 1.25, CYAN, align='center')


@glyph(51, 52, 53, *range(59, 71))
def g_letter_gauge(a, i):
    if i in (51, 52, 53):
        letter_gauge(a, 'SAJ'[i - 51], ('speed', 'acc', 'jerk')[i - 51])
    else:
        letter_gauge(a, 'XYZE'[(i - 59) % 4], ('speed', 'acc', 'jerk')[(i - 59) // 4])


@glyph(54, 71, 72, 73)
def g_gear_letter(a, i):
    a.line(gear(10, 10, 6, 6.0, 8.2), 1.2, TEAL, closed=True)
    if i == 54:
        a.circle(10, 10, 2.4, 1.3, CYAN)
    else:
        a.text('XYZ'[i - 71], 10, 7.2, 5.6, 1.2, CYAN, align='center')


@glyph(74)
def g_flow(a, i):
    cx, cy, r = 10, 12.2, 4.6
    pts = [(10, 3)] + [P(cx, cy, r, d) for d in range(-30, 211, 10)] + [(10, 3)]
    a.line(pts, 1.4, CYAN)
    a.arc(cx, cy, 2.5, 100, 170, 1.1, ICE)


@glyph(55)
def g_size(a, i):
    for x, y, dx, dy in ((4, 4, 1, 1), (16, 4, -1, 1), (16, 16, -1, -1), (4, 16, 1, -1)):
        a.line([(x, y + 4 * dy), (x, y), (x + 4 * dx, y)], 1.4, CYAN)
    a.line([(7.6, 7.6), (12.4, 7.6), (12.4, 12.4), (7.6, 12.4)], 1.0, TEAL, closed=True)


@glyph(56)
def g_version(a, i):
    a.line(hexagon(10, 10, 7.6, flat=False), 1.2, TEAL, closed=True)
    a.text('V', 10, 7, 6, 1.3, CYAN, align='center')


@glyph(57)
def g_contact(a, i):
    a.line([(3.5, 4), (16.5, 4), (16.5, 12.6), (9.6, 12.6), (6, 16.2), (6, 12.6), (3.5, 12.6)], 1.3, CYAN, closed=True)
    a.line([(6.4, 7.2), (13.6, 7.2)], 1.0, TEAL)
    a.line([(6.4, 9.6), (11.4, 9.6)], 1.0, TEAL)


@glyph(58)
def g_defaults(a, i):
    a.line([(4, 11.5), (4, 16.5), (16, 16.5), (16, 11.5)], 1.3, CYAN)
    arrow(a, (10, 3.2), (10, 13.2), 3.0, 1.4, ICE)


@glyph(200, 201)
def g_box(a, i):
    a.line([(4.5, 4.5), (15.5, 4.5), (15.5, 15.5), (4.5, 15.5)], 1.4, CYAN, closed=True)
    if i == 201:
        a.line([(6.8, 10.4), (9.2, 12.8), (13.6, 7.2)], 1.6, ICE)


@glyph(202)
def g_fade(a, i):
    wave(a, (3, 14.5), (17, 14.5), 1.0, 2, 1.3, CYAN)
    a.line([(5, 10), (15, 10)], 1.1, TEAL)
    a.line([(7, 6), (13, 6)], 1.0, DIM, lit=False)


@glyph(203)
def g_mesh(a, i):
    A, B, C, D = (2.8, 16), (6.2, 5), (13.8, 5), (17.2, 16)

    def lerp(p, q, t):
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    for t in (1 / 3, 2 / 3):
        a.line([lerp(A, D, t), lerp(B, C, t)], 1.0, TEAL)
    for s in (0.42, 0.75):
        a.line([lerp(A, B, s), lerp(D, C, s)], 1.0, TEAL)
    a.line([A, B, C, D], 1.3, CYAN, closed=True)


@glyph(204)
def g_tilt(a, i):
    a.line([(3, 15.5), (17, 15.5)], 1.0, DIM, lit=False)
    a.line([(3, 15.5), (17, 9.5)], 1.4, CYAN)
    a.arc(3, 15.5, 7, -23, 0, 1.0, TEAL)
    arrow(a, (12, 3), (12, 9.2), 2.2, 1.2, ICE)


@glyph(205)
def g_sun(a, i):
    a.circle(10, 10, 3.3, 1.4, CYAN)
    for d in range(0, 360, 45):
        a.line([P(10, 10, 5.4, d), P(10, 10, 7.3, d)], 1.2, TEAL)


@glyph(206)
def g_probe(a, i):
    a.line([(7, 3), (13, 3), (13, 10), (7, 10)], 1.3, CYAN, closed=True)
    a.line([(8.4, 10), (10, 12.6), (11.6, 10)], 1.2, CYAN)
    a.line([(10, 12.6), (10, 16.6)], 1.3, ICE)


@glyph(250, 251, 252, 253, 254)
def g_corner(a, i):
    a.line([(3.5, 3.5), (16.5, 3.5), (16.5, 16.5), (3.5, 16.5)], 1.0, TEAL, closed=True)
    x, y = {250: (12.6, 12.6), 251: (12.6, 7.4), 252: (7.4, 12.6), 253: (7.4, 7.4), 254: (10, 10)}[i]
    a.circle(x, y, 2.3, 1.2, CYAN)
    a.disc(x, y, 0.9, ICE)


def menu_glyph(i):
    a = Art(20, 20)
    GLYPHS[i](a, i)
    return a.render()


# ---------------------------------------------------------------- buttons and popups

def g_print(a, cx, cy, hi):
    top, ur, lr, bot, ll, ul, c = ((cx, cy - 14), (cx + 12.1, cy - 7), (cx + 12.1, cy + 7), (cx, cy + 14),
                                   (cx - 12.1, cy + 7), (cx - 12.1, cy - 7), (cx, cy))
    for k in (1, 2):                                     # layer lines on the front faces
        dy = 14 * k / 3
        a.line([(ul[0], ul[1] + dy), (c[0], c[1] + dy), (ur[0], ur[1] + dy)], 1.0, TEAL)
    stroke(a, [ul, c, ur], hi, 1.4)
    stroke(a, [c, bot], hi, 1.4)
    stroke(a, [top, ur, lr, bot, ll, ul], hi, 1.8, closed=True)


def g_prepare(a, cx, cy, hi):
    for y, kx in ((cy - 9, cx - 5), (cy, cx + 6), (cy + 9, cx - 1)):
        a.line([(cx - 14, y), (kx - 3.6, y)], 1.3, TEAL)
        a.line([(kx + 3.6, y), (cx + 14, y)], 1.3, TEAL)
        stroke(a, [(kx - 2.2, y - 3), (kx + 2.2, y - 3), (kx + 2.2, y + 3), (kx - 2.2, y + 3)], hi, 1.6, closed=True)


def g_control(a, cx, cy, hi):
    stroke(a, gear(cx, cy, 8, 10.6, 14.2), hi, 1.6, closed=True)
    stroke(a, [P(cx, cy, 4.6, d) for d in range(0, 361, 10)], hi, 1.6)


def g_level(a, cx, cy, hi):
    L, F, R, B = (cx - 15, cy + 8), (cx, cy + 14.5), (cx + 15, cy + 8), (cx, cy + 1.5)

    def lerp(p, q, t):
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    for t in (1 / 3, 2 / 3):
        a.line([lerp(L, B, t), lerp(F, R, t)], 1.0, TEAL)
        a.line([lerp(L, F, t), lerp(B, R, t)], 1.0, TEAL)
    stroke(a, [L, F, R, B], hi, 1.6, closed=True)
    nozzle(a, cx, cy - 15, 1.0, 1.6, CYAN)
    if hi:
        nozzle(a, cx, cy - 15, 1.0, 0.7, ICE)
    for y in (cy - 4.6, cy - 2.2, cy + 0.2):
        a.line([(cx, y), (cx, y + 1.0)], 1.2, TEAL)
    a.disc(cx, cy + 8, 1.6, ICE)


def g_info_ring(a, cx, cy, hi):
    stroke(a, [P(cx, cy, 13, d) for d in range(0, 361, 6)], hi, 1.6)
    a.disc(cx, cy - 6.4, 1.9, ICE)
    stroke(a, [(cx - 2.2, cy - 2), (cx, cy - 2), (cx, cy + 7)], hi, 2.2)
    stroke(a, [(cx - 3.2, cy + 7.4), (cx + 3.2, cy + 7.4)], hi, 1.8)


def g_printer(a, cx, cy, hi):
    stroke(a, [(cx - 11, cy + 12), (cx - 11, cy - 13), (cx + 11, cy - 13), (cx + 11, cy + 12)], hi, 1.6)
    a.line([(cx - 14, cy - 3.5), (cx + 14, cy - 3.5)], 1.2, TEAL)              # X gantry
    stroke(a, [(cx - 3, cy - 7), (cx + 3, cy - 7), (cx + 3, cy - 1), (cx - 3, cy - 1)], hi, 1.4, closed=True)
    a.line([(cx - 1.2, cy - 1), (cx, cy + 1.2), (cx + 1.2, cy - 1)], 1.2, ICE)
    a.line([(cx - 3, cy + 4), (cx + 3, cy + 4), (cx + 3, cy + 7.6), (cx - 3, cy + 7.6)], 1.0, TEAL, closed=True)
    stroke(a, [(cx - 9, cy + 7.6), (cx + 9, cy + 7.6)], hi, 1.6)                 # bed
    a.line([(cx - 15, cy + 12), (cx + 15, cy + 12)], 1.8, CYAN)                 # base


def g_tune(a, cx, cy, hi):
    stroke(a, [P(cx, cy, 10.5, d) for d in range(0, 361, 6)], hi, 1.6)
    for d in range(135, 406, 45):
        a.line([P(cx, cy, 13, d), P(cx, cy, 15, d)], 1.2, TEAL)
    stroke(a, [(cx, cy), P(cx, cy, 7.6, -60)], hi, 1.8)
    a.disc(cx, cy, 1.8, ICE)


def g_pause(a, cx, cy, hi):
    for x0 in (cx - 7.5, cx + 2.5):
        box = [(x0, cy - 10), (x0 + 5, cy - 10), (x0 + 5, cy + 10), (x0, cy + 10)]
        a.fill(box, mix(BLACK, CYAN, 0.24 if hi else 0.14))
        stroke(a, box, hi, 1.6, closed=True)


def g_resume(a, cx, cy, hi):
    tri = [(cx - 7, cy - 11), (cx + 11, cy), (cx - 7, cy + 11)]
    a.fill(tri, mix(BLACK, CYAN, 0.24 if hi else 0.14))
    stroke(a, tri, hi, 1.6, closed=True)


def g_stop(a, cx, cy, hi):
    box = [(cx - 9, cy - 9), (cx + 9, cy - 9), (cx + 9, cy + 9), (cx - 9, cy + 9)]
    a.fill(box, mix(BLACK, AMBER, 0.26 if hi else 0.16))
    stroke(a, box, hi, 1.8, AMBER, closed=True)


def corner_brackets(a, x0, y0, x1, y1, hi, c, size=7):
    for x, y, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x1, y1, -1, -1), (x0, y1, 1, -1)):
        if hi:
            a.fill([(x, y), (x + dx * size, y), (x, y + dy * size)], c, lit=True)
        else:
            a.line([(x, y + dy * size), (x, y), (x + dx * size, y)], 1.2, c)


# JPEG codes 8x8 blocks: a bright stroke in a block that also holds pixels of the 1-px border (or of
# CAPTION_ROWS / DASH_KEEPOUT / SPLASH_KEEPOUT) rings them by 6-30 at q85-95. The bigger icons
# therefore keep their strokes in the blocks that hold none of those pixels, about 4 px in from the
# outer blocks (brackets at 13), so that the glow reaching the outer blocks is under 10 and clamped to 0.
# Icons too small for that (20x20, 24x24, 14x52, the bar) are raised to the JPEG quality that keeps
# their border black instead, when needed (encode()).


def button(w, draw_glyph, hi, accent=CYAN):
    """110x100 / 80x100 button: glyph in a hexagon on rows 12-58; CAPTION_ROWS stay black."""
    a = Art(w, 100)
    cx, cy, r = w / 2.0, 35, 26.5
    if hi:
        a.fill(hexagon(cx, cy, r - 0.6), mix(BLACK, TEAL, 0.11))
    a.line(hexagon(cx, cy, r - 3.6), 1.0, DIM, lit=False, closed=True)
    a.line(hexagon(cx, cy, r), 1.3, CYAN if hi else TEAL, closed=True)
    if w > 100:                                           # ticks off the side vertices (no room at 80)
        for sx in (-1, 1):
            d = 90 - sx * 90
            a.line([P(cx, cy, r + 2.4, d - 13), P(cx, cy, r + 4.2, d), P(cx, cy, r + 2.4, d + 13)], 1.2,
                   ICE if hi else CYAN)
    corner_brackets(a, 13, 13, w - 13, 57, hi, accent, 6)
    draw_glyph(a, cx, cy, hi)
    r0, r1 = spec.CAPTION_ROWS
    return a.render(black=[(0, r0, w - 1, r1)])


def alert(draw_glyph, amber=False):
    """73x66 popup icon: glyph in a hexagon."""
    a = Art(73, 66)
    cx, cy, r = 36.5, 34, 24
    frame = AMBER if amber else TEAL
    a.line(hexagon(cx, cy, r - 3.2), 1.0, mix(BLACK, frame, 0.33), lit=False, closed=True)
    a.line(hexagon(cx, cy, r), 1.4, frame, closed=True)
    corner_brackets(a, 13, 13, 60, 54, False, AMBER if amber else CYAN, 5)
    draw_glyph(a, cx, cy)
    return a.render()


def p_bltouch(a, cx, cy):
    a.line([(cx - 4.5, cy - 15), (cx + 4.5, cy - 15), (cx + 4.5, cy - 4), (cx - 4.5, cy - 4)], 1.6, CYAN, closed=True)
    a.line([(cx - 6.5, cy - 15), (cx + 6.5, cy - 15)], 1.6, CYAN)
    a.line([(cx - 3, cy - 4), (cx, cy), (cx + 3, cy - 4)], 1.4, CYAN)
    a.line([(cx, cy), (cx, cy + 7)], 1.6, ICE)
    a.line([(cx - 13, cy + 10), (cx + 13, cy + 10)], 1.4, TEAL)
    a.disc(cx, cy + 10, 1.8, ICE)


def p_too_low(a, cx, cy):
    thermo(a, cx - 5, cy - 13, 19, 2.6, 4.6, 1.6, CYAN, 0.25)
    arrow(a, (cx + 8, cy - 11), (cx + 8, cy + 9), 3.6, 1.7, ICE)


def p_autolevel(a, cx, cy):
    g_level(a, cx, cy + 1, False)


def p_too_high(a, cx, cy):
    thermo(a, cx - 5, cy - 13, 19, 2.6, 4.6, 1.6, AMBER, 0.9, AMBER_HI)
    a.line([(cx + 8, cy - 12), (cx + 8, cy + 3)], 2.4, AMBER)
    a.disc(cx + 8, cy + 8.6, 1.7, AMBER_HI)


# ---------------------------------------------------------------- other stock ids

def logo():
    """130x26 "AQUILA X2" with a tick ruler, on rows 8-23."""
    a = Art(130, 26)
    a.text('AQUILA X2', 65, 9, 11, 1.5, CYAN, align='center', track=1.6)
    a.line([(16, 22.5), (114, 22.5)], 1.0, TEAL)
    for x in range(16, 115, 7):
        a.line([(x, 21.6 if (x - 16) % 49 == 0 else 22.5), (x, 23.4)], 1.0, TEAL)
    for x, dx in ((9.5, 1), (120.5, -1)):
        a.line([(x + 4 * dx, 9), (x, 9), (x, 23), (x + 4 * dx, 23)], 1.2, CYAN)
    return a.render()


def clock(i):
    a = Art(24, 24)
    if i == 15:                                          # elapsed: clock
        a.circle(12, 12, 8.6, 1.4, CYAN)
        for d in (0, 90, 180, 270):
            a.line([P(12, 12, 6.2, d), P(12, 12, 7.2, d)], 1.0, TEAL)
        a.line([(12, 7), (12, 12), (15.6, 12)], 1.4, ICE)
    else:                                                # remaining: hourglass
        for y in (4.4, 19.6):
            a.line([(6.6, y), (17.4, y)], 1.5, CYAN)
        a.line([(8.2, 4.4), (8.2, 6.4), (12, 12), (8.2, 17.6), (8.2, 19.6)], 1.3, CYAN)
        a.line([(15.8, 4.4), (15.8, 6.4), (12, 12), (15.8, 17.6), (15.8, 19.6)], 1.3, CYAN)
        a.fill([(9.6, 19), (14.4, 19), (12, 15.6)], TEAL, lit=True)
        a.line([(10.4, 8), (13.6, 8)], 1.0, TEAL)
    return a.render()


def progress_bar():
    """30 segments of 6 px with 2-px gaps from x 2, on rows 8-15; the firmware covers the rest."""
    a = Art(242, 20)
    for k in range(30):
        x0 = 2 + 8 * k
        a.rect(x0, 8, x0 + 6, 16, CYAN)
        a.rect(x0 + 2, 10, x0 + 4, 14, CYAN, lit=True)    # glow source: core of the segment
    return a.render()


def menu_cursor():
    """14x52 menu cursor: 2-px bar and chevron (JARVIS_CURSOR draws it at x 0 of the row)."""
    a = Art(14, 52)
    a.line([(3, 4.5), (3, 47.5)], 2.0, CYAN)
    a.line([(6.6, 20), (10.6, 26), (6.6, 32)], 1.6, ICE)
    for y in (8, 44):
        a.line([(5.6, y), (8, y)], 1.0, TEAL)
    return a.render()


# ---------------------------------------------------------------- JARVIS ids

def spinner(f):
    """Frame f (0-7): outer arcs (symmetry 3) +15 deg/frame and inner arcs (symmetry 4) -11.25 deg/frame
    over a static tick ring; frame 8 would equal frame 0."""
    a = Art(80, 80)
    c = 40
    for k in range(48):
        major = k % 6 == 0
        a.line([P(c, c, 27.8 if major else 28.8, k * 7.5), P(c, c, 30.6, k * 7.5)],
               1.2 if major else 1.0, TEAL if major else DIM, lit=major)
    a.circle(c, c, 19.6, 1.0, DIM, lit=False)
    for k in range(3):
        s = -90 + 15 * f + 120 * k
        a.arc(c, c, 24.2, s, s + 70, 2.8, CYAN)
        a.arc(c, c, 24.2, s + 58, s + 70, 2.8, ICE)      # bright leading edge
    for k in range(4):
        s = -11.25 * f + 90 * k
        a.arc(c, c, 15.4, s, s + 48, 1.8, TEAL)
        a.arc(c, c, 15.4, s, s + 8, 1.8, CYAN)
    a.line(hexagon(c, c, 6.4), 1.2, TEAL, closed=True)
    a.disc(c, c, 1.6, ICE)
    return a.render()


def gauge(bed, level):
    """24x24 gauge: dim 270-degree track, cyan arc of level/8, nozzle or bed glyph; level 9 = HOT."""
    a = Art(24, 24)
    c, r = 12, 8.2
    if level == 9:
        a.circle(c, c, r, 2.0, AMBER)
        col = AMBER
    else:
        a.arc(c, c, r, 135, 405, 2.0, DIM, lit=False)
        if level:
            a.arc(c, c, r, 135, 135 + 270 * level / 8.0, 2.0, CYAN)
        col = CYAN if level else TEAL
    if bed:                                              # plate on legs
        a.line([(7.4, 10.6), (16.6, 10.6), (16.6, 12.8), (7.4, 12.8)], 1.1, col, closed=True)
        for x in (9, 15):
            a.line([(x, 12.8), (x, 15.6)], 1.1, col)
    else:
        nozzle(a, 12, 7.4, 0.72, 1.1, col)
    return a.render()


def title():
    """272x30 title bar: dark band x 20-251 y 3-25 for the caption (drawn on top), brackets, teal rule
    on rows 27-29 (its last row is the icon's bottom row: the title bar ends there)."""
    a = Art(272, 30)
    band = [(25, 3), (246, 3), (251, 8), (251, 20), (246, 25), (25, 25), (20, 20), (20, 8)]
    a.fill(band, (0, 16, 19))
    for x, dx in ((9.5, 1), (262.5, -1)):
        a.line([(x + 5 * dx, 9), (x, 9), (x, 22), (x + 5 * dx, 22)], 1.3, CYAN)
        for k in range(2):
            xc = 136 - dx * (109 - 3.6 * k)
            a.line([(xc - 1.6 * dx, 12), (xc + 1.6 * dx, 15.5), (xc - 1.6 * dx, 19)], 1.1, TEAL)
    a.line([(9, 28.5), (263, 28.5)], 1.0, TEAL)
    a.line([(96, 28.5), (176, 28.5)], 1.4, CYAN)
    return a.render(margin=(2, 2, 2, 0))


def dash():
    """272x105 dashboard frame at screen y 375: rails, corner brackets and the rules on rows 74-75 and
    103-104 (screen 449-450 and 478-479), nothing else (ruling R13: no baked icons); DASH_KEEPOUT
    (values, gauges and the icons the firmware still draws) stays black."""
    a = Art(272, 105)
    a.line([(30, 34.5), (263, 34.5)], 1.0, DIM, lit=False)              # rail between the value rows
    for x in range(48, 241, 48):
        a.line([(x, 33.4), (x, 35.6)], 1.0, TEAL)
    a.line([(255.5, 9), (262.5, 9), (262.5, 28)], 1.2, CYAN)            # top-right bracket and rail
    for x in (89.5, 174.5):                                               # rails between X, Y and Z
        a.line([(x, 82), (x, 97)], 1.0, DIM, lit=False)
    a.line([(9, 75), (263, 75)], 2.0, TEAL)
    a.line([(9, 104), (263, 104), (263, 99.5)], 2.0, TEAL)              # bottom rule, bottom-right corner
    # Nothing at x < 8: those 8x8 JPEG blocks also hold the border and the gauge keep-outs (x 4-27), and
    # the X icon (x 10-29, rows 79-98) is too close to the bottom rule's left end for a corner there.
    return a.render(margin=(2, 2, 2, 0), black=spec.DASH_KEEPOUT)


def splash(frame0):
    """0_start.jpg: 272x480 portrait design (art only on rows 0-215 and 344-479, clear of the JPEG blocks
    of SPLASH_KEEPOUT), frame 0 of the spinner pasted in SPLASH_SPINNER, turned with transpose(ROTATE_90)."""
    a = Art(272, 480)
    sx0, sy0, sx1, sy1 = spec.SPLASH_SPINNER
    cx, cy = (sx0 + sx1 + 1) / 2.0, (sy0 + sy1 + 1) / 2.0
    grid = (0, 22, 26)
    for y0, y1 in ((0, 216), (344, 480)):
        for x in range(8, 272, 24):
            a.rect(x, y0, x + 1, y1, grid)
        for y in range(y0 + 10, y1, 24):
            a.rect(0, y, 272, y + 1, grid)
    a.disc(cx, cy, 72, BLACK, lit=False)                                    # round hole for the rings
    a.circle(cx, cy, 59, 1.2, TEAL)
    a.circle(cx, cy, 64.5, 1.0, DIM, lit=False)
    for k in range(72):
        major = k % 6 == 0
        a.line([P(cx, cy, 59, k * 5), P(cx, cy, 64.5 if major else 62.5, k * 5)], 1.0, TEAL if major else DIM,
               lit=major)
    for k in range(3):
        s = -60 + 120 * k
        a.arc(cx, cy, 69, s, s + 40, 2.0, CYAN)
    a.text('SYSTEM BOOT', 136, 26, 9, 1.3, CYAN, align='center', track=1.8)
    a.line([(40, 43.5), (232, 43.5)], 1.0, TEAL)
    for x in range(40, 233, 8):
        a.line([(x, 43.5), (x, 46 if (x - 40) % 32 == 0 else 45)], 1.0, TEAL)
    a.text('INITIALIZING', 136, 205, 7, 1.1, TEAL, align='center', track=1.8)
    a.line([(30, 360.5), (242, 360.5)], 1.0, TEAL)
    for x in range(30, 243, 8):
        a.line([(x, 360.5), (x, 363 if (x - 30) % 32 == 0 else 362)], 1.0, TEAL)
    a.text('HUD ONLINE', 136, 440, 8, 1.2, CYAN, align='center', track=1.8)
    for x, dx in ((6.5, 1), (265.5, -1)):
        for y, dy in ((6.5, 1), (473.5, -1)):
            a.line([(x, y + 14 * dy), (x, y), (x + 14 * dx, y)], 1.4, CYAN)
    im = a.render(margin=(0, 0, 0, 0), black=spec.SPLASH_KEEPOUT)
    im.paste(frame0, (sx0, sy0))
    return im.transpose(Image.Transpose.ROTATE_90)


# ---------------------------------------------------------------- pack, budget, files

def build():
    """id -> (budget class, RGB image) for every id of jarvis_spec.ICONS."""
    art = {0: ('logo 130x26', logo()), 15: ('24x24', clock(15)), 16: ('24x24', clock(16)),
           25: ('bar 242x20', progress_bar()), 77: ('cursor 14x52', menu_cursor())}
    big = {1: g_print, 3: g_prepare, 5: g_control, 7: g_level, 90: g_info_ring, 93: g_printer}
    for i, f in big.items():
        art[i] = ('button 110x100', button(110, f, False))
        if i != 93:
            art[i + 1] = ('button 110x100', button(110, f, True))
    for i, f in {17: g_tune, 19: g_pause, 21: g_resume, 23: g_stop}.items():
        accent = AMBER if i == 23 else CYAN
        art[i] = ('button 80x100', button(80, f, False, accent))
        art[i + 1] = ('button 80x100', button(80, f, True, accent))
    for i, f in {78: p_bltouch, 79: p_too_low, 80: p_autolevel, 81: p_too_high}.items():
        art[i] = ('popup 73x66', alert(f, i == 81))
    for i in GLYPHS:
        art[i] = ('glyph 20x20', menu_glyph(i))
    for f in range(8):
        art[100 + f] = ('spinner 80x80', spinner(f))
    for g in range(10):
        art[110 + g] = ('24x24', gauge(False, g))
        art[120 + g] = ('24x24', gauge(True, g))
    art[130] = ('title 272x30', title())
    art[131] = ('dash 272x105', dash())
    assert sorted(art) == sorted(spec.ICONS), set(art) ^ set(spec.ICONS)
    for i, (_, im) in art.items():
        assert im.size == spec.ICONS[i][:2], (i, im.size)
    return art


def jpeg(im, q):
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=q, subsampling=0, optimize=True, progressive=False)
    return buf.getvalue()


def decode(data):
    return Image.open(io.BytesIO(data)).convert('RGB')


def encode(i, im, q):
    """(quality, JPEG) of icon i: quality q, raised 1 by 1 while the JPEG noise lifts an area that must
    stay black (border, caption rows, keep-outs) above check_dwin_set.BLACK, the validator's own measure."""
    while True:
        data = jpeg(im, q)
        if not chk.black_problems(i, decode(data)):
            return q, data
        if q >= 100:
            sys.exit('icon %d: black areas fail even at q100' % i)
        q += 1


def fit(art):
    """Quality per budget class, starting at Q_START; while 9.ICO is over ICO_TARGET the class with most
    bytes drops Q_STEP (not below Q_MIN). Icons whose black areas need more stay at their own floor
    (see encode); a class that no longer shrinks is left alone."""
    ids = {}
    for i in sorted(art):
        ids.setdefault(art[i][0], []).append(i)
    quality = {cls: Q_START for cls in ids}
    enc = {i: encode(i, art[i][1], Q_START) for i in sorted(art)}
    pinned = set()

    def weight(cls):
        return sum(len(enc[i][1]) for i in ids[cls])
    while HEADER + sum(len(d) for _, d in enc.values()) > ICO_TARGET:
        cands = {cls: weight(cls) for cls in sorted(ids) if cls not in pinned and quality[cls] > Q_MIN}
        if not cands:
            break
        cls = max(cands, key=lambda k: cands[k])
        q = max(Q_MIN, quality[cls] - Q_STEP)
        new = {i: encode(i, art[i][1], q) for i in ids[cls]}
        if sum(len(d) for _, d in new.values()) >= cands[cls]:
            pinned.add(cls)                               # its icons sit at their floors already
            continue
        quality[cls] = q
        enc.update(new)
    return ids, quality, enc


def icon_name(i):
    if i in DWIN_ICO._icon_names:
        return DWIN_ICO._icon_names[i]
    if 100 <= i <= 107:
        return 'JV_Spin%d' % (i - 100)
    if 110 <= i <= 129:
        return 'JV_%sG%d' % ('Hot' if i < 120 else 'Bed', i % 10)      # level 9 = HOT
    return {130: 'JV_Title', 131: 'JV_Dash'}[i]


def write(path, data):
    with open(path, 'wb') as f:
        f.write(data)


def main():
    art = build()
    ids, quality, enc = fit(art)
    blobs = {i: d for i, (_, d) in enc.items()}
    os.makedirs(PACK, exist_ok=True)
    os.makedirs(DWIN_SET, exist_ok=True)
    for name in sorted(os.listdir(PACK)):                 # drop the previous run's files
        if re.match(r'^\d{3}-.*\.jpg$', name):
            os.remove(os.path.join(PACK, name))
    jarvis_ids = [77] + [i for i in sorted(art) if 100 <= i <= 131]
    stock_ids = [i for i in sorted(art) if i not in jarvis_ids]
    for i in stock_ids + jarvis_ids:                      # stock ids first, then the JARVIS ones
        write(os.path.join(PACK, '%03d-ICON_%s.jpg' % (i, icon_name(i))), blobs[i])
    left = sorted(set(os.listdir(PACK)) - {'%03d-ICON_%s.jpg' % (i, icon_name(i)) for i in art})
    assert not left, 'unexpected files in %s: %s' % (PACK, left)

    ico = os.path.join(DWIN_SET, '9.ICO')
    if os.path.exists(ico):                               # makeIco.py does not overwrite
        os.remove(ico)
    res = subprocess.run([sys.executable, '-E', '-s', MAKEICO, PACK, ico], capture_output=True, text=True)
    log = res.stdout + res.stderr
    expect = HEADER + sum(map(len, blobs.values()))
    if res.returncode or 'Error' in log or 'Whoops' in log or not os.path.isfile(ico) \
            or os.path.getsize(ico) != expect:
        sys.exit('makeIco.py failed (expected %d B):\n%s' % (expect, log))

    land = splash(art[100][1])
    q = Q_START
    data = jpeg(land, q)
    while len(data) > START_FIT:
        q -= Q_STEP
        if q < START_QMIN:
            sys.exit('0_start.jpg does not fit %d B even at q%d' % (START_FIT, START_QMIN))
        data = jpeg(land, q)
    portrait = decode(data).transpose(Image.Transpose.ROTATE_270)
    dirty = [(box, chk.box_max(portrait, box)) for box in spec.SPLASH_KEEPOUT
             if chk.box_max(portrait, box) > chk.BLACK]
    if dirty:
        sys.exit('0_start.jpg: keep-out areas not black at q%d: %s' % (q, dirty))
    write(os.path.join(DWIN_SET, '0_start.jpg'), data)
    left = sorted(set(os.listdir(DWIN_SET)) - {'9.ICO', '0_start.jpg'})
    assert not left, 'unexpected files in %s: %s' % (DWIN_SET, left)

    print('icons: %d files in %s' % (len(blobs), os.path.relpath(PACK, ROOT)))
    for cls in sorted(ids):
        up = sorted(enc[i][0] for i in ids[cls] if enc[i][0] > quality[cls])
        print('  %-15s q%-3d %3d icons %7d B%s' % (
            cls, quality[cls], len(ids[cls]), sum(len(blobs[i]) for i in ids[cls]),
            '  (%d raised to q%d-%d to keep black areas black)' % (len(up), up[0], up[-1]) if up else ''))
    size = os.path.getsize(ico)
    print('9.ICO: %d B (target %d, cap %d)%s' % (size, ICO_TARGET, ICO_MAX, '' if size <= ICO_TARGET else '  OVER TARGET'))
    print('0_start.jpg: %d B at q%d (fit %d, cap 32768)' % (len(data), q, START_FIT))
    if size > ICO_MAX:
        sys.exit('9.ICO over the %d B cap' % ICO_MAX)
    return 0


if __name__ == '__main__':
    sys.exit(main())
