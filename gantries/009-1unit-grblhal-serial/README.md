# 009-1unit-grblhal-serial

EIS Qubot (Electrochemical station). Limits key: `eis_qubot`.

Serial `009`, 1unit, grblHAL. Connects over serial, and can also connect over the GRBL WebSocket. An `http://` host is opened as `ws://` on port 81. Default deck is 2 rows by 2 columns (1 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.

Frame travel is X −300 to 300, Y −199 to 0, Z −300 to 300. Y travel is 199 mm, inside the 300 mm allowed for one unit. X is −300 to 300, a span of 600 mm, which is past that allowance. Z is the same −300 to 300 figure. The 300 mm rule covers X and Y; Z is flagged with X. Both uploaded ranges are kept for correction.

Safety text, confirm, and startup homing are placeholders filled by the edge contract.
