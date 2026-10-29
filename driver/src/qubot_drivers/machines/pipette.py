"""
Pipette machine class containing GrblTelnetController and SatoriusController.

This class integrates:
- GrblTelnetController: Handles motion control over grblHAL NETCON Telnet
- SatoriusController: Handles liquid handling operations
"""

import logging
import time
from typing import Any, Dict, Optional, Union
from qubot_drivers.move.grbl_telnet import GrblTelnetController
from qubot_drivers.position import Position
from qubot_drivers.satorius import SatoriusController
from puda import command, safety, tlm_stream

logger = logging.getLogger(__name__)


class Pipette:
    """Pescador pipetting robot that moves a pipette over the deck and handles liquid, controlled over WebSocket and serial."""

    def __init__(
        self,
        qubot_ip: Optional[str] = None,
        satorius_port: Optional[str] = None,
    ):
        """
        Initialize the Pipette machine.

        qubot_ip and satorius_port must both be specified; otherwise ValueError is raised.

        Args:
            qubot_ip: IP address for GrblTelnetController (e.g., '192.168.2.113').
            satorius_port: Serial port for SatoriusController (e.g., '/dev/ttyUSB0').

        Raises:
            ValueError: If qubot_ip or satorius_port is not specified.
        """
        if qubot_ip is None:
            raise ValueError("qubot_ip is required")
        if satorius_port is None:
            raise ValueError("satorius_port is required")

        self.qubot = GrblTelnetController(host=qubot_ip)
        self.pipette = SatoriusController(port_name=satorius_port)

        logger.info(
            "Pipette machine initialized: qubot_ip=%s, satorius_port=%s",
            qubot_ip,
            satorius_port,
        )

    def startup(self):
        """
        Start up the machine by connecting all controllers and initializing subsystems.

        This method:
        - Connects to the gantry controller
        - Homes the gantry to establish a known position
        - Connects to and initializes the pipette to reset it to a known state

        The machine is ready for operations after this method completes.
        """
        logger.info("Starting up machine and connecting gantry controller")
        self.qubot.connect()

        logger.info("Homing gantry and initializing pipette...")
        self.home()
        time.sleep(3)  # need to wait for the pipette to initialize
        logger.info("Machine startup complete - ready for operations")

    @command
    @safety(
        summary='Homes the gantry into its limit switches and re-initializes the pipette; the gantry can collide.',
        hazards=['collision', 'lost-steps'],
        requires='Deck is clear and the motor-power cutoff is reachable.',
    )
    def home(self):
        """Home the qubot gantry and reinitialize the pipette."""
        logger.info("Homing qubot gantry...")
        self.qubot.home()
        # Reconnect after gantry homing: an idle serial session can stop responding.
        if self.pipette.is_connected:
            self.pipette.disconnect()
        self.pipette.connect()
        self.pipette.initialize()
        logger.info("Qubot gantry homing complete")

    @command
    def shutdown(self):
        """Gracefully shut down the machine by disconnecting all controllers."""
        logger.info("Shutting down machine and disconnecting all controllers")
        self.qubot.disconnect()
        self.pipette.disconnect()
        logger.info("Machine shutdown complete")

    @command
    @safety(
        summary='Moves the gantry directly to an absolute position, bypassing the safe-Z path.',
        hazards=['collision'],
        requires='Gantry is homed and the path is clear.',
    )
    def move_to(self, x: float, y: float, z: float):
        """
        Move the gantry directly to an absolute position.

        Issues a single G0 (rapid) move in machine coordinates. Does not retract
        Z first; use :meth:`safe_move_to` when the tip must stay clear of obstacles.

        Args:
            x: Target X coordinate in mm.
            y: Target Y coordinate in mm.
            z: Target Z coordinate in mm.
        """
        self.qubot.g0(Position(x=x, y=y, z=z))

    @command
    @safety(
        summary='Moves the gantry to an absolute position via safe Z, then XY, then Z.',
        hazards=['collision'],
        requires='Gantry is homed and the target is within reach.',
    )
    def safe_move_to(self, x: float, y: float, z: float, z_safe: float = -10):
        """
        Move to an absolute position while keeping the tip clear of obstacles.

        Retracts to ``z_safe``, moves XY at that height, then descends to ``z``.
        Each step is a G0 (rapid) move. Prefer this over :meth:`move_to` when
        traveling between deck locations with a tip attached.

        Args:
            x: Target X coordinate in mm.
            y: Target Y coordinate in mm.
            z: Target Z coordinate in mm.
            z_safe: Retracted Z height in mm for the horizontal move. Defaults to -10.
        """
        self.qubot.g0(Position(z=z_safe))
        self.qubot.g0(Position(x=x, y=y))
        self.qubot.g0(Position(z=z))

    @command
    @tlm_stream(interval=3.0, name="pos")
    def get_position(self) -> Dict[str, Union[Dict[str, float], int]]:
        """
        Get the current position of the machine.

        Returns:
            Dictionary containing the current position of the machine and its components (qubot, pipette).
        """
        qubot_position = self.qubot.get_position()
        satorius_position = self.pipette.get_position()
        return {
            "qubot": qubot_position.to_dict(),
            "pipette": satorius_position,
        }

    ### Pipette operations ###

    @command
    @safety(
        summary='Moves down onto a tiprack position to pick up a tip.',
        hazards=['collision'],
        requires='Gantry is homed and a tip is at the target position.',
    )
    def attach_tip(
        self,
        x: float,
        y: float,
        z: float,
        approach_offset: float = 5,
        feed: int = 500,
    ) -> Dict[str, bool]:
        """
        Attach a tip at the given position.

        Same as :meth:`safe_move_to`, but stops ``approach_offset`` mm above the
        target Z and completes the move at ``feed`` mm/min before attaching.

        Args:
            x: Target X coordinate in mm.
            y: Target Y coordinate in mm.
            z: Target Z coordinate in mm.
            approach_offset: Height in mm above target Z for the slow approach. Defaults to 5.
            feed: Feed rate in mm/min for the slow Z approach. Defaults to 500.

        Returns:
            Dictionary with skipped set to True if attachment was skipped, False otherwise.

        Note:
            This method is idempotent - if a tip is already attached, it will
            log a warning and return successfully without raising an error.
        """
        if self.pipette.is_tip_attached():
            logger.warning("Tip already attached - skipping attachment (idempotent operation)")
            return {"skipped": True}

        logger.info("Attaching tip at position (%.2f, %.2f, %.2f)", x, y, z)
        self.safe_move_to(x, y, z + approach_offset)
        logger.debug("Slowly descending %.2f mm to insert tip", approach_offset)
        self.qubot.set_absolute_mode()
        self.qubot.execute_and_wait(f"G1Z{z}F{feed}")
        self.pipette.set_tip_attached(attached=True)
        logger.info("Tip attached successfully, homing Z axis")
        self.qubot.home(axis="Z")
        return {"skipped": False}

    @command
    @safety(
        summary='Ejects the attached tip at the current position.',
        hazards=['dropped tip'],
        requires='A tip is attached and the gantry is above a safe disposal location.',
    )
    def drop_tip(self) -> Dict[str, Any]:
        """
        Drop the attached tip.

        Raises:
            ValueError: If no tip is attached.
        """
        if not self.pipette.is_tip_attached():
            logger.error("Cannot drop tip: no tip attached")
            raise ValueError("Tip not attached")

        logger.info("Dropping tip")
        self.pipette.eject_tip()
        time.sleep(5)
        self.pipette.set_tip_attached(attached=False)
        logger.info("Tip dropped successfully")
        return {}

    @command
    @safety(
        summary='Draws liquid at the current position.',
        hazards=['liquid handling'],
        requires='A tip is attached and positioned in the liquid.',
    )
    def aspirate_from(self, amount: int) -> Dict[str, int]:
        """
        Aspirate a volume of liquid at the current position.

        Args:
            amount: Volume to aspirate in µL

        Raises:
            ValueError: If no tip is attached.
        """
        if not self.pipette.is_tip_attached():
            logger.error("Cannot aspirate: no tip attached")
            raise ValueError("Tip not attached")

        logger.info("Aspirating %d µL", amount)
        self.pipette.aspirate(amount=amount)
        time.sleep(5)
        logger.info("Aspiration completed: %d µL", amount)
        return {"amount": amount}

    @command
    @safety(
        summary='Dispenses liquid at the current position.',
        hazards=['liquid handling'],
        requires='A tip is attached and positioned over the target.',
    )
    def dispense_to(self, amount: int) -> Dict[str, int]:
        """
        Dispense a volume of liquid at the current position.

        Args:
            amount: Volume to dispense in µL

        Raises:
            ValueError: If no tip is attached.
        """
        if not self.pipette.is_tip_attached():
            logger.error("Cannot dispense: no tip attached")
            raise ValueError("Tip not attached")

        logger.info("Dispensing %d µL", amount)
        self.pipette.dispense(amount=amount)
        time.sleep(5)
        logger.info("Dispense completed: %d µL", amount)
        return {"amount": amount}

    @command
    @safety(
        summary='Blows out the pipette.',
        hazards=['liquid spray'],
    )
    def blowout(self) -> Dict[str, Any]:
        """Blow out the pipette."""
        logger.info("Blowing out pipette")
        self.pipette.run_blowout()
        logger.info("Blowout completed")
        return {}

    ### Control (immediate commands) ###

    @command
    def pause(self):
        """Pause the execution of queued commands."""
        logger.info("Pausing machine")

    @command
    def resume(self):
        """Resume the execution of queued commands."""
        logger.info("Resuming machine")

    @command
    def cancel(self):
        """Cancel the execution of queued commands."""
        logger.info("Cancelling machine")

    @command
    def reset(self):
        """Reset the machine to its initial state."""
        logger.info("Resetting machine")
