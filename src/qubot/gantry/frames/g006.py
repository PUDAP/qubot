"""Physical frame facts for 006-1unit-grblhal-serial. No host, port, or machine id.

Intended name: Dancefloor (Vacuum chamber). Limits key: vacuum_chamber.

Dancefloor (Vacuum chamber). Limits key: `vacuum_chamber`.

Serial `006`, 1unit, grblHAL. Connects over serial, and can also connect over the GRBL WebSocket. An `http://` host is opened as `ws://` on port 81. Default deck is 2 rows by 2 columns (1 by 1 units of 2x2). Hardware limits are frame travel. Slot origins, host addresses, and machine ids are not stored here.

Frame travel is X −116 to 0, Y −28 to 0, Z 0 to 0. Z has no travel. X travel is 116 mm and Y travel is 28 mm, both inside the 300 mm allowed for one unit. The combined pescador2 config says X low is −119. This package keeps −116. The chamber loading position X=−118 is outside this frame until that conflict is confirmed. The limits file names a port placeholder `__dancefloor__`. That value is not stored in this package.

Safety text, confirm, and startup homing are placeholders filled by the edge contract. The serial controller can feed-hold with realtime `!` without taking the command lock. Z has no travel, so a safe-Z lift is not inside this frame.
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
AXIS_LIMITS = HARDWARE_LIMITS
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
