"""Physical frame facts for 009-1unit-grblhal-serial. No host, port, or machine id.

Intended name: EIS Qubot (Electrochemical station). Limits key: eis_qubot.

EIS Qubot (Electrochemical station). Limits key: `eis_qubot`.

Serial `009`, 1unit, grblHAL. Connects over serial, and can also connect over the GRBL WebSocket. An `http://` host is opened as `ws://` on port 81. Default deck is 2 rows by 2 columns (1 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.

Frame travel is X −300 to 300, Y −199 to 0, Z −300 to 300. Y travel is 199 mm, inside the 300 mm allowed for one unit. X is −300 to 300, a span of 600 mm, which is past that allowance. Z is the same −300 to 300 figure. The 300 mm rule covers X and Y; Z is flagged with X. Both uploaded ranges are kept for correction.

Safety text, confirm, and startup homing are placeholders filled by the edge contract. The serial controller can feed-hold with realtime `!` without taking the command lock.
"""

SERIAL = "009"
SIZE = "1unit"
BUS = "grblhal-serial"
AXES = ("X", "Y", "Z")
HARDWARE_LIMITS = {
    "X": (-300, 300),
    "Y": (-199, 0),
    "Z": (-300, 300),
}
# Kept as uploaded. A 1-unit frame may travel at most 300 mm on X and on Y.
TRAVEL_CORRECTIONS = (
    "X is −300 to 300, a span of 600 mm, past the 300 mm allowed for 1 unit.",
    "Z is −300 to 300, the same uploaded figure. The 300 mm rule covers X and Y; Z is flagged with X.",
)
AXIS_LIMITS = HARDWARE_LIMITS
DEFAULT_DECK = {"rows": 2, "cols": 2}


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
