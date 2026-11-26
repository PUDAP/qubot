"""eis-qubot: gantry 009-1unit-grblhal-serial.

Starting-point driver.py for this machine. Copy it into the edge, pass the
ports from main.py's Config, review every @safety text, and add the
machine's own commands. Importing this file opens no port; Driver() does.

EIS Qubot (Electrochemical station). Limits key: `eis_qubot`.
Frame travel is X −300 to 300, Y −199 to 0, Z −300 to 300. Y travel is 199 mm,
inside the 300 mm allowed for one unit. X is −300 to 300, a span of 600 mm,
which is past that allowance. Z is the same −300 to 300 figure. The 300 mm
rule covers X and Y; Z is flagged with X. Both uploaded ranges are kept for
correction.
"""

from puda import command, safety

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector.parallel_force_actuator import ParallelFingers
from qubot.geometry import Position

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (-300, 300), "Y": (-199, 0), "Z": (-300, 300)},
    default_deck={"rows": 2, "cols": 2},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Review per edge.
HOME_ON_STARTUP = False

# Four actuators, port envs FINGER_1_PORT to FINGER_4_PORT, channels 0-3.
# corrections are (slope, intercept) per channel: corrected = (raw - b) / a.
# Touch thresholds: pescador2 sets 30000, the demo uses 7500. Neither is a
# plausible newton value, so threshold stops stay off until the unit is named.
FINGER_CORRECTIONS = [
    (1.0453861330027523, -717.008056157306),
    (0.8792176759765562, -3546.5827171758337),
    (1.0266252637365454, -823.8747617486401),
    (0.9109718487428711, -1188.2464990482106),
]
FORCE_CALIBRATION_FACTOR = 573.2622826433104
FINGER_LIMITS_MM = (-30.0, 0.0)
# Unit unresolved; force-threshold stops stay off until it is named.
TOUCH_THRESHOLD_CANDIDATES = (30000, 7500)


class Driver:
    """EIS qubot: 1-unit grblHAL electrochemical station with four force actuators."""

    def __init__(self, gantry_port: str, finger_ports: list[str]) -> None:
        """Open the hardware and apply this machine's limits.

        Args:
            gantry_port: Serial port of the gantry controller, from main.py Config (GANTRY_PORT).
            finger_ports: One serial port per actuator, channel order (FINGER_1_PORT ...).
        """
        self._gantry = GrblHALController(port_name=gantry_port)
        self._gantry.connect()
        FRAME.apply_axis_limits(self._gantry, SOFT_LIMITS)
        self._fingers = ParallelFingers(
            finger_ports,
            corrections=FINGER_CORRECTIONS,
            calibration_factor=FORCE_CALIBRATION_FACTOR,
            limits_mm=FINGER_LIMITS_MM,
        )
        self._fingers.connect()
        if HOME_ON_STARTUP:
            self.home()

    def shutdown(self) -> bool:
        """Hook: close every port before the edge stops."""
        self._fingers.disconnect()
        self._gantry.disconnect()
        return True

    def estop(self) -> bool:
        """Hook: emergency stop. Feed-holds the controller without waiting for its command lock."""
        self._gantry.halt()
        # No actuator stop command is known; the fingers keep their last target.
        return True

    @command
    @safety(
        summary="Homing drives every axis to its end stops.",
        hazards=["collision"],
        requires="The workspace is clear of hands and loose labware.",
        confirm=True,
    )
    def home(self) -> bool:
        """Home the gantry, axis by axis when FRAME has a home order.

        Returns:
            bool: True once homing finished.
        """
        if FRAME.home_order:
            for axis in FRAME.home_order:
                self._gantry.home(axis)
        else:
            self._gantry.home()
        return True

    @command
    @safety(
        summary="Collision risk from gantry motion.",
        hazards=["collision"],
        requires="The gantry has been homed since power-on.",
        forbidden_when="The workspace is occupied.",
        confirm=True,
    )
    def move_absolute(
        self,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
    ) -> dict[str, float]:
        """Move to an absolute position in mm. Omitted axes stay where they are.

        Args:
            x: Target on X in mm, or None.
            y: Target on Y in mm, or None.
            z: Target on Z in mm, or None.

        Returns:
            dict[str, float]: Position after the move.

        Raises:
            ValueError: If the target is outside the axis limits.
        """
        return self._gantry.move_absolute(Position(x=x, y=y, z=z)).to_dict()

    @command
    @safety(
        summary="Collision risk from gantry motion.",
        hazards=["collision"],
        requires="The gantry has been homed since power-on.",
        forbidden_when="The workspace is occupied.",
        confirm=True,
    )
    def move_relative(
        self,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
    ) -> dict[str, float]:
        """Move by a relative offset in mm. Omitted axes stay where they are.

        Args:
            x: Offset on X in mm, or None.
            y: Offset on Y in mm, or None.
            z: Offset on Z in mm, or None.

        Returns:
            dict[str, float]: Position after the move.

        Raises:
            ValueError: If the target is outside the axis limits.
        """
        return self._gantry.move_relative(Position(x=x, y=y, z=z)).to_dict()

    @command
    def get_position(self) -> dict[str, float]:
        """Position the gantry controller is tracking.

        Returns:
            dict[str, float]: Axis positions in mm.
        """
        return self._gantry.get_internal_position().to_dict()
