# 006-1unit-grblhal-serial

Dancefloor (Vacuum chamber). Limits key: `vacuum_chamber`.

Serial `006`, 1unit, grblHAL. Connects over serial, and can also connect over the GRBL WebSocket. An `http://` host is opened as `ws://` on port 81. Default deck is 2 rows by 2 columns (1 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.

Frame travel is X −116 to 0, Y −28 to 0, Z 0 to 0. Z has no travel. X travel is 116 mm and Y travel is 28 mm, both inside the 300 mm allowed for one unit. The limits file names a port placeholder `__dancefloor__`. That value is not stored in this package.

Safety text, confirm, and startup homing are placeholders filled by the edge contract.
