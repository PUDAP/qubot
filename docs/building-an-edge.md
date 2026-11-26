# Building a qubot edge

This repository is the reference an agent uses to build a new qubot edge. It holds the ingredients as one Python package, `qubot`: gantry transports and the `Frame` type, end-effector drivers, geometry, and the edge kit. Machine values (frame limits, calibration) live in each edge's code; `docs/examples/` has one reference file per known machine. It does not hold a running edge, a host `.env`, or a site's machine id.

Read [MODULARIZATION.md](../MODULARIZATION.md) for the split, and [EDGE_CHECKLIST.md](../EDGE_CHECKLIST.md) for what an edge must define. Record driver changes in [CHANGELOG.md](../CHANGELOG.md).

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

## Steps

1. Answer every item in [EDGE_CHECKLIST.md](../EDGE_CHECKLIST.md). Scaffold the service from [edge-python-template](https://github.com/PUDAP/edge-python-template) only after that. Keep the existing directory name and `MACHINE_ID`.
2. Add `qubot` to the edge's `[project].dependencies`, pinned to a release or git ref (`qubot @ git+https://github.com/PUDAP/qubot@<ref>` until it is on PyPI). Run `uv lock`.
3. Copy the matching `docs/examples/<machine>.py` into the edge as `hardware.py`, or write one the same way. Fill the safety text, confirm, startup homing, and soft limits. Leave `.env.example` as placeholders.
4. Import `hardware.py` once offline (`uv run python -c "import hardware"`). `Frame` and the effector constructors raise on values outside the frame or bad calibration. No port is opened at import.
5. Build and start the container only when a person allows that machine to move.

Attaching another toolhead is an edit to `hardware.py` and `driver.py`, then a rebuild.

If the user supplies this host's `.env`, copy it with `scripts/accept_host_env.py`. Otherwise leave `.env` absent. The edge refuses to start until that file is filled.
