# First edge

The PUDA service entrypoint is `main.py`. Machine implementation and calibration
live in `driver.py`, imported as `from driver import First` from this folder.
Shared controllers and labware come from `qubot-drivers`.

See the repository README for environment, Docker, and baremetal setup.
Starting this edge can home the gantry and initialize the pipette.
Scripts in `examples/` are manual hardware operations, not offline tests.
