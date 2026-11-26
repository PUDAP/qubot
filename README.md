# qubot

One Python package, `qubot`, with the gantry and end-effector drivers for building a PUDA qubot edge. Nothing in this repository is a running edge. Agents start from [docs/building-an-edge.md](docs/building-an-edge.md). The split is explained in [MODULARIZATION.md](MODULARIZATION.md). Changes are recorded in [CHANGELOG.md](CHANGELOG.md).

- No `MACHINE_ID`, NATS servers, host addresses, serial-device paths, container config, or `.env`. A site edge's `.env.example` stays placeholders.
- Code lives in `src/qubot/`. One `pyproject.toml` at the root; gantries and end effectors are modules, not separate packages.
- `qubot.gantry.grbl`, `qubot.gantry.grbl_ws`, `qubot.gantry.reprap_http` are the transports, shared by every gantry.
- `qubot.gantry.frames.g{serial}` holds one gantry's frame limits, axes, and default deck. `qubot.end_effector.<name>` is one toolhead.
- `qubot.geometry` is the shared position, deck, and labware module. `qubot.edgekit` loads a numbered contract and refuses to start an edge until a filled local `.env` exists.
- Contracts name gantries `{serial}-{size}-{bus}`. Serials `001` to `004` are provisional labels for the first build, not recorded asset tags. `005` to `009` continue from the gantry limits file. `005` is 8 units, arranged 2 along Y by 4 along X.
- Each gantry `frames/g{serial}.toml` leaves safety, confirm, and startup homing unset. The edge contract fills them.
- Each gantry has a default deck of one 2x2 block per unit. Calibrated holder positions belong to the site edge.
- Finished edges are not stored on `main`. For an edge built before the qubot modularization and the monorepo restructuring, use the `legacy-edges` branch.

```python
from qubot.gantry.grbl import GrblHALController
from qubot.gantry.frames import g005
from qubot.end_effector.rline_50_1000 import connect
from qubot.geometry import Position
```

Contract names resolve with `qubot.gantry.frames.load("005-8unit-grblhal-serial")` and `qubot.end_effector.load("rline-50-1000")`.

## Build a site edge

Fill [CONTRACT.md](CONTRACT.md), then scaffold the edge service from [edge-python-template](https://github.com/PUDAP/edge-python-template). Keep the edge directory out of this repository and put it in the site monorepo's `edges/`.

```bash
python3 scripts/check_contract.py path/to/edge/contracts/1.toml
python3 scripts/vendor_edge.py path/to/edge/contracts/1.toml path/to/edge
```

`vendor_edge.py` copies the `qubot` package into `path/to/edge/vendor/qubot`, points the edge's `[tool.uv.sources]` at it, and writes `vendor/REVISION` with the commit and the contract's gantry and effector modules. The edge lists `qubot` in its dependencies. It does not build an image or start a container. From the edge directory, generate the lock with `uv lock`, then build only when that edge is allowed to move.

Attaching another toolhead writes the next contract and refreshes `vendor/`. It also does not build or remove an image:

```bash
python3 scripts/attach_toolhead.py path/to/edge a-axis-capper
```

`.env.example` is placeholders only. If the user supplies this host's `.env`, copy it with `python3 scripts/accept_host_env.py path/to/edge path/to.env`. Otherwise the edge refuses to start until `.env` exists and its required values are filled.

## Gantries

| Package | Where it has been used |
|---|---|
| `001-1unit-grbl-serial` | miniqubot |
| `002-1unit-reprap-http` | capper, then syringequbot |
| `003-2unit-grbl-serial` | pipqubot-mof |
| `004-4unit-reprap-http` | pipqubot-xl |
| `005-8unit-grblhal-serial` | Claw machine (Pick-and-place) |
| `006-1unit-grblhal-serial` | Dancefloor (Vacuum chamber) |
| `007-2unit-grblhal-serial` | Overkill2 (Liquid handling - pipette gantry) |
| `008-1unit-grblhal-serial` | Photoreactor (UV qubot) |
| `009-1unit-grblhal-serial` | EIS Qubot (Electrochemical station) |

## End effectors

| Package | Where it has been used |
|---|---|
| `rline-50-1000` | pipqubot-mof, then pipqubot-xl. |
| `rline-50-1000-multistep` | PESCador pipette. Same 50-1000 µL body, with calibrated multistep aspirate and dispense speed. |
| `a-axis-capper` | pipqubot-xl |
| `autosampler-syringe` | syringequbot |
| `rotating-vacuum-gripper` | PESCador claw. Vacuum and yaw share the gantry port. |
| `vacuum-chamber` | PESCador dancefloor. Valve and lid waypoints share the gantry port. |
| `orion-4ch-led` | PESCador photoreactor. Four channels, one serial port. |
| `parallel-force-actuator` | PESCador EIS station. Four serial actuators. |

## Offline checks

```bash
uv sync --group dev
uv run pytest
```
