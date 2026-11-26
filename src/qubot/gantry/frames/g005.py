"""Physical frame facts for 005-8unit-grblhal-serial. No host, port, or machine id.

Intended name: Claw machine (Pick-and-place). Limits key: claw_gantry.
The frame is 2 by 4 units: 2 along Y and 4 along X.

Claw machine (Pick-and-place). Limits key: `claw_gantry`.

Serial `005`, 8unit, grblHAL. The frame is 2 by 4 units: 2 along Y and 4 along X. Connects over serial, and can also connect over the GRBL WebSocket. An `http://` host is opened as `ws://` on port 81. Default deck is 4 rows by 8 columns (2 by 4 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.

Frame travel is X 0 to 830, Y −280 to 0, Z −240 to 0. One unit may travel at most 300 mm on X and on Y, so this frame may travel 1200 mm on X and 600 mm on Y. The uploaded spans are 830 mm and 280 mm, both inside that allowance.

Homing for this frame is Z, then X, then Y. The transport line ending remains CR. A claw configuration set CR LF; that conflict stays in the edge contract.

Safety text, confirm, and startup homing are placeholders filled by the edge contract. The serial controller can feed-hold with realtime `!` without taking the command lock.
"""

SERIAL = "005"
SIZE = "8unit"
BUS = "grblhal-serial"
AXES = ("X", "Y", "Z")
HARDWARE_LIMITS = {
    "X": (0, 830),
    "Y": (-280, 0),
    "Z": (-240, 0),
}
AXIS_LIMITS = HARDWARE_LIMITS
DEFAULT_DECK = {"rows": 4, "cols": 8}
# ClawMachine homes Z, then X, then Y. One $H is not the procedure for this frame.
HOME_ORDER = ("Z", "X", "Y")


def slot_names(rows: int, cols: int) -> list[str]:
    return [f"{chr(65 + row)}{col + 1}" for row in range(rows) for col in range(cols)]


def apply_axis_limits(controller, limits: dict | None = None) -> None:
    """Apply limits that sit inside this frame. None uses the hardware limits."""
    chosen = HARDWARE_LIMITS if limits is None else limits
    for axis, bounds in chosen.items():
        if axis not in HARDWARE_LIMITS:
            raise ValueError(f"Axis {axis} is not on this frame")
        low, high = bounds
        hard_low, hard_high = HARDWARE_LIMITS[axis]
        if low < hard_low or high > hard_high or low > high:
            raise ValueError(
                f"{axis} limits {bounds} are outside the frame {HARDWARE_LIMITS[axis]}"
            )
        controller.set_axis_limits(axis, low, high)
