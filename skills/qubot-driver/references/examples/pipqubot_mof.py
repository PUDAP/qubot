"""pipqubot-mof: 2-unit, GRBL over serial (GrblHALController) gantry.

Starting-point driver.py for this machine. Copy it into the edge, pass the
ports from main.py's Config, review every @safety text, and add the
machine's own commands. Importing this file opens no port; Driver() does.

Commands the earlier edge advertised: `home`, `move_to_well`,
`move_z_relative`, `reconcile_tip_attached`, `attach_tip`, `drop_tip`,
`aspirate_from`, `dispense_to`, `blowout`.
"""

from pathlib import Path

from puda import command, safety

from qubot.gantry import Frame, GrblHALController
from qubot.end_effector import rline_50_1000
from qubot.geometry import Position
from qubot.labware import Deck, get_available_labware

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (0, 161.7), "Y": (-444, 0), "Z": (-175, 0)},
    default_deck={"rows": 4, "cols": 2},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Review per edge.
HOME_ON_STARTUP = False

# The edge's own labware definitions (<name>.json), searched before the bundled
# ones. See references/labware/vial_rack_2x2.json in the qubot-driver skill.
LABWARE_DIR = Path(__file__).resolve().parent / "labware"


class Driver:
    """Pipqubot-mof: 2-unit GRBL gantry with a Sartorius rLine 50-1000 µL pipette."""

    def __init__(self, gantry_port: str, pipette_port: str) -> None:
        """Open the hardware and apply this machine's limits.

        Args:
            gantry_port: Serial port of the gantry controller, from main.py Config (GANTRY_PORT).
            pipette_port: Serial port of the rLine pipette (SATORIUS_PORT).
        """
        self._gantry = GrblHALController(port_name=gantry_port)
        self._gantry.connect()
        FRAME.apply_axis_limits(self._gantry, SOFT_LIMITS)
        self._pipette = rline_50_1000.connect(pipette_port)
        self._pipette.connect()
        self._deck = Deck.from_frame(FRAME, labware_paths=[LABWARE_DIR])
        if HOME_ON_STARTUP:
            self.home()

    def shutdown(self) -> bool:
        """Hook: close every port before the edge stops."""
        self._pipette.disconnect()
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
    def list_labware(self) -> dict[str, dict[str, list[str]]]:
        """Labware this edge can load: its own labware/ folder plus the bundled definitions.

        Returns:
            dict[str, dict[str, list[str]]]: Labware name to its row and column labels.
        """
        return get_available_labware([LABWARE_DIR])

    @command
    def load_labware(self, slot: str, labware_name: str) -> dict[str, str | None]:
        """Record which labware sits in a deck slot. Nothing moves.

        Args:
            slot: Deck slot, for example "A1".
            labware_name: A name from list_labware, for example "vial_rack_2x2".

        Returns:
            dict[str, str | None]: The whole deck, slot to labware name.

        Raises:
            KeyError: If the slot is not on this deck.
            FileNotFoundError: If no definition has that name.
        """
        self._deck.load_labware(slot, labware_name)
        return self._deck.to_dict()

    @command
    def get_deck(self) -> dict[str, str | None]:
        """Current deck layout.

        Returns:
            dict[str, str | None]: Slot to labware name, None for empty slots.
        """
        return self._deck.to_dict()

    @command
    def get_position(self) -> dict[str, float]:
        """Position the gantry controller is tracking.

        Returns:
            dict[str, float]: Axis positions in mm.
        """
        return self._gantry.get_internal_position().to_dict()
