"""
Pescador machine class containing GrblTelnetController.

This class integrates:
- GrblTelnetController: Handles motion control over grblHAL NETCON Telnet
"""

import logging
import time
from typing import Any, Dict, Optional

from qubot_drivers.move.grbl_telnet import GrblTelnetController
from qubot_drivers.position import Position

logger = logging.getLogger(__name__)


class Pescador:
    """
    Pescador pipette machine class integrating motion control.
    """

    Z_SAFE = -10

    def __init__(
        self,
        qubot_ip: Optional[str] = None,
    ):
        """
        Initialize the Pescador machine.

        Args:
            qubot_ip: IP address for GrblTelnetController (e.g., '192.168.2.113').

        Raises:
            ValueError: If qubot_ip is not specified.
        """
        if qubot_ip is None:
            raise ValueError("qubot_ip is required")

        self.qubot = GrblTelnetController(host=qubot_ip)

        logger.info("Pescador machine initialized: qubot_ip=%s", qubot_ip)

    def startup(self):
        """
        Start up the machine by connecting all controllers and initializing subsystems.

        This method:
        - Connects to the gantry controller
        - Homes the gantry to establish a known position

        The machine is ready for operations after this method completes.
        """
        logger.info("Starting up machine and connecting controllers")
        self.qubot.connect()
        logger.info("Controller connected successfully")

        logger.info("Homing gantry...")
        self.home()
        logger.info("Machine startup complete - ready for operations")

    def shutdown(self):
        """
        Gracefully shut down the machine by disconnecting all controllers.

        This method ensures all connections are properly closed and resources are released.
        """
        logger.info("Shutting down machine and disconnecting controllers")
        self.qubot.disconnect()
        logger.info("Machine shutdown complete")

    def wait(self, seconds: float):
        """
        Wait for a specified number of seconds.

        Args:
            seconds: Number of seconds to wait (can be a float for fractional seconds)
        """
        logger.debug("Waiting for %.2f seconds", seconds)
        time.sleep(seconds)
        logger.debug("Waited for %.2f seconds", seconds)

    def move_to(self, x: float, y: float, z: float):
        """Move directly to an absolute position."""
        self.qubot.g0(Position(x=x, y=y, z=z))

    def safe_move_to(self, x: float, y: float, z: float):
        """Move to an absolute position via safe Z, then XY, then Z."""
        self.qubot.g0(Position(z=self.Z_SAFE))
        self.qubot.g0(Position(x=x, y=y))
        self.qubot.g0(Position(z=z))

    def home(self):
        """Home all axes."""
        self.qubot.home()

    def clear_deck(self):
        """Move to a clear position on the deck."""
        self.safe_move_to(10, -10, self.Z_SAFE)

    def get_position(self) -> Dict[str, float]:
        """
        Get the current gantry position.

        Returns:
            Dictionary of axis positions (e.g. x, y, z, a).
        """
        return self.qubot.get_position().to_dict()

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current GRBL firmware status.

        Returns:
            Dictionary with motion state, status report, and coordinates.
        """
        return self.qubot.get_status()

    ### Control (immediate commands) ###

    def pause(self):
        """Pause the execution of queued commands."""
        print("Pausing machine")

    def resume(self):
        """Resume the execution of queued commands."""
        print("Resuming machine")

    def cancel(self):
        """Cancel the execution of queued commands."""
        print("Cancelling machine")
