"""Rotating vacuum gripper. Commands are GRBL lines on the gantry port.

A vacuum cup on the coolant valve and a yaw servo on the spindle PWM. The edge
configures the calibration for its gripper::

    gripper = RotatingVacuumGripper(
        axis="C",
        yaw_pulses=[(0, ...), (-90, ...), (-180, ...)],
        rotation_min_z_mm=...,
        vacuum_on_delay_s=...,
        vacuum_off_delay_s=...,
    )

``yaw_pulses`` are calibrated ``(degrees, pulse)`` points. Yaw is limited to the
span they cover and in-between angles are linear on the enclosing segment.
Emergency stop of the gantry does not vent the cup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

COMMUNICATION = "gantry"


@dataclass(frozen=True)
class RotatingVacuumGripper:
    axis: str
    yaw_pulses: Sequence[tuple[float, int]]
    rotation_min_z_mm: float
    vacuum_on_delay_s: float
    vacuum_off_delay_s: float
    valve_on: str = "M8"
    valve_off: str = "M9"

    def __post_init__(self) -> None:
        points = tuple(sorted(((float(deg), int(pulse)) for deg, pulse in self.yaw_pulses), reverse=True))
        if len(points) < 2:
            raise ValueError("yaw_pulses needs at least two calibrated points")
        if len({deg for deg, _ in points}) != len(points):
            raise ValueError("yaw_pulses has a repeated angle")
        if self.vacuum_on_delay_s < 0 or self.vacuum_off_delay_s < 0:
            raise ValueError("vacuum delays must be zero or positive")
        object.__setattr__(self, "yaw_pulses", points)

    @property
    def yaw_min_deg(self) -> float:
        return self.yaw_pulses[-1][0]

    @property
    def yaw_max_deg(self) -> float:
        return self.yaw_pulses[0][0]

    def pulse_for_yaw(self, yaw_deg: float) -> int:
        """Servo pulse for a yaw in degrees.

        Raises:
            ValueError: If yaw is outside the calibrated span.
        """
        yaw = float(yaw_deg)
        if yaw < self.yaw_min_deg or yaw > self.yaw_max_deg:
            raise ValueError(f"Yaw {yaw}° is outside [{self.yaw_min_deg}, {self.yaw_max_deg}]")
        for (start_deg, start_pulse), (end_deg, end_pulse) in zip(self.yaw_pulses, self.yaw_pulses[1:]):
            if end_deg <= yaw <= start_deg:
                fraction = (start_deg - yaw) / (start_deg - end_deg)
                return int(round(start_pulse + fraction * (end_pulse - start_pulse)))
        raise ValueError(f"Yaw {yaw}° is outside the calibrated map")

    def servo_command(self, yaw_deg: float) -> str:
        """GRBL spindle line for this yaw. The gantry transport appends its line ending."""
        return f"M3 S{self.pulse_for_yaw(yaw_deg)}"

    def valve_command(self, on: bool) -> tuple[str, float]:
        """Coolant-valve line and the delay in seconds."""
        if on:
            return self.valve_on, float(self.vacuum_on_delay_s)
        return self.valve_off, float(self.vacuum_off_delay_s)

    def require_rotation_height(self, z_mm: float) -> None:
        """Refuse rotation when the cup is below the configured safe height.

        Raises:
            RuntimeError: If Z is below ``rotation_min_z_mm``.
        """
        if float(z_mm) < self.rotation_min_z_mm:
            raise RuntimeError(
                f"Z {z_mm} mm is below {self.rotation_min_z_mm} mm. Raise the gripper before rotating."
            )


__all__ = ["COMMUNICATION", "RotatingVacuumGripper"]
