/**
 * JARVIS HUD skin helpers for PRO UI
 * No Marlin includes, so buildroot/share/dwin/jarvis/test_gauge.cpp can check them on the host.
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

#include <stdint.h>

#ifndef JARVIS_HOT_TEMP
  #define JARVIS_HOT_TEMP 45 // (degC) Gauges show HOT above this with the heater off
#endif

// Limit a gauge level to 0..8
constexpr uint8_t jv_clamp8(const int32_t v) { return v < 0 ? 0 : v > 8 ? 8 : uint8_t(v); }

// Temperature gauge level, the icon offset from ICON_JV_HotG0 / ICON_JV_BedG0, in 32-bit integer math:
//  target > 20  : 0..8 eighths of the way from 20 degC ambient to the target (2 degC early)
//  target 1..20 : 8 once within 2 degC of the target, else 0
//  heater off   : 9 (HOT) above JARVIS_HOT_TEMP, else 0
constexpr uint8_t jv_gauge_level(const int16_t cur, const int16_t tgt) {
  return tgt > 20 ? jv_clamp8((int32_t(cur) + 2 - 20) * 8 / (int32_t(tgt) - 20))
       : tgt > 0  ? (int32_t(cur) + 2 >= tgt ? 8 : 0)
       : (cur > JARVIS_HOT_TEMP ? 9 : 0);
}
