"""pipqubot-xl: gantry 004-4unit-reprap-http.

Reference hardware config. A site edge copies this into its own code and
fills the blanks. Ports and hosts come from the edge's .env. Nothing here
opens a port at import.
"""

import os

from qubot.gantry import Frame
from qubot.gantry.reprap_http import RepRapHTTPController
from qubot.end_effector import rline_50_1000
from qubot.end_effector.a_axis_capper import Capper

FRAME = Frame(
    axes=('X', 'Y', 'Z', 'A'),
    hardware_limits={"X": (0, 345), "Y": (-490, 0), "Z": (-170, 0), "A": (-170, 0)},
    default_deck={"rows": 4, "cols": 4},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Fill per edge: True or False.
HOME_ON_STARTUP = None

# Fill per edge: safety text and confirm for each command the edge advertises.
COMMANDS = {
    "reconcile_tip_attached": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "dispense_to_proxy_vial": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "move_capper": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "move_to_well": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
}

# Pipette serial port env: SATORIUS_PORT. Axis: Z.

# Rides gantry axis A. No port of its own.
CAPPER = Capper(axis='A', tool_length_mm=2, mount_offset_x_mm=60)


def connect_gantry() -> RepRapHTTPController:
    """Open the gantry and apply this machine's limits."""
    gantry = RepRapHTTPController(host=os.environ["GANTRY_HOST"])
    gantry.connect()
    FRAME.apply_axis_limits(gantry, SOFT_LIMITS)
    return gantry


def connect_pipette():
    pipette = rline_50_1000.connect(os.environ["SATORIUS_PORT"])
    pipette.connect()
    return pipette
