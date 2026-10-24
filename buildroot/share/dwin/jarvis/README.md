# JARVIS HUD skin: tools and build notes

Tools for the "JARVIS" HUD skin of MRiscoC ProUI on the Voxelab Aquila X2 (HC32F460 "H32" board,
DWIN T5UIC1 4.3" display with a knob, 272x480 portrait). The skin has three parts:

- display assets, stored in the display's own flash (no MCU flash): `DWIN_SET (JARVIS)` =
  `9.ICO` (icon library) + `0_start.jpg` (boot splash);
- palette defaults (`JARVIS_PALETTE`, `Marlin/src/lcd/dwin/proui/dwin_defines.h`) and the theme file
  `themes/jarvis_theme.gcode`;
- small firmware changes, each behind its own `JARVIS_*` switch in
  `configurations/Voxelab Aquila HC32/X2-JARVIS/Configuration.h`.

Firmware and `DWIN_SET (JARVIS)` always ship together: the firmware draws ids 77 and 100-131, which
only this set has in the JARVIS shapes (100-131 exist in no other set).

## Files

All commands run from the repository root.

- `jarvis_spec.py` - single source of truth shared by the other tools: `PALETTE` (C11 slots
  E2..E20 as RGB565 components R 0-31, G 0-63, B 0-31), `JV` accents, `SLOTS`, `ICONS`
  (id -> width, height, class), the black areas `CAPTION_ROWS`, `DASH_KEEPOUT`, `SPLASH_KEEPOUT`,
  `SPLASH_SPINNER`, and `LAYOUT` (firmware screen coordinates). Run as a script it writes
  `themes/jarvis_theme.gcode`, re-reads it and asserts its format and values, then asserts that the
  `JARVIS_PALETTE` defaults and `JV_*` macros in `dwin_defines.h` still match `PALETTE` and `JV`.
  `python3 -I buildroot/share/dwin/jarvis/jarvis_spec.py`
- `gen_icons.py` - draws every icon and the boot splash from code (no image or font files) and
  writes `display assets/Aquila Display Firmware/Icon Packs/JARVIS/NNN-ICON_<Name>.jpg` (127 icons),
  then `Firmware Sets/DWIN_SET (JARVIS)/9.ICO` (through `buildroot/share/dwin/bin/makeIco.py`, after
  deleting the old one: makeIco does not overwrite) and `0_start.jpg`. Prints the total size and the
  final JPEG quality per class. No clock, no randomness: two runs write the same bytes.
  `python3 -I buildroot/share/dwin/jarvis/gen_icons.py`
- `check_dwin_set.py` - validator for a `DWIN_SET` folder. Profile `stock`: what any set needs
  (9.ICO size, header, every blob a non-progressive JPEG that decodes at its header size, the stock
  ids with the `ICONS` sizes, optional 0_start.jpg). Profile `jarvis` adds the delivery rules below.
  `--selftest` runs the stock profile on `DWIN_SET (Original)` (must pass) and on two broken copies
  (must fail). Exit status 0 only when every check passes.
  `python3 -I buildroot/share/dwin/jarvis/check_dwin_set.py "display assets/Aquila Display Firmware/Firmware Sets/DWIN_SET (JARVIS)" --profile jarvis`
  `python3 -I buildroot/share/dwin/jarvis/check_dwin_set.py --selftest`
- `mockup.py` - renders the screens (boot, boot_black, main, print, menu, popup, alert, main_stock and
  a contact sheet of every icon) into `mockups/`, each at 1x and @2x (18 PNGs), following the
  firmware's drawing order and coordinates, with text from the display's own `0T5UIC1.HZK` font and
  emulated `Draw_Icon` transparency (pixels with all channels <= 12 dropped).
  `python3 -I buildroot/share/dwin/jarvis/mockup.py`
- `test_gauge.cpp` - host test of `jv_gauge_level()` in `Marlin/src/lcd/dwin/proui/jarvis.h`, all
  `static_assert` (8 plan cases + 5 boundary cases); compiling is the test.
  `g++ -std=c++11 -fsyntax-only -I Marlin/src/lcd/dwin/proui buildroot/share/dwin/jarvis/test_gauge.cpp`
- `tram_check.py` - host check of Tram from Mesh (`JARVIS_TRAM_FROM_MESH`): the plane fit, corner
  deviations and knob-turn text of `Marlin/src/lcd/dwin/proui/tram_from_mesh.h` written again in
  Python, and the `C36` lines. Asserts the advice for synthetic meshes (tilts, flat, twist, no mesh,
  every 1/8 turn text) and, when `g++` is installed, compiles `tram_from_mesh.h` on the host and
  checks that it prints the same numbers and texts. Ends with `tram_check: OK`.
  `python3 -I buildroot/share/dwin/jarvis/tram_check.py`

## Prerequisites

- Asset tools (`*.py`): the system `python3` (3.12) with Pillow 10.2 (Ubuntu 24.04 `python3-pil`),
  not the PlatformIO venv, which has no PIL. Standard library + Pillow only; run them with
  `python3 -I` (isolated mode: each script adds its own folder to `sys.path`).
- Byte-identical output of `gen_icons.py` and `mockup.py` depends on the Pillow / libjpeg version.
  Another version can encode different bytes and sizes (the quality fitter may then pick other
  qualities). Judge a regenerated set with `check_dwin_set.py`, not by its hash.
- Firmware: a `.venv` in the repository root with `platformio==6.1.19` (the HC32 platform's
  `platform.py:15` imports the legacy `platformio.managers.platform` alias) and
  `PLATFORMIO_CORE_DIR=$PWD/.pio-core`. The HC32 platform and frameworks are pinned to commits in
  `ini/hc32.ini`. `build.sh` activates the venv and sets `PLATFORMIO_CORE_DIR` itself. Create the
  venv once with `python3 -m venv .venv && .venv/bin/pip install platformio==6.1.19`.
- Host tests: g++ with C++11 for `test_gauge.cpp`, C++17 for the `tram_check.py` cross-check
  (checked with g++ 13.3).

## Asset pipeline

1. Change the data in `jarvis_spec.py` (palette, icon sizes, black areas, layout) and/or the art in
   `gen_icons.py`.
2. `python3 -I buildroot/share/dwin/jarvis/gen_icons.py`
3. `python3 -I buildroot/share/dwin/jarvis/check_dwin_set.py "display assets/Aquila Display Firmware/Firmware Sets/DWIN_SET (JARVIS)" --profile jarvis`
   must end with `=> OK`.
4. `python3 -I buildroot/share/dwin/jarvis/mockup.py` and look at the PNGs in `mockups/`.
5. If the palette changed: update the `JARVIS_PALETTE` block of `dwin_defines.h` by hand, then run
   `python3 -I buildroot/share/dwin/jarvis/jarvis_spec.py` (rewrites the theme, checks the defines).
6. Commit the icon pack, the set and the mockups together. Ship the set with the firmware.

### Budgets and rules (`check_dwin_set.py --profile jarvis`)

- `9.ICO` <= 229,376 B (hard cap: 7 banks of 32 KiB); target <= 215,000 B (warning above).
  Now: 212,702 B, 127 icons.
- `0_start.jpg`: 480x272 (the 272x480 portrait design turned with `transpose(ROTATE_90)`),
  <= 32,768 B (one bank). `gen_icons.py` fits it to <= 31,744 B, from q90 down by 2. Now: 30,895 B.
- The delivered folder holds exactly `9.ICO` + `0_start.jpg`: never the display kernel
  (`.BIN`, `.CFG`) or fonts (`.HZK`).
- Every JPEG: RGB, baseline (SOF0), 4:4:4, `optimize=True`, not progressive, no EXIF (APP1);
  pure black background.
- Black means max channel <= 12 (`check_dwin_set.BLACK`, the border/keep-out tolerance). It is
  required on the 1-px border of every icon (the bottom row of 130 and 131 is exempt: it carries the
  title and dashboard rules), on rows 68-92 of the 110x100 and 80x100 buttons (the firmware writes
  the caption at y + 72), in the `DASH_KEEPOUT` boxes of icon 131 (where values are drawn) and in the
  `SPLASH_KEEPOUT` bands of `0_start.jpg`.
- Required ids: the ids of `DWIN_SET (Original)` except 27, 85, 87 and 89, plus 77 (menu cursor
  14x52), 100-107 (spinner 80x80, 8 frames), 110-129 (gauges 24x24: hotend 110 + level 0..8,
  119 = HOT; bed 120 + level, 129 = HOT), 130 (title 272x30) and 131 (dashboard frame 272x105,
  drawn at y 375). Sizes come from `jarvis_spec.ICONS`.
- Quality fitter: every class starts at q90; while `9.ICO` > 215,000 B the class with most bytes
  drops 2 points (not below q75); each icon is raised 1 point at a time until its black areas pass.
- Glow: drawn at 4x and reduced with LANCZOS; glow = lighter(GaussianBlur(6) x 0.55,
  GaussianBlur(2) x 0.9); then every channel below 10 is set to 0 (`LUT_CLAMP`), which is where the
  glow tail is cut off to pure black.

## Firmware switches

In `configurations/Voxelab Aquila HC32/X2-JARVIS/Configuration.h`. Each delta was measured with
`build.sh`, one switch at a time, against the previous build (`out/SIZES.md`).

| Switch | Default | What it does | Flash |
|---|---|---|---:|
| `JARVIS_PALETTE` | on | HUD palette as the color defaults; needs `ALT_COLOR_MENU 1` (`#error` otherwise) | +4 B |
| `JARVIS_BOOT` | on | Boot screen on black: machine name, credits, spinner ids 100-107 (3 turns x 8 frames x 83 ms, ~2 s) | +136 B |
| `JARVIS_TITLE` | on | Title bar = icon 130 | -16 B |
| `JARVIS_CURSOR` | on | Menu cursor = icon 77 | -88 B |
| `JARVIS_GAUGES` | on | Hotend and bed gauges = icons 110-129, redrawn only when the level changes | -52 B |
| `JARVIS_DASH_FRAME` | on | Dashboard frame = icon 131, plus the flow "%" fix (the redraw no longer covers the "%") | -64 B |
| `JARVIS_BOOT_JPG` | off | Boot screen over `0_start.jpg` instead of black; only if `M997` shows the splash upright | +0 B (trial) |
| `JARVIS_FANBAR` | off | Fan speed bar under the fan value; not in the approved mockups | +96 B (trial) |
| `JARVIS_HOT_TEMP` | 45 | (degC) a gauge shows HOT when the heater is off and the temperature is above this (`jarvis.h` default) | - |
| `JARVIS_TRAM_FROM_MESH` | on | *Prepare > Bed Tramming > Tram from Mesh* and `C36`: least-squares plane of the manual mesh at the four bed screws (`BED_SCREW_INSET`), each corner's height against their mean as *Raise/Lower* and *loosen/tighten N/8 turn CW/CCW*; reads the mesh only, moves nothing (`tram_from_mesh.cpp`, math in `tram_from_mesh.h`) | +2,448 B |
| `JARVIS_TRAM_SCREW_PITCH` | 0.7 | (mm/turn) bed screw thread, M4 | - |
| `JARVIS_TRAM_LOOSEN_CW` | true | turning a knob clockwise loosens its spring and raises the corner (false swaps the CW/CCW words only) | - |
| `JARVIS_TRAM_TOLERANCE` | 0.05 | (mm) corners closer than this to the mean are "ok" | - |

- Any skin switch (`JARVIS_PALETTE` ... `JARVIS_FANBAR`) with `TJC_DISPLAY` or `DACAI_DISPLAY` is an
  `#error`; `JARVIS_TRAM_FROM_MESH` draws no JARVIS icon and needs `MESH_BED_LEVELING` and
  `BED_SCREW_INSET` instead (`#error` otherwise).
- X2 defaults that are not switches: `BED_SCREW_INSET 29` (measured on the X2) and the mesh area
  12..208 mm on both axes (`MESH_MIN_X` ... `MESH_MAX_Y` in the MBL block), 12 mm clear of the glass
  clips. Fixed numbers on purpose: `MESH_INSET` gives `X_BED_SIZE - inset`, and with ProUI-EX
  `X_BED_SIZE` is `PRO_data.x_bed_size`, which `mesh_max` reads at boot before the settings load,
  while it still holds the closed library's own default 230, hence the old `C29 ... R220 B220`.
- Release build: v1.2, 184,488 B, 28,504 B free of the 212,992 B gate (target <= 207,000 B): v1.1
  (182,064 B) + `JARVIS_TRAM_FROM_MESH` (+2,448 B) - 24 B (`mesh_max` is now constant data: -40 B of
  boot code, +8 B of data; the `C851` newline +8 B). v1 was 182,176 B, and v1.1 replaces four
  closed-library C-codes with open code (-112 B, see below). The six default skin switches together
  save 80 B: 182,256 B (X2-JARVIS config before any skin code) -> 182,176 B, per the rows of
  `out/SIZES.md`.

## Rebuild the firmware

    ./build.sh X2-JARVIS "" "note for out/SIZES.md"

`build.sh` activates `.venv`, sets `PLATFORMIO_CORE_DIR`, copies the three headers of
`configurations/Voxelab Aquila HC32/X2-JARVIS/` into `Marlin/`, deletes
`.pio/build/HC32F460C_aquila_101`, builds that env, fails if the `.bin` is over 212,992 B or if a
ProUI-EX build fails the libproui checks below, prints `arm-none-eabi-size` and `libres=N`, copies the
result to `out/HC32_X2-JARVIS-<YYYYMMDD>.bin` and adds a row to `out/SIZES.md` (keep `|` out of the
note: it breaks the table). On exit, success or failure, it restores `Marlin/Configuration.h`,
`Configuration_adv.h` and `Version.h` with `git checkout`.

- Edit `configurations/Voxelab Aquila HC32/X2-JARVIS/`, never `Marlin/Configuration*.h`: `build.sh`
  overwrites those before the build and restores them after it, so a local edit there is lost.
- Run one build per working tree at a time: builds share the `Marlin/` headers and `.pio/build`.
- `HC32 libproui checks: OK`. On HC32, `proui.py` links the GD32F10 `libproui.a`, which is built for
  the Maple HAL: its serial and pin code does not match the HC32 core (`M503` hard-faulted, the
  runout monitor read the wrong pin). `custom_gcodes.cpp` replaces that code, and `build.sh` fails if
  the library's `C29`/`C412`/`C562`/`C810` handlers or reports are linked, or if
  `serial_echopair_P<short>`, `serial_echolnpair_P<short>`, `FilamentSensorBase::poll_runout_pins()`,
  `SERIAL_ECHO<float>` or `SERIAL_ECHO<char*>` are linked from anywhere but `Marlin/src`
  (`nm`, `addr2line`), or if the image holds the Maple-layout address `&MSerialN + 22`. One closed
  report stays: `ProUIClass::C851_report()` writes its final newline with `MSerial1.write('\n')`,
  which on HC32 is the display UART (`LCD_SERIAL_PORT 1`), so `custom_gcodes.cpp` adds
  `SERIAL_EOL()` after it and after `C851` (since v1.2; before, `M503` ended in `C851 Z0.00ok`).
- To measure a switch, toggle it in the X2-JARVIS `Configuration.h`, build with a note, and put the
  delta in the define's comment and in `out/SIZES.md`.
- The `.bin` embeds the build date and time (`M115`, and the EEPROM build hash), so two builds of
  the same commit differ in a few bytes: compare sizes, not hashes. With `EEPROM_AUTO_INIT` +
  `EEPROM_INIT_NOW`, the first boot of every new build resets the printer's stored settings (mesh,
  Z-offset, colors, ...); the user kit README says so.

