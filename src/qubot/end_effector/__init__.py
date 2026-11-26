"""End effectors. One module per physical toolhead, for example
``qubot.end_effector.rline_50_1000``. Shared rLine code is in ``rline``,
``satorius``, ``satorius_multistep``, and ``rline_pace``.
"""

from __future__ import annotations

import importlib
from types import ModuleType

EFFECTORS = {
    "rline-50-1000": "rline_50_1000",
    "rline-50-1000-multistep": "rline_50_1000_multistep",
    "a-axis-capper": "a_axis_capper",
    "autosampler-syringe": "autosampler_syringe",
    "rotating-vacuum-gripper": "rotating_vacuum_gripper",
    "vacuum-chamber": "vacuum_chamber",
    "orion-4ch-led": "orion_4ch_led",
    "parallel-force-actuator": "parallel_force_actuator",
}


def module_name(effector: str) -> str:
    try:
        return EFFECTORS[effector]
    except KeyError:
        raise KeyError(f"unknown effector {effector}") from None


def load(effector: str) -> ModuleType:
    """Import the module for a contract effector name."""
    return importlib.import_module(f"{__name__}.{module_name(effector)}")


__all__ = ["EFFECTORS", "load", "module_name"]
