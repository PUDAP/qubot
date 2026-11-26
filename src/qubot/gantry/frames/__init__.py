"""Frame facts for each numbered gantry: limits, axes, default deck, placeholders.

Modules are ``g{serial}``, for example ``qubot.gantry.frames.g005``. A contract
names the gantry by directory-style name, for example ``005-8unit-grblhal-serial``.
"""

from __future__ import annotations

import importlib
import tomllib
from importlib import resources
from types import ModuleType

GANTRIES = {
    "001-1unit-grbl-serial": "g001",
    "002-1unit-reprap-http": "g002",
    "003-2unit-grbl-serial": "g003",
    "004-4unit-reprap-http": "g004",
    "005-8unit-grblhal-serial": "g005",
    "006-1unit-grblhal-serial": "g006",
    "007-2unit-grblhal-serial": "g007",
    "008-1unit-grblhal-serial": "g008",
    "009-1unit-grblhal-serial": "g009",
}


def module_name(gantry: str) -> str:
    try:
        return GANTRIES[gantry]
    except KeyError:
        raise KeyError(f"unknown gantry {gantry}") from None


def load(gantry: str) -> ModuleType:
    """Import the frame module for a contract gantry name."""
    return importlib.import_module(f"{__name__}.{module_name(gantry)}")


def placeholders(gantry: str) -> dict:
    """Unfilled safety, confirm, and startup-homing fields for that gantry."""
    text = resources.files(__name__).joinpath(f"{module_name(gantry)}.toml").read_text()
    return tomllib.loads(text)


__all__ = ["GANTRIES", "load", "module_name", "placeholders"]
