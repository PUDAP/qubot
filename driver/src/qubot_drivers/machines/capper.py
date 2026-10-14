"""
Capper machine class containing RepRapHTTPController.

This class integrates:
- RepRapHTTPController: Handles motion control over HTTP (hardware-specific)
"""

import logging
import time
from typing import Any, Dict, Optional

from qubot_drivers.move.reprap_http import RepRapHTTPController
from qubot_drivers.position import Position
from puda import command, safety, tlm_stream

logger = logging.getLogger(__name__)


class Capper:
    """
    Tube capper that screws caps onto and off of tubes using a gantry with two clamps.
    """

    TUBE_X = 32.5
    TUBE_Y = -189.8
    Z_SAFE = -10
    Z_DECAP_APPROACH = -52
    Z_DECAP_RETRACT = -33
    Z_CAP_APPROACH = -44
    Z_CAP = -52

    def __init__(
        self,
        qubot_ip: Optional[str] = None,
    ):
        """
        Initialize the Capper machine.

        Args:
            qubot_ip: IP address for RepRapHTTPController (e.g., '192.168.2.113').

        Raises:
            ValueError: If qubot_ip is not specified.
        """
        if qubot_ip is None:
            raise ValueError("qubot_ip is required")

        self.qubot = RepRapHTTPController(host=qubot_ip)

        logger.info("Capper machine initialized: qubot_ip=%s", qubot_ip)

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

    @command
    def shutdown(self):
        """
        Gracefully shut down the machine by disconnecting all controllers.

        This method ensures all connections are properly closed and resources are released.
        """
        logger.info("Shutting down machine and disconnecting controllers")
        self.qubot.disconnect()
        logger.info("Machine shutdown complete")

    @command
    @safety(
        summary='Moves the gantry directly to an absolute position, bypassing the safe-Z path.',
        hazards=['collision'],
        requires='Gantry is homed and the path is clear.',
    )
    def move_to(self, x: float, y: float, z: float):
        """Move directly to an absolute position."""
        self.qubot.g0(Position(x=x, y=y, z=z))

    @command
    @safety(
        summary='Moves the gantry to an absolute position via safe Z, then XY, then Z.',
        hazards=['collision'],
        requires='Gantry is homed and the target is within reach.',
    )
    def safe_move_to(self, x: float, y: float, z: float):
        """Move to an absolute position via safe Z, then XY, then Z."""
        self.qubot.g0(Position(z=self.Z_SAFE))
        self.qubot.g0(Position(x=x, y=y))
        self.qubot.g0(Position(z=z))

    @command
    def release_bottom(self):
        """Release the bottom clamp."""
        self.qubot.set_pin(0, 0)

    @command
    @safety(
        summary='Engages the bottom clamp.',
        hazards=['pinch point'],
    )
    def clamp_bottom(self):
        """Engage the bottom clamp."""
        self.qubot.set_pin(0, 1)

    @command
    def release_top(self):
        """Release the top clamp."""
        self.qubot.set_pin(1, 0)

    @command
    @safety(
        summary='Engages the top clamp.',
        hazards=['pinch point'],
    )
    def clamp_top(self):
        """Engage the top clamp."""
        self.qubot.set_pin(1, 1)

    @command
    @safety(
        summary='Homes all axes and releases both clamps; the gantry can collide.',
        hazards=['collision', 'held tube or cap released'],
        requires='Deck is clear.',
    )
    def home(self):
        """Home all axes and release both clamps."""
        self.qubot.home()
        self.release_bottom()
        self.release_top()

    @command
    def clear_deck(self):
        """Move to a clear position on the deck."""
        self.safe_move_to(10, -10, self.Z_SAFE)

    @command
    @safety(
        summary='Unscrews the cap from the tube at the capping station.',
        hazards=['collision', 'pinch point'],
        requires='A tube is seated in the capping station and the gantry is homed.',
    )
    def decap(self):
        """Unscrew the cap from the tube at the capping station."""
        self.release_top()
        self.safe_move_to(self.TUBE_X, self.TUBE_Y, self.Z_DECAP_APPROACH)
        self.move_to(self.TUBE_X, self.TUBE_Y, self.Z_CAP)
        self.clamp_bottom()
        self.clamp_top()

        self.qubot.set_relative_mode()
        self.qubot.g0(Position(a=336, z=10.5))
        self.qubot.set_absolute_mode()

        self.qubot.g0(Position(z=self.Z_DECAP_RETRACT))

    @command
    @safety(
        summary='Moves to a position and releases the held cap.',
        hazards=['collision', 'dropped cap'],
        requires='A cap is held and the target is clear.',
    )
    def place_cap_at(self, x: float, y: float, z: float):
        """Place the held cap at the specified position."""
        self.safe_move_to(x, y, z)
        self.release_top()
        time.sleep(3)

    @command
    @safety(
        summary='Moves to a position and clamps a cap.',
        hazards=['collision', 'pinch point'],
        requires='Gantry is homed and the target is clear.',
    )
    def pick_cap_from(self, x: float, y: float, z: float):
        """Pick up a cap from the specified position."""
        self.safe_move_to(x, y, z)
        self.clamp_top()
        time.sleep(1)
        self.qubot.g0(Position(z=self.Z_SAFE))

    @command
    @safety(
        summary='Screws a cap onto the tube at the capping station.',
        hazards=['collision', 'pinch point'],
        requires='A tube is seated in the capping station and a cap is held.',
    )
    def cap(self):
        """Screw a cap onto the tube at the capping station."""
        self.clamp_bottom()
        self.safe_move_to(self.TUBE_X, self.TUBE_Y, self.Z_CAP_APPROACH)

        self.qubot.set_relative_mode()
        self.qubot.g0(Position(a=144, z=-2.5))
        self.qubot.g0(Position(a=-216, z=-6.75))
        self.qubot.set_absolute_mode()

        self.release_top()
        time.sleep(2)
        self.qubot.g0(Position(z=self.Z_SAFE))

    @command
    @tlm_stream(interval=3.0, name="pos")
    def get_position(self) -> Dict[str, float]:
        """
        Get the current gantry position.

        Returns:
            Dictionary of axis positions (e.g. x, y, z, a).
        """
        return self.qubot.get_position().to_dict()

    @command
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current RepRap firmware status.

        Returns:
            Dictionary from the rr_status endpoint (motion state, coordinates, etc.).
        """
        return self.qubot.get_status()

    ### Control (immediate commands) ###

    @command
    def pause(self):
        """Pause the execution of queued commands."""
        print("Pausing machine")

    @command
    def resume(self):
        """Resume the execution of queued commands."""
        print("Resuming machine")

    @command
    def cancel(self):
        """Cancel the execution of queued commands."""
        print("Cancelling machine")

    @command
    def reset(self) -> bool:
        """
        Software reset. Disconnects, reconnects, and homes the gantry.

        Returns:
            bool: True if the machine restarted
        """
        self.shutdown()
        self.startup()
        return True
