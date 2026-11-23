# 002-1unit-reprap-http

Serial `002`, 1unit, reprap-http. Default deck is 2 rows by 2 columns (1 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.
 The RepRap HTTP driver includes `set_pin`.

Firmware travel is X 0 to 140, Y -170 to 0, Z -175 to 0. A later observation that Z past -125 meets the current vial holder is not stored as a limit.
Safety text, confirm, and startup homing are placeholders filled by the edge contract.
