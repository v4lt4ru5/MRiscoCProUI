/**
 * Custom G-code implementation for PRO UI
 * Author: Miguel A. Risco-Castillo (MRISCOC)
 * Version: 1.4.0
 * Date: 2023/05/03
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

#if ALL(DWIN_LCD_PROUI, HAS_CGCODE)

#include "../../../gcode/gcode.h"
#include "../../../libs/buzzer.h"
#include "../../marlinui.h"

#include "dwin.h"

#if ALL(PROUI_EX, ARDUINO_ARCH_HC32)
  #include "menus.h"
  #if HAS_MESH
    #include "../../../feature/bedlevel/bedlevel.h"
  #endif
  #if HAS_FILAMENT_SENSOR
    #include "../../../feature/runout.h"
  #endif
  #if HAS_TOOLBAR
    #include "toolbar.h"
  #endif
#endif

#define DEBUG_OUT ENABLED(DEBUG_DWIN)
#include "../../../core/debug_out.h"

//=============================================================================
// Extended G-CODES
//=============================================================================

void CError() {
  SERIAL_ECHO_START();
  SERIAL_ECHOLNPGM("C-code Error: Not implemented in firmware");
}

#if HAS_CUSTOM_COLORS
  // C11 Set color for UI element E
  void C11() {
    const int16_t E = parser.seenval('E') ? parser.value_byte() : 0; // UI element
    switch (E) {
      case 0:
        DWIN_RedrawScreen();
        break;
      case 1: // Apply default colors
        DWIN_ApplyColor(1);
        break;
      default:
        HMI_value.Color.r = parser.seenval('R') ? parser.value_byte() : 0;
        HMI_value.Color.g = parser.seenval('G') ? parser.value_byte() : 0;
        HMI_value.Color.b = parser.seenval('B') ? parser.value_byte() : 0;
        DWIN_ApplyColor(E);
        break;
    }
  }
#endif

#if ENABLED(PROUI_ITEM_TRAM)
  // Bed tramming
  void C35() {
    if (parser.seenval('T')) {
      const int8_t i = parser.value_byte();
      if (WITHIN(i, 0, 4)) tram(i);
    }
    TERN_(HAS_BED_PROBE, else Trammingwizard());
  }
#endif

// Cancel a Wait for User without an Emergecy Parser
void C108() {
  #if DEBUG_OUT
    DEBUG_ECHOLNPGM("wait_for_user was ", marlin.wait_for_user);
    DEBUG_ECHOLNPGM("checkkey was ", checkkey);
  #endif
  TERN_(HAS_BACKLIGHT_TIMEOUT, ui.refresh_backlight_timeout();)
  if (!ui.backlight) ui.refresh_brightness();
  marlin.user_resume();
  DONE_BUZZ(true);
}

#if HAS_GCODE_PREVIEW
  // Enable or disable preview screen
  void C250() {
    if (parser.seenval('P')) {
      HMI_data.EnablePreview = !!parser.value_byte();
    }
    SERIAL_ECHOPGM("G-code Thumbnail Preview: ");
    SERIAL_ECHOLN(HMI_data.EnablePreview ? F("Enabled") : F("Disabled"));
  }
#endif

#if HAS_LOCKSCREEN
  // Lock/Unlock screen
  void C510() {
    if (parser.seenval('U') && parser.value_int()) DWIN_UnLockScreen();
    else DWIN_LockScreen();
  }
#endif

#if DEBUG_OUT
  #include "../../../module/planner.h"
  void C997() {
    DWIN_RebootScreen();
    DEBUG_ECHOLNPGM("Simulating a printer freeze");
    while (1) {};
  }
#endif

#if ALL(PROUI_EX, ARDUINO_ARCH_HC32)
  // HC32 links the GD32F10 libproui.a (see proui.py), built for the Maple HAL. It ships weak
  // serial_echopair_P<short> / serial_echolnpair_P<short> that address MSerial1 with the Maple
  // HardwareSerial layout (SerialBase at +22; the HC32 Usart has it at +33) -> bus fault. Defining
  // the same templates here (identical mangled names) makes the linker drop the library copies.
  template <typename T> void serial_echopair_P(PGM_P const pstr, T v) { SERIAL_ECHO_P(pstr); SERIAL_ECHO(v); }
  template <typename T> void serial_echolnpair_P(PGM_P const pstr, T v) { serial_echopair_P(pstr, v); SERIAL_EOL(); }
  template void serial_echopair_P<short>(PGM_P const, short);
  template void serial_echolnpair_P<short>(PGM_P const, short);

  #if HAS_FILAMENT_SENSOR
    // libproui.a also carries a weak FilamentSensorBase::poll_runout_pins() compiled with the Maple
    // READ() (PIN_MAP layout of the GD32F103). Taking the address here emits our HC32 copy, which the
    // linker keeps instead; FilamentSensorDevice::run() in the library then reads the real pin.
    static uint8_t (* const _hc32_poll_runout_pins)() __attribute__((used)) = &FilamentSensorBase::poll_runout_pins;
  #endif

  // The library's C29/C412/C562/C810 reports print through MSerial1 + 22 and its handlers tail-call
  // them, so both are re-implemented here with the library's output and parameters.
  #if HAS_MESH
    #if ENABLED(MESH_BED_LEVELING)
      void ManualMesh_Resize(); // libproui.a export, not declared in the open headers
    #endif

    static void hc32_C29_report(const bool forReplay) {
      GcodeSuite::report_heading_etc(forReplay, F("Mesh Insets and leveling settings"));
      SERIAL_ECHOPGM("  C29 L", PRO_data.mesh_min_x, " R", PRO_data.mesh_max_x,
                     " F", PRO_data.mesh_min_y, " B", PRO_data.mesh_max_y, " N", uint16_t(PRO_data.grid_max_points));
      #if ENABLED(PREHEAT_BEFORE_LEVELING) // the library prints T and T= from HMI_data+44, which is ExtMinT without this option
        SERIAL_ECHOPGM(" T", HMI_data.BedLevT);
      #endif
      SERIAL_ECHOPGM(" ; ", uint16_t(PRO_data.grid_max_points), "x", uint16_t(PRO_data.grid_max_points));
      #if ENABLED(PREHEAT_BEFORE_LEVELING)
        SERIAL_ECHOPGM("  T=", HMI_data.BedLevT, "\xC2\xB0" "C");
      #endif
      SERIAL_EOL();
    }

    static void hc32_C29() {
      if (parser.seenval('L')) PRO_data.mesh_min_x = parser.value_float();
      if (parser.seenval('R')) PRO_data.mesh_max_x = parser.value_float();
      if (parser.seenval('F')) PRO_data.mesh_min_y = parser.value_float();
      if (parser.seenval('B')) PRO_data.mesh_max_y = parser.value_float();
      if (parser.seenval('N')) {
        set_bed_leveling_enabled(false);
        PRO_data.grid_max_points = parser.value_byte();
        LIMIT(PRO_data.grid_max_points, GRID_MIN, GRID_LIMIT);
        TERN_(MESH_BED_LEVELING, ManualMesh_Resize());
        reset_bed_level();
      }
      if (parser.seenval('T')) {
        #if ENABLED(PREHEAT_BEFORE_LEVELING)
          HMI_data.BedLevT = parser.value_int();
          LIMIT(HMI_data.BedLevT, 0, 110);
        #else // the library would write T into HMI_data+44, which is ExtMinT here
          SERIAL_ECHOLNPGM("C29 T is not supported on the HC32 build (no PREHEAT_BEFORE_LEVELING)");
        #endif
      }
      ProEx.CheckMeshInsets();
      ReDrawMenu(false); // the library skips redraw and report for C10 config files (fileprop.isConfig, CV_LASER_MODULE only)
      hc32_C29_report(false);
    }
  #endif

  #if HAS_FILAMENT_SENSOR
    static void hc32_C412_report(const bool forReplay) {
      GcodeSuite::report_heading_etc(forReplay, F("Filament runout sensor"));
      const uint8_t mode = PRO_data.FilamentMotionSensor ? 2 : PRO_data.Runout_active_state ? 1 : 0;
      SERIAL_ECHOLNPGM("  C412 M", uint16_t(mode), " ; Active mode: ", mode == 2 ? F("Motion") : mode ? F("HIGH") : F("LOW"));
    }

    static void hc32_C412() {
      if (!parser.seenval('M')) return; // as the library: without M nothing changes and nothing is printed
      switch (parser.value_int()) {
        case 0: PRO_data.FilamentMotionSensor = false; PRO_data.Runout_active_state = false; break;
        case 1: PRO_data.FilamentMotionSensor = false; PRO_data.Runout_active_state = true;  break;
        case 2: PRO_data.FilamentMotionSensor = true;  PRO_data.Runout_active_state = false; break;
      }
      ReDrawMenu(false);
      hc32_C412_report(false);
    }
  #endif

  #if HAS_EXTRUDERS
    static void hc32_C562_report(const bool forReplay) {
      GcodeSuite::report_heading_etc(forReplay, F("Invert Extruder"));
      SERIAL_ECHOLNPGM("  C562 E", uint16_t(PRO_data.Invert_E0), " ; ", PRO_data.Invert_E0 ? F("inverted") : F("No inverted"));
    }

    static void hc32_C562() {
      if (parser.seenval('E')) PRO_data.Invert_E0 = (parser.value_byte() == 1);
      ReDrawMenu(false);
      hc32_C562_report(false);
    }
  #endif

  #if HAS_TOOLBAR
    static void hc32_C810_report(const bool forReplay) {
      GcodeSuite::report_heading_etc(forReplay, F("Toolbar configuration"));
      SERIAL_ECHOPGM("  C810");
      for (uint8_t i = 0; i < TBMaxOpt; ++i) { SERIAL_CHAR(' ', char('A' + i)); SERIAL_ECHO(uint16_t(PRO_data.TBopt[i])); }
      SERIAL_EOL(); // the library ends this line with \r\n
    }

    static void hc32_C810() {
      for (uint8_t i = 0; i < TBMaxOpt; ++i) if (parser.seenval(char('A' + i))) PRO_data.TBopt[i] = parser.value_byte();
      Draw_ToolBar(true);
      hc32_C810_report(false);
    }
  #endif
#endif // PROUI_EX && ARDUINO_ARCH_HC32

// Special Creality DWIN G-Codes
void custom_gcode(const int16_t codenum) {
  switch (codenum) {
    #if HAS_CUSTOM_COLORS
      case 11: C11(); break;           // Set color for UI element E
    #endif
    #if ENABLED(PROUI_ITEM_TRAM)
      case 35: C35(); break;           // Launch bed tramming wizard
    #endif
    case 108: C108(); break;           // Cancel a Wait for User without an Emergecy Parser
    #if HAS_GCODE_PREVIEW
      case 250: C250(); break;         // Enable or disable preview screen
    #endif
    #if HAS_LOCKSCREEN
      case 510: C510(); break;         // Lock screen
    #endif
    #if DEBUG_OUT
      case 997: C997(); break;         // Simulate a printer freeze
    #endif
    #if PROUI_EX
      #if HAS_MEDIA
        case 10: ProEx.C10(); break;   // Mark the G-code file as a Configuration file
      #endif
      #if HAS_MESH
        case 29: TERN(ARDUINO_ARCH_HC32, hc32_C29, ProEx.C29)(); break;    // Set probing area and mesh leveling settings
      #endif
      case 100: ProEx.C100(); break;   // Change Physical minimums
      case 101: ProEx.C101(); break;   // Change Physical maximums
      case 102: ProEx.C102(); break;   // Change Bed size
      case 104: ProEx.C104(); break;   // Set extruder max temperature (limited by maxtemp in thermistor table)
      case 115: ProEx.C115(); break;   // ProUI Info
      #if ENABLED(NOZZLE_PARK_FEATURE)
        case 125: ProEx.C125(); break; // Set park position
      #endif
      #if HAS_FILAMENT_SENSOR
        case 412: TERN(ARDUINO_ARCH_HC32, hc32_C412, ProEx.C412)(); break; // Set runout sensor active mode
      #endif
      #if HAS_EXTRUDERS
        case 562: TERN(ARDUINO_ARCH_HC32, hc32_C562, ProEx.C562)(); break; // Invert Extruder
      #endif
      #if HAS_TOOLBAR
        case 810: TERN(ARDUINO_ARCH_HC32, hc32_C810, ProEx.C810)(); break; // Config toolbar
      #endif
      case 851: ProEx.C851(); break;   // If has probe, set Z feed rate and multiple probes. If not, set manual Z-Offset
    #endif
    default: CError(); break;
  }
}

#if PROUI_EX
  void custom_gcode_report(const bool forReplay/*=true*/) {
    #if HAS_MESH
      TERN(ARDUINO_ARCH_HC32, hc32_C29_report, ProEx.C29_report)(forReplay);
    #endif
    ProEx.C100_report(forReplay);
    ProEx.C101_report(forReplay);
    ProEx.C102_report(forReplay);
    ProEx.C104_report(forReplay);
    #if ENABLED(NOZZLE_PARK_FEATURE)
      ProEx.C125_report(forReplay);
    #endif
    #if HAS_FILAMENT_SENSOR
      TERN(ARDUINO_ARCH_HC32, hc32_C412_report, ProEx.C412_report)(forReplay);
    #endif
    #if HAS_EXTRUDERS
      TERN(ARDUINO_ARCH_HC32, hc32_C562_report, ProEx.C562_report)(forReplay);
    #endif
    #if HAS_TOOLBAR
      TERN(ARDUINO_ARCH_HC32, hc32_C810_report, ProEx.C810_report)(forReplay);
    #endif
    ProEx.C851_report(forReplay);
  }
#endif

#endif // DWIN_LCD_PROUI && HAS_CGCODE
