"""
PipQuBot XL machine class containing Deck, RepRapController, and SatoriusController.

This class demonstrates the integration of:
- RepRapController: Handles motion control (hardware-specific)
- Deck: Manages labware layout (configuration-agnostic)
- SatoriusController: Handles liquid handling operations
"""

import asyncio
import inspect
import logging
import math
import time
from typing import Any, Optional, Dict, Tuple, Union
from puda import command, machine_state, safety, tlm_stream
from qubot_drivers.move import RepRapController, Deck
from qubot_drivers.move.reprap_http import RepRapHTTPController
from qubot_drivers import Position
from qubot_drivers.rline import RLineModel
from qubot_drivers.satorius import SatoriusController

logger = logging.getLogger(__name__)


class PipQuBotXL:
    """
    PipQuBot XL machine integrating motion control, deck management, and liquid handling.
    
    The deck has 16 slots arranged in a 4x4 grid (A1-D4).
    Each slot's origin location is stored for absolute movement calculation.
    """
    CEILING_HEIGHT = 244 # Height from z and a origin to the deck

    # Pipette
    Z_ORIGIN = Position(x=0, y=0, z=0)
    TIP_LENGTH = 97  # Pipette tip length in mm
    # BRL1000-1 is the rLine 50-1000 µL head: 2.5 µL/step (manual v1.1 Table 1).
    # 100 µL is RI40 and 1000 µL is RI400.
    PIPETTE_MODEL = RLineModel.UL_50_1000
    
    # Capper (vertical travel on the A axis)
    CAPPER_ORIGIN = Position(x=60, y=0, a=0)
    CAPPER_LENGTH = 2  # Distance from the A-axis origin to the capper tip in mm
    
    # Default axis limits - customize based on your hardware
    DEFAULT_AXIS_LIMITS = {
        "X": (0, 345),
        "Y": (-490, 0),
        "Z": (-170, 0),
        "A": (-170, 0),
    }
    
    # Slot origins (the bottom left corner of each deck slot relative to the deck origin)
    SLOT_ORIGINS = {
        "A1": Position(x=4.3, y=-470.3),
        "A2": Position(x=104.3, y=-470.3),
        "A3": Position(x=204.3, y=-470.3),
        "A4": Position(x=304.3, y=-470.3),
        "B1": Position(x=4.3, y=-320.3),
        "B2": Position(x=104.3, y=-320.3),
        "B3": Position(x=204.3, y=-320.3),
        "B4": Position(x=304.3, y=-320.3),
        "C1": Position(x=4.3, y=-170.3),
        "C2": Position(x=104.3, y=-170.3),
        "C3": Position(x=204.3, y=-170.3),
        "C4": Position(x=304.3, y=-170.3),
        "D1": Position(x=4.3, y=-20.3),
        "D2": Position(x=104.3, y=-20.3),
        "D3": Position(x=204.3, y=-20.3),
        "D4": Position(x=304.3, y=-20.3),
    }

    PROXY_VIAL_CALIBRATION_ID = "70792568-cf46-493a-8ce6-5fdf08025df6"
    PROXY_VIAL_POSITIONS = {
        "A1": Position(x=318.5, y=-310.0, z=-28.5),
        "A2": Position(x=318.5, y=-290.0, z=-28.5),
        "A3": Position(x=318.5, y=-270.0, z=-28.5),
        "A4": Position(x=318.5, y=-250.0, z=-28.5),
        "A5": Position(x=318.5, y=-230.0, z=-28.5),
        "A6": Position(x=318.5, y=-210.0, z=-28.5),
        "B1": Position(x=338.0, y=-310.0, z=-28.5),
        "B2": Position(x=338.0, y=-290.0, z=-28.5),
        "B3": Position(x=338.0, y=-270.0, z=-28.5),
        "B4": Position(x=338.0, y=-250.0, z=-28.5),
        "B5": Position(x=338.0, y=-230.0, z=-28.5),
        "B6": Position(x=338.0, y=-210.0, z=-28.5),
    }
    
    def __init__(
        self,
        qubot_port: Optional[str] = None,
        satorius_port: Optional[str] = None,
        qubot_ip: Optional[str] = None,
        axis_limits: Optional[Dict[str, Tuple[float, float]]] = None,
    ):
        """
        Initialize the PipQuBot XL machine.

        Either qubot_port or qubot_ip, plus satorius_port, must be specified.

        Args:
            qubot_port: Serial port for RepRapController (e.g., '/dev/ttyACM0').
            satorius_port: Serial port for SatoriusController (e.g., '/dev/ttyUSB0').
            qubot_ip: Hostname or IP for RepRapHTTPController.
            axis_limits: Dictionary mapping axis names to (min, max) limits. Defaults to DEFAULT_AXIS_LIMITS.

        Raises:
            ValueError: If qubot_port or satorius_port is not specified.
        """
        if (qubot_port is None) == (qubot_ip is None):
            raise ValueError("exactly one of qubot_port or qubot_ip is required")
        if satorius_port is None:
            raise ValueError("satorius_port is required")

        # Initialize deck
        self.deck = Deck(rows=4, cols=4)

        if qubot_ip is not None:
            self.qubot = RepRapHTTPController(host=qubot_ip)
        else:
            self.qubot = RepRapController(port_name=qubot_port)
        limits = axis_limits or self.DEFAULT_AXIS_LIMITS
        for axis, (min_val, max_val) in limits.items():
            self.qubot.set_axis_limits(axis, min_val, max_val)

        self.pipette = SatoriusController(
            port_name=satorius_port,
            model=self.PIPETTE_MODEL,
        )

        logger.info(
            "PipQuBot XL machine initialized: qubot=%s, satorius_port=%s",
            qubot_ip or qubot_port,
            satorius_port,
        )

    ### State ###
    @machine_state
    def snapshot(self) -> Dict[str, Any]:
        """Deck layout merged into MACHINE_STATE updates."""
        return {"deck": self.deck.to_dict()}

    ### Telemetry streams ###
    @tlm_stream(interval=3.0, name="pos")
    def position_stream(self) -> Dict[str, Union[Dict[str, float], int]]:
        """Current position of the qubot gantry and pipette."""
        # Runs in a worker thread with no event loop, so asyncio.run is safe here.
        return asyncio.run(self.get_position())

    def startup(
        self,
        *,
        home_gantry: bool = True,
        initialize_pipette: bool = True,
    ):
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

        if home_gantry:
            logger.info("Homing gantry...")
            self.qubot.home()
        else:
            logger.info("Skipping gantry homing by configuration")
        if initialize_pipette:
            logger.info("Initializing pipette...")
            self.pipette.initialize()
            time.sleep(3)  # need to wait for the pipette to initialize
        else:
            logger.info("Skipping pipette initialization by configuration")
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
        qubot_position = self.qubot.get_position()
        if inspect.isawaitable(qubot_position):
            qubot_position = await qubot_position
        return {
            "qubot": qubot_position.to_dict(),
            "pipette": self.pipette.get_position(),
        }

    @command
    def get_pipette_info(self) -> Dict[str, int | str]:
        """Return read-only Sartorius model, firmware, piston position, and tracked volume."""
        return self.pipette.get_device_info()

    @command
    def get_deck(self) -> Dict[str, str]:
        """
        Get the current deck layout.
        
        Returns:
            Dictionary mapping deck slot names (e.g., "A1") to labware classes.
        
        Raises:
            None
        """
        return self.deck.to_dict()
        
    @command
    def load_labware(self, deck_slot: str, labware_name: str) -> Dict[str, str]:
        """
        Load a labware object into a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            labware_name: Name of the labware class to load
        
        Returns:
            Dictionary with the normalized deck_slot and labware_name that was loaded.
        
        Raises:
            KeyError: If deck_slot is not found in deck
        """
        logger.info("Loading labware '%s' into deck slot '%s'", labware_name, deck_slot)
        self.deck.load_labware(slot=deck_slot, labware_name=labware_name)
        logger.debug("Labware '%s' loaded into deck slot '%s'", labware_name, deck_slot)
        return {"deck_slot": deck_slot.upper(), "labware_name": labware_name}

    @command
    def remove_labware(self, deck_slot: str) -> Dict[str, str]:
        """
        Remove labware from a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')

        Returns:
            Dictionary with the normalized deck_slot that was emptied.
        
        Raises:
            KeyError: If deck_slot is not found in deck
        """
        self.deck.empty_slot(slot=deck_slot)
        logger.debug("Deck slot '%s' emptied", deck_slot)
        return {"deck_slot": deck_slot.upper()}
        
    @command
    def load_deck(self, layout: Dict[str, str]) -> Dict[str, Dict[str, str | None]]:
        """
        Load multiple labware into the deck at once.
        
        Args:
            deck_layout: Dictionary mapping deck slot names (e.g., "A1") to labware strings.

        Returns:
            Dictionary with the full deck layout after loading.
        
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
        return {"layout": self.get_deck()}
        
    ### Pipette operations ###
    @command
    @safety(
        summary="Reconciles software tip state with an operator-confirmed attached physical tip after an edge restart.",
        hazards=["physical/software tip-state mismatch"],
        requires="The operator has freshly confirmed that exactly one disposable tip is physically attached and the tip contains no liquid.",
        forbidden_when="Do not reconcile if tip attachment or retained liquid is uncertain.",
        confirm=True,
    )
    def reconcile_tip_attached(self, *, physical_tip_confirmed: bool) -> Dict[str, bool]:
        """Restore software attachment state without moving hardware.

        Args:
            physical_tip_confirmed: Must be true after direct operator confirmation.

        Returns:
            Dictionary containing the reconciled software tip state.

        Raises:
            ValueError: If explicit physical confirmation is absent.
        """
        if physical_tip_confirmed is not True:
            raise ValueError("physical_tip_confirmed must be true")
        self.pipette.set_tip_attached(attached=True)
        return {"tip_attached": True}

    @command
    def attach_tip(self, deck_slot: str, well_name: str) -> Dict[str, bool]:
        """
        Attach a tip from a deck slot and well.

        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Well name (e.g., 'A1' for a well in a tiprack)

        Returns:
            Dictionary with skipped set to True if attachment was skipped, False otherwise.

        Note:
            This method is idempotent - if a tip is already attached, it will
            log a warning and return successfully without raising an error.
        """
        if self.pipette.is_tip_attached():
            logger.warning("Tip already attached - skipping attachment (idempotent operation)")
            return {"skipped": True}
        
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
        return {"skipped": False}
        
    @command
    def drop_tip(self, *, deck_slot: str, well_name: str, height_from_bottom: float = 0.0) -> Dict[str, Any]:
        """
        Drop a tip into a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Well name within the deck slot (e.g., 'A1' for a well in a tiprack)
            height_from_bottom: Height from the bottom of the well in mm. Defaults to 0.0.
                               Must be non-negative. Positive values move up from the bottom.

        Returns:
            Dictionary with deck_slot, well_name, and height_from_bottom.
        
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
        return {
            "deck_slot": deck_slot.upper(),
            "well_name": well_name,
            "height_from_bottom": height_from_bottom,
        }
        
    @command
    def aspirate_from(self, *, deck_slot: str, well_name: str, amount: int, height_from_bottom: float = 0.0) -> Dict[str, Any]:
        """
        Aspirate a volume of liquid from a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Well name within the deck slot (e.g., 'A1')
            amount: Volume to aspirate in µL
            height_from_bottom: Height from the bottom of the well in mm. Defaults to 0.0.
                               Must be non-negative. Positive values move up from the bottom.

        Returns:
            Dictionary with deck_slot, well_name, amount, and height_from_bottom.
        
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
        return {
            "deck_slot": deck_slot.upper(),
            "well_name": well_name,
            "amount": amount,
            "height_from_bottom": height_from_bottom,
        }
        
    @command
    def dispense_to(self, *, deck_slot: str, well_name: str, amount: int, height_from_bottom: float = 0.0) -> Dict[str, Any]:
        """
        Dispense a volume of liquid to a deck slot.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Well name within the deck slot (e.g., 'A1')
            amount: Volume to dispense in µL
            height_from_bottom: Height from the bottom of the well in mm. Defaults to 0.0.
                               Must be non-negative. Positive values move up from the bottom.

        Returns:
            Dictionary with deck_slot, well_name, amount, and height_from_bottom.
        
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
        return {
            "deck_slot": deck_slot.upper(),
            "well_name": well_name,
            "amount": amount,
            "height_from_bottom": height_from_bottom,
        }

    @command
    @safety(
        summary="Retracts Z and capper A to safe transit height, moves XY to a calibrated proxy vial, descends Z, restores A, and dispenses liquid.",
        hazards=["collision", "pinch point", "chemical exposure", "capper A-axis motion"],
        requires="Gantry Z and capper A axis homed; operator-confirmed 345 mm X travel; calibrated proxy rack unchanged; attached tip and tracked liquid state reconciled; capper and tip transit paths clear.",
        forbidden_when="Do not run if the proxy rack moved, the destination is occupied beyond capacity, or tip/liquid state is uncertain.",
        confirm=False,
    )
    def dispense_to_proxy_vial(self, *, well_name: str, amount: int) -> Dict[str, Any]:
        """Dispense at a calibrated absolute proxy-vial position.

        Args:
            well_name: Proxy rack well A1-A6 or B1-B6.
            amount: Positive volume to dispense in microlitres.

        Returns:
            Well, volume, calibrated machine coordinates, and calibration UUID.

        Raises:
            KeyError: If the proxy well is unknown.
            ValueError: If amount is nonpositive or no tip is attached.
        """
        well_name = well_name.upper()
        if well_name not in self.PROXY_VIAL_POSITIONS:
            raise KeyError(f"Unknown proxy vial well: {well_name}")
        if amount <= 0:
            raise ValueError(f"Dispense amount must be positive, got {amount}")
        if not self.pipette.is_tip_attached():
            raise ValueError("Tip not attached")
        tracked_volume = self.pipette.get_tracked_volume()
        if amount > tracked_volume:
            raise ValueError(
                f"Dispense amount {amount} uL exceeds tracked aspirated volume "
                f"{tracked_volume} uL"
            )

        calibrated = self.PROXY_VIAL_POSITIONS[well_name]
        position = Position(x=calibrated.x, y=calibrated.y, z=calibrated.z)
        self.qubot.move_absolute(position=position)
        self.pipette.dispense(amount=amount)
        time.sleep(5)
        return {
            "well_name": well_name,
            "amount": amount,
            "x": position.x,
            "y": position.y,
            "z": position.z,
            "calibration_id": self.PROXY_VIAL_CALIBRATION_ID,
        }
        
    @command
    def blowout(self, *, return_position: Optional[int] = None) -> Dict[str, Any]:
        """
        Blow out the pipette.
        
        Args:
            return_position: Optional position to return to after blowout. Defaults to None.

        Returns:
            Dictionary with the return_position used for the blowout, if any.
        """
        logger.info("Blowing out pipette")
        self.pipette.run_blowout(return_position=return_position)
        logger.info("Blowout completed")
        return {"return_position": return_position}

    # Capper operations
    @command
    @safety(
        summary="Moves the capper head over labware and lowers it on the A axis.",
        hazards=["collision", "pinch point"],
        requires="The gantry is homed, the target labware is loaded, and the path is clear.",
    )
    def move_capper(self, deck_slot: str, well_name: str, height_from_bottom: float = 0.0) -> Dict[str, Any]:
        """
        Move the capper head to a deck slot using A for vertical travel.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Well name within the deck slot (e.g., 'A1')
            height_from_bottom: Height from the bottom of the well in mm. Defaults to 0.0.
                               Must be non-negative. Positive values move up from the bottom.

        Returns:
            Dictionary with deck_slot, well_name, and height_from_bottom.
        
        Raises:
            ValueError: If height_from_bottom is negative.
        """
        if height_from_bottom < 0:
            logger.error("height_from_bottom must be non-negative, got %f", height_from_bottom)
            raise ValueError(f"height_from_bottom must be non-negative, got {height_from_bottom}")
        
        pos = self._get_absolute_capper_position(deck_slot, well_name)
        pos += Position(a=height_from_bottom)
        self.qubot.move_absolute(position=pos)
        logger.info("Capper moved to deck slot '%s', well '%s' at height %s mm from bottom", deck_slot, well_name, height_from_bottom)
        return {
            "deck_slot": deck_slot.upper(),
            "well_name": well_name,
            "height_from_bottom": height_from_bottom,
        }
        
    @command
    @safety(
        summary="Positions the pipette at the labware top plane or an optional height from the bottom without liquid handling.",
        hazards=["collision", "pinch point"],
        requires="Gantry homed, correct labware loaded, physical and software tip state consistent, and path clear.",
    )
    def move_to_well(
        self, *, deck_slot: str, well_name: str, height_from_bottom: Optional[float] = None
    ) -> Dict[str, float]:
        """Position at the labware top plane or an optional bottom-relative height.

        Uses the current slot calibration, labware transform and software tip
        offset. ``height_from_bottom=None`` preserves the top plane; a specified
        height in mm uses the same bottom reference as dispense_to, without
        pipetting or tip operations. Returns commanded machine coordinates in mm.

        Raises:
            ValueError: If height is nonfinite or negative, labware is missing,
                or the destination is outside the controller's axis limits.
        """
        if height_from_bottom is not None and (
            not math.isfinite(height_from_bottom) or height_from_bottom < 0
        ):
            raise ValueError("height_from_bottom must be finite and non-negative")
        deck_slot = deck_slot.upper()
        position = self._get_absolute_z_position(deck_slot, well_name)
        if height_from_bottom is not None:
            position += Position(z=height_from_bottom)
            position -= Position(z=self.deck[deck_slot].get_insert_depth())
        self.qubot.move_absolute(position=position)
        return position.to_dict()

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
            if labware.name in {
                "sartorious_96_tiprack_1000ul",
                "polyelectric_8_wellplate_30000ul",
                "bioshake",
            }:
                # XL mounting: the first row is at low machine X.
                row_coordinates = [well["y"] for well in labware._wells.values()]
                well_pos = Position(
                    x=well_pos.x,
                    y=min(row_coordinates) + max(row_coordinates) - well_pos.y,
                )
            # Preserve the existing transform for other labware.
            pos += well_pos.swap_xy()
            # get z
            pos += Position(z=labware.get_height() - self.CEILING_HEIGHT)
            # if tip attached, add tip length
            if self.pipette.is_tip_attached():
                pos += Position(z=self.TIP_LENGTH)
            logger.debug("Absolute Z position for deck slot '%s', well '%s': %s", deck_slot, well_name, pos)
        else:
            logger.debug("Absolute Z position for deck slot '%s': %s", deck_slot, pos)
        return pos
    
    def _get_absolute_capper_position(self, deck_slot: str, well_name: Optional[str] = None) -> Position:
        """
        Get the capper position, using A as the vertical axis.
        
        Args:
            deck_slot: Deck slot name (e.g., 'A1', 'B2')
            well_name: Optional well name within the deck slot (e.g., 'A1' for a well in a tiprack)
            
        Returns:
            Position with absolute coordinates
            
        Raises:
            ValueError: If well_name is specified but no labware is loaded in the deck slot
        """
        # get x and y
        pos = self._get_slot_origin(deck_slot)
        pos -= self.CAPPER_ORIGIN  # subtract the capper origin
        
        # Get labware for capper positioning
        labware = self.deck[deck_slot]
        if labware is None:
            logger.error("Cannot get capper position: no labware loaded in deck slot '%s'", deck_slot)
            raise ValueError(f"No labware loaded in deck slot '{deck_slot}'. Load labware before moving the capper.")
        
        # get x and y for well if specified
        if well_name:
            well_pos = labware.get_well_position(well_name).get_xy()
            pos += well_pos.swap_xy()
        
        # get a (applies to both with and without well_name)
        pos += Position(a=labware.get_height() - self.CEILING_HEIGHT)
        pos += Position(a=self.CAPPER_LENGTH)
        
        if well_name:
            logger.debug("Absolute capper position for deck slot '%s', well '%s': %s", deck_slot, well_name, pos)
        else:
            logger.debug("Absolute capper position for deck slot '%s': %s", deck_slot, pos)
        
        return pos

    ### Control (immediate commands) ###
    @command
    def pause(self):
        """
        Pause the execution of queued commands.
        """
        logger.info("Pausing machine")
    
    @command
    def resume(self):
        """
        Resume the execution of queued commands.
        """
        logger.info("Resuming machine")

    @command
    def cancel(self):
        """
        Cancel the execution of queued commands.
        """
        logger.info("Cancelling machine")
        
    @command
    def reset(self):
        """
        Reset the machine to its initial state.
        """
        logger.info("Resetting machine")