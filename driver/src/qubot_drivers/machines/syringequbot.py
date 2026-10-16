"""Syringe Qubot: the capper gantry with a passive syringe instead of clamps."""

import asyncio
import logging
from typing import Any, Optional

from puda import command, machine_state, safety, tlm_stream

from qubot_drivers.move.reprap_http import RepRapHTTPController
from qubot_drivers.position import Position

logger = logging.getLogger(__name__)


class SyringeQubot:
    """Qubot XYZ gantry with a passive syringe and no A axis. Liquid is drawn by the separate sf10-peristaltic-pump edge."""

    AXES = ("x", "y", "z")
    # Z first, matching homeall.g, so the syringe is up before X or Y move.
    HOME_ORDER = ("Z", "X", "Y")
    # Inclusive travel, matching the Duet M208 end limits. There is no A axis.
    AXIS_LIMITS = {
        "X": (0.0, 140.0),
        "Y": (-170.0, 0.0),
        "Z": (-125.0, 0.0),
    }
    Z_SAFE = 0.0

    def __init__(
        self,
        qubot_ip: Optional[str] = None,
        *,
        controller: Optional[RepRapHTTPController] = None,
    ):
        """
        Initialize the syringe gantry.

        Args:
            qubot_ip: RepRapFirmware host, for example '192.168.2.103'.
            controller: Existing controller, used by tests. Replaces qubot_ip.

        Raises:
            ValueError: If neither qubot_ip nor controller is provided.
        """
        if controller is None:
            if qubot_ip is None:
                raise ValueError("qubot_ip is required")
            controller = RepRapHTTPController(host=qubot_ip)
        self.qubot = controller
        self._homed = False
        self._position: Optional[dict[str, float]] = None
        for axis, (minimum, maximum) in self.AXIS_LIMITS.items():
            self.qubot.set_axis_limits(axis, minimum, maximum)
        logger.info("SyringeQubot initialized")

    def startup(self) -> None:
        """Connect to the RepRap controller. Does not home."""
        logger.info("Connecting to the gantry controller")
        self.qubot.connect()
        self._homed = False

    @machine_state
    def snapshot(self) -> dict[str, Any]:
        """
        Cached homing flag and last known position.

        Returns:
            dict: homed, and position when a move or position read has cached one.
        """
        return {"homed": self._homed, "position": self._position}

    @command
    def shutdown(self) -> bool:
        """
        Disconnect from the gantry controller.

        Returns:
            bool: True after the controller is marked disconnected.
        """
        logger.info("Disconnecting the gantry controller")
        self.qubot.disconnect()
        self._homed = False
        return True

    @command
    @safety(
        summary="Homing drives X, Y, and Z into their limit switches and can collide.",
        hazards=["collision"],
        requires="Deck is clear.",
        forbidden_when="Do not home while the controller is disconnected.",
        confirm=True,
    )
    def home(self) -> bool:
        """
        Home X, Y, and Z. Z homes first. This gantry has no A axis.

        Returns:
            bool: True after the controller finishes homing.

        Raises:
            ConnectionError: If the RepRap board cannot be reached.
        """
        for axis in self.HOME_ORDER:
            self.qubot.home(axis=axis)
        self._homed = True
        self._position = {"x": 0.0, "y": 0.0, "z": 0.0}
        return True

    @command
    @safety(
        summary="Direct XYZ motion can collide because it does not retract Z first.",
        hazards=["collision"],
        requires="Home in this connection and keep the path clear.",
        forbidden_when="Do not move while a person is in the workspace.",
        confirm=True,
    )
    def move_to(self, x: float, y: float, z: float) -> dict[str, float]:
        """
        Move directly to an absolute XYZ position.

        Args:
            x: Target X in millimeters.
            y: Target Y in millimeters.
            z: Target Z in millimeters.

        Returns:
            dict[str, float]: Commanded X, Y, and Z in millimeters.

        Raises:
            RuntimeError: If this connection has not homed.
            ValueError: If X is outside 0 to 140, Y is outside -170 to 0, or Z is outside -125 to 0.
            ConnectionError: If the RepRap board cannot be reached.
        """
        self._require_homed()
        self._validate_target(x=x, y=y, z=z)
        self.qubot.g0(Position(x=x, y=y, z=z))
        self._position = {"x": float(x), "y": float(y), "z": float(z)}
        return dict(self._position)

    @command
    @safety(
        summary="Safe motion still collides if Z 0 is not clear of the workspace.",
        hazards=["collision"],
        requires="Home in this connection. Z 0 must be above every obstacle.",
        forbidden_when="Do not move while a person is in the workspace.",
        confirm=True,
    )
    def safe_move_to(self, x: float, y: float, z: float) -> dict[str, float]:
        """
        Move to an absolute position by retracting Z to 0, then moving XY, then Z.

        Args:
            x: Target X in millimeters.
            y: Target Y in millimeters.
            z: Target Z in millimeters.

        Returns:
            dict[str, float]: Commanded X, Y, and Z in millimeters.

        Raises:
            RuntimeError: If this connection has not homed.
            ValueError: If X is outside 0 to 140, Y is outside -170 to 0, or Z is outside -125 to 0.
            ConnectionError: If the RepRap board cannot be reached.
        """
        self._require_homed()
        self._validate_target(x=x, y=y, z=z)
        self.qubot.g0(Position(z=self.Z_SAFE))
        self.qubot.g0(Position(x=x, y=y))
        self.qubot.g0(Position(z=z))
        self._position = {"x": float(x), "y": float(y), "z": float(z)}
        return dict(self._position)

    @command
    @tlm_stream(interval=3.0, name="pos")
    def get_position(self) -> dict[str, float]:
        """
        Read the current gantry position.

        Returns:
            dict[str, float]: X, Y, and Z in millimeters. A is not part of this gantry.
        """
        reported = asyncio.run(self.qubot.get_position()).to_dict()
        position = {axis: float(reported[axis]) for axis in self.AXES if axis in reported}
        self._position = position
        return position

    @command
    def get_status(self) -> dict[str, Any]:
        """
        Read the current RepRap firmware status.

        Returns:
            dict: Response from the rr_status endpoint.
        """
        return self.qubot.get_status()

    @command
    @safety(
        summary="Reset reconnects and homes, which drives X, Y, and Z into their limit switches.",
        hazards=["collision"],
        requires="Deck is clear.",
        forbidden_when="Do not reset while a person is in the workspace.",
        confirm=True,
    )
    def reset(self) -> bool:
        """
        Disconnect, reconnect, and home the gantry.

        Returns:
            bool: True after homing completes.

        Raises:
            ConnectionError: If the RepRap board cannot be reached.
        """
        self.shutdown()
        self.startup()
        self.home()
        return True

    def _require_homed(self) -> None:
        if not self._homed:
            raise RuntimeError("Cannot move: machine is not homed in this connection")

    def _validate_target(self, **axes: float) -> None:
        """Reject a target outside the inclusive firmware end limits."""
        for name, value in axes.items():
            axis = name.upper()
            minimum, maximum = self.AXIS_LIMITS[axis]
            if not minimum <= float(value) <= maximum:
                raise ValueError(
                    f"Value {value} outside {axis} axis limits [{minimum}, {maximum}]"
                )
