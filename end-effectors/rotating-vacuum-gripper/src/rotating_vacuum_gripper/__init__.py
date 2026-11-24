"""Rotating vacuum gripper. Commands are GRBL lines on the gantry port."""

AXIS = "C"
COMMUNICATION = "gantry"
PORT_ENV = ""
YAW_MIN_DEG = -180.0
YAW_MAX_DEG = 0.0
DEGREE_000 = 14
DEGREE_090 = 124
DEGREE_180 = 244
VACUUM_ON_DELAY_S = 3.0
VACUUM_OFF_DELAY_S = 3.0
ROTATION_MIN_Z_MM = -5.0
VALVE_ON = "M8"
VALVE_OFF = "M9"

_CALIBRATED = (
    (0.0, DEGREE_000),
    (-90.0, DEGREE_090),
    (-180.0, DEGREE_180),
)


def pulse_for_yaw(yaw_deg: float) -> int:
    """Return the servo pulse for a yaw in degrees.

    Raises:
        ValueError: If yaw is outside −180° to 0°.
    """
    yaw = float(yaw_deg)
    if yaw < YAW_MIN_DEG or yaw > YAW_MAX_DEG:
        raise ValueError(f"Yaw {yaw}° is outside [{YAW_MIN_DEG}, {YAW_MAX_DEG}]")
    for index, (start_deg, start_pulse) in enumerate(_CALIBRATED[:-1]):
        end_deg, end_pulse = _CALIBRATED[index + 1]
        if (end_deg <= yaw <= start_deg) or yaw == start_deg:
            span = start_deg - end_deg
            fraction = (start_deg - yaw) / span
            return int(round(start_pulse + fraction * (end_pulse - start_pulse)))
    raise ValueError(f"Yaw {yaw}° is outside the calibrated map")


def servo_command(yaw_deg: float) -> str:
    """GRBL spindle line for this yaw. The gantry transport appends its line ending."""
    return f"M3 S{pulse_for_yaw(yaw_deg)}"


def valve_command(on: bool) -> tuple[str, float]:
    """Return the coolant-valve line and the delay in seconds."""
    if on:
        return VALVE_ON, VACUUM_ON_DELAY_S
    return VALVE_OFF, VACUUM_OFF_DELAY_S


def require_rotation_height(z_mm: float) -> None:
    """Refuse rotation when the cup is below the robot-frame safe height.

    Raises:
        RuntimeError: If Z is below −5 mm.
    """
    if float(z_mm) < ROTATION_MIN_Z_MM:
        raise RuntimeError(
            f"Z {z_mm} mm is below {ROTATION_MIN_Z_MM} mm. "
            "Raise the claw before rotating."
        )


__all__ = [
    "AXIS",
    "COMMUNICATION",
    "DEGREE_000",
    "DEGREE_090",
    "DEGREE_180",
    "PORT_ENV",
    "ROTATION_MIN_Z_MM",
    "VACUUM_OFF_DELAY_S",
    "VACUUM_ON_DELAY_S",
    "VALVE_OFF",
    "VALVE_ON",
    "YAW_MAX_DEG",
    "YAW_MIN_DEG",
    "pulse_for_yaw",
    "require_rotation_height",
    "servo_command",
    "valve_command",
]
