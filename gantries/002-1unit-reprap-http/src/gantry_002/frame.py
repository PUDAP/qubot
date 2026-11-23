"""Physical frame facts for 002-1unit-reprap-http. No host, port, or machine id."""

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
