# Families

Unmodified transport snapshots. Copy a family into a gantry or effector package when creating one. Do not import `families/` from a module or from another package.

`grbl-websocket/` is the GRBL WebSocket snapshot (`grbl_ws.py`). A `grblhal-serial` gantry copies it beside the serial transport. The gantry copy imports `qubot_geometry` instead of `qubot_drivers`.
