# Changelog

Driver, geometry, labware, and skill changes are recorded here. A site edge does not append to this file; it pins the qubot version it uses.

## Unreleased

- `GrblTelnetController` (`from qubot.gantry import GrblTelnetController`): grblHAL over TCP port 23. Realtime bytes stay raw. Other commands use a line feed, and the reply includes the lines before `ok` so `$I` and `$$` match the serial controller. `connect()` does not home. Feed-hold sends `!` without taking the command lock.
- `GrblHALController` still starts at 3000 mm/min and still lifts to `SAFE_MOVE_HEIGHT` before XY when `apply_safe_z` is true. An edge can pass `feed` and `z_motion="directional"` (Z first only when rising, no safe-height detour). `read_hardware_feed_limits()` reads `$110`/`$111`/`$112`. `send_immediate()` writes one line without the command lock. The telnet controller forwards `feed` and `z_motion` and sends that immediate line as NETCON.
- `Finger.move_to` takes an optional `stopping_force`. `None` does not stop on force. `LedBoard` powers are integers 0 to 255. `LedBoard`, `Chamber`, and `ParallelFingers` expose `snapshot()`. The multistep Sartorius controller exposes `read_telemetry()`, which skips the plunger query when the port is busy or closed.

## 0.1.1 - 2026-11-26

- `RepRapSerialController` (`from qubot.gantry import RepRapSerialController`): RepRapFirmware over USB serial, from the `RepRapController` in the running first-edge's `qubot_drivers` 0.0.39. G-code with CR terminator, `G28` homing, absolute moves with relative moves converted internally, `M400` move wait, and async `M114` position. Used by the first gantry in puda-eletrochem.
- Sartorius `SatoriusController` accepts echo-only drive responses again (fix from `qubot_drivers` 0.0.39 that the 0.1.0 merge dropped). A drive that echoes the sent frame and never replies reads as `ok`, and `_wait_ready` stops polling `DS` on such a drive.
- README and the qubot-driver skill no longer use numbered gantry labels; reference drivers are described by size and controller.

## 0.1.0 - 2026-11-26

- First PyPI release, `qubot-drivers` 0.1.0. Publishing runs from `.github/workflows/publish.yml` on a GitHub release via PyPI trusted publishing.
- One package replaces the 18 workspace packages. It is distributed as `qubot-drivers` (`qubot` is taken on PyPI) and imported as `qubot`. One root `pyproject.toml`; code is under `src/qubot/`.
- Imports: `from qubot.gantry import Frame, GrblHALController, GrblWSController, RepRapHTTPController` and `from qubot.end_effector import Capper, RotatingVacuumGripper, Chamber, LedBoard, ParallelFingers, narrow_z, RLineModel`, loaded on first use. The rLine pipettes are modules: `from qubot.end_effector import rline_50_1000, rline_50_1000_multistep`. Defining modules such as `qubot.gantry.grbl` still import. `qubot.geometry` and `qubot.edgekit` are unchanged. Old names such as `gantry_005`, `rline_50_1000`, and `qubot_geometry` are gone.
- No machine settings in the package. Each edge imports the drivers and configures them in its own code. Gantry frames `001` to `009`, their command lists, and effector calibration moved to starting-point PUDA `driver.py` files in `skills/qubot-driver/references/examples/`, one per machine (`claw_machine.py`, `dancefloor.py`, …). Each has the constants, a `Driver` that takes ports from `main.py`, `shutdown`/`estop` hooks, and basic `home`/`move_*`/`get_position` commands.
- `qubot.gantry.Frame` is constructed by the edge. Effector calibration is a constructor argument: `Capper`, `RotatingVacuumGripper`, `Chamber`, `ParallelFingers(corrections=, calibration_factor=)`, and the multistep pipette's `step_resolution` and `response_time_s` (no longer defaulted). `AXIS` and `PORT_ENV` constants are gone; axis and port env names are edge wiring.
- `qubot.labware` holds `StandardLabware`, `Deck`, and the bundled definitions (moved out of `qubot.geometry`, which now has only `Position`). Edges add or override labware with folders of `<name>.json` (`search_paths` / `Deck(labware_paths=...)`), `StandardLabware.from_file`, or `from_definition`. `Deck.from_frame(frame)` uses the frame's grid. A missing well now raises `KeyError` in `get_height`.
- `qubot.edgekit` is removed; required `Config` fields in the edge's `main.py` stop an edge without a filled `.env`.
- Contracts are gone. The build guide (`docs/building-an-edge.md`) and the checklist that replaced `CONTRACT.md` are now the agent skill `skills/qubot-driver/SKILL.md`. `check_contract.py`, `vendor_edge.py`, `attach_toolhead.py`, and `qubot.edgekit.load_contract` are removed. An edge depends on a pinned `qubot` instead of a vendored copy.
- `MODULARIZATION.md` is merged into the README's Design section. `scripts/accept_host_env.py` is removed; the skill says to copy the user's `.env` and `chmod 600` it.
- Gantries share one copy of each transport. `001` and `003` now get the `grbl.py` that `005` to `009` used, which adds `halt()` and the `apply_safe_z` keyword on `move_relative`. Nothing else changed in it.
- The two rLine bodies share `rline.py`. `rline-50-1000-multistep` keeps its own controller in `satorius_multistep.py` and pacing in `rline_pace.py`.
- `families/` is removed; its transports are the package modules. The rLine manual moved to `docs/`.
- `requires-python` is `>=3.11`; the previous `qubot-edgekit` already needed `tomllib`.

