"""Physical frame facts for 007-2unit-grblhal-serial. No host, port, or machine id.

Intended name: Overkill2 (Liquid handling - pipette gantry). Limits key: pipQubot.

Overkill2 (Liquid handling - pipette gantry). Limits key: `pipQubot`.

Serial `007`, 2unit, grblHAL. Connects over serial, and can also connect over the GRBL WebSocket. An `http://` host is opened as `ws://` on port 81. Default deck is 4 rows by 2 columns (2 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.

Frame travel is X −176 to 0, Y −480 to 0, Z −190 to 0. The frame is 2 by 1 units, so X may travel at most 300 mm and Y at most 600 mm. The uploaded spans are 176 mm and 480 mm, both inside that allowance.

Safety text, confirm, and startup homing are placeholders filled by the edge contract. The serial controller can feed-hold with realtime `!` without taking the command lock.
"""

SERIAL = "007"
SIZE = "2unit"
BUS = "grblhal-serial"
AXES = ("X", "Y", "Z")
HARDWARE_LIMITS = {
    "X": (-176, 0),
    "Y": (-480, 0),
    "Z": (-190, 0),
}
AXIS_LIMITS = HARDWARE_LIMITS
DEFAULT_DECK = {"rows": 4, "cols": 2}


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
