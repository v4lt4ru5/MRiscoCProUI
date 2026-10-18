#!/usr/bin/env python3
"""Check a DWIN_SET folder for the Voxelab Aquila X2 display (DWIN T5UIC1) and ProUI.

usage: python3 -I buildroot/share/dwin/jarvis/check_dwin_set.py <folder> --profile stock|jarvis
       python3 -I buildroot/share/dwin/jarvis/check_dwin_set.py --selftest

Profile stock, what any set needs:
  - 9.ICO <= 229376 B (7 banks of 32 KiB; warning above 215000 B), 0_start.jpg optional
  - ICO header: 256 entries of 16 B, big-endian (W, H, offset, 3-byte length, 5 zero bytes); every
    entry is empty or valid, offsets start at 4096 and run contiguous up to EOF in id order
  - every blob starts with FFD8, ends with FFD9, is not progressive and decodes in Pillow with the
    W x H of its entry
  - the ids of DWIN_SET (Original) but 27, 85, 87 and 89 are present, with the sizes of
    jarvis_spec.ICONS
  - 0_start.jpg, when present: a non-progressive JPEG, 480x272, <= 32768 B (one bank)
  - the 1-px border of every icon is black (max channel <= BLACK = 12; both profiles skip the bottom
    row of 130 and 131, see below); only a WARNING in this profile (ruling R12), because the Original
    art sits on a slate background (the 1-px border of 99 of its 100 icons is above 6)
  - other files in the folder (1_English.jpg, *.CFG, *.BIN, ...) are only listed (ruling R12)
Profile jarvis, DWIN_SET (JARVIS) as gen_icons.py makes it, adds:
  - the folder holds exactly 9.ICO and 0_start.jpg (no .BIN/.CFG/.HZK: those stay from the user's
    set); this folder rule is jarvis-only (ruling R12)
  - ids 77, 100-107 and 110-131 too; every id is in jarvis_spec.ICONS with its size
  - every JPEG is baseline (SOF0), 3 components 4:4:4, without APP1 (EXIF)
  - black (max channel <= BLACK = 12, ruling R11): the 1-px border of every icon, rows CAPTION_ROWS
    of the 110x100 and 80x100 buttons, DASH_KEEPOUT in icon 131 and SPLASH_KEEPOUT in 0_start.jpg.
    The bottom row of 130 and 131 is skipped in both profiles (ruling R12): it carries the title
    rule (rows 27-29) and the dashboard's bottom rule (rows 103-104 = screen 478-479)

--selftest runs the stock profile on DWIN_SET (Original), which must pass, and on two broken copies
(9.ICO truncated; a 33 KiB 0_start.jpg), which must fail; the jarvis profile must reject the Original.
Exit status 0 when every check passes.
Standard library and Pillow. `python3 -I` does not put this folder on sys.path, so it is added here.
"""
import argparse
import io
import os
import struct
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, HERE)
import jarvis_spec as spec  # noqa: E402

SETS = os.path.join(ROOT, 'display assets', 'Aquila Display Firmware', 'Firmware Sets')
ORIGINAL = os.path.join(SETS, 'DWIN_SET (Original)')

ICO_NAME, START_NAME = '9.ICO', '0_start.jpg'
ICO_MAX, ICO_TARGET = 229376, 215000
START_MAX, START_SIZE = 32768, (480, 272)
HEADER, ENTRY = 4096, 16
# "Black": every channel <= 12 once decoded (RGB565: R <= 1, G <= 3, B <= 1), ruling R11. JPEG rings
# an 8x8 block that holds a bright stroke by 6-30, so <= 6 would need q95-98 on icons of 24 px or less;
# the display's near-black filtering (BFI=1) already accepts the Original's ~8/255 slate, and <= 12 on
# a 0x0000 background is invisible.
BLACK = 12

# Ids of DWIN_SET (Original)/9.ICO; ProUI does not use 27, 85, 87 and 89
ORIGINAL_IDS = (tuple(range(0, 39)) + tuple(range(40, 82)) + (85, 87, 89, 90, 91, 93)
                + tuple(range(200, 207)) + tuple(range(249, 255)))
