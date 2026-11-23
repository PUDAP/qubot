# 005-8unit-grblhal-serial

Claw machine (Pick-and-place). Limits key: `claw_gantry`.

Serial `005`, 8unit, grblHAL. The frame is 2 by 4 units: 2 along Y and 4 along X. Connects over serial, and can also connect over the GRBL WebSocket. An `http://` host is opened as `ws://` on port 81. Default deck is 4 rows by 8 columns (2 by 4 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.

Frame travel is X 0 to 830, Y −280 to 0, Z −240 to 0. One unit may travel at most 300 mm on X and on Y, so this frame may travel 1200 mm on X and 600 mm on Y. The uploaded spans are 830 mm and 280 mm, both inside that allowance.

Safety text, confirm, and startup homing are placeholders filled by the edge contract.
