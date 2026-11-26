"""photoreactor: gantry 008-1unit-grblhal-serial.

Starting-point driver.py for this machine. Copy it into the edge, pass the
ports from main.py's Config, review every @safety text, and add the
machine's own commands. Importing this file opens no port; Driver() does.

Photoreactor (UV qubot). Limits key: `photoreactor`.
Frame travel is X −300 to 300, Y −199 to 0, Z −78 to 0. Y travel is 199 mm,
inside the 300 mm allowed for one unit. X is −300 to 300, a span of 600 mm,
which is past that allowance. The uploaded X range is kept and flagged for
correction.
"""

from puda import command, safety

from qubot.gantry import Frame, GrblHALController
from qubot.end_effector import LedBoard
from qubot.geometry import Position

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (-300, 300), "Y": (-199, 0), "Z": (-78, 0)},
    default_deck={"rows": 2, "cols": 2},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Review per edge.
HOME_ON_STARTUP = False

# Serial port env: LED_PORT. 9600 baud, 1 s timeout. A force_threshold value
# appears on one lamp config and is not used.
LED_BAUD = 9600
LED_TIMEOUT_S = 1.0


class Driver:
    """Photoreactor: 1-unit grblHAL gantry with a four-channel UV LED board."""

    def __init__(self, gantry_port: str, led_port: str) -> None:
        """Open the hardware and apply this machine's limits.

        Args:
            gantry_port: Serial port of the gantry controller, from main.py Config (GANTRY_PORT).
            led_port: Serial port of the LED board (LED_PORT).
        """
        self._gantry = GrblHALController(port_name=gantry_port)
        self._gantry.connect()
        FRAME.apply_axis_limits(self._gantry, SOFT_LIMITS)
        self._led = LedBoard(led_port, baud=LED_BAUD, timeout_s=LED_TIMEOUT_S)
        self._led.connect()
        if HOME_ON_STARTUP:
            self.home()

    def shutdown(self) -> bool:
        """Hook: close every port before the edge stops."""
        self._led.off()
        self._led.disconnect()
        self._gantry.disconnect()
        return True

    def estop(self) -> bool:
        """Hook: emergency stop. Feed-holds the controller without waiting for its command lock."""
        self._gantry.halt()
        self._led.off()
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