STOCK_REQUIRED = sorted(set(ORIGINAL_IDS) - {27, 85, 87, 89})
JARVIS_REQUIRED = sorted(set(STOCK_REQUIRED) | {77} | set(range(100, 108)) | set(range(110, 132)))
BORDER_LIT_BOTTOM = (130, 131)  # full-width bars whose last row carries a rule (see the docstring)
PROGRESSIVE_SOF = (0xC2, 0xC6, 0xCA, 0xCE)


class Report:
    """Collects failed checks (errors), warnings and notes; `ok` when there is no error."""

    def __init__(self):
        self.errors, self.warnings, self.notes = [], [], []

    def expect(self, cond, msg):
        if not cond:
            self.errors.append(msg)
        return cond

    @property
    def ok(self):
        return not self.errors


def jpeg_segments(blob):
    """(marker, payload) of the header segments of a JPEG, up to and including SOS."""
    segs, i = [], 2
    while i + 4 <= len(blob):
        if blob[i] != 0xFF:
            raise ValueError('no marker at byte %d' % i)
        m = blob[i + 1]
        if m == 0xFF:                       # fill byte
            i += 1
            continue
        if m == 0x01 or 0xD0 <= m <= 0xD8:  # markers without a length
            i += 2
            continue
        n = struct.unpack('>H', blob[i + 2:i + 4])[0]
        segs.append((m, blob[i + 4:i + 2 + n]))
        if m == 0xDA:
            return segs
        i += 2 + n
    raise ValueError('no SOS segment')


def check_jpeg(rep, what, blob, size, strict):
    """Check one JPEG blob; return its pixels as an RGB image, or None when it does not decode."""
    if not rep.expect(blob[:2] == b'\xff\xd8' and blob[-2:] == b'\xff\xd9',
                      '%s: does not start with FFD8 and end with FFD9' % what):
        return None
    try:
        segs = jpeg_segments(blob)
    except (ValueError, struct.error) as e:
        rep.errors.append('%s: bad JPEG header (%s)' % (what, e))
        return None
    sofs = [(m, p) for m, p in segs if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC)]
    if not rep.expect(len(sofs) == 1, '%s: %d SOF segments' % (what, len(sofs))):
        return None
    sof, payload = sofs[0]
    rep.expect(sof not in PROGRESSIVE_SOF, '%s: progressive JPEG (SOF%X)' % (what, sof - 0xC0))
    if strict:
        rep.expect(sof == 0xC0, '%s: not baseline (SOF%X instead of SOF0)' % (what, sof - 0xC0))
        ncomp = payload[5] if len(payload) > 5 else 0
        factors = [payload[7 + 3 * k] for k in range(ncomp) if len(payload) > 7 + 3 * k]
        rep.expect(ncomp == 3 and factors == [0x11] * 3,
                   '%s: not 3 components 4:4:4 (sampling %s)' % (what, ['%02X' % f for f in factors]))
        rep.expect(not any(m == 0xE1 for m, _ in segs), '%s: has an APP1 (EXIF) segment' % what)
    try:
        im = Image.open(io.BytesIO(blob))
        im.load()
    except Exception as e:  # Pillow raises several types for broken data
        rep.errors.append('%s: does not decode (%s)' % (what, e))
        return None
    rep.expect(im.size == size, '%s: decodes as %dx%d, expected %dx%d' % ((what,) + im.size + size))
    return im.convert('RGB')


def box_max(im, box):
    """Max channel value inside box (x1, y1, x2, y2), inclusive."""
    x1, y1, x2, y2 = box
    return max(hi for lo, hi in im.crop((x1, y1, x2 + 1, y2 + 1)).getextrema())


def border_max(im, lit_bottom=False):
    w, h = im.size
    edges = [(0, 0, w - 1, 0), (0, 0, 0, h - 1), (w - 1, 0, w - 1, h - 1)]
    if not lit_bottom:
        edges.append((0, h - 1, w - 1, h - 1))
    return max(box_max(im, e) for e in edges)


def black_problems(i, im):
    """Areas of icon i (decoded RGB) that the jarvis profile needs black but are not: [(area, max)].
    gen_icons.py uses it too, to pick JPEG qualities that keep these areas black."""
    w, h = im.size
    found = []
    m = border_max(im, i in BORDER_LIT_BOTTOM)
    if m > BLACK:
        found.append(('border', m))
    if (w, h) in ((110, 100), (80, 100)):
        m = box_max(im, (0, spec.CAPTION_ROWS[0], w - 1, spec.CAPTION_ROWS[1]))
        if m > BLACK:
            found.append(('caption rows %d-%d' % spec.CAPTION_ROWS, m))
    if i == 131:
        for box in spec.DASH_KEEPOUT:
            m = box_max(im, box)
            if m > BLACK:
                found.append(('keep-out %s' % (box,), m))
    return found


