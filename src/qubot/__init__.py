"""Qubot gantry and end-effector drivers.

Import the part you need, for example::

    from qubot.gantry.grbl import GrblHALController
    from qubot.gantry.frames import g005
    from qubot.end_effector.rline_50_1000 import connect

Importing ``qubot`` itself does not open a port or import ``serial``.
"""

__version__ = "0.1.0"
