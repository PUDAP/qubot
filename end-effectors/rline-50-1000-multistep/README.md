# rline-50-1000-multistep

Sartorius rLine 50-1000 µL body, 2.5 µL/step. Manual v1.1 Table 1: home 30, max 443, tip eject −40. The six preset speeds are 150, 265, 410, 650, 945, and 1120 µL/s. This is not the 5-200 µL body (0.5 µL/step) and not the 100-5000 µL body (10 µL/step).

`aspirate` and `dispense` take `speed_ul_s`. A preset speed is one `RI` or `RO`. Any other positive speed uses a faster preset, split into several moves. The pause after each move makes the transfer take `volume / speed` seconds. `step_resolution` (default 10 steps) and `response_time_s` (default 1.03 s) are the controllably Sartorius calibrations: the smallest step that keeps the volume error tolerable, and the shortest command round-trip the plan is allowed to assume. A speed this calibration cannot hit raises. Nothing faster than 1120 µL/s is possible.

A dispense of the whole tracked volume paces those outward steps and then sends `RB`.

Axis Z, serial `SATORIUS_PORT`. No host address is stored here. `rline-50-1000` is unchanged.
