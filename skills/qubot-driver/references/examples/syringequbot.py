"""syringequbot: gantry 002-1unit-reprap-http.

Starting-point driver.py for this machine. Copy it into the edge, pass the
ports from main.py's Config, review every @safety text, and add the
machine's own commands. Importing this file opens no port; Driver() does.

Commands the earlier edge advertised: `home`, `move_to`, `safe_move_to`, `reset`.

The RepRap HTTP driver includes `set_pin`.
Firmware travel is X 0 to 140, Y -170 to 0, Z -175 to 0. A later observation
that Z past -125 meets the current vial holder is not stored as a limit.
"""

from puda import command, safety

from qubot.gantry import Frame
from qubot.gantry.reprap_http import RepRapHTTPController
from qubot.end_effector.autosampler_syringe import narrow_z
from qubot.geometry import Position

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (0.0, 140.0), "Y": (-170.0, 0.0), "Z": (-175.0, 0.0)},
    default_deck={"rows": 2, "cols": 2},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Review per edge.
HOME_ON_STARTUP = False

# Syringe plus the current IMRE vial holder, not the needle alone. Travel past
# Z = -125 was observed to knock the needle into the base of the mounted vial
# holder (-175 firmware Z + 50). Clearance figure, not an axis limit. Remeasure
# if the vial holder changes.
SYRINGE_LENGTH_MM = 50
Z_LIMITS = narrow_z(FRAME.hardware_limits["Z"], SYRINGE_LENGTH_MM)


class Driver:
    """Syringequbot: 1-unit RepRap gantry carrying a passive autosampler syringe."""

    def __init__(self, gantry_host: str) -> None:
        """Open the hardware and apply this machine's limits.

        Args:
            gantry_host: RepRapFirmware host, from main.py Config (for example GANTRY_HOST).
        """
        self._gantry = RepRapHTTPController(host=gantry_host)
        self._gantry.connect()
        FRAME.apply_axis_limits(self._gantry, SOFT_LIMITS)
        if HOME_ON_STARTUP:
            self.home()

    def shutdown(self) -> bool:
        """Hook: close every port before the edge stops."""
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
