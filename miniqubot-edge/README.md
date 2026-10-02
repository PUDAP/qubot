# MiniQubot edge

PUDA edge for the empty-head three-axis MiniQubot. It uses `GrblHALController` from `qubot-drivers` and Python SDK 0.0.18.

Starting the service connects the GRBL serial port, checks `$I` and `$$`, then homes all axes. The gantry has commissioned limit switches on X, Y, and Z.

Commands: `home`, `move_absolute`, `move_relative`, and `get_position`. `home`, `move_absolute`, and `move_relative` publish `@safety` with `confirm=False`.

`get_position` is also the `pos` telemetry stream, sampled every 3 seconds. Machine state carries the same-session `homed` flag and the last sampled position. The SDK publishes heartbeat and host health.
