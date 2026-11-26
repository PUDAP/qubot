"""syringequbot: gantry 002-1unit-reprap-http.

Reference hardware config. A site edge copies this into its own code and
fills the blanks. Ports and hosts come from the edge's .env. Nothing here
opens a port at import.

The RepRap HTTP driver includes `set_pin`.
Firmware travel is X 0 to 140, Y -170 to 0, Z -175 to 0. A later observation
that Z past -125 meets the current vial holder is not stored as a limit.
"""

import os

from qubot.gantry import Frame
from qubot.gantry.reprap_http import RepRapHTTPController
from qubot.end_effector.autosampler_syringe import narrow_z

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (0.0, 140.0), "Y": (-170.0, 0.0), "Z": (-175.0, 0.0)},
    default_deck={"rows": 2, "cols": 2},
)

# Soft limits inside FRAME, or None for the hardware limits.
SOFT_LIMITS = None

# Fill per edge: True or False.
HOME_ON_STARTUP = None

# Fill per edge: safety text and confirm for each command the edge advertises.
COMMANDS = {
    "home": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "move_to": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "safe_move_to": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
    "reset": {"summary": "", "hazards": [], "requires": "", "forbidden_when": "", "confirm": None},
}

# Syringe plus the current IMRE vial holder, not the needle alone. Travel past
# Z = -125 was observed to knock the needle into the base of the mounted vial
# holder (-175 firmware Z + 50). Clearance figure, not an axis limit. Remeasure
# if the vial holder changes.
SYRINGE_LENGTH_MM = 50
Z_LIMITS = narrow_z(FRAME.hardware_limits["Z"], SYRINGE_LENGTH_MM)


def connect_gantry() -> RepRapHTTPController:
    """Open the gantry and apply this machine's limits."""
    gantry = RepRapHTTPController(host=os.environ["GANTRY_HOST"])
    gantry.connect()
    FRAME.apply_axis_limits(gantry, SOFT_LIMITS)
    return gantry
