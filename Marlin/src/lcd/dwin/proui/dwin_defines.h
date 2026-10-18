/**
 * DWIN general defines and data structs for PRO UI
 * Based on the original work of: Miguel A. Risco-Castillo (MRISCOC)
 * Version: 3.13.3
 * Date: 2022/05/18
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

#include "../../../inc/MarlinConfigPre.h"
#include <stddef.h>
#include "../../../core/types.h"
#include "proui.h"

//#define DEBUG_DWIN 1
//#define TJC_DISPLAY         // Enable for TJC display
//#define DACAI_DISPLAY       // Enable for DACAI display
#define TITLE_CENTERED        // Center Menu Title Text

#if HAS_MESH
  #define Z_OFFSET_MIN -3.0 // (mm)
  #define Z_OFFSET_MAX  3.0 // (mm)
#endif

#define HAS_FEEDRATE_EDIT 1 // Feedrate percentage
#define HAS_FLOW_EDIT 1     // Flow percentage

#if ENABLED(HYBRID_THRESHOLD)
  #define HYBRID_THRESHOLD_MENU // Enable Hybrid Threshold menu
#endif
#if HAS_STEALTHCHOP
  #define STEALTHCHOP_MENU      // Enable StealthChop menu (352 bytes)
#endif

#if defined(__STM32F1__) || defined(STM32F1) || defined(ARDUINO_ARCH_HC32) || MB(CREALITY_V24S1_301, CREALITY_V24S1_301F4)
  #define DASH_REDRAW 1
#endif

#if !HAS_BED_PROBE && ENABLED(BABYSTEPPING)
  #define JUST_BABYSTEP 1
#endif

// JARVIS HUD skin: JARVIS_* switches in Configuration.h, tools in buildroot/share/dwin/jarvis
#if ANY(TJC_DISPLAY, DACAI_DISPLAY) && ANY(JARVIS_PALETTE, JARVIS_TITLE, JARVIS_CURSOR, JARVIS_DASH_FRAME, JARVIS_GAUGES, JARVIS_BOOT, JARVIS_BOOT_JPG, JARVIS_FANBAR)
  #error "JARVIS_* options need the DWIN T5UIC1 display with DWIN_SET (JARVIS). Disable them for TJC_DISPLAY or DACAI_DISPLAY."
#endif
#if ENABLED(JARVIS_PALETTE) && ALT_COLOR_MENU != 1
  #error "JARVIS_PALETTE requires ALT_COLOR_MENU 1 (the only DWIN_SetColorDefaults() that applies every Def_*_Color)."
#endif

// JARVIS accents (R 0-31, G 0-63, B 0-31) for any JARVIS_* switch. RGB() has no outer parentheses, so each use is wrapped.
#define JV_CYAN   (RGB( 0, 57, 31))
#define JV_TEAL   (RGB( 0, 44, 22))
#define JV_ICE    (RGB(25, 59, 31))
#define JV_AMBER  (RGB(31, 44,  0))

#if ENABLED(JARVIS_PALETTE) // Same values as PALETTE in buildroot/share/dwin/jarvis/jarvis_spec.py and themes/jarvis_theme.gcode
  #define Def_Background_Color  (RGB( 0,  0,  0)) // Pure black, needed by Draw_IconWB
  #define Def_Cursor_Color      JV_CYAN           // Selection frames
  #define Def_TitleBg_Color     (RGB( 0, 14, 11)) // Popup buttons (the title bar is an icon)
  #define Def_TitleTxt_Color    (RGB(20, 63, 31))
  #define Def_Text_Color        JV_ICE
  #define Def_Selected_Color    (RGB( 0, 20, 10))
  #define Def_SplitLine_Color   (RGB( 0, 18, 12))
  #define Def_Highlight_Color   JV_TEAL           // Popup frame
  #define Def_StatusBg_Color    (RGB( 0,  6,  6))
  #define Def_StatusTxt_Color   (RGB(15, 58, 31))
  #define Def_PopupBg_Color     (RGB( 0,  6,  6))
  #define Def_PopupTxt_Color    JV_ICE
  #define Def_AlertBg_Color     (RGB( 8,  6,  0))
  #define Def_AlertTxt_Color    JV_AMBER
  #define Def_PercentTxt_Color  JV_CYAN
  #define Def_Barfill_Color     (RGB( 0,  8,  6)) // Unlit part of the progress bar
  #define Def_Indicator_Color   JV_CYAN
  #define Def_Coordinate_Color  JV_ICE
  #define Def_Bottom_Color      (RGB( 0, 30, 18))
#else // Stock ProUI defaults
#if (ALT_COLOR_MENU == 2)
  #define Def_Background_Color  RGB( 0, 8, 6) // Dark Green/Blue
  #define Def_TitleBg_Color     RGB( 0, 23, 16) // Orient Blue
#else
  #define Def_Background_Color  Color_Bg_Black //
  #define Def_TitleBg_Color     Color_Voxelab_Red //
#endif
#define Def_Cursor_Color      Color_Cyan //
#define Def_TitleTxt_Color    Color_White
#define Def_Text_Color        Color_White
#define Def_Selected_Color    Select_Color
#define Def_SplitLine_Color   Color_White //
#define Def_Highlight_Color   Color_White
#define Def_StatusBg_Color    Color_Bg_Black //
#define Def_StatusTxt_Color   Color_Yellow
#define Def_PopupBg_Color     Color_Bg_Window
#define Def_PopupTxt_Color    Popup_Text_Color
#define Def_AlertBg_Color     Color_Bg_Red
#define Def_AlertTxt_Color    Color_Yellow
#define Def_PercentTxt_Color  Percent_Color
#define Def_Barfill_Color     BarFill_Color
#define Def_Indicator_Color   Color_Cyan //
#define Def_Coordinate_Color  Color_Brown //
#define Def_Bottom_Color      Color_Silver //
#endif // JARVIS_PALETTE

#if ALL(LED_CONTROL_MENU, HAS_COLOR_LEDS)
  #define Def_Leds_Color      LEDColorWhite()
#endif

#if CASELIGHT_USES_BRIGHTNESS
  #define Def_CaseLight_Brightness 255
#endif

#if ALL(INDIVIDUAL_AXIS_HOMING_SUBMENU, MESH_BED_LEVELING)
  #ifdef Z_AFTER_HOMING
    #define DEF_Z_AFTER_HOMING Z_AFTER_HOMING
  #else
    #define DEF_Z_AFTER_HOMING 10
  #endif
#endif

#ifndef PREHEAT_1_TEMP_HOTEND
  #define PREHEAT_1_TEMP_HOTEND 210
#endif
#ifndef PREHEAT_1_TEMP_BED
  #define PREHEAT_1_TEMP_BED 60
#endif
#ifndef PREHEAT_1_TEMP_CHAMBER
  #define PREHEAT_1_TEMP_CHAMBER 35
#endif
#define DEF_HOTENDPIDT PREHEAT_1_TEMP_HOTEND
#define DEF_BEDPIDT PREHEAT_1_TEMP_BED
#define DEF_CHAMBERPIDT PREHEAT_1_TEMP_CHAMBER
#define DEF_PIDCYCLES 5
#define EXT motion.extruder

//=============================================================================
// Only for Professional Firmware UI extensions
//=============================================================================

#if PROUI_EX

  #undef X_BED_SIZE
  #undef Y_BED_SIZE
  #undef X_MIN_POS
  #undef Y_MIN_POS
  #undef X_MAX_POS
  #undef Y_MAX_POS
  #undef Z_MAX_POS
  #undef NOZZLE_PARK_POINT
  #define X_BED_SIZE (float)PRO_data.x_bed_size
  #define Y_BED_SIZE (float)PRO_data.y_bed_size
  #define X_MIN_POS  (float)PRO_data.x_min_pos
  #define Y_MIN_POS  (float)PRO_data.y_min_pos
  #define X_MAX_POS  (float)PRO_data.x_max_pos
  #define Y_MAX_POS  (float)PRO_data.y_max_pos
  #define Z_MAX_POS  (float)PRO_data.z_max_pos
  #define NOZZLE_PARK_POINT {(float)PRO_data.Park_point.x, (float)PRO_data.Park_point.y, (float)PRO_data.Park_point.z}
  #if HAS_MESH
    #undef  GRID_MAX_POINTS_X
    #undef  GRID_MAX_POINTS_Y
    #undef  GRID_MAX_POINTS
    #define GRID_MAX_POINTS_X PRO_data.grid_max_points
    #define GRID_MAX_POINTS_Y PRO_data.grid_max_points
    #define GRID_MAX_POINTS  (PRO_data.grid_max_points * PRO_data.grid_max_points)
  #endif
  #if HAS_BED_PROBE
    #undef  Z_PROBE_FEEDRATE_SLOW
    #define Z_PROBE_FEEDRATE_SLOW PRO_data.zprobefeedslow
  #endif
  #if HAS_EXTRUDERS
    #undef  INVERT_E0_DIR
    #define INVERT_E0_DIR PRO_data.Invert_E0
  #endif

#else

// ProUI extra feature redefines
  #if PROUI_GRID_PNTS
    #undef  GRID_MAX_POINTS_X
    #undef  GRID_MAX_POINTS_Y
    #undef  GRID_MAX_POINTS
    #define GRID_MAX_POINTS_X HMI_data.grid_max_points
    #define GRID_MAX_POINTS_Y HMI_data.grid_max_points
    #define GRID_MAX_POINTS  (HMI_data.grid_max_points * HMI_data.grid_max_points)
  #endif
  #if HAS_BED_PROBE
    #undef  Z_PROBE_FEEDRATE_SLOW
    #define Z_PROBE_FEEDRATE_SLOW HMI_data.zprobefeedslow
  #endif
  #if HAS_EXTRUDERS
    #undef  INVERT_E0_DIR
    #define INVERT_E0_DIR HMI_data.Invert_E0
  #endif

#endif // PROUI_EX
