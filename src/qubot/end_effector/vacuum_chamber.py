"""Vacuum-chamber valve and lid waypoints. Motion is performed by the gantry.

The valve is a coolant line on the gantry port; there is no second port. The edge
configures the positions and delays for its chamber::

    chamber = Chamber(
        loading_position=(...),
        close_waypoints=[(...), (...)],
        vacuum_on_delay_s=...,
        vacuum_off_delay_s=...,
    )

Evacuation is refused unless the chamber is marked closed. Motion is refused
while it is marked closed. Homing vents first when the chamber is not marked vented.
"""

from __future__ import annotations

from typing import Sequence

COMMUNICATION = "gantry"

Point = tuple[float, float, float]


def _point(value: Sequence[float]) -> Point:
    if len(value) != 3:
        raise ValueError(f"expected an (x, y, z) point, got {value!r}")
    x, y, z = (float(item) for item in value)
    return (x, y, z)


class Chamber:
    """Closed and vented flags for one chamber. Starts open and vented."""

    def __init__(
        self,
        *,
        loading_position: Sequence[float],
        close_waypoints: Sequence[Sequence[float]],
        vacuum_on_delay_s: float,
        vacuum_off_delay_s: float,
        valve_on: str = "M8",
        valve_off: str = "M9",
    ) -> None:
        if not close_waypoints:
            raise ValueError("close_waypoints is empty")
        if vacuum_on_delay_s < 0 or vacuum_off_delay_s < 0:
            raise ValueError("vacuum delays must be zero or positive")
        self.loading_position_mm = _point(loading_position)
        self.close_path = tuple(_point(point) for point in close_waypoints)
        self.vacuum_on_delay_s = float(vacuum_on_delay_s)
        self.vacuum_off_delay_s = float(vacuum_off_delay_s)
        self.valve_on = valve_on
        self.valve_off = valve_off
        self.closed = False
        self.vented = True

    def close_waypoints(self) -> list[Point]:
        """Waypoints to close the lid.

        Raises:
            RuntimeError: If the chamber is already marked closed.
        """
        if self.closed:
            raise RuntimeError("Chamber is already closed")
        return list(self.close_path)

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
        return self.valve_on, self.vacuum_on_delay_s

    def vent(self) -> tuple[str, float]:
        """Valve line and delay for releasing vacuum."""
        self.vented = True
        return self.valve_off, self.vacuum_off_delay_s

    def require_motion(self) -> None:
        """Refuse travel while the lid is marked closed.

        Raises:
            RuntimeError: If the chamber is marked closed.
        """
        if self.closed:
            raise RuntimeError("Chamber is closed. Home it before moving.")

    def mark_homed(self) -> None:
        self.closed = False

    def snapshot(self) -> dict:
        """Lid and vent flags from the last close, home, evacuate, or vent command."""
        return {
            "closed": self.closed,
            "vented": self.vented,
            "source": "last_command",
        }

    def loading_position(self, x_limits: tuple[float, float]) -> Point:
        """Return the loading position when it sits inside the frame X span.

        Raises:
            RuntimeError: If the loading X is outside the gantry frame.
        """
        low, high = x_limits
        x_mm = self.loading_position_mm[0]
        if x_mm < low or x_mm > high:
            raise RuntimeError(
                f"Loading position X={x_mm} mm is outside frame X {(low, high)}. "
                "Confirm the frame limits before moving to the loading position."
            )
        return self.loading_position_mm


__all__ = ["COMMUNICATION", "Chamber"]
