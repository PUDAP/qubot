"""Physical frame facts for 002-1unit-reprap-http. No host, port, or machine id.

Serial `002`, 1unit, reprap-http. Default deck is 2 rows by 2 columns (1 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.
 The RepRap HTTP driver includes `set_pin`.

Firmware travel is X 0 to 140, Y -170 to 0, Z -175 to 0. A later observation that Z past -125 meets the current vial holder is not stored as a limit.
Safety text, confirm, and startup homing are placeholders filled by the edge contract.
"""

SERIAL = "002"
SIZE = "1unit"
BUS = "reprap-http"
AXES = ('X', 'Y', 'Z')
HARDWARE_LIMITS = {
    "X": (0.0, 140.0),
    "Y": (-170.0, 0.0),
    # Firmware travel. A syringe-plus-holder clearance is recorded on the effector, not here.
    "Z": (-175.0, 0.0),
}
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
