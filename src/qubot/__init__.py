"""Qubot gantry and end-effector drivers.

Import the part you need, for example::

    from qubot.gantry import Frame, GrblHALController
    from qubot.end_effector import RotatingVacuumGripper, rline_50_1000

qubot holds no machine settings. Each edge imports the drivers it needs and
configures frame limits, decks, calibration, and ports in its own code. Importing ``qubot`` itself does not
open a port or import ``serial``.
"""

__version__ = "0.1.0"
