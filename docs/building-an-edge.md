# Building a qubot edge

This repository is the reference an agent uses to build a new qubot edge. It holds the ingredients as one Python package, `qubot`: gantry transports and the `Frame` type, end-effector drivers, geometry, and the edge kit. Machine values (frame limits, calibration) live in the edge contract; `docs/examples/` has reference contracts and `edge_config.py` shows how an edge configures qubot from one. It does not hold a running edge, a host `.env`, or a site's machine id.

Read [MODULARIZATION.md](../MODULARIZATION.md) for the split, and [CONTRACT.md](../CONTRACT.md) for the blank form. Record ingredient changes in [CHANGELOG.md](../CHANGELOG.md).

## Where a finished edge lives

One qubot is one directory directly under the site monorepo's `edges/` directory. Do not put that directory in this repository, and do not group several qubots under a shared folder in the site monorepo.

```text
<puda-site>/edges/<one-qubot>/
  contracts/<version>.toml
  vendor/
  driver.py
  main.py
  pyproject.toml
  Dockerfile
  compose.yml
  .env.example
```

On IMRE that is `puda-imre-mof/edges/pipqubot-xl-edge/` and `puda-imre-mof/edges/syringequbot-edge/`. Another site gets its own monorepo and only its own qubot directories.

`vendor/qubot` is a snapshot of the `qubot` package; `vendor/REVISION` names the gantry and effector modules that edge's contract uses. List `qubot` in the edge's `[project].dependencies`. The site edge builds from its own directory. It does not need this checkout at image-build time.

## Steps

1. Fill every blank in [CONTRACT.md](../CONTRACT.md). Scaffold the service from [edge-python-template](https://github.com/PUDAP/edge-python-template) only after that. Keep the existing directory name and `MACHINE_ID`.
2. Start from `docs/examples/<machine>.toml`, fill it, and put it at `<edge>/contracts/<version>.toml`. Leave `.env.example` as placeholders.
3. Check it: `python3 scripts/check_contract.py <edge>/contracts/<version>.toml`
4. Copy the ingredients: `python3 scripts/vendor_edge.py <edge>/contracts/<version>.toml <edge>`
5. From the edge directory, run `uv lock`. Build and start the container only when a person allows that machine to move.

`scripts/attach_toolhead.py` writes the next contract and refreshes `vendor/`. It does not build an image or start a container.

If the user supplies this host's `.env`, copy it with `scripts/accept_host_env.py`. Otherwise leave `.env` absent. The edge refuses to start until that file is filled.
