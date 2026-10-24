/**
 * Tram from Mesh for PRO UI (JARVIS_TRAM_FROM_MESH): bed-screw turns from the manual mesh, no probe needed.
 * The math has no Marlin includes, so it can be compiled on the host; buildroot/share/dwin/jarvis/tram_check.py
 * repeats the same formulas.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 */
#pragma once

#include <math.h>
#include <stdio.h>

#ifndef JARVIS_TRAM_SCREW_PITCH
  #define JARVIS_TRAM_SCREW_PITCH 0.7 // (mm/turn) M4 bed screws
#endif
#ifndef JARVIS_TRAM_LOOSEN_CW
  #define JARVIS_TRAM_LOOSEN_CW true  // turning a knob clockwise loosens the spring and raises the corner
#endif
#ifndef JARVIS_TRAM_TOLERANCE
  #define JARVIS_TRAM_TOLERANCE 0.05  // (mm) corners within this are reported as leveled
#endif

void TramFromMesh(); // Bed Tramming > Tram from Mesh
void C36();          // the same analysis as text

// Least-squares plane z = a + b*x + c*y through the mesh points (sums of the 3x3 normal equations)
struct TramFit {
  float n = 0, x = 0, y = 0, xx = 0, xy = 0, yy = 0, z = 0, xz = 0, yz = 0;
  void add(const float px, const float py, const float pz) {
    n += 1; x += px; y += py; xx += px * px; xy += px * py; yy += py * py; z += pz; xz += px * pz; yz += py * pz;
  }
  // Tilt b, c (mm/mm) by Cramer's rule, then the plane at the screws FL, FR, BR, BL (inset s on a w x h bed, as tram())
  // minus their mean, which drops a: d = -+b(w-2s)/2 -+c(h-2s)/2, so opposite corners are exact negatives. False if
  // the points span no plane.
  // ponytail: float sums of raw coordinates, ample for 3..9 points on a 220 mm bed; centre x and y first for a big bed
  bool corners(float d[4], float &b, float &c, const float w, const float h, const float s) const {
    const float D = n * (xx * yy - xy * xy) - x * (x * yy - xy * y) + y * (x * xy - xx * y);
    if (!(D > 1e-6f * n * xx * yy)) return false;
    b = (n * (xz * yy - xy * yz) - z * (x * yy - xy * y) + y * (x * yz - xz * y)) / D;
    c = (n * (xx * yz - xz * xy) - x * (x * yz - xz * y) + z * (x * xy - xx * y)) / D;
    const float u = b * (w - 2 * s) / 2, v = c * (h - 2 * s) / 2;
    d[0] = -u - v; d[1] = u - v; d[2] = u + v; d[3] = v - u;
    return true;
  }
};

// |v| clamped to 99.99 mm (NaN too), so the texts below always fit their buffers
inline float tram_abs(const float v) { const float a = fabsf(v); return a < 99.99f ? a : 99.99f; }

// Signed mm with 2 decimals, "+0.06" / "-0.18" ("+0.00" for anything that rounds to 0)
inline char* tram_mm(char *p, const float mm) {
  const unsigned v = unsigned(tram_abs(mm) * 100 + 0.5f);
  return p + sprintf(p, "%c%u.%02u", mm < 0 && v ? '-' : '+', v / 100, v % 100);
}

// Knob advice for a corner deviation d (mm) to the nearest 1/8 turn: "loosen 1/4 turn CW", "tighten 1 1/8 turn CCW",
// "<1/8" below 1/16 turn. A low corner (d < 0) rises when its spring is loosened.
inline char* tram_advice(char *p, const float d) {
  const bool raise = d < 0;
  const unsigned e = unsigned(tram_abs(d) * (8 / float(JARVIS_TRAM_SCREW_PITCH)) + 0.5f), // eighths of a turn
                 w = e / 8, f = e % 8, g = f & -f;                                         // g = gcd(f, 8)
  p += sprintf(p, "%s ", raise ? "loosen" : "tighten");
  if (!e) p += sprintf(p, "<1/8");
  if (w) p += sprintf(p, "%u", w);
  if (f) p += sprintf(p, w ? " %u/%u" : "%u/%u", f / g, 8 / g);
  return p + sprintf(p, " turn %s", raise == JARVIS_TRAM_LOOSEN_CW ? "CW" : "CCW");
}
