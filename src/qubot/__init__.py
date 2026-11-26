"""Qubot gantry and end-effector drivers.

Import the part you need, for example::

    from qubot.gantry import Frame
    from qubot.gantry.grbl import GrblHALController
    from qubot.end_effector.rline_50_1000 import connect

qubot holds no machine settings. Each edge imports the drivers it needs and
configures frame limits, decks, calibration, and ports in its own code. Importing ``qubot`` itself does not
open a port or import ``serial``.
"""

__version__ = "0.1.0"
