"""claw-machine: gantry 005-8unit-grblhal-serial.

Starting-point driver.py for this machine. Copy it into the edge, pass the
ports from main.py's Config, review every @safety text, and add the
machine's own commands. Importing this file opens no port; Driver() does.

The frame is 2 by 4 units: 2 along Y and 4 along X.
Claw machine (Pick-and-place). Limits key: `claw_gantry`.
Frame travel is X 0 to 830, Y −280 to 0, Z −240 to 0. One unit may travel at
most 300 mm on X and on Y, so this frame may travel 1200 mm on X and 600 mm on
Y. The uploaded spans are 830 mm and 280 mm, both inside that allowance.
Homing for this frame is Z, then X, then Y. The transport line ending remains
CR. A claw configuration set CR LF; that conflict stays in the edge config.
"""

from puda import command, safety

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector.rotating_vacuum_gripper import RotatingVacuumGripper
from qubot.geometry import Position

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (0, 830), "Y": (-280, 0), "Z": (-240, 0)},
    default_deck={"rows": 4, "cols": 8},
    home_order=('Z', 'X', 'Y'),
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Review per edge.
HOME_ON_STARTUP = False

# Claw vacuum cup and yaw servo on the gantry GRBL port.
# Calibrated servo pulses: 0° -> S14, -90° -> S124, -180° -> S244. The older
# in-between expression omits the calibrated endpoint and yields a negative
# pulse; RotatingVacuumGripper interpolates linearly instead.
GRIPPER = RotatingVacuumGripper(
    axis='C',
    yaw_pulses=[(0, 14), (-90, 124), (-180, 244)],
    rotation_min_z_mm=-5.0,
    vacuum_on_delay_s=3.0,
    vacuum_off_delay_s=3.0,
    valve_on='M8',
    valve_off='M9',
)


class Driver:
    """Claw machine: 8-unit grblHAL pick-and-place gantry with a rotating vacuum gripper."""

    def __init__(self, gantry_port: str) -> None:
        """Open the hardware and apply this machine's limits.

        Args:
            gantry_port: Serial port of the gantry controller, from main.py Config (GANTRY_PORT).
        """
        self._gantry = GrblHALController(port_name=gantry_port)
        self._gantry.connect()
        FRAME.apply_axis_limits(self._gantry, SOFT_LIMITS)
        self._gripper = GRIPPER
        if HOME_ON_STARTUP:
            self.home()

    def shutdown(self) -> bool:
        """Hook: close every port before the edge stops."""
        self._gantry.disconnect()
        return True

    def estop(self) -> bool:
        """Hook: emergency stop. Feed-holds the controller without waiting for its command lock."""
        self._gantry.halt()
        # The vacuum cup is not vented on estop.
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
