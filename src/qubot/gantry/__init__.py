"""Gantry controllers and the frame type an edge configures.

    from qubot.gantry import Frame, GrblHALController

- ``GrblHALController``: GRBL 1.1 and grblHAL over serial (``qubot.gantry.grbl``).
- ``GrblTelnetController``: grblHAL over TCP port 23 (``qubot.gantry.grbl_telnet``).
- ``GrblWSController``: GRBL over WebSocket (``qubot.gantry.grbl_ws``).
- ``RepRapHTTPController``: RepRapFirmware over HTTP (``qubot.gantry.reprap_http``).
- ``RepRapSerialController``: RepRapFirmware over USB serial (``qubot.gantry.reprap_serial``).
- ``Frame``: axes, travel, and deck of one machine (``qubot.gantry.frame``).

Controllers load on first use, so importing this package opens nothing and
does not import ``serial``.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from .frame import Frame

_LAZY = {
    "GrblHALController": ".grbl",
    "GrblStatusReport": ".grbl",
    "GrblTelnetController": ".grbl_telnet",
    "GrblWSController": ".grbl_ws",
    "RepRapHTTPController": ".reprap_http",
    "RepRapSerialController": ".reprap_serial",
}

if TYPE_CHECKING:
    from .grbl import GrblHALController, GrblStatusReport
    from .grbl_telnet import GrblTelnetController
    from .grbl_ws import GrblWSController
    from .reprap_http import RepRapHTTPController
    from .reprap_serial import RepRapSerialController


def __getattr__(name: str):
    try:
        module = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))


__all__ = ["Frame", *_LAZY]
