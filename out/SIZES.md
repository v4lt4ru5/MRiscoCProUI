| fecha | cfg | bytes | libres | nota |
|---|---|---|---|---|
| 2026-10-18 14:25 | MM | 181728 | 31264 | HC32_MM-20261018.bin |
| 2026-10-18 14:51 | X2-JARVIS | 182256 | 30736 | X2-JARVIS base |
| 2026-10-18 15:23 | X2-JARVIS | 182260 | 30732 | JARVIS_PALETTE, +4 B vs X2-JARVIS base |
| 2026-10-18 15:50 | X2-JARVIS | 182260 | 30732 | dwin_set.h JV ids, +0 B vs JARVIS_PALETTE |
| 2026-10-18 18:10 | X2-JARVIS | 182260 | 30732 | R14 StatusBg/PopupBg (0,6,3), +0 B vs dwin_set.h JV ids |
| 2026-10-18 18:12 | X2-JARVIS | 182396 | 30596 | JARVIS_BOOT, +136 B vs R14 (Init() kept for the Info screen) |
| 2026-10-18 18:14 | X2-JARVIS | 182396 | 30596 | JARVIS_BOOT_JPG trial (not committed), +0 B vs JARVIS_BOOT |
| 2026-10-18 18:15 | X2-JARVIS | 182260 | 30732 | JARVIS_BOOT off check (trial), same bytes as R14 but the build time |
| 2026-10-18 18:40 | X2-JARVIS | 182380 | 30612 | JARVIS_TITLE, -16 B vs JARVIS_BOOT |
| 2026-10-18 18:42 | X2-JARVIS | 182292 | 30700 | JARVIS_CURSOR, -88 B vs JARVIS_TITLE (GCC drops the out-of-line DWINUI::Draw_Box) |
| 2026-10-18 18:44 | X2-JARVIS | 182240 | 30752 | JARVIS_GAUGES, -52 B vs JARVIS_CURSOR |
| 2026-10-18 18:46 | X2-JARVIS | 182176 | 30816 | JARVIS_DASH_FRAME incl. flow % fix, -64 B vs JARVIS_GAUGES |
| 2026-10-18 18:48 | X2-JARVIS | 182396 | 30596 | TITLE/CURSOR/GAUGES/DASH_FRAME off check (trial), same bytes as JARVIS_BOOT but the build time |
| 2026-10-18 18:55 | X2-JARVIS | 182272 | 30720 | JARVIS_FANBAR trial (define stays commented), +96 B vs JARVIS_DASH_FRAME |
| 2026-10-18 19:12 | X2-JARVIS | 182176 | 30816 | v1 release build |
| 2026-10-24 19:52 | X2-JARVIS | 182064 | 30928 | v1.1 M503 hardfault + runout pin fix |
| 2026-10-24 21:16 | MM | 181616 | 31376 | MM at v1.1 (3b610cca0), baseline for the v1.2 guard check |
| 2026-10-24 21:27 | X2-JARVIS | 182040 | 30952 | trial: v1.2 tree with JARVIS_TRAM_FROM_MESH off (not committed), -24 B vs v1.1: mesh_max no longer set at boot (-40 B code, +8 B data), C851 EOL +8 B |
| 2026-10-24 21:28 | MM | 181624 | 31368 | MM at the v1.2 tree, guard check vs MM v1.1 (not a release), +8 B = the C851 EOL only |
| 2026-10-24 21:35 | X2-JARVIS | 184488 | 28504 | v1.2 tram from mesh, clip insets, C851 EOL; JARVIS_TRAM_FROM_MESH +2448 B vs the trial, +2424 B vs v1.1 |
| 2026-10-24 22:38 | X2-JARVIS | 184488 | 28504 | v1.2 fix round 1 (kit build): C115 EOL + Tramming menu size 11, same image size as the 21:35 build (custom_gcode -4 B, absorbed by alignment) |
| 2026-10-24 22:40 | MM | 181616 | 31376 | MM at v1.2 fix round 1 (not a release), guard check vs MM v1.1: same size, only the C851/C115 EOL code differs |
