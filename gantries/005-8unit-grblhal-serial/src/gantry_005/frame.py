"""Physical frame facts for 005-8unit-grblhal-serial. No host, port, or machine id.

Intended name: Claw machine (Pick-and-place). Limits key: claw_gantry.
The frame is 2 by 4 units: 2 along Y and 4 along X.
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
