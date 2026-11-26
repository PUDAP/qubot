"""photoreactor: gantry 008-1unit-grblhal-serial.

Reference hardware config. A site edge copies this into its own code and
fills the blanks. Ports and hosts come from the edge's .env. Nothing here
opens a port at import.

Photoreactor (UV qubot). Limits key: `photoreactor`.
Frame travel is X −300 to 300, Y −199 to 0, Z −78 to 0. Y travel is 199 mm,
inside the 300 mm allowed for one unit. X is −300 to 300, a span of 600 mm,
which is past that allowance. The uploaded X range is kept and flagged for
correction.
"""

import os

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector.orion_4ch_led import LedBoard

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (-300, 300), "Y": (-199, 0), "Z": (-78, 0)},
    default_deck={"rows": 2, "cols": 2},
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

# Serial port env: LED_PORT. 9600 baud, 1 s timeout. A force_threshold value
# appears on one lamp config and is not used.


def connect_gantry() -> GrblHALController:
    """Open the gantry and apply this machine's limits."""
    gantry = GrblHALController(port_name=os.environ["GANTRY_PORT"])
    gantry.connect()
    FRAME.apply_axis_limits(gantry, SOFT_LIMITS)
    return gantry


def connect_led() -> LedBoard:
    led = LedBoard(os.environ["LED_PORT"], baud=9600, timeout_s=1.0)
    led.connect()
    return led
