# PipQuBot XL Edge

PUDA edge service for the `PipQuBotXL` driver.

## Configure

Copy `.env.example` to `.env`, then set the NATS servers, Duet/RepRap controller
IP, and Sartorius serial port. `HOME_GANTRY_ON_STARTUP` and
`INITIALIZE_PIPETTE_ON_STARTUP` are explicit startup-motion gates; keep both
`false` for a connect-only deployment.

## Sartorius XL volume calibration

The PipQuBot XL head is a BRL1000-1 (rLine 50-1000 µL). Its machine selects
`RLineModel.UL_50_1000`, which is **2.5 µL/step** from rLine manual v1.1 Table 1.
The conversion is `steps = volume_µL / 2.5`, so 100 µL emits `RI40` and 1,000 µL
emits `RI400`. The shared controller has no numeric default; every caller passes
a model. Software tests verify the generated step count. Rebuild and recreate the XL
edge after pulling this change so the running service uses it. After deployment, validate
physical delivery with a fresh tip and an independent volume or gravimetric
measurement before relying on accuracy for samples.

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

## XL BioShake row orientation

The operator-verified XL mounting requires raw labware-Y reflection before the
existing XY swap: **A↔D and B↔C**, with columns unchanged. The XL well-position
helper applies `min(row_y) + max(row_y) - raw_y` for `bioshake`, as it already
does for the separately verified Sartorius and Polyelectric mountings. This
machine/labware-scoped override preserves shared `bioshake.json`, sibling-machine
orientation, slot origins, Z/insert depth, tip offset and volume conversion.
Use normal `bioshake` and unchanged well labels; do not swap protocol labels or
apply a second mirror. Regression coverage spans all 24 wells with/without tips.

With the currently calibrated B1 origin, corrected row machine-X coordinates are
A=16.54, B=34.54, C=52.54, D=70.54 mm. Column machine-Y remains
`-302.42 + 18*(column-1)` mm. These examples are not permanent calibration.
The confirmed bottom-relative dispense height remains 21 mm (current attached-tip
Z=-56.80 mm); mirror correction alone never authorizes a validation move, pickup,
repeated dispense or home.

## PipQuBot XL proxy-vial dispensing

The operator-confirmed XL X travel limit is **345 mm**. The driver exposes the
machine-specific calibration `70792568-cf46-493a-8ce6-5fdf08025df6` through
`dispense_to_proxy_vial(well_name=..., amount=...)`; it does not expose a generic
raw-coordinate liquid command. Proxy wells A1-A6/B1-B6 use calibrated absolute
machine coordinates, including B6 at `[338.0, -210.0, -28.5]` mm. The controller's
normal staged `move_absolute` path retracts both pipette Z and capper A to `-5 mm`
before XY travel, descends pipette Z only over the selected vial, then restores
capper A to `0 mm`. Both Z and A must be homed and both transit paths clear.

An edge restart clears the process-local tip flag but does not remove a physical
tip. Only after fresh operator confirmation that exactly one empty tip is still
attached, use `reconcile_tip_attached(physical_tip_confirmed=true)`; this command
changes software state only and performs no hardware I/O. Both reconciliation and
proxy dispensing publish confirmation safety metadata. Never reconcile when tip
presence or retained liquid is uncertain.

## Run on Windows

```powershell
.\start_edge.bat
```

## Run with Docker

From this directory:

```powershell
docker compose up --build
```
