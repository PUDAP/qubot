---
name: qubot-driver
description: Build or update a qubot edge's driver.py with the qubot driver package. Use for choosing a gantry controller and end effectors, configuring a machine's frame and calibration, adding a toolhead, or pinning qubot in an edge.
---

# Building a qubot edge

`qubot` is one Python package of gantry controllers, the `Frame` type, end-effector drivers, `Position`, and labware (`qubot.labware`). It holds no machine values. Each edge's `driver.py` imports the drivers it carries, sets its frame limits and calibration as constants, and wraps them in a PUDA `Driver` class. Import from each area: `from qubot.gantry import Frame, GrblHALController`, `from qubot.end_effector import RotatingVacuumGripper`; the two rLine pipettes as modules (`from qubot.end_effector import rline_50_1000`). This repository does not hold a running edge, a host `.env`, or a site's machine id. For NATS, `@command`/`@safety`, hooks, telemetry, and `main.py`, use the `puda-edge` skill.

Supported controllers and end effectors are listed in the [README](../../README.md#supported-hardware). The README's [design](../../README.md#design) section explains the split. Record driver changes in [CHANGELOG.md](../../CHANGELOG.md).

## Reference drivers

[references/examples/](references/examples/) has one starting-point `driver.py` per known machine:

| File | Gantry | Toolheads |
|---|---|---|
| [`miniqubot.py`](references/examples/miniqubot.py) | `001-1unit-grbl-serial` | none |
| [`syringequbot.py`](references/examples/syringequbot.py) | `002-1unit-reprap-http` | autosampler syringe (frame was the capper before) |
| [`pipqubot_mof.py`](references/examples/pipqubot_mof.py) | `003-2unit-grbl-serial` | rLine 50-1000 µL |
| [`pipqubot_xl.py`](references/examples/pipqubot_xl.py) | `004-4unit-reprap-http` | rLine 50-1000 µL, A-axis capper |
| [`claw_machine.py`](references/examples/claw_machine.py) | `005-8unit-grblhal-serial` | rotating vacuum gripper |
| [`dancefloor.py`](references/examples/dancefloor.py) | `006-1unit-grblhal-serial` | vacuum chamber |
| [`overkill2.py`](references/examples/overkill2.py) | `007-2unit-grblhal-serial` | rLine 50-1000 µL multistep |
| [`photoreactor.py`](references/examples/photoreactor.py) | `008-1unit-grblhal-serial` | Orion 4-channel LED |
| [`eis_qubot.py`](references/examples/eis_qubot.py) | `009-1unit-grblhal-serial` | parallel force actuators |

Each file has:
- Constants: `FRAME`, `SOFT_LIMITS`, `HOME_ON_STARTUP`, and the toolhead calibration measured on that machine.
- `Driver.__init__`, which takes ports and hosts as arguments, opens the hardware, and applies the frame limits.
- The `shutdown` and `estop` hooks.
- The basic commands `home`, `move_absolute`, `move_relative`, and `get_position`, with review-me `@safety` text.

The docstring keeps the machine's notes, open limit questions, and the commands its earlier edge advertised. Machine-specific commands (aspirate, grip, lamp, press) are written per edge on top of these. Gantry serials `001` to `004` are provisional labels, not asset tags.

## Where a finished edge lives

One qubot is one directory directly under the site monorepo's `edges/` directory. Do not put that directory in this repository, and do not group several qubots under a shared folder in the site monorepo.

```text
<puda-site>/edges/<one-qubot>/
  driver.py        # qubot imports, FRAME + calibration constants, Driver with @command methods
  main.py          # Config (MACHINE_ID, NATS_SERVERS, ports) -> Driver(...)
  labware/         # the edge's own <name>.json labware definitions, if any
  pyproject.toml   # depends on qubot-drivers, pinned
  uv.lock
  Dockerfile
  compose.yml
  .env.example
```

On IMRE that is `puda-imre-mof/edges/pipqubot-xl-edge/` and `puda-imre-mof/edges/syringequbot-edge/`. Another site gets its own monorepo and only its own qubot directories.

## Custom labware

Labware that qubot does not bundle goes in the edge's `labware/` folder as `<name>.json`. Loading by name searches the edge's folders first, then the bundled definitions, so a file there can also replace a bundled one with the same name. List what is bundled with `get_available_labware()`.

`edges/<one-qubot>/labware/vial_rack_2x2.json`. Coordinates are mm from the labware's front-left-bottom corner. `x`/`y` are well centers, `z` is the well bottom.

```json
{
  "metadata": {"displayName": "2x2 Vial Rack 20 mL", "displayCategory": "tubeRack", "displayVolumeUnits": "µL"},
  "dimensions": {"xDimension": 60.0, "yDimension": 60.0, "zDimension": 45.0},
  "ordering": [["A1", "B1"], ["A2", "B2"]],
  "wells": {
    "A1": {"x": 15.0, "y": 45.0, "z": 5.0, "depth": 40.0, "diameter": 28.0, "shape": "circular", "totalLiquidVolume": 20000},
    "B1": {"x": 15.0, "y": 15.0, "z": 5.0, "depth": 40.0, "diameter": 28.0, "shape": "circular", "totalLiquidVolume": 20000},
    "A2": {"x": 45.0, "y": 45.0, "z": 5.0, "depth": 40.0, "diameter": 28.0, "shape": "circular", "totalLiquidVolume": 20000},
    "B2": {"x": 45.0, "y": 15.0, "z": 5.0, "depth": 40.0, "diameter": 28.0, "shape": "circular", "totalLiquidVolume": 20000}
  },
  "insert_depth": 40.0
}
```

- `ordering` lists wells column by column; `get_available_labware` reads rows and columns from it.
- `wells.<id>.x/y/z` gives `get_well_position`.
- `dimensions.zDimension` gives `get_height()`.
- `insert_depth` gives `get_insert_depth()`.

Other Opentrons fields (`brand`, `parameters`, `groups`, …) may be included and are ignored.

In `driver.py`:

```python
from pathlib import Path

from qubot.labware import Deck, StandardLabware

LABWARE_DIR = Path(__file__).resolve().parent / "labware"

deck = Deck.from_frame(FRAME, labware_paths=[LABWARE_DIR])
deck.load_labware("A1", "vial_rack_2x2")                 # edges/<one-qubot>/labware/vial_rack_2x2.json
deck.load_labware("A2", "opentrons_96_tiprack_300ul")    # bundled with qubot
rack = deck["A1"]
rack.get_well_position("B2")                             # Position(x=45.0, y=15.0, z=5.0), relative to the rack

# Without a deck: one file, or a folder search.
rack = StandardLabware.from_file(LABWARE_DIR / "vial_rack_2x2.json")
rack = StandardLabware("vial_rack_2x2", search_paths=[LABWARE_DIR])
```

Add the slot's calibrated origin to `get_well_position(...)` to get a machine coordinate. Slot origins are calibrated per edge and kept in `driver.py`, not in the labware file. The template's Dockerfile copies the whole edge directory (`COPY . .`), so `labware/` ships in the image unless `.dockerignore` excludes it.

## Edge checklist

Answer every item before scaffolding. The answers go into the edge's `driver.py` (constants, `@safety`) and `main.py` (`Config` fields). Start from the matching reference driver if there is one.

- `qubot-drivers` version or git ref the edge pins:
- Gantry controller (`GrblHALController`, `GrblWSController`, `RepRapHTTPController`) and its port or host `Config` field:
- `Frame`: axes, hardware limits, default deck, home order, expected firmware identity and settings:
- Soft limits inside the frame, or none:
- Startup homing: yes or no:
- For each command the edge advertises: safety summary, hazards, requires, forbidden_when, confirm:
- End effectors, and for each: axis, port `Config` field, calibration values:
- Syringe length, if an autosampler syringe is mounted:
- Deck: frame default grid, or a replacement. Calibrated slot origins, or uncalibrated:
- Labware used, and which are new (each new one is a `<name>.json` in the edge's `labware/`, passed as `labware_paths`):
- Advertise deck commands: yes or no:
- MACHINE_ID:
- NATS_SERVERS:
- Existing edge this must match:

## Steps

1. Answer every item in the edge checklist above. Scaffold the service from [edge-python-template](https://github.com/PUDAP/edge-python-template) only after that. Keep the existing directory name and `MACHINE_ID`.
2. Add `qubot-drivers` to the edge's `[project].dependencies`, pinned to a release (`qubot-drivers==<version>`) or a git ref (`qubot-drivers @ git+https://github.com/PUDAP/qubot@<ref>`). Run `uv lock`. The import name stays `qubot`.
3. Copy the matching `references/examples/<machine>.py` over the template's `driver.py`, or write one the same way. Set `SOFT_LIMITS` and `HOME_ON_STARTUP`, rewrite every `@safety` for this site, and add the machine's own commands.
4. Add the port and host fields to `Config` in `main.py` and pass them to `Driver(...)`. Leave `.env.example` as placeholders.
5. Import `driver.py` once offline (`uv run python -c "import driver"`). `Frame` and the effector constructors raise on values outside the frame or bad calibration. Importing opens no port; `Driver(...)` does.
6. Build and start the container only when a person allows that machine to move. Check `puda machine commands <machine_id>` once it is connected.

Attaching another toolhead is an edit to `driver.py` and `main.py`, then a rebuild.

`.env.example` stays placeholders. If the user supplies this host's `.env`, copy it to `<edge>/.env` and `chmod 600` it; never copy `.env.example`. Otherwise leave `.env` absent. Make each port and host a required `Config` field (no default) in `main.py`, so a missing or blank `.env` stops the edge at startup.
