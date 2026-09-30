"""
PipQuBotMOF machine class containing Deck, GrblHALController, and SatoriusController.

This class integrates:
- GrblHALController: Handles motion control (hardware-specific)
- Deck: Manages labware layout (configuration-agnostic)
- SatoriusController: Handles liquid handling operations
"""

import logging
import time
from typing import Optional, Dict, Tuple, Union
from qubot_drivers.move import GrblHALController, Deck
from qubot_drivers import Position
from qubot_drivers.satorius import SatoriusController
from puda import command, machine_state

logger = logging.getLogger(__name__)

class PipQuBotMOF:
    """
    MOF PipQuBot machine class integrating motion control, deck management, and liquid handling.
    
    The deck has 8 slots arranged in a 2x4 grid (A1-D2).
    Each slot's origin location is stored for absolute movement calculation.
    """
    
    
    CEILING_HEIGHT = 225.0 # Height from z and a origin to the deck

    # Pipette
    Z_ORIGIN = Position(x=0, y=0, z=0)
    TIP_LENGTH = 97 # Pipette tip length in mm
    SARTORIUS_MICROLITER_PER_STEP = 2.5

    
    # Default axis limits - customize based on your hardware
    DEFAULT_AXIS_LIMITS = {
        "X": (0, 161.7 ),
        "Y": (-444, 0),
        "Z": (-175, 0),
    }
    
    # Slot origins (the bottom left corner of each deck slot relative to the deck origin)
    SLOT_ORIGINS = {
        "A1": Position(x=0.2, y=-456.2),
        "A2": Position(x=100.2, y=-456.2),
        "B1": Position(x=0.2, y=-306.2),
        "B2": Position(x=100.2, y=-306.2),
        "C1": Position(x=0.2, y=-156.2),
        "C2": Position(x=100.2, y=-156.2),
        "D1": Position(x=0.2, y=-6.2),
        "D2": Position(x=100.2, y=-6.2),
    }
    
    def __init__(
        self,
        qubot_port: Optional[str] = None,
        satorius_port: Optional[str] = None,
        axis_limits: Optional[Dict[str, Tuple[float, float]]] = None,
    ):
        """
        Initialize the First machine.

        qubot_port and satorius_port must both be specified; otherwise ValueError is raised.

        Args:
            qubot_port: Serial port for GrblHALController (e.g., '/dev/ttyACM0').
            satorius_port: Serial port for SatoriusController (e.g., '/dev/ttyUSB0').
            axis_limits: Dictionary mapping axis names to (min, max) limits. Defaults to DEFAULT_AXIS_LIMITS.

        Raises:
            ValueError: If qubot_port or satorius_port is not specified.
        """
        if qubot_port is None:
            raise ValueError("qubot_port is required")
        if satorius_port is None:
            raise ValueError("satorius_port is required")

        # Initialize deck
        self.deck = Deck(rows=4, cols=4)

        self.qubot = GrblHALController(port_name=qubot_port)
        limits = axis_limits or self.DEFAULT_AXIS_LIMITS
        for axis, (min_val, max_val) in limits.items():
            self.qubot.set_axis_limits(axis, min_val, max_val)

        self.pipette = SatoriusController(
            port_name=satorius_port,
            microliter_per_step=self.SARTORIUS_MICROLITER_PER_STEP,
        )

        logger.info(
            "MOF PipQuBot initialized: qubot_port=%s, satorius_port=%s",
            qubot_port,
            satorius_port,
        )

    ### State ###
    @machine_state
    def snapshot(self) -> Dict[str, Dict]:
        """Deck layout merged into MACHINE_STATE updates."""
        return {"deck": self.deck.to_dict()}

    def startup(self):
        """
        Start up the machine by connecting all controllers and initializing subsystems.
        
        This method:
        - Connects to all controllers (gantry, pipette)
        - Homes the gantry to establish a known position
        - Initializes the pipette to reset it to a known state
        
        The machine is ready for operations after this method completes.
        """
        logger.info("Starting up machine and connecting all controllers")
        self.qubot.connect()
        self.pipette.connect()
        logger.info("All controllers connected successfully")

        logger.info("Homing gantry...")
        self.qubot.home()
        logger.info("Initializing pipette...")
        self.pipette.initialize()
        time.sleep(3)  # need to wait for the pipette to initialize
        logger.info("Machine startup complete - ready for operations")
    
    @command
    def home(self):
        """
        Home the qubot gantry to establish a known position.
        
        This method homes the gantry to its reference position, which is useful
        for establishing a known starting point before operations or after
        potential position drift.
        """
        logger.info("Homing qubot gantry...")
        self.qubot.home()
        self.pipette.initialize()
        logger.info("Qubot gantry homing complete")
        
    @command
    def shutdown(self):
        """
        Gracefully shut down the machine by disconnecting all controllers.
        
        This method ensures all connections are properly closed and resources are released.
        """
        logger.info("Shutting down machine and disconnecting all controllers")
        self.qubot.disconnect()
        self.pipette.disconnect()
        logger.info("Machine shutdown complete")
    
    ### Queue (public commands) ###
    async def get_position(self) -> Dict[str, Union[Dict[str, float], int]]:
        """
        Get the current position of the machine. Queries only configured controllers.

        Returns:
            Dictionary containing the current position of the machine and its components (qubot, pipette).
        """
        qubot_position = await self.qubot.get_position()
        satorius_position = self.pipette.get_position()
        return {
            "qubot": qubot_position.to_dict(),
            "pipette": satorius_position,
        }
    @command
    def get_deck(self):
        """
        Get the current deck layout.
        
        Returns:
            Dictionary mapping deck slot names (e.g., "A1") to labware classes.
        
        Raises:
            None
        """
        return self.deck.to_dict()
        
    @command
    def load_labware(self, deck_slot: str, labware_name: str):
        """
        Load a labware object into a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            labware_name: Name of the labware class to load
        
        Raises:
            KeyError: If deck_slot is not found in deck
        """
        logger.info("Loading labware '%s' into deck slot '%s'", labware_name, deck_slot)
        self.deck.load_labware(slot=deck_slot, labware_name=labware_name)
        logger.debug("Labware '%s' loaded into deck slot '%s'", labware_name, deck_slot)

    @command
    def remove_labware(self, deck_slot: str):
        """
        Remove labware from a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
        
        Raises:
            KeyError: If deck_slot is not found in deck
        """
        self.deck.empty_slot(slot=deck_slot)
        logger.debug("Deck slot '%s' emptied", deck_slot)
        
    @command
    def load_deck(self, layout: Dict[str, str]):
        """
        Load multiple labware into the deck at once.
        
        Args:
            deck_layout: Dictionary mapping deck slot names (e.g., "A1") to labware strings.
        
        Example:
            machine.load_deck({
                "A1": "opentrons_96_tiprack_300ul",
                "B1": "polyelectric_8_wellplate_30000ul",
                "C1": "trash_bin",
            })
        """
        logger.info("Loading deck layout with %d labware items", len(layout))
        for deck_slot, labware_name in layout.items():
            self.load_labware(deck_slot=deck_slot, labware_name=labware_name)
        logger.info("Deck layout loaded successfully")

    @command
    def move_to_well(self, *, deck_slot: str, well_name: str) -> Dict[str, float]:
        """Move to the top of a loaded labware well without liquid handling."""
        logger.info("Moving to deck slot '%s', well '%s'", deck_slot, well_name)
        pos = self._get_absolute_z_position(deck_slot, well_name)
        self.qubot.move_absolute(position=pos)
        logger.info("Move to well completed at %s", pos)
        return pos.to_dict()

    @command
    def move_z_relative(self, *, distance_mm: float) -> Dict[str, float]:
        """Move only the Z axis by a signed relative distance in millimetres."""
        logger.info("Moving Z axis relative by %s mm", distance_mm)
        pos = self.qubot.move_relative(position=Position(z=distance_mm))
        logger.info("Relative Z move completed at %s", pos)
        return pos.to_dict()
        
    ### Pipette operations ###
    @command
    def attach_tip(self, deck_slot: str, well_name: str):
        """
        Attach a tip from a deck slot and well.

        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Well name (e.g., 'A1' for a well in a tiprack)
        
        Note:
            This method is idempotent - if a tip is already attached, it will
            log a warning and return successfully without raising an error.
        """
        if self.pipette.is_tip_attached():
            logger.warning("Tip already attached - skipping attachment (idempotent operation)")
            return
        
        logger.info("Attaching tip from deck slot '%s'%s", deck_slot, f", well '{well_name}'" if well_name else "")
        pos = self._get_absolute_z_position(deck_slot, well_name)
        logger.debug("Moving to position %s for tip attachment", pos)
        # return the offset from the origin
        self.qubot.move_absolute(position=pos)
        
        # attach tip (move slowly down)
        labware = self.deck[deck_slot]
        if labware is None:
            logger.error("Cannot attach tip: no labware loaded in deck slot '%s'", deck_slot)
            raise ValueError(f"No labware loaded in deck slot '{deck_slot}'. Load labware before attaching tips.")
        logger.debug("Moving down by %s mm to insert tip", labware.get_insert_depth())
        self.qubot.move_relative(
            position=Position(z=-labware.get_insert_depth()),
            feed=500
        )
        self.pipette.set_tip_attached(attached=True)
        logger.info("Tip attached successfully, homing Z axis")
        # must home Z axis after, as pressing in tip might cause it to lose steps
        self.qubot.home(axis="Z")
        logger.debug("Z axis homed after tip attachment")
        
    @command
    def drop_tip(self, *, deck_slot: str, well_name: str, height_from_bottom: float = 0.0):
        """
        Drop a tip into a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Well name within the deck slot (e.g., 'A1' for a well in a tiprack)
            height_from_bottom: Height from the bottom of the well in mm. Defaults to 0.0.
                               Must be non-negative. Positive values move up from the bottom.
        
        Raises:
            ValueError: If no tip is attached, if height_from_bottom is negative, or if
                       the resulting position is outside the Z axis limits.
        """
        if height_from_bottom < 0:
            logger.error("height_from_bottom must be non-negative, got %f", height_from_bottom)
            raise ValueError(f"height_from_bottom must be non-negative, got {height_from_bottom}")
        
        if not self.pipette.is_tip_attached():
            logger.error("Cannot drop tip: no tip attached")
            raise ValueError("Tip not attached")
        
        logger.info("Dropping tip into deck slot '%s', well '%s'", deck_slot, well_name)
        pos = self._get_absolute_z_position(deck_slot, well_name)
        # add height from bottom
        pos += Position(z=height_from_bottom)
        logger.debug("Moving to position %s for tip drop", pos)
        self.qubot.move_absolute(position=pos)

        logger.debug("Ejecting tip")
        self.pipette.eject_tip()
        time.sleep(5)
        self.pipette.set_tip_attached(attached=False)
        logger.info("Tip dropped successfully")
        
    @command
    def aspirate_from(self, *, deck_slot: str, well_name: str, amount: int, height_from_bottom: float = 0.0):
        """
        Aspirate a volume of liquid from a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Well name within the deck slot (e.g., 'A1')
            amount: Volume to aspirate in µL
            height_from_bottom: Height from the bottom of the well in mm. Defaults to 0.0.
                               Must be non-negative. Positive values move up from the bottom.
        
        Raises:
            ValueError: If no tip is attached, if height_from_bottom is negative, or if
                       the resulting position is outside the Z axis limits.
        """
        if height_from_bottom < 0:
            logger.error("height_from_bottom must be non-negative, got %f", height_from_bottom)
            raise ValueError(f"height_from_bottom must be non-negative, got {height_from_bottom}")
        
        if not self.pipette.is_tip_attached():
            logger.error("Cannot aspirate: no tip attached")
            raise ValueError("Tip not attached")
        
        logger.info("Aspirating %d µL from deck slot '%s', well '%s'", amount, deck_slot, well_name)

        pos = self._get_absolute_z_position(deck_slot, well_name)
        # add height from bottom
        pos += Position(z=height_from_bottom)
        # subtract insert depth to get the bottom of the well
        pos -= Position(z=self.deck[deck_slot].get_insert_depth())

        logger.debug("Moving Z axis to position %s", pos)
        self.qubot.move_absolute(position=pos)
        logger.debug("Aspirating %d µL", amount)
        self.pipette.aspirate(amount=amount)
        time.sleep(5)
        logger.info("Aspiration completed: %d µL from deck slot '%s', well '%s'", amount, deck_slot, well_name)
        
    @command
    def dispense_to(self, *, deck_slot: str, well_name: str, amount: int, height_from_bottom: float = 0.0):
        """
        Dispense a volume of liquid to a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Well name within the deck slot (e.g., 'A1')
            amount: Volume to dispense in µL
            height_from_bottom: Height from the bottom of the well in mm. Defaults to 0.0.
                               Must be non-negative. Positive values move up from the bottom.
        
        Raises:
            ValueError: If no tip is attached, if height_from_bottom is negative, or if
                       the resulting position is outside the Z axis limits.
        """
        if height_from_bottom < 0:
            logger.error("height_from_bottom must be non-negative, got %f", height_from_bottom)
            raise ValueError(f"height_from_bottom must be non-negative, got {height_from_bottom}")
        
        if not self.pipette.is_tip_attached():
            logger.error("Cannot dispense: no tip attached")
            raise ValueError("Tip not attached")
        
        logger.info("Dispensing %d µL to deck slot '%s', well '%s'", amount, deck_slot, well_name)

        pos = self._get_absolute_z_position(deck_slot, well_name)
        # add height from bottom
        pos += Position(z=height_from_bottom)
        # subtract insert depth to get the bottom of the well
        pos -= Position(z=self.deck[deck_slot].get_insert_depth())

        logger.debug("Moving Z axis to position %s", pos)
        self.qubot.move_absolute(position=pos)
        logger.debug("Dispensing %d µL", amount)
        self.pipette.dispense(amount=amount)
        time.sleep(5)
        logger.info("Dispense completed: %d µL to deck slot '%s', well '%s'", amount, deck_slot, well_name)
        
    @command
    def blowout(self, *, return_position: Optional[int] = None):
        """
        Blow out the pipette.
        
        Args:
            return_position: Optional position to return to after blowout. Defaults to None.
        """
        logger.info("Blowing out pipette")
        self.pipette.run_blowout(return_position=return_position)
        logger.info("Blowout completed")

    # Helper methods
    def _get_slot_origin(self, deck_slot: str) -> Position:
        """
        Get the origin coordinates of a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            
        Returns:
            Position for the deck slot origin
            
        Raises:
            KeyError: If deck_slot name is invalid
        """
        deck_slot = deck_slot.upper()
        if deck_slot not in self.SLOT_ORIGINS:
            logger.error("Invalid deck slot name: '%s'. Must be one of %s", deck_slot, list(self.SLOT_ORIGINS.keys()))
            raise KeyError(f"Invalid deck slot name: {deck_slot}. Must be one of {list(self.SLOT_ORIGINS.keys())}")
        pos = self.SLOT_ORIGINS[deck_slot]
        logger.debug("Deck slot origin for '%s': %s", deck_slot, pos)
        return pos
    
    def _get_absolute_z_position(self, deck_slot: str, well_name: Optional[str] = None) -> Position:
        """
        Get the absolute position for a deck slot (and optionally a well within that deck slot) based on the origin
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Optional well name within the deck slot (e.g., 'A1' for a well in a tiprack)
            
        Returns:
            Position with absolute coordinates
            
        Raises:
            ValueError: If well_name is specified but no labware is loaded in the deck slot
        """
        # Get deck slot origin
        pos = self._get_slot_origin(deck_slot)

        # relative well position from deck slot origin
        if well_name:
            labware = self.deck[deck_slot]
            if labware is None:
                logger.error("Cannot get well position: no labware loaded in deck slot '%s'", deck_slot)
                raise ValueError(f"No labware loaded in deck slot '{deck_slot}'. Load labware before accessing wells.")
            well_pos = labware.get_well_position(well_name).get_xy()
            # The MOF deck mounts labware with the row direction reversed
            # after the XY axis swap. Mirror the labware Y coordinate across
            # the occupied well grid so physical A..H matches logical A..H.
            well_y_positions = [
                labware.get_well_position(well).y for well in labware.wells
            ]
            mirrored_y = min(well_y_positions) + max(well_y_positions) - well_pos.y
            pos += Position(x=mirrored_y, y=well_pos.x)
            # get z
            pos += Position(z=labware.get_height() - self.CEILING_HEIGHT)
            # Trash-bin moves always assume a physical disposable tip is
            # attached. A full home/Sartorius initialization can clear the
            # software tip flag while leaving the physical tip in place.
            assume_tip_for_trash = labware.name.startswith("trash_bin")
            if self.pipette.is_tip_attached() or assume_tip_for_trash:
                if assume_tip_for_trash and not self.pipette.is_tip_attached():
                    logger.warning(
                        "Applying the %s mm tip offset for trash labware '%s' despite cleared software tip state",
                        self.TIP_LENGTH,
                        labware.name,
                    )
                pos += Position(z=self.TIP_LENGTH)
            logger.debug("Absolute Z position for deck slot '%s', well '%s': %s", deck_slot, well_name, pos)
        else:
            logger.debug("Absolute Z position for deck slot '%s': %s", deck_slot, pos)
        return pos
    
    ### Control (immediate commands) ###
    
    @command
    def pause(self):
        """
        Pause the execution of queued commands.
        """
        print("Pausing machine")
    
    @command
    def resume(self):
        """
        Resume the execution of queued commands.
        """
        print("Resuming machine")

    @command
    def cancel(self):
        """
        Cancel the execution of queued commands.
        """
        print("Cancelling machine")

    @command
    def reset(self) -> bool:
        """
        Software reset. Disconnects, reconnects, homes the gantry, and initializes the pipette.

        Returns:
            bool: True if the machine restarted
        """
        self.shutdown()
        self.startup()
        return True