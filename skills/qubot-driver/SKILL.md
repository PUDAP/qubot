---
name: qubot-driver
description: Build or update a qubot edge's driver.py with the qubot driver package. Use for choosing a gantry controller and end effectors, configuring a machine's frame and calibration, adding a toolhead, or pinning qubot in an edge.
---

# Building a qubot edge

`qubot` is one Python package of gantry controllers, the `Frame` type, end-effector drivers, geometry, and the edge kit. It holds no machine values. Each edge's `driver.py` imports the drivers it carries, sets its frame limits and calibration as constants, and wraps them in a PUDA `Driver` class. This repository does not hold a running edge, a host `.env`, or a site's machine id. For NATS, `@command`/`@safety`, hooks, telemetry, and `main.py`, use the `puda-edge` skill.

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
  pyproject.toml   # depends on qubot-drivers, pinned
  uv.lock
  Dockerfile
  compose.yml
  .env.example
```

On IMRE that is `puda-imre-mof/edges/pipqubot-xl-edge/` and `puda-imre-mof/edges/syringequbot-edge/`. Another site gets its own monorepo and only its own qubot directories.

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

`.env.example` stays placeholders. If the user supplies this host's `.env`, copy it to `<edge>/.env` and `chmod 600` it; never copy `.env.example`. Otherwise leave `.env` absent; the edge refuses to start until it is filled (`qubot.edgekit.require_filled_env`).
