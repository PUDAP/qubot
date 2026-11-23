# 008-1unit-grblhal-serial

Photoreactor (UV qubot). Limits key: `photoreactor`.

Serial `008`, 1unit, grblHAL. Connects over serial, and can also connect over the GRBL WebSocket. An `http://` host is opened as `ws://` on port 81. Default deck is 2 rows by 2 columns (1 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.

Frame travel is X −300 to 300, Y −199 to 0, Z −78 to 0. Y travel is 199 mm, inside the 300 mm allowed for one unit. X is −300 to 300, a span of 600 mm, which is past that allowance. The uploaded X range is kept and flagged for correction.

Safety text, confirm, and startup homing are placeholders filled by the edge contract.
