"""Physical frame facts for 001-1unit-grbl-serial. No host, port, or machine id.

Serial `001`, 1unit, grbl-serial. Default deck is 2 rows by 2 columns (1 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.


Safety text, confirm, and startup homing are placeholders filled by the edge contract.
"""

SERIAL = "001"
SIZE = "1unit"
BUS = "grbl-serial"
AXES = ('X', 'Y', 'Z')
HARDWARE_LIMITS = {
    "X": (0.0, 175.0),
    "Y": (-190.0, 0.0),
    "Z": (-75.0, 0.0),
}
AXIS_LIMITS = HARDWARE_LIMITS
DEFAULT_DECK = {"rows": 2, "cols": 2}

EXPECTED_IDENTITY = "[VER:1.1h.20190830:]"
REQUIRED_SETTINGS = {20: 1.0, 21: 1.0, 22: 1.0, 23: 1.0, 130: 175.0, 131: 190.0, 132: 75.0}


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
