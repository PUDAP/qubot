# qubot

One Python package, `qubot`, with the gantry and end-effector drivers for building a PUDA qubot edge. It holds no machine settings: each edge imports qubot and configures it from its own contract. Nothing in this repository is a running edge. Agents start from [docs/building-an-edge.md](docs/building-an-edge.md). The split is explained in [MODULARIZATION.md](MODULARIZATION.md). Changes are recorded in [CHANGELOG.md](CHANGELOG.md).

- No `MACHINE_ID`, NATS servers, host addresses, serial-device paths, frame limits, calibration, container config, or `.env`. A site edge's `.env.example` stays placeholders.
- Code lives in `src/qubot/`. One `pyproject.toml` at the root; gantries and end effectors are modules, not separate packages.
- `qubot.gantry.grbl`, `qubot.gantry.grbl_ws`, `qubot.gantry.reprap_http` are the transports, shared by every gantry.
- `qubot.gantry.Frame` is the frame type. The edge builds it from its contract `[frame]` table: axes, hardware limits, default deck, and optional home order and firmware checks.
- `qubot.end_effector.<name>` is one toolhead driver. Calibration (servo pulses, waypoints, delays, force corrections, pipette pacing) is passed in by the edge from `[effector.<name>]`.
- `qubot.geometry` is the shared position, deck, and labware module. `qubot.edgekit` loads a numbered contract and refuses to start an edge until a filled local `.env` exists.
- [docs/examples/](docs/examples/) has one reference contract per known machine, named after the machine (`claw-machine.toml`, `pipqubot-xl.toml`, …), with the frame and calibration values from the machines built so far, and [edge_config.py](docs/examples/edge_config.py) showing how an edge imports and configures qubot from it. Serials `001` to `004` are provisional labels, not recorded asset tags.
- Safety text, confirm, and startup homing are blank in the examples. Each edge contract fills them.
- Finished edges are not stored on `main`. For an edge built before the qubot modularization and the monorepo restructuring, use the `legacy-edges` branch.

```python
from qubot.edgekit import load_contract
from qubot.gantry import Frame
from qubot.gantry.grbl import GrblHALController
from qubot.end_effector.rotating_vacuum_gripper import RotatingVacuumGripper

contract = load_contract(edge_dir)
frame = Frame.from_dict(contract["frame"])
gantry = GrblHALController(port_name=os.environ["GANTRY_PORT"])
gripper = RotatingVacuumGripper(**contract["effector"]["rotating-vacuum-gripper"])
# after gantry.connect():
frame.apply_axis_limits(gantry, contract.get("soft_limits"))
```

## Build a site edge

Fill [CONTRACT.md](CONTRACT.md), starting from the matching file in [docs/examples/](docs/examples/), then scaffold the edge service from [edge-python-template](https://github.com/PUDAP/edge-python-template). Keep the edge directory out of this repository and put it in the site monorepo's `edges/`.

```bash
python3 scripts/check_contract.py path/to/edge/contracts/1.toml
python3 scripts/vendor_edge.py path/to/edge/contracts/1.toml path/to/edge
```

`vendor_edge.py` copies the `qubot` package into `path/to/edge/vendor/qubot`, points the edge's `[tool.uv.sources]` at it, and writes `vendor/REVISION` with the commit and the contract's effector modules. The edge lists `qubot` in its dependencies. It does not build an image or start a container. From the edge directory, generate the lock with `uv lock`, then build only when that edge is allowed to move.

Attaching another toolhead writes the next contract and refreshes `vendor/`. It also does not build or remove an image:

```bash
python3 scripts/attach_toolhead.py path/to/edge a-axis-capper
```

`.env.example` is placeholders only. If the user supplies this host's `.env`, copy it with `python3 scripts/accept_host_env.py path/to/edge path/to.env`. Otherwise the edge refuses to start until `.env` exists and its required values are filled.

## Example machines

Reference contracts in `docs/examples/`. These are machines, not modules.

| Example | Gantry | Notes |
|---|---|---|
| [`miniqubot.toml`](docs/examples/miniqubot.toml) | `001-1unit-grbl-serial` |  |
| [`syringequbot.toml`](docs/examples/syringequbot.toml) | `002-1unit-reprap-http` | Same frame was the capper before. |
| [`pipqubot-mof.toml`](docs/examples/pipqubot-mof.toml) | `003-2unit-grbl-serial` |  |
| [`pipqubot-xl.toml`](docs/examples/pipqubot-xl.toml) | `004-4unit-reprap-http` |  |
| [`claw-machine.toml`](docs/examples/claw-machine.toml) | `005-8unit-grblhal-serial` | Pick-and-place. |
| [`dancefloor.toml`](docs/examples/dancefloor.toml) | `006-1unit-grblhal-serial` | Vacuum chamber. |
| [`overkill2.toml`](docs/examples/overkill2.toml) | `007-2unit-grblhal-serial` | Liquid handling, pipette gantry. |
| [`photoreactor.toml`](docs/examples/photoreactor.toml) | `008-1unit-grblhal-serial` | UV qubot. |
| [`eis-qubot.toml`](docs/examples/eis-qubot.toml) | `009-1unit-grblhal-serial` | Electrochemical station. |

## End effectors

Contract name; module is `qubot.end_effector.<name with underscores>`.

| Effector | Where it has been used |
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
