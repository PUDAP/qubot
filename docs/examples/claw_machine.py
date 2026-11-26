"""claw-machine: gantry 005-8unit-grblhal-serial.

Reference hardware config. A site edge copies this into its own code and
fills the blanks. Ports and hosts come from the edge's .env. Nothing here
opens a port at import.

The frame is 2 by 4 units: 2 along Y and 4 along X.
Claw machine (Pick-and-place). Limits key: `claw_gantry`.
Frame travel is X 0 to 830, Y −280 to 0, Z −240 to 0. One unit may travel at
most 300 mm on X and on Y, so this frame may travel 1200 mm on X and 600 mm on
Y. The uploaded spans are 830 mm and 280 mm, both inside that allowance.
Homing for this frame is Z, then X, then Y. The transport line ending remains
CR. A claw configuration set CR LF; that conflict stays in the edge config.
"""

import os

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector.rotating_vacuum_gripper import RotatingVacuumGripper

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (0, 830), "Y": (-280, 0), "Z": (-240, 0)},
    default_deck={"rows": 4, "cols": 8},
    home_order=('Z', 'X', 'Y'),
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

# Claw vacuum cup and yaw servo on the gantry GRBL port.
# Calibrated servo pulses: 0° -> S14, -90° -> S124, -180° -> S244. The older
# in-between expression omits the calibrated endpoint and yields a negative
# pulse; RotatingVacuumGripper interpolates linearly instead.
GRIPPER = RotatingVacuumGripper(
    axis='C',
    yaw_pulses=[(0, 14), (-90, 124), (-180, 244)],
    rotation_min_z_mm=-5.0,
    vacuum_on_delay_s=3.0,
    vacuum_off_delay_s=3.0,
    valve_on='M8',
    valve_off='M9',
)


def connect_gantry() -> GrblHALController:
    """Open the gantry and apply this machine's limits."""
    gantry = GrblHALController(port_name=os.environ["GANTRY_PORT"])
    gantry.connect()
    FRAME.apply_axis_limits(gantry, SOFT_LIMITS)
    return gantry
