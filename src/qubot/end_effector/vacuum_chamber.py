"""Vacuum-chamber valve and lid waypoints. Motion is performed by the gantry.

Dancefloor lid and vacuum valve. The valve is `M8` / `M9` on the gantry port. There is no second port. On and off delays are 5 s.

Close waypoints, robot frame: (−3, 0, 0) then (−3, −27, 0). Loading position: (−118, 0, 0). Evacuation is refused unless the chamber is marked closed. Motion is refused while it is marked closed. Homing vents first when the chamber is not marked vented.

The loading position is outside gantry 006's X limit of −116. `loading_position` raises against that frame. The pescador2 config uses X low −119. The edge contract carries that question.
"""

LOADING_POSITION = (-118.0, 0.0, 0.0)
CLOSE_WAYPOINTS = ((-3.0, 0.0, 0.0), (-3.0, -27.0, 0.0))
VACUUM_ON_DELAY_S = 5.0
VACUUM_OFF_DELAY_S = 5.0
VALVE_ON = "M8"
VALVE_OFF = "M9"
AXIS = ""
COMMUNICATION = "gantry"
PORT_ENV = ""


class Chamber:
    """Closed and vented flags for one chamber. Starts open and vented."""

    def __init__(self) -> None:
        self.closed = False
        self.vented = True

    def close_waypoints(self) -> list[tuple[float, float, float]]:
        """Waypoints to close the lid.

        Raises:
            RuntimeError: If the chamber is already marked closed.
        """
        if self.closed:
            raise RuntimeError("Chamber is already closed")
        return list(CLOSE_WAYPOINTS)

    def mark_closed(self) -> None:
        self.closed = True

    def evacuate(self) -> tuple[str, float]:
        """Valve line and delay for pulling vacuum.

        Raises:
            RuntimeError: If the lid is not marked closed.
        """
        if not self.closed:
            raise RuntimeError("Close the chamber before evacuating")
        self.vented = False
        return VALVE_ON, VACUUM_ON_DELAY_S

    def vent(self) -> tuple[str, float]:
        """Valve line and delay for releasing vacuum."""
        self.vented = True
        return VALVE_OFF, VACUUM_OFF_DELAY_S

    def require_motion(self) -> None:
        """Refuse travel while the lid is marked closed.

        Raises:
            RuntimeError: If the chamber is marked closed.
        """
        if self.closed:
            raise RuntimeError("Chamber is closed. Home it before moving.")

    def mark_homed(self) -> None:
        self.closed = False

    def loading_position(self, x_limits: tuple[float, float]) -> tuple[float, float, float]:
        """Return the loading position when it sits inside the frame X span.

        Raises:
            RuntimeError: If X=−118 is outside the gantry frame.
        """
        low, high = x_limits
        x_mm = LOADING_POSITION[0]
        if x_mm < low or x_mm > high:
            raise RuntimeError(
                f"Loading position X={x_mm} mm is outside frame X {(low, high)}. "
                "pescador2 uses X low -119 and this gantry frame keeps -116. "
                "Confirm the frame before moving to the loading position."
            )
        return LOADING_POSITION


__all__ = [
    "AXIS",
    "CLOSE_WAYPOINTS",
    "COMMUNICATION",
    "Chamber",
    "LOADING_POSITION",
    "PORT_ENV",
    "VACUUM_OFF_DELAY_S",
    "VACUUM_ON_DELAY_S",
    "VALVE_OFF",
    "VALVE_ON",
]
