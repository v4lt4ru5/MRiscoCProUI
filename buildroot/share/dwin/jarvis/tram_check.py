#!/usr/bin/env python3
"""
Host check for Tram from Mesh (JARVIS_TRAM_FROM_MESH): the plane fit, corner deviations and knob-turn text of
Marlin/src/lcd/dwin/proui/tram_from_mesh.h, written again with the same formulas (double here, float there), and the
C36 lines of tram_from_mesh.cpp. From the repository root:
  python3 buildroot/share/dwin/jarvis/tram_check.py
Asserts the expected advice on synthetic meshes, that opposite corners always tie (so the screen always names a front
corner) and how many passes the knob procedure of the kit README takes on a rigid bed; when g++ is installed, compiles
tram_from_mesh.h on the host and checks that it prints the same numbers and texts.
"""
import math, os, random, re, shutil, subprocess, tempfile

PITCH, LOOSEN_CW, TOL = 0.7, True, 0.05  # JARVIS_TRAM_SCREW_PITCH, JARVIS_TRAM_LOOSEN_CW, JARVIS_TRAM_TOLERANCE
BED, INSET = 220, 29                     # X/Y_BED_SIZE and BED_SCREW_INSET of the X2-JARVIS config
NAMES = ('FL', 'FR', 'BR', 'BL')
SCREWS = [(INSET, INSET), (BED - INSET, INSET), (BED - INSET, BED - INSET), (INSET, BED - INSET)]  # tram(0..3)
HDR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../Marlin/src/lcd/dwin/proui')

def corners(pts, w=BED, h=BED, s=INSET):
  """TramFit::add() + corners(): ([d FL, FR, BR, BL], b, c) or None"""
  n = x = y = xx = xy = yy = z = xz = yz = 0.0
  for px, py, pz in pts:
    n += 1; x += px; y += py; xx += px * px; xy += px * py; yy += py * py; z += pz; xz += px * pz; yz += py * pz
  D = n * (xx * yy - xy * xy) - x * (x * yy - xy * y) + y * (x * xy - xx * y)
  if not D > 1e-6 * n * xx * yy: return None
  b = (n * (xz * yy - xy * yz) - z * (x * yy - xy * y) + y * (x * yz - xz * y)) / D
  c = (n * (xx * yz - xz * xy) - x * (x * yz - xz * y) + z * (x * xy - xx * y)) / D
  u, v = b * (w - 2 * s) / 2, c * (h - 2 * s) / 2
  return [-u - v, u - v, u + v, v - u], b, c

def tram_abs(v): a = abs(v); return a if a < 99.99 else 99.99

