"""miniqubot: gantry 001-1unit-grbl-serial.

Reference hardware config. A site edge copies this into its own code and
fills the blanks. Ports and hosts come from the edge's .env. Nothing here
opens a port at import.
"""

import os

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (0.0, 175.0), "Y": (-190.0, 0.0), "Z": (-75.0, 0.0)},
    default_deck={"rows": 2, "cols": 2},
    expected_identity='[VER:1.1h.20190830:]',
    required_settings={20: 1.0, 21: 1.0, 22: 1.0, 23: 1.0, 130: 175.0, 131: 190.0, 132: 75.0},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Fill per edge: True or False.
HOME_ON_STARTUP = None

# Fill per edge: safety text and confirm for each command the edge advertises.
COMMANDS = {
    "home": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "move_absolute": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "move_relative": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
}


def connect_gantry() -> GrblHALController:
    """Open the gantry and apply this machine's limits."""
    gantry = GrblHALController(port_name=os.environ["GANTRY_PORT"])
    gantry.connect()
    FRAME.apply_axis_limits(gantry, SOFT_LIMITS)
    return gantry
