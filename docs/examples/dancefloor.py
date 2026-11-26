"""dancefloor: gantry 006-1unit-grblhal-serial.

Reference hardware config. A site edge copies this into its own code and
fills the blanks. Ports and hosts come from the edge's .env. Nothing here
opens a port at import.

Dancefloor (Vacuum chamber). Limits key: `vacuum_chamber`.
Frame travel is X −116 to 0, Y −28 to 0, Z 0 to 0. Z has no travel. X travel
is 116 mm and Y travel is 28 mm, both inside the 300 mm allowed for one unit.
The combined pescador2 config says X low is −119. This frame keeps −116. The
chamber loading position X=−118 is outside this frame until that conflict is
confirmed. The limits file names a port placeholder `__dancefloor__`. That
value belongs in the site edge .env.
"""

import os

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector.vacuum_chamber import Chamber

# pescador2 config X low is -119. This frame keeps the dancefloor-alone value
# -116. The chamber loading position X=-118 is outside this frame until the
# limit is confirmed.
FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (-116, 0), "Y": (-28, 0), "Z": (0, 0)},
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

# Dancefloor lid and vacuum valve on the gantry port. Robot frame.
# Loading X = -118 is outside this frame's X low of -116. pescador2 uses -119.
# Confirm the frame before moving to the loading position.

def make_chamber() -> Chamber:
    """A fresh chamber state (open, vented) with this machine's positions."""
    return Chamber(
        loading_position=(-118.0, 0.0, 0.0),
        close_waypoints=[(-3.0, 0.0, 0.0), (-3.0, -27.0, 0.0)],
        vacuum_on_delay_s=5.0,
        vacuum_off_delay_s=5.0,
        valve_on='M8',
        valve_off='M9',
    )


def connect_gantry() -> GrblHALController:
    """Open the gantry and apply this machine's limits."""
    gantry = GrblHALController(port_name=os.environ["GANTRY_PORT"])
    gantry.connect()
    FRAME.apply_axis_limits(gantry, SOFT_LIMITS)
    return gantry
