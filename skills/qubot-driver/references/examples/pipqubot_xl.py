"""pipqubot-xl: 4-unit, RepRapFirmware over HTTP (RepRapHTTPController) gantry.

Starting-point driver.py for this machine. Copy it into the edge, pass the
ports from main.py's Config, review every @safety text, and add the
machine's own commands. Importing this file opens no port; Driver() does.

Commands the earlier edge advertised: `reconcile_tip_attached`,
`dispense_to_proxy_vial`, `move_capper`, `move_to_well`.
"""

from puda import command, safety

from qubot.gantry import Frame, RepRapHTTPController
from qubot.end_effector import Capper, rline_50_1000
from qubot.geometry import Position

FRAME = Frame(
    axes=('X', 'Y', 'Z', 'A'),
    hardware_limits={"X": (0, 345), "Y": (-490, 0), "Z": (-170, 0), "A": (-170, 0)},
    default_deck={"rows": 4, "cols": 4},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Review per edge.
HOME_ON_STARTUP = False

# Rides gantry axis A. No port of its own.
CAPPER = Capper(axis='A', tool_length_mm=2, mount_offset_x_mm=60)


class Driver:
    """Pipqubot-xl: 4-unit RepRap gantry with an rLine 50-1000 µL pipette and an A-axis capper."""

    def __init__(self, gantry_host: str, pipette_port: str) -> None:
        """Open the hardware and apply this machine's limits.

        Args:
            gantry_host: RepRapFirmware host, from main.py Config (for example GANTRY_HOST).
            pipette_port: Serial port of the rLine pipette (SATORIUS_PORT).
        """
        self._gantry = RepRapHTTPController(host=gantry_host)
        self._gantry.connect()
        FRAME.apply_axis_limits(self._gantry, SOFT_LIMITS)
        self._pipette = rline_50_1000.connect(pipette_port)
        self._pipette.connect()
        self._capper = CAPPER
        if HOME_ON_STARTUP:
            self.home()

    def shutdown(self) -> bool:
        """Hook: close every port before the edge stops."""
        self._pipette.disconnect()
        self._gantry.disconnect()
        return True

    def estop(self) -> bool:
        """Hook: emergency stop. Sends RepRapFirmware M112 without waiting for other commands."""
        self._gantry.execute("M112")
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
        a: float | None = None,
    ) -> dict[str, float]:
        """Move to an absolute position in mm. Omitted axes stay where they are.

        Args:
            x: Target on X in mm, or None.
            y: Target on Y in mm, or None.
            z: Target on Z in mm, or None.
            a: Target on A in mm, or None.

        Returns:
            dict[str, float]: Position after the move.

        Raises:
            ValueError: If the target is outside the axis limits.
        """
        return self._gantry.move_absolute(Position(x=x, y=y, z=z, a=a)).to_dict()

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
        a: float | None = None,
    ) -> dict[str, float]:
        """Move by a relative offset in mm. Omitted axes stay where they are.

        Args:
            x: Offset on X in mm, or None.
            y: Offset on Y in mm, or None.
            z: Offset on Z in mm, or None.
            a: Offset on A in mm, or None.

        Returns:
            dict[str, float]: Position after the move.

        Raises:
            ValueError: If the target is outside the axis limits.
        """
        return self._gantry.move_relative(Position(x=x, y=y, z=z, a=a)).to_dict()

    @command
    def get_position(self) -> dict[str, float]:
        """Position the gantry controller is tracking.

        Returns:
            dict[str, float]: Axis positions in mm.
        """
        return self._gantry.get_internal_position().to_dict()
