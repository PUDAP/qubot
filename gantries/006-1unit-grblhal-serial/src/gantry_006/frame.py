"""Physical frame facts for 006-1unit-grblhal-serial. No host, port, or machine id.

Intended name: Dancefloor (Vacuum chamber). Limits key: vacuum_chamber.
"""

SERIAL = "006"
SIZE = "1unit"
BUS = "grblhal-serial"
AXES = ("X", "Y", "Z")
HARDWARE_LIMITS = {
    "X": (-116, 0),
    "Y": (-28, 0),
    "Z": (0, 0),
}
DEFAULT_DECK = {"rows": 2, "cols": 2}
# pescador2 says X low is -119. The loading position X=-118 needs that wider span.
# This frame keeps the dancefloor-alone value -116 until that conflict is confirmed.
LIMITS_CONFLICT = (
    "pescador2 config X low is -119. This frame keeps the dancefloor-alone value -116. "
    "The chamber loading position X=-118 is outside this frame until the limit is confirmed."
)


def slot_names(rows: int, cols: int) -> list[str]:
    return [f"{chr(65 + row)}{col + 1}" for row in range(rows) for col in range(cols)]


def apply_axis_limits(controller, limits: dict | None = None) -> None:
    """Apply limits that sit inside this frame. None uses the hardware limits.

    Z is the point 0. The transport rejects a zero-length window, and an unset
    axis is already 0 to 0, so that axis is not pushed to the controller.
    """
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
        if low == high:
            if (low, high) != (hard_low, hard_high):
                raise ValueError(
                    f"{axis} limits {bounds} have no travel inside the frame {HARDWARE_LIMITS[axis]}"
                )
            continue
        controller.set_axis_limits(axis, low, high)
