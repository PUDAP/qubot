"""eis-qubot: gantry 009-1unit-grblhal-serial.

Reference hardware config. A site edge copies this into its own code and
fills the blanks. Ports and hosts come from the edge's .env. Nothing here
opens a port at import.

EIS Qubot (Electrochemical station). Limits key: `eis_qubot`.
Frame travel is X −300 to 300, Y −199 to 0, Z −300 to 300. Y travel is 199 mm,
inside the 300 mm allowed for one unit. X is −300 to 300, a span of 600 mm,
which is past that allowance. Z is the same −300 to 300 figure. The 300 mm
rule covers X and Y; Z is flagged with X. Both uploaded ranges are kept for
correction.
"""

import os

from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector.parallel_force_actuator import ParallelFingers

FRAME = Frame(
    axes=('X', 'Y', 'Z'),
    hardware_limits={"X": (-300, 300), "Y": (-199, 0), "Z": (-300, 300)},
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

# Four actuators, port envs FINGER_1_PORT to FINGER_4_PORT, channels 0-3.
# corrections are (slope, intercept) per channel: corrected = (raw - b) / a.
# Touch thresholds: pescador2 sets 30000, the demo uses 7500. Neither is a
# plausible newton value, so threshold stops stay off until the unit is named.
FINGER_CORRECTIONS = [
    (1.0453861330027523, -717.008056157306),
    (0.8792176759765562, -3546.5827171758337),
    (1.0266252637365454, -823.8747617486401),
    (0.9109718487428711, -1188.2464990482106),
]
FORCE_CALIBRATION_FACTOR = 573.2622826433104
FINGER_LIMITS_MM = (-30.0, 0.0)
# Unit unresolved; force-threshold stops stay off until it is named.
TOUCH_THRESHOLD_CANDIDATES = (30000, 7500)


def connect_gantry() -> GrblHALController:
    """Open the gantry and apply this machine's limits."""
    gantry = GrblHALController(port_name=os.environ["GANTRY_PORT"])
    gantry.connect()
    FRAME.apply_axis_limits(gantry, SOFT_LIMITS)
    return gantry


def make_fingers() -> ParallelFingers:
    ports = [os.environ[f"FINGER_{index}_PORT"] for index in range(1, len(FINGER_CORRECTIONS) + 1)]
    return ParallelFingers(
        ports,
        corrections=FINGER_CORRECTIONS,
        calibration_factor=FORCE_CALIBRATION_FACTOR,
        limits_mm=FINGER_LIMITS_MM,
    )
