# MiniQubot edge

PUDA edge for the empty-head three-axis MiniQubot. It uses `GrblHALController` from `qubot-drivers`.

Starting the service connects the GRBL serial port, checks `$I` and `$$`, then homes all axes. `HOME_ON_STARTUP` defaults to true. The gantry has commissioned limit switches on X, Y, and Z.

Commands: `home`, `move_absolute`, `move_relative`, and `get_position`. `home`, `move_absolute`, and `move_relative` publish `@safety` with `confirm=False`. `get_position` is also the `pos` telemetry stream, published every 3 seconds on `puda.<machine_id>.tlm.stream.pos`. `snapshot` adds `homed` to machine state. The SDK publishes heartbeat and host health. `PUDA_NATS_CA` and `PUDA_E2E_KEY_FILE` are optional and are passed through only when set.
