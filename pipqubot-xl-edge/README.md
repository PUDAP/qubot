# PipQuBot XL Edge

PUDA edge service for the `PipQuBotXL` driver.

## Configure

Copy `.env.example` to `.env`, then set the NATS servers, Duet/RepRap controller
IP, and Sartorius serial port. `HOME_GANTRY_ON_STARTUP` and
`INITIALIZE_PIPETTE_ON_STARTUP` are explicit startup-motion gates; keep both
`false` for a connect-only deployment.

## Pure pipette positioning

`move_to_well(deck_slot=..., well_name=...)` retains the configured labware-top
position when `height_from_bottom` is omitted. With an explicit
`height_from_bottom`, it calculates the same bottom-relative target used by
`dispense_to`, but performs **only gantry positioning**: no aspiration, dispensing,
blowout, tip ejection, or pipette initialization.

For example, after a normal acknowledged pickup and logical BioShake loading:

```python
move_to_well(deck_slot="B1", well_name="A1", height_from_bottom=21.0)
```

Coordinates depend on the live slot origin, labware definition, ceiling height,
and software tip-length offset. Verify those inputs and physical/software tip
consistency before motion. A process-local tip flag is not a tip-presence sensor.
An explicitly requested pick-and-position operation leaves the tip attached and
the gantry at the requested destination; do not append a drop or home.

After a driver change, rebuild only this service and inspect the built image
before recreating it. Keep both startup-motion gates `false` for connect-only
activation. Confirm controller axis-homed flags independently and reload the
logical deck after restart. A serial `Errno 5` can require restarting the sole
edge to reopen a stale descriptor; never open a competing serial session, and
never treat the shallow container health check as proof of pipette connectivity.

## Run on Windows

```powershell
.\start_edge.bat
```

## Run with Docker

From this directory:

```powershell
docker compose up --build
```