## 2026-11-25

- `rline-50-1000-multistep`: 50-1000 µL rLine body that splits a requested aspirate or dispense speed across a faster preset. Step resolution and response time are the calibrated inputs, defaulting to 10 steps and 1.03 s. `rline-50-1000` is unchanged.

## 2026-11-24

- `rotating-vacuum-gripper`: claw vacuum cup and yaw servo on the gantry port. Intermediate yaw uses linear interpolation between the three calibrated pulses.
- Gantry `005` homes Z, then X, then Y, and can feed-hold with realtime `!` without taking the command lock. `move_relative` accepts `apply_safe_z`.
- `vacuum-chamber`: dancefloor valve and lid waypoints. Loading X=−118 stays outside gantry `006` until the −119 versus −116 limit is confirmed. Gantry `006` can feed-hold the same way.
- Gantry `007` can feed-hold without taking the command lock. `move_relative` accepts `apply_safe_z`. The PESCador pipette reuses `rline-50-1000`.
- `orion-4ch-led`: four-channel LED line on one 9600 baud port. The reply is not parsed. Gantry `008` can feed-hold without taking the command lock.
- `parallel-force-actuator`: four serial actuators. Force-threshold stops stay disabled until an edge contract names the threshold unit. Gantry `009` can feed-hold without taking the command lock.

## 2026-11-23

`main` keeps gantries, end effectors, transport families, geometry, and the edge kit. Finished edges are not stored on `main`. The previous edge tree remains on `legacy-edges`. A site edge is one directory under that site's `edges/`. [docs/building-an-edge.md](docs/building-an-edge.md) is the build reference.

### Gantries

- `001-1unit-grbl-serial`: Integrated as miniqubot.
- `002-1unit-reprap-http`: Integrated as capper, then syringequbot.
- `003-2unit-grbl-serial`: Integrated as pipqubot-mof.
- `004-4unit-reprap-http`: Integrated as pipqubot-xl.
- `005-8unit-grblhal-serial`: New frame from the gantry limits file. Intended name: Claw machine (Pick-and-place). Size is 2 by 4 units. No previous edge.
- `006-1unit-grblhal-serial`: New frame from the gantry limits file. Intended name: Dancefloor (Vacuum chamber). No previous edge.
- `007-2unit-grblhal-serial`: New frame from the gantry limits file. Intended name: Overkill2 (Liquid handling - pipette gantry). No previous edge.
- `008-1unit-grblhal-serial`: New frame from the gantry limits file. Intended name: Photoreactor (UV qubot). No previous edge. X −300 to 300 is flagged for correction. A 1-unit frame may travel at most 300 mm on X, and that range spans 600 mm. The uploaded value is unchanged.
- `009-1unit-grblhal-serial`: New frame from the gantry limits file. Intended name: EIS Qubot (Electrochemical station). No previous edge. X −300 to 300 is flagged for correction. A 1-unit frame may travel at most 300 mm on X, and that range spans 600 mm. Z −300 to 300 is the same uploaded figure and is flagged with X. The uploaded values are unchanged.

### End effectors

- `rline-50-1000`: Integrated as pipqubot-mof, then pipqubot-xl.
- `a-axis-capper`: Integrated as pipqubot-xl.
- `autosampler-syringe`: Integrated as syringequbot.
