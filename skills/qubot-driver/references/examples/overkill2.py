"""overkill2: gantry 007-2unit-grblhal-serial.

Starting-point driver.py for this machine. Copy it into the edge, pass the
ports from main.py's Config, review every @safety text, and add the
machine's own commands. Importing this file opens no port; Driver() does.

Overkill2 (Liquid handling - pipette gantry). Limits key: `pipQubot`.
Frame travel is X −176 to 0, Y −480 to 0, Z −190 to 0. The frame is 2 by 1
units, so X may travel at most 300 mm and Y at most 600 mm. The uploaded spans
are 176 mm and 480 mm, both inside that allowance.
"""

from puda import command, safety

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector import rline_50_1000_multistep
from qubot.geometry import Position

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (-176, 0), "Y": (-480, 0), "Z": (-190, 0)},
    default_deck={"rows": 4, "cols": 2},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Review per edge.
HOME_ON_STARTUP = False

# Serial port env: SATORIUS_PORT. Axis: Z.
# step_resolution and response_time_s are the PESCador pipette calibration.
PIPETTE_STEP_RESOLUTION = 10
PIPETTE_RESPONSE_TIME_S = 1.03


class Driver:
    """Overkill2: 2-unit grblHAL pipette gantry with a multistep rLine 50-1000 µL pipette."""

    def __init__(self, gantry_port: str, pipette_port: str) -> None:
        """Open the hardware and apply this machine's limits.

        Args:
            gantry_port: Serial port of the gantry controller, from main.py Config (GANTRY_PORT).
            pipette_port: Serial port of the rLine pipette (SATORIUS_PORT).
        """
        self._gantry = GrblHALController(port_name=gantry_port)
        self._gantry.connect()
        FRAME.apply_axis_limits(self._gantry, SOFT_LIMITS)
        self._pipette = rline_50_1000_multistep.connect(
            pipette_port,
            step_resolution=PIPETTE_STEP_RESOLUTION,
            response_time_s=PIPETTE_RESPONSE_TIME_S,
        )
        self._pipette.connect()
        if HOME_ON_STARTUP:
            self.home()

    def shutdown(self) -> bool:
        """Hook: close every port before the edge stops."""
        self._pipette.disconnect()
        self._gantry.disconnect()
        return True

    def estop(self) -> bool:
        """Hook: emergency stop. Feed-holds the controller without waiting for its command lock."""
        self._gantry.halt()
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