def tram_mm(mm):
  v = int(tram_abs(mm) * 100 + 0.5)
  return '%c%u.%02u' % ('-' if mm < 0 and v else '+', v // 100, v % 100)

def tram_advice(d):
  e = int(tram_abs(d) * (8 / PITCH) + 0.5)  # eighths of a turn
  w, f = divmod(e, 8); g = f & -f
  t = ('loosen' if d < 0 else 'tighten') + ' ' + ('<1/8' if not e else '') + ('%u' % w if w else '')
  if f: t += (' %u/%u' if w else '%u/%u') % (f // g, 8 // g)
  return t + ' turn ' + ('CW' if (d < 0) == LOOSEN_CW else 'CCW')

def worst(d):
  """tram_worst(): the largest |d|, the first in FL, FR, BR, BL order on a tie"""
  w = 0
  for i in range(1, 4):
    if abs(d[i]) > abs(d[w]): w = i
  return w

def c36(pts):
  """The lines C36() prints after 'echo:'; pts = [(x, y, z)] of the mesh"""
  r = None if not any(p[2] for p in pts) else corners(pts)  # bedlevel.has_mesh(): any z != 0
  if r is None: return ['  no mesh']
  d, b, c = r
  ok = lambda v: abs(v) < TOL
  out = ['  %s  %s mm  %s' % (NAMES[i], tram_mm(d[i]),
         'ok' if ok(d[i]) else '%s  %s' % ('RAISE' if d[i] < 0 else 'LOWER', tram_advice(d[i]))) for i in range(4)]
  w = worst(d)
  out.append('  corners leveled (tol %.2f)' % TOL if ok(d[w]) else '  worst: ' + NAMES[w])
  return out + ['  tilt X %s mm/100mm  Y %s mm/100mm' % (tram_mm(b * 100), tram_mm(c * 100))]

def mesh(f, n=3, lo=12, hi=208):
  """n x n points from lo to hi on both axes (ManualMesh_Resize() spacing), z = f(x, y)"""
  p = [lo + i * (hi - lo) / (n - 1) for i in range(n)]
  return [(x, y, f(x, y)) for x in p for y in p]

CASES = {
  'tilt +0.3 mm front to back, 3x3':     mesh(lambda x, y: 0.3 * (y - 12) / 196),
  'flat at 0.20 mm, 3x3':                mesh(lambda x, y: 0.2),
  'all zero (no mesh measured), 3x3':    mesh(lambda x, y: 0.0),
  'tilt +0.5 mm left to right, 5x5':     mesh(lambda x, y: 0.5 * (x - 12) / 196, 5),
  'saddle (twisted bed), 3x3':           mesh(lambda x, y: 0.0004 * (x - 110) * (y - 110) + 0.2),
  'tilt +2 mm front to back, 3x3':       mesh(lambda x, y: 2.0 * (y - 12) / 196),
  'tilts in X and Y + bumps, 5x5':       mesh(lambda x, y: 0.1 + 0.0012 * x - 0.0007 * y + 0.03 * math.sin(x * y), 5),
}

def knob(advice):
  """'loosen 1 1/8 turn CW' -> the knob travel in mm, + when the corner rises"""
  m = re.fullmatch(r'(loosen|tighten) (?:<1/8|(\d+)?(?: ?(\d)/(\d))?) turn CC?W', advice)
  t = (int(m.group(2) or 0) + (int(m.group(3)) / int(m.group(4)) if m.group(3) else 0)) * PITCH
  return t if m.group(1) == 'loosen' else -t

def passes(h, knobs):
  """A rigid bed on its screws at heights h (FL, FR, BR, BL, mm): rounds of 3x3 mesh, Tram from Mesh and knob turns
  until 'Corners leveled'; knobs(d, w) lists the corners turned, each by its own advice"""
  h = list(h)
  for n in range(10):
    _, b, c = corners([(x, y, z) for (x, y), z in zip(SCREWS, h)])  # the plate takes the plane of its four screws
    a = sum(h) / 4 - (b + c) * BED / 2
    d = corners(mesh(lambda x, y: a + b * x + c * y))[0]
    w = worst(d)
    if abs(d[w]) < TOL: return n
    for i in knobs(d, w): h[i] += knob(tram_advice(d[i]))
  return None

PROCEDURES = {  # README step 4: the named knob and its diagonal opposite, or the four C36 lines; not the named knob alone
  'named + opposite': lambda d, w: (w, (w + 2) % 4),
  'all four (C36)':   lambda d, w: [i for i in range(4) if abs(d[i]) >= TOL],
  'named knob only':  lambda d, w: (w,),
}

def check():
  t = {k: c36(v) for k, v in CASES.items()}
  for k, v in t.items(): print(k + ':\n' + '\n'.join('  echo:' + s for s in v))
  tilt = t['tilt +0.3 mm front to back, 3x3']
  # screws 29 mm in: the plane rises 0.3 * (191 - 29) / 196 = 0.248 mm between the screw rows, -+0.124 mm about the mean
  assert tilt[:4] == ['  FL  -0.12 mm  RAISE  loosen 1/8 turn CW', '  FR  -0.12 mm  RAISE  loosen 1/8 turn CW',
                      '  BR  +0.12 mm  LOWER  tighten 1/8 turn CCW', '  BL  +0.12 mm  LOWER  tighten 1/8 turn CCW'], tilt
  assert tilt[4] in ('  worst: FL', '  worst: FR') and tilt[5] == '  tilt X +0.00 mm/100mm  Y +0.15 mm/100mm', tilt
  assert abs(corners(CASES['tilt +0.3 mm front to back, 3x3'])[0][0] + 0.3 * 81 / 196) < 1e-12
  assert t['flat at 0.20 mm, 3x3'] == ['  %s  +0.00 mm  ok' % n for n in NAMES] + [
    '  corners leveled (tol 0.05)', '  tilt X +0.00 mm/100mm  Y +0.00 mm/100mm']
  assert t['all zero (no mesh measured), 3x3'] == ['  no mesh']
  x5 = t['tilt +0.5 mm left to right, 5x5']  # -+0.5 * 81 / 196 = 0.207 mm = 0.295 turn -> 1/4
  assert x5[0] == '  FL  -0.21 mm  RAISE  loosen 1/4 turn CW' and x5[1] == '  FR  +0.21 mm  LOWER  tighten 1/4 turn CCW', x5
  assert t['saddle (twisted bed), 3x3'][4] == '  corners leveled (tol 0.05)'  # a pure twist has no tilt: the plane is level
  assert t['tilt +2 mm front to back, 3x3'][0] == '  FL  -0.83 mm  RAISE  loosen 1 1/8 turn CW'  # 0.827 mm = 1.18 turn
  # turn text: nearest 1/8, "<1/8" below 1/16 turn (0.04375 mm)
  frac = ['<1/8', '1/8', '1/4', '3/8', '1/2', '5/8', '3/4', '7/8', '1', '1 1/8', '1 1/4', '1 3/8', '1 1/2']
  for k, s in enumerate(frac):
    assert tram_advice(-PITCH * k / 8 - 0.001) == 'loosen %s turn CW' % s, (k, tram_advice(-PITCH * k / 8 - 0.001))
  assert tram_advice(0.0437) == 'tighten <1/8 turn CCW' and tram_advice(0.0438) == 'tighten 1/8 turn CCW'
  assert tram_mm(-0.004) == '+0.00' and tram_mm(-0.18) == '-0.18' and tram_mm(1e9) == '+99.99'
  # opposite corners tie exactly (d BR = -d FL, d BL = -d FR), so the named corner is always FL or FR
  rnd = random.Random(1)
  meshes = [p for p in CASES.values() if any(q[2] for q in p)]
  meshes += [mesh(lambda x, y: rnd.gauss(0, 0.3), rnd.randint(3, 9)) for _ in range(500)]
  for p in meshes:
    d = corners(p)[0]
    assert d[2] == -d[0] and d[3] == -d[1] and worst(d) in (0, 1), d
  # passes until "Corners leveled": one knob alone moves its own corner and the opposite one half of its travel each
  heights = {'back 0.3 mm high': [0.3 * (y - 12) / 196 for x, y in SCREWS],
             'right 0.5 mm high': [0.5 * (x - 12) / 196 for x, y in SCREWS],
             'FL knob 1/2 turn low': [-0.35, 0, 0, 0]}
  want = {'back 0.3 mm high': (2, 1, 4), 'right 0.5 mm high': (2, 1, 6), 'FL knob 1/2 turn low': (1, 1, 2)}
  for k, h in heights.items():
    got = tuple(passes(h, f) for f in PROCEDURES.values())
    print('rigid bed, %s: passes until "Corners leveled": %s' % (k, ', '.join('%s %s' % q for q in zip(PROCEDURES, got))))
    assert got == want[k], (k, got)
  return t

CXX = r'''
#include "tram_from_mesh.h"
int main() { // per case: n x y z ... -> "d mm|advice or ok" for each corner, then b*100 c*100
  int n; char t[40];
  while (scanf("%d", &n) == 1) {
    TramFit f; float d[4], b, c, x, y, z;
    while (n--) { if (scanf("%f %f %f", &x, &y, &z) != 3) return 1; f.add(x, y, z); }
    if (!f.corners(d, b, c, BED, BED, INSET)) { puts("none"); continue; }
    for (int i = 0; i < 4; ++i) {
      tram_mm(t, d[i]); printf("%s|", t);
      if (fabsf(d[i]) < float(JARVIS_TRAM_TOLERANCE)) printf("ok;"); else { tram_advice(t, d[i]); printf("%s;", t); }
    }
    tram_mm(t, b * 100); printf("%s ", t); tram_mm(t, c * 100); printf("%s\n", t);
  }
}
'''

def cross_check():
  """Compile tram_from_mesh.h on the host and compare its output with this file's formulas"""
  gxx = shutil.which('g++')
  if not gxx: return print('g++ not found: C++ cross-check skipped')
  with tempfile.TemporaryDirectory() as tmp:
    src, exe = os.path.join(tmp, 'tram.cpp'), os.path.join(tmp, 'tram')
    open(src, 'w').write(CXX)
    subprocess.run([gxx, '-std=c++17', '-O2', '-Wall', '-Werror', '-DBED=%d' % BED, '-DINSET=%d' % INSET,
                    '-I', HDR, src, '-o', exe], check=True)
    pts = [v for v in CASES.values()]
    got = subprocess.run([exe], input=''.join('%d %s\n' % (len(p), ' '.join('%r %r %r' % q for q in p)) for p in pts),
                         capture_output=True, text=True, check=True).stdout.splitlines()
  for name, p, line in zip(CASES, pts, got):
    r = corners(p)
    want = 'none' if r is None else ''.join('%s|%s;' % (tram_mm(v), 'ok' if abs(v) < TOL else tram_advice(v)) for v in r[0]) + \
           '%s %s' % (tram_mm(r[1] * 100), tram_mm(r[2] * 100))
    assert line == want, (name, line, want)
    print('C++ == Python: %-36s %s' % (name, line))

if __name__ == '__main__':
  check()
  cross_check()
  print('tram_check: OK')
