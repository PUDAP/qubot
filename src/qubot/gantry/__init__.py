"""Gantry transports and the frame type an edge configures.

- ``qubot.gantry.grbl``: ``GrblHALController`` over serial (grbl and grblHAL).
- ``qubot.gantry.grbl_ws``: ``GrblWSController`` over the GRBL WebSocket.
- ``qubot.gantry.reprap_http``: ``RepRapHTTPController`` over RepRap HTTP.
- ``qubot.gantry.frame``: ``Frame``, built by the edge from its contract.
"""

from .frame import Frame

__all__ = ["Frame"]
