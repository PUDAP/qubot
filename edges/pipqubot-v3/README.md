# Legacy PipQuBot V3

Preserved `PipQuBotV3` implementation in `driver.py`. This is a separate GRBL and Sartorius machine from the MOF edge. It has no service entrypoint and no Compose file. Importing the module does not initialize hardware.

Do not instantiate it until the installed head's rLine model is known. The preserved constructor does not name that model.
