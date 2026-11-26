"""dancefloor: gantry 006-1unit-grblhal-serial.

Starting-point driver.py for this machine. Copy it into the edge, pass the
ports from main.py's Config, review every @safety text, and add the
machine's own commands. Importing this file opens no port; Driver() does.

Dancefloor (Vacuum chamber). Limits key: `vacuum_chamber`.
Frame travel is X −116 to 0, Y −28 to 0, Z 0 to 0. Z has no travel. X travel
is 116 mm and Y travel is 28 mm, both inside the 300 mm allowed for one unit.
The combined pescador2 config says X low is −119. This frame keeps −116. The
chamber loading position X=−118 is outside this frame until that conflict is
confirmed. The limits file names a port placeholder `__dancefloor__`. That
value belongs in the site edge .env.
"""

from puda import command, safety

from qubot.gantry import Frame, GrblHALController
from qubot.end_effector import Chamber
from qubot.geometry import Position

# pescador2 config X low is -119. This frame keeps the dancefloor-alone value
# -116. The chamber loading position X=-118 is outside this frame until the
# limit is confirmed.
FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (-116, 0), "Y": (-28, 0), "Z": (0, 0)},
    default_deck={"rows": 2, "cols": 2},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Review per edge.
HOME_ON_STARTUP = False

# Dancefloor lid and vacuum valve on the gantry port. Robot frame.
# Loading X = -118 is outside this frame's X low of -116. pescador2 uses -119.
# Confirm the frame before moving to the loading position.

def make_chamber() -> Chamber:
    """A fresh chamber state (open, vented) with this machine's positions."""
    return Chamber(
        loading_position=(-118.0, 0.0, 0.0),
        close_waypoints=[(-3.0, 0.0, 0.0), (-3.0, -27.0, 0.0)],
        vacuum_on_delay_s=5.0,
        vacuum_off_delay_s=5.0,
        valve_on='M8',
        valve_off='M9',
    )


class Driver:
    """Dancefloor: 1-unit grblHAL gantry that opens and closes a vacuum chamber."""

    def __init__(self, gantry_port: str) -> None:
        """Open the hardware and apply this machine's limits.

        Args:
            gantry_port: Serial port of the gantry controller, from main.py Config (GANTRY_PORT).
        """
        self._gantry = GrblHALController(port_name=gantry_port)
        self._gantry.connect()
        FRAME.apply_axis_limits(self._gantry, SOFT_LIMITS)
        self._chamber = make_chamber()
        if HOME_ON_STARTUP:
            self.home()

    def shutdown(self) -> bool:
        """Hook: close every port before the edge stops."""
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
        if not self._chamber.vented:
            raise RuntimeError("Vent the chamber before homing.")
        if FRAME.home_order:
            for axis in FRAME.home_order:
                self._gantry.home(axis)
        else:
            self._gantry.home()
        self._chamber.mark_homed()
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
            RuntimeError: If the chamber is marked closed.
        """
        self._chamber.require_motion()
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
            RuntimeError: If the chamber is marked closed.
        """
        self._chamber.require_motion()
        return self._gantry.move_relative(Position(x=x, y=y, z=z)).to_dict()

    @command
    def get_position(self) -> dict[str, float]:
        """Position the gantry controller is tracking.

        Returns:
            dict[str, float]: Axis positions in mm.
        """
        return self._gantry.get_internal_position().to_dict()
