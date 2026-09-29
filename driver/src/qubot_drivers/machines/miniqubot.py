"""MiniQubot machine: one GRBL gantry with an empty moving head."""

import math

from puda import command, safety
from qubot_drivers.move.grblHAL import GrblHALController
from qubot_drivers.position import Position

EXPECTED_IDENTITY = "[VER:1.1h.20190830:]"
REQUIRED_SETTINGS = {
    20: 1.0,
    21: 1.0,
    22: 1.0,
    23: 1.0,
    130: 175.0,
    131: 190.0,
    132: 75.0,
}
AXIS_LIMITS = {
    "X": (0.0, 175.0),
    "Y": (-190.0, 0.0),
    "Z": (-75.0, 0.0),
}
POSITION_TOLERANCE_MM = 0.01
MAX_MOVE_TIMEOUT_S = 300
XY_FEED_MM_MIN = 1500.0
Z_FEED_MM_MIN = 200.0


def _parse_settings(response: str) -> dict[int, float]:
    settings: dict[int, float] = {}
    for line in response.splitlines():
        stripped = line.strip()
        if not stripped.startswith("$") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        settings[int(key[1:])] = float(value)
    return settings


class MiniQubot:
    """Three-axis empty-head Qubot on a GRBL serial controller."""

    def __init__(
        self,
        qubot_port: str | None = None,
        *,
        controller: GrblHALController | None = None,
    ) -> None:
        if controller is None:
            if qubot_port is None:
                raise ValueError("qubot_port is required")
            controller = GrblHALController(
                port_name=qubot_port,
                baudrate=115200,
                timeout=90,
            )
        self.qubot = controller
        self._homed = False

    def startup(self) -> None:
        """Connect, check identity and settings, then home all axes."""
        self.qubot.connect()
        self._homed = False
        identity = self.qubot.get_info()
        if EXPECTED_IDENTITY not in identity:
            raise RuntimeError(
                f"Controller identity does not match {EXPECTED_IDENTITY}: {identity!r}"
            )
        settings = _parse_settings(self.qubot.execute("$$"))
        mismatches = {
            number: {"expected": expected, "actual": settings.get(number)}
            for number, expected in REQUIRED_SETTINGS.items()
            if settings.get(number) is None
            or abs(settings[number] - expected) > 1e-6
        }
        if mismatches:
            raise RuntimeError(f"GRBL settings mismatch: {mismatches}")
        for axis, (minimum, maximum) in AXIS_LIMITS.items():
            self.qubot.set_axis_limits(axis, minimum, maximum)
        self.home()

    def shutdown(self) -> None:
        """Close the serial port and drop same-session homing."""
        self.qubot.disconnect()
        self._homed = False

    @command
    def home(self) -> dict[str, float]:
        """
        Home all axes and require Idle at controller-reported zero.

        Returns:
            dict[str, float]: Controller-reported XYZ machine position in millimeters.
        """
        self.qubot.home(verify_origin=True)
        self._homed = True
        return self.get_position()

    @command
    @safety(
        summary="Absolute XYZ motion can collide. The controller reports no lost-step feedback.",
        hazards=["collision", "lost-steps"],
        requires="Home in this connection and keep the motor-power cutoff reachable.",
        forbidden_when="Do not move while the controller is disconnected, alarmed, or busy.",
        confirm=True,
    )
    def move_absolute(
        self,
        x_mm: float,
        y_mm: float,
        z_mm: float,
        feed_mm_min: float | None = None,
    ) -> dict[str, float]:
        """
        Move to one absolute XYZ position.

        Args:
            x_mm: X target in millimeters.
            y_mm: Y target in millimeters.
            z_mm: Z target in millimeters.
            feed_mm_min: Speed in millimeters per minute. Omitted uses 1500 for
                XY and 200 for Z. A given value is sent unchanged.

        Returns:
            dict[str, float]: Controller-reported XYZ position after the move.
        """
        return self._move_to(
            x_mm=x_mm,
            y_mm=y_mm,
            z_mm=z_mm,
            feed_mm_min=feed_mm_min,
        )

    @command
    @safety(
        summary="Relative XYZ motion can collide. The controller reports no lost-step feedback.",
        hazards=["collision", "lost-steps"],
        requires="Home in this connection and keep the motor-power cutoff reachable.",
        forbidden_when="Do not move while the controller is disconnected, alarmed, or busy.",
        confirm=True,
    )
    def move_relative(
        self,
        dx_mm: float,
        dy_mm: float,
        dz_mm: float,
        feed_mm_min: float | None = None,
    ) -> dict[str, float]:
        """
        Move by one XYZ delta from a fresh controller position.

        Args:
            dx_mm: X displacement in millimeters.
            dy_mm: Y displacement in millimeters.
            dz_mm: Z displacement in millimeters.
            feed_mm_min: Speed in millimeters per minute. Omitted uses each
                axis maximum. A given value is sent unchanged.

        Returns:
            dict[str, float]: Controller-reported XYZ position after the move.
        """
        current = self.qubot.read_status().position
        return self._move_to(
            x_mm=current.x + dx_mm,
            y_mm=current.y + dy_mm,
            z_mm=current.z + dz_mm,
            feed_mm_min=feed_mm_min,
        )

    @command
    def get_position(self) -> dict[str, float]:
        """
        Read controller-reported XYZ machine position.

        Returns:
            dict[str, float]: X, Y, and Z in millimeters.
        """
        position = self.qubot.read_status().position
        return {"x": position.x, "y": position.y, "z": position.z}

    def _move_to(
        self,
        *,
        x_mm: float,
        y_mm: float,
        z_mm: float,
        feed_mm_min: float | None,
    ) -> dict[str, float]:
        if not self._homed:
            raise RuntimeError("Cannot move: machine is not homed in this connection")
        if feed_mm_min is not None:
            feed_mm_min = float(feed_mm_min)
            if not math.isfinite(feed_mm_min) or feed_mm_min <= 0:
                raise ValueError("feed_mm_min must be finite and greater than 0")
        for label, value in (("x_mm", x_mm), ("y_mm", y_mm), ("z_mm", z_mm)):
            if not math.isfinite(float(value)):
                raise ValueError(f"{label} must be finite")

        current = self.qubot.read_status()
        if current.state != "Idle":
            raise RuntimeError(f"Cannot move: controller state is {current.state}")
        x_mm, y_mm, z_mm = float(x_mm), float(y_mm), float(z_mm)
        legs = self._motion_legs(
            current.position.x,
            current.position.y,
            current.position.z,
            x_mm,
            y_mm,
            z_mm,
            feed_mm_min,
        )
        try:
            report = current
            for leg_x, leg_y, leg_z, leg_feed in legs:
                distance_mm = math.dist(
                    (report.position.x, report.position.y, report.position.z),
                    (leg_x, leg_y, leg_z),
                )
                timeout_s = max(10, math.ceil(distance_mm / leg_feed * 60.0 + 10.0))
                if timeout_s > MAX_MOVE_TIMEOUT_S:
                    raise ValueError(
                        "Requested move exceeds the maximum operation deadline"
                    )
                self.qubot.move_absolute(
                    Position(x=leg_x, y=leg_y, z=leg_z),
                    feed=leg_feed,
                    apply_safe_z=False,
                    timeout=timeout_s,
                )
                report = self.qubot.read_status()
        except Exception:
            self._homed = False
            raise

        if report.state != "Idle" or any(
            abs(getattr(report.position, axis) - target) > POSITION_TOLERANCE_MM
            for axis, target in (("x", float(x_mm)), ("y", float(y_mm)), ("z", float(z_mm)))
        ):
            self._homed = False
            raise RuntimeError(
                "Move finished away from the requested target: "
                f"state={report.state}, position={report.position}"
            )
        return {"x": report.position.x, "y": report.position.y, "z": report.position.z}

    @staticmethod
    def _motion_legs(
        current_x: float,
        current_y: float,
        current_z: float,
        x_mm: float,
        y_mm: float,
        z_mm: float,
        feed_mm_min: float | None,
    ) -> list[tuple[float, float, float, float]]:
        """XY first, then Z. An omitted feed uses each axis maximum."""
        xy_feed = XY_FEED_MM_MIN if feed_mm_min is None else feed_mm_min
        z_feed = Z_FEED_MM_MIN if feed_mm_min is None else feed_mm_min
        xy_changes = (
            abs(x_mm - current_x) > POSITION_TOLERANCE_MM
            or abs(y_mm - current_y) > POSITION_TOLERANCE_MM
        )
        z_changes = abs(z_mm - current_z) > POSITION_TOLERANCE_MM
        legs: list[tuple[float, float, float, float]] = []
        if xy_changes:
            legs.append((x_mm, y_mm, current_z, xy_feed))
        if z_changes:
            legs.append((x_mm, y_mm, z_mm, z_feed))
        return legs
