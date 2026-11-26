"""Physical frame facts for 004-4unit-reprap-http. No host, port, or machine id.

Serial `004`, 4unit, reprap-http. Default deck is 4 rows by 4 columns (2 by 2 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.


Safety text, confirm, and startup homing are placeholders filled by the edge contract.
"""

SERIAL = "004"
SIZE = "4unit"
BUS = "reprap-http"
AXES = ('X', 'Y', 'Z', 'A')
HARDWARE_LIMITS = {
    "X": (0, 345),
    "Y": (-490, 0),
    "Z": (-170, 0),
    "A": (-170, 0),
}
DEFAULT_DECK = {"rows": 4, "cols": 4}


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
