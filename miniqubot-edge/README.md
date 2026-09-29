# MiniQubot edge

PUDA edge for the empty-head three-axis MiniQubot. It uses `GrblHALController` from `qubot-drivers`.

Starting the service connects the GRBL serial port, checks `$I` and `$$`, then homes all axes. The gantry has commissioned limit switches on X, Y, and Z.

Commands: `home`, `move_absolute`, `move_relative`, and `get_position`. The two move commands publish `@safety` confirmation. `home` does not.
