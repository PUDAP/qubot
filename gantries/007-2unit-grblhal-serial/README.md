# 007-2unit-grblhal-serial

Overkill2 (Liquid handling - pipette gantry). Limits key: `pipQubot`.

Serial `007`, 2unit, grblHAL. Connects over serial, and can also connect over the GRBL WebSocket. An `http://` host is opened as `ws://` on port 81. Default deck is 4 rows by 2 columns (2 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.

Frame travel is X −176 to 0, Y −480 to 0, Z −190 to 0. The frame is 2 by 1 units, so X may travel at most 300 mm and Y at most 600 mm. The uploaded spans are 176 mm and 480 mm, both inside that allowance.

Safety text, confirm, and startup homing are placeholders filled by the edge contract. The serial controller can feed-hold with realtime `!` without taking the command lock.
