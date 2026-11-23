"""Physical frame facts for 008-1unit-grblhal-serial. No host, port, or machine id.

Intended name: Photoreactor (UV qubot). Limits key: photoreactor.
"""

SERIAL = "008"
SIZE = "1unit"
BUS = "grblhal-serial"
AXES = ("X", "Y", "Z")
HARDWARE_LIMITS = {
    "X": (-300, 300),
    "Y": (-199, 0),
    "Z": (-78, 0),
}
# Kept as uploaded. A 1-unit frame may travel at most 300 mm on X and on Y.
TRAVEL_CORRECTIONS = (
    "X is −300 to 300, a span of 600 mm, past the 300 mm allowed for 1 unit.",
)
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
