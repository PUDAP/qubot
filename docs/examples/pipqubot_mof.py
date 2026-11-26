"""pipqubot-mof: gantry 003-2unit-grbl-serial.

Reference hardware config. A site edge copies this into its own code and
fills the blanks. Ports and hosts come from the edge's .env. Nothing here
opens a port at import.
"""

import os

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector import rline_50_1000

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (0, 161.7), "Y": (-444, 0), "Z": (-175, 0)},
    default_deck={"rows": 4, "cols": 2},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Fill per edge: True or False.
HOME_ON_STARTUP = None

# Fill per edge: safety text and confirm for each command the edge advertises.
COMMANDS = {
    "home": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "move_to_well": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "move_z_relative": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "reconcile_tip_attached": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "attach_tip": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "drop_tip": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "aspirate_from": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "dispense_to": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "blowout": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
}

# Pipette serial port env: SATORIUS_PORT. Axis: Z.


def connect_gantry() -> GrblHALController:
    """Open the gantry and apply this machine's limits."""
    gantry = GrblHALController(port_name=os.environ["GANTRY_PORT"])
    gantry.connect()
    FRAME.apply_axis_limits(gantry, SOFT_LIMITS)
    return gantry


def connect_pipette():
    pipette = rline_50_1000.connect(os.environ["SATORIUS_PORT"])
    pipette.connect()
    return pipette