## Fallbacks

Documented in the plan; none has been needed so far.

- The display rejects 272-px-wide icons (130 title, 131 dashboard frame): split each into two
  136-px halves (new ids) and draw both halves, +12 B of flash per draw.
- The boot spinner stutters: 16 frames x 125 ms (same 2 s), or 64x64 frames (smaller JPEGs).
- A dark halo shows around icons drawn transparent (`Draw_Icon`) on the popup background: the
  display drops only (near-)black pixels, so the dim tail of the glow is drawn as a dark rim. Fix the
  assets only, no firmware change: cut the glow off sooner so the dim tail becomes pure black and is
  dropped. That means raising the `LUT_CLAMP` level (now channel < 10 -> 0) towards the popup
  background level (about 24), and lowering the glow (gains 0.55 / 0.9 in the module-level
  `LUT_G6` / `LUT_G2`, blur radii 6 / 2 in `Art.render()`) if the cut then shows; if specks remain,
  use a stricter black tolerance for those icons. Do it at least for the 110x100, 80x100 and 73x66
  icons, which popups draw transparent.
  Then regenerate and re-validate.
- `9.ICO` over the cap: move ids >= 100 to a second library `3.ICO` (bank 3) and select its `libID`
  in `DWINUI::ICON_Show` (about 10 B).
- Before enabling `JARVIS_FANBAR`: fix the fan-0 1-px column. `_draw_jv_fanbar()` always draws the
  Indicator rectangle from x 187 to 187 + (fan >> 2), so at fan 0 a 1-px column stays lit at x 187;
  skip that rectangle when fan >> 2 is 0 (and name the 63, the bar width in px). Add a mockup too.

## Delivery

The user kit is kept outside this repository (`entrega/v1.2/` next to it; `entrega/v1/` is the first
release, `entrega/v1.1/` the M503 fix): the firmware, this `DWIN_SET (JARVIS)`, `jarvis_theme.gcode`,
the rollback files, a Spanish flashing README and an acceptance checklist. Nothing is flashed from
here: the user flashes and reports.
