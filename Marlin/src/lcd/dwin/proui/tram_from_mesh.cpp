/**
 * Tram from Mesh for PRO UI (JARVIS_TRAM_FROM_MESH): bed-screw turns from the manual mesh, no probe needed.
 * The best-fit plane of the mesh is evaluated at the four bed screws (the tram() points, BED_SCREW_INSET from the
 * corners); each screw is told how far its corner is above or below their mean, in knob turns.
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

#include "../../../inc/MarlinConfigPre.h"

#if ALL(DWIN_LCD_PROUI, JARVIS_TRAM_FROM_MESH)

#include "dwin.h"
#include "../../marlinui.h"
#include "../../../feature/bedlevel/bedlevel.h"
#include "meshviewer.h"
#include "tram_from_mesh.h"

static const char tram_name[4][3] = { "FL", "FR", "BR", "BL" }; // tram(0..3) order

// Corner deviations (mm) from the manual mesh: reads bedlevel.z_values and the XY of each point, nothing moves and
// no heater changes. False without a mesh.
static bool tram_mesh(float d[4], float &b, float &c) {
  if (!bedlevel.has_mesh()) return false;
  TramFit fit;
  GRID_LOOP(i, j) fit.add(bedlevel.get_mesh_x(i), bedlevel.get_mesh_y(j), bedlevel.z_values[i][j]);
  return fit.corners(d, b, c, X_BED_SIZE, Y_BED_SIZE, ui.screw_pos);
}

static bool tram_ok(const float d) { return fabsf(d) < float(JARVIS_TRAM_TOLERANCE); }

// The corner to turn: largest |d|, the first in FL, FR, BR, BL order on a tie (opposite corners always tie). All four
// are within the tolerance when this one is.
static uint8_t tram_worst(const float d[4]) {
  uint8_t w = 0;
  for (uint8_t i = 1; i < 4; ++i) if (fabsf(d[i]) > fabsf(d[w])) w = i;
  return w;
}

// The Trammingwizard() screen with the corners of the mesh plane instead of probed points
void TramFromMesh() {
  float d[4], b, c;
  if (!tram_mesh(d, b, c)) {
    DWINUI::ClearMainArea();
    DWINUI::Draw_CenteredString(140, F("No mesh."));
    DWINUI::Draw_CenteredString(160, F("Run Level > Manual Mesh"));
  }
  else {
    // ponytail: the corners drawn one by one as in Trammingwizard(), the DrawMesh(zval, 2, 2) picture without a 324-byte bed_mesh_t
    constexpr uint8_t coords[4][2] = { {0, 0}, {1, 0}, {1, 1}, {0, 1} }; // FL, FR, BR, BL; MeshViewer puts {0, 0} bottom-left
    MeshViewer.DrawMeshGrid(2, 2);
    for (uint8_t i = 0; i < 4; ++i) MeshViewer.DrawMeshPoint(coords[i][0], coords[i][1], d[i]);
    const uint8_t w = tram_worst(d);
    if (tram_ok(d[w])) {
      DWINUI::Draw_CenteredString(140, GET_TEXT_F(MSG_CORNERS_LEVELED));
      DWINUI::Draw_CenteredString(160, GET_TEXT_F(MSG_TOLERANCE_ACHIEVED));
    }
    else {
      PGM_P const label[4] = { GET_TEXT(MSG_TRAM_FL), GET_TEXT(MSG_TRAM_FR), GET_TEXT(MSG_TRAM_BR), GET_TEXT(MSG_TRAM_BL) };
      const bool raise = d[w] < 0;
      char line[40];
      DWINUI::Draw_CenteredString(120, GET_TEXT_F(MSG_CORNERS_NOT_LEVELED));
      snprintf_P(line, sizeof(line), PSTR("%s %s"), raise ? GET_TEXT(MSG_RAISE) : GET_TEXT(MSG_LOWER), label[w]);
      DWINUI::Draw_CenteredString(raise ? Color_Error_Red : Color_Green, 140, line); // colors as Trammingwizard()
      tram_advice(line, d[w]);
      line[0] += 'A' - 'a'; // "Loosen ..." / "Tighten ..."
      DWINUI::Draw_CenteredString(160, line);
      char *p = line;       // the other corners out of tolerance: "FR +0.06  BL -0.09"
      for (uint8_t i = 0; i < 4; ++i) if (i != w && !tram_ok(d[i])) {
        p += sprintf_P(p, PSTR("%s%s "), p == line ? "" : "  ", tram_name[i]);
        p = tram_mm(p, d[i]);
      }
      if (p != line) DWINUI::Draw_CenteredString(180, line);
    }
  }
  DWINUI::Draw_Button(BTN_Continue, 86, 305, true);
  checkkey = Menu;
  HMI_SaveProcessID(WaitResponse);
}

#if HAS_CGCODE
  // C36: the same analysis as text, e.g. "  FL  -0.18 mm  RAISE  loosen 1/4 turn CW"
  void C36() {
    float d[4], b, c;
    if (!tram_mesh(d, b, c)) { SERIAL_ECHO_MSG("  no mesh"); return; }
    char line[56];
    for (uint8_t i = 0; i < 4; ++i) {
      char *p = tram_mm(line + sprintf_P(line, PSTR("  %s  "), tram_name[i]), d[i]);
      if (tram_ok(d[i])) strcpy_P(p, PSTR(" mm  ok"));
      else tram_advice(p + sprintf_P(p, PSTR(" mm  %s  "), d[i] < 0 ? "RAISE" : "LOWER"), d[i]);
      SERIAL_ECHO_START(); SERIAL_ECHOLN(line);
    }
    const uint8_t w = tram_worst(d);
    if (tram_ok(d[w])) SERIAL_ECHO_MSG("  corners leveled (tol ", float(JARVIS_TRAM_TOLERANCE), ")");
    else SERIAL_ECHO_MSG("  worst: ", tram_name[w]);
    char tx[8], ty[8];
    tram_mm(tx, b * 100); tram_mm(ty, c * 100);
    sprintf_P(line, PSTR("  tilt X %s mm/100mm  Y %s mm/100mm"), tx, ty);
    SERIAL_ECHO_START(); SERIAL_ECHOLN(line);
  }
#endif

#endif // DWIN_LCD_PROUI && JARVIS_TRAM_FROM_MESH
