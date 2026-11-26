---
name: qubot-driver
description: Build or update a qubot edge's hardware with the qubot driver package. Use for choosing a gantry controller and end effectors, writing an edge's hardware.py, adding a toolhead, or pinning qubot in an edge.
---

# Building a qubot edge

`qubot` is one Python package of gantry controllers, the `Frame` type, end-effector drivers, geometry, and the edge kit. It holds no machine values. Each edge imports the drivers it carries and sets its frame limits, calibration, and wiring in its own code. This repository does not hold a running edge, a host `.env`, or a site's machine id. For NATS commands, decorators, and `driver.py`/`main.py`, use the `puda-edge` skill.

Supported controllers and end effectors are listed in the [README](../../README.md#supported-hardware). Reference configs for known machines are in [docs/examples/](../../docs/examples/), one file per machine. The README's [design](../../README.md#design) section explains the split. Record driver changes in [CHANGELOG.md](../../CHANGELOG.md).

## Where a finished edge lives

One qubot is one directory directly under the site monorepo's `edges/` directory. Do not put that directory in this repository, and do not group several qubots under a shared folder in the site monorepo.

```text
<puda-site>/edges/<one-qubot>/
  hardware.py      # imports qubot, constructs Frame, gantry, end effectors
  driver.py
  main.py
  pyproject.toml   # depends on qubot, pinned
  uv.lock
  Dockerfile
  compose.yml
  .env.example
```

On IMRE that is `puda-imre-mof/edges/pipqubot-xl-edge/` and `puda-imre-mof/edges/syringequbot-edge/`. Another site gets its own monorepo and only its own qubot directories.

## Edge checklist

Answer every item before scaffolding. The answers go into the edge's own code, usually `hardware.py`. Start from the matching machine in `docs/examples/` if there is one.

- qubot version or git ref the edge pins:
- Gantry controller (`GrblHALController`, `GrblWSController`, `RepRapHTTPController`) and its port or host env name:
- `Frame`: axes, hardware limits, default deck, home order, expected firmware identity and settings:
- Soft limits inside the frame, or none:
- Startup homing: yes or no:
- For each command the edge advertises: safety summary, hazards, requires, forbidden_when, confirm:
- End effectors, and for each: axis, port env name, calibration values:
- Syringe length, if an autosampler syringe is mounted:
- Deck: frame default grid, or a replacement. Calibrated slot origins, or uncalibrated:
- Advertise deck commands: yes or no:
- MACHINE_ID:
- NATS_SERVERS:
- Existing edge this must match:

## Steps

1. Answer every item in the edge checklist above. Scaffold the service from [edge-python-template](https://github.com/PUDAP/edge-python-template) only after that. Keep the existing directory name and `MACHINE_ID`.
2. Add `qubot` to the edge's `[project].dependencies`, pinned to a release or git ref (`qubot @ git+https://github.com/PUDAP/qubot@<ref>` until it is on PyPI). Run `uv lock`.
3. Copy the matching `docs/examples/<machine>.py` into the edge as `hardware.py`, or write one the same way. Fill the safety text, confirm, startup homing, and soft limits. Leave `.env.example` as placeholders.
4. Import `hardware.py` once offline (`uv run python -c "import hardware"`). `Frame` and the effector constructors raise on values outside the frame or bad calibration. No port is opened at import.
5. Build and start the container only when a person allows that machine to move.

Attaching another toolhead is an edit to `hardware.py` and `driver.py`, then a rebuild.

`.env.example` stays placeholders. If the user supplies this host's `.env`, copy it to `<edge>/.env` and `chmod 600` it; never copy `.env.example`. Otherwise leave `.env` absent; the edge refuses to start until it is filled (`qubot.edgekit.require_filled_env`).
