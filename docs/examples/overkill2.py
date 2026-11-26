"""overkill2: gantry 007-2unit-grblhal-serial.

Reference hardware config. A site edge copies this into its own code and
fills the blanks. Ports and hosts come from the edge's .env. Nothing here
opens a port at import.

Overkill2 (Liquid handling - pipette gantry). Limits key: `pipQubot`.
Frame travel is X −176 to 0, Y −480 to 0, Z −190 to 0. The frame is 2 by 1
units, so X may travel at most 300 mm and Y at most 600 mm. The uploaded spans
are 176 mm and 480 mm, both inside that allowance.
"""

import os

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector import rline_50_1000_multistep

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (-176, 0), "Y": (-480, 0), "Z": (-190, 0)},
    default_deck={"rows": 4, "cols": 2},
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

# Serial port env: SATORIUS_PORT. Axis: Z.
# step_resolution and response_time_s are the PESCador pipette calibration.
PIPETTE_STEP_RESOLUTION = 10
PIPETTE_RESPONSE_TIME_S = 1.03


def connect_gantry() -> GrblHALController:
    """Open the gantry and apply this machine's limits."""
    gantry = GrblHALController(port_name=os.environ["GANTRY_PORT"])
    gantry.connect()
    FRAME.apply_axis_limits(gantry, SOFT_LIMITS)
    return gantry


def connect_pipette():
    pipette = rline_50_1000_multistep.connect(
        os.environ["SATORIUS_PORT"],
        step_resolution=PIPETTE_STEP_RESOLUTION,
        response_time_s=PIPETTE_RESPONSE_TIME_S,
    )
    pipette.connect()
    return pipette
