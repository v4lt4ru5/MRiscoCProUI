/**
 * Host test for jv_gauge_level() in Marlin/src/lcd/dwin/proui/jarvis.h (JARVIS_GAUGES).
 * Everything is checked at compile time; from the repository root:
 *   g++ -std=c++11 -fsyntax-only -I Marlin/src/lcd/dwin/proui buildroot/share/dwin/jarvis/test_gauge.cpp
 * Levels 0..8 are eighths from 20 degC ambient to the target, 9 = HOT with the heater off.
 */
#include "jarvis.h"

// Task 8 plan cases (cur, tgt) -> level
static_assert(jv_gauge_level(25, 60) == 1, "(25,60) -> 1");
static_assert(jv_gauge_level(58, 60) == 8, "(58,60) -> 8");
static_assert(jv_gauge_level(117, 210) == 4, "(117,210) -> 4");
static_assert(jv_gauge_level(205, 210) == 7, "(205,210) -> 7");
static_assert(jv_gauge_level(208, 210) == 8, "(208,210) -> 8");
static_assert(jv_gauge_level(46, 0) == 9, "(46,0) -> 9, HOT with the heater off");
static_assert(jv_gauge_level(-10, 210) == 0, "(-10,210) -> 0");
static_assert(jv_gauge_level(20, 0) == 0, "(20,0) -> 0");

// Extra: the 1..20 target branch, the upper clamp and the HOT threshold itself
static_assert(jv_gauge_level(18, 20) == 8, "(18,20) -> 8");
static_assert(jv_gauge_level(17, 20) == 0, "(17,20) -> 0");
static_assert(jv_gauge_level(5, 1) == 8, "(5,1) -> 8");
static_assert(jv_gauge_level(300, 210) == 8, "(300,210) -> 8");
static_assert(jv_gauge_level(45, 0) == 0, "(45,0) -> 0");

int main() { return 0; }