def read_ico(rep, path, strict):
    """Check 9.ICO; return {id: (W, H, RGB image or None)} of its entries."""
    size = os.path.getsize(path)
    rep.expect(size <= ICO_MAX, '9.ICO: %d B > %d B (it would spill past bank 15)' % (size, ICO_MAX))
    if size > ICO_TARGET:
        rep.warnings.append('9.ICO: %d B is above the %d B target' % (size, ICO_TARGET))
    with open(path, 'rb') as f:
        data = f.read()
    if not rep.expect(len(data) > HEADER, '9.ICO: %d B, shorter than its %d B header' % (len(data), HEADER)):
        return {}
    icons, pos = {}, HEADER
    for i in range(HEADER // ENTRY):
        raw = data[i * ENTRY:(i + 1) * ENTRY]
        if raw == bytes(ENTRY):
            continue
        w, h, off, len_hi, len_lo, *pad = struct.unpack('>HHLBHBBBBB', raw)
        length = len_hi * 65536 + len_lo
        what = 'icon %d' % i
        if not rep.expect(w > 0 and h > 0 and length > 0 and off >= HEADER and not any(pad),
                          '%s: bad header entry %s' % (what, raw.hex())):
            continue
        rep.expect(off == pos, '%s: offset %d, expected %d (offsets must be contiguous)' % (what, off, pos))
        pos = off + length
        if not rep.expect(off + length <= len(data), '%s: data %d..%d runs past EOF (%d B): truncated'
                          % (what, off, off + length, len(data))):
            icons[i] = (w, h, None)
            continue
        icons[i] = (w, h, check_jpeg(rep, what, data[off:off + length], (w, h), strict))
    rep.expect(pos == len(data), '9.ICO: the last icon ends at %d but EOF is at %d' % (pos, len(data)))
    return icons


def check_set(folder, profile):
    """Run the checks of `profile` ('stock' or 'jarvis') on a DWIN_SET folder; return a Report."""
    jarvis = profile == 'jarvis'
    rep = Report()
    if not rep.expect(os.path.isdir(folder), '%s is not a folder' % folder):
        return rep
    names = sorted(os.listdir(folder))
    extra = [n for n in names if n not in (ICO_NAME, START_NAME)]
    if jarvis:
        rep.expect(not extra, 'folder: unexpected files %s (only %s and %s)' % (extra, ICO_NAME, START_NAME))
        rep.expect(START_NAME in names, 'folder: %s missing' % START_NAME)
    elif extra:
        rep.notes.append('other files (not checked): %s' % ', '.join(extra))
    if not rep.expect(ICO_NAME in names, 'folder: %s missing' % ICO_NAME):
        return rep

    icons = read_ico(rep, os.path.join(folder, ICO_NAME), jarvis)
    required = JARVIS_REQUIRED if jarvis else STOCK_REQUIRED
    missing = [i for i in required if i not in icons]
    rep.expect(not missing, 'missing icons: %s' % missing)
    for i, (w, h, _) in sorted(icons.items()):
        if i in spec.ICONS:
            rep.expect((w, h) == spec.ICONS[i][:2], 'icon %d: %dx%d, jarvis_spec.ICONS says %dx%d'
                       % ((i, w, h) + spec.ICONS[i][:2]))
        elif jarvis:
            rep.errors.append('icon %d: not in jarvis_spec.ICONS' % i)

    lit = []
    for i, (w, h, im) in sorted(icons.items()):
        if im is None:
            continue
        if jarvis:
            for area, m in black_problems(i, im):
                rep.errors.append('icon %d: %s not black (max channel %d > %d)' % (i, area, m, BLACK))
        else:
            m = border_max(im, i in BORDER_LIT_BOTTOM)
            if m > BLACK:
                lit.append('%d (%d)' % (i, m))
    if lit:
        rep.warnings.append('border not black (max channel > %d) in %d icons: %s'
                            % (BLACK, len(lit), ', '.join(lit[:12] + (['...'] if len(lit) > 12 else []))))

    start = os.path.join(folder, START_NAME)
    if os.path.isfile(start):
        n = os.path.getsize(start)
        rep.expect(n <= START_MAX, '%s: %d B > %d B (one bank)' % (START_NAME, n, START_MAX))
        with open(start, 'rb') as f:
            im = check_jpeg(rep, START_NAME, f.read(), START_SIZE, jarvis)
        if jarvis and im is not None:
            portrait = im.transpose(Image.Transpose.ROTATE_270)
            for box in spec.SPLASH_KEEPOUT:
                m = box_max(portrait, box)
                rep.expect(m <= BLACK, '%s: keep-out %s of the portrait design not black (max %d)'
                           % (START_NAME, box, m))
    rep.notes.insert(0, '%s: %d icons, %d B' % (ICO_NAME, len(icons), os.path.getsize(os.path.join(folder, ICO_NAME))))
    if os.path.isfile(start):
        rep.notes.insert(1, '%s: %d B' % (START_NAME, os.path.getsize(start)))
    return rep


def print_report(folder, profile, rep):
    print('%s [profile %s]' % (os.path.relpath(folder, ROOT) if folder.startswith(ROOT) else folder, profile))
    for n in rep.notes:
        print('  note: ' + n)
    for w in rep.warnings:
        print('  WARNING: ' + w)
    for e in rep.errors:
        print('  FAIL: ' + e)
    print('  => %s' % ('OK' if rep.ok else 'FAILED (%d)' % len(rep.errors)))


def selftest():
    rep = check_set(ORIGINAL, 'stock')
    print_report(ORIGINAL, 'stock', rep)
    assert rep.ok, 'the stock profile must pass on DWIN_SET (Original)'
    with open(os.path.join(ORIGINAL, ICO_NAME), 'rb') as f:
        ico = f.read()
    with open(os.path.join(ORIGINAL, START_NAME), 'rb') as f:
        start = f.read()
    with tempfile.TemporaryDirectory() as tmp:
        cut = os.path.join(tmp, 'truncated')
        os.mkdir(cut)
        with open(os.path.join(cut, ICO_NAME), 'wb') as f:
            f.write(ico[:-1000])
        rep = check_set(cut, 'stock')
        print_report(cut, 'stock (9.ICO truncated by 1000 B)', rep)
        assert not rep.ok and any('EOF' in e for e in rep.errors), 'a truncated 9.ICO must fail'

        big = os.path.join(tmp, 'big_start')
        os.mkdir(big)
        with open(os.path.join(big, ICO_NAME), 'wb') as f:
            f.write(ico)
        pad = 33 * 1024 - len(start) - 4    # a COM segment right after SOI: still a valid JPEG
        assert 0 < pad < 65534
        with open(os.path.join(big, START_NAME), 'wb') as f:
            f.write(start[:2] + b'\xff\xfe' + struct.pack('>H', pad + 2) + bytes(pad) + start[2:])
        assert os.path.getsize(os.path.join(big, START_NAME)) == 33 * 1024
        rep = check_set(big, 'stock')
        print_report(big, 'stock (0_start.jpg of 33 KiB)', rep)
        assert not rep.ok and any(e.startswith(START_NAME) and str(START_MAX) in e for e in rep.errors), \
            'a 33 KiB 0_start.jpg must fail'
    rep = check_set(ORIGINAL, 'jarvis')
    assert not rep.ok and any(e.startswith('missing icons') for e in rep.errors), \
        'the jarvis profile must reject DWIN_SET (Original)'
    print('DWIN_SET (Original) [profile jarvis] => FAILED (%d), as expected' % len(rep.errors))
    print('selftest OK: Original passes the stock profile, both broken copies fail')


def main():
    ap = argparse.ArgumentParser(description='Check a DWIN_SET folder (9.ICO, 0_start.jpg).')
    ap.add_argument('folder', nargs='?')
    ap.add_argument('--profile', choices=('stock', 'jarvis'))
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return 0
    if not args.folder or not args.profile:
        ap.error('give <folder> and --profile, or --selftest')
    rep = check_set(os.path.abspath(args.folder), args.profile)
    print_report(os.path.abspath(args.folder), args.profile, rep)
    return 0 if rep.ok else 1


if __name__ == '__main__':
    sys.exit(main())
