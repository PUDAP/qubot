"""End-effector drivers. Calibration is passed in by the edge.

    from qubot.end_effector import RotatingVacuumGripper, Chamber

- ``Capper``: A-axis capping tool (``qubot.end_effector.a_axis_capper``).
- ``narrow_z``: autosampler syringe clearance (``qubot.end_effector.autosampler_syringe``).
- ``RotatingVacuumGripper``: vacuum cup and yaw servo (``qubot.end_effector.rotating_vacuum_gripper``).
- ``Chamber``: vacuum-chamber valve and lid (``qubot.end_effector.vacuum_chamber``).
- ``LedBoard``: Orion four-channel LED (``qubot.end_effector.orion_4ch_led``).
- ``ParallelFingers``, ``Finger``: force actuators (``qubot.end_effector.parallel_force_actuator``).
- ``RLineModel``, ``RLINE_SPECS``: rLine spec table (``qubot.end_effector.rline``).

The two rLine pipettes are used through their modules, because both define
``connect`` and ``SatoriusController``::

    from qubot.end_effector import rline_50_1000, rline_50_1000_multistep

Everything loads on first use, so importing this package does not import ``serial``.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

_LAZY = {
    "Capper": ".a_axis_capper",
    "narrow_z": ".autosampler_syringe",
    "RotatingVacuumGripper": ".rotating_vacuum_gripper",
    "Chamber": ".vacuum_chamber",
    "LedBoard": ".orion_4ch_led",
    "ParallelFingers": ".parallel_force_actuator",
    "Finger": ".parallel_force_actuator",
    "RLineModel": ".rline",
    "RLINE_SPECS": ".rline",
}
_MODULES = ("rline_50_1000", "rline_50_1000_multistep")

if TYPE_CHECKING:
    from . import rline_50_1000, rline_50_1000_multistep
    from .a_axis_capper import Capper
    from .autosampler_syringe import narrow_z
    from .orion_4ch_led import LedBoard
    from .parallel_force_actuator import Finger, ParallelFingers
    from .rline import RLINE_SPECS, RLineModel
    from .rotating_vacuum_gripper import RotatingVacuumGripper
    from .vacuum_chamber import Chamber


def __getattr__(name: str):
    if name in _MODULES:
        value = importlib.import_module(f".{name}", __name__)
    elif name in _LAZY:
        value = getattr(importlib.import_module(_LAZY[name], __name__), name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY) | set(_MODULES))


__all__ = [*_LAZY, *_MODULES]
