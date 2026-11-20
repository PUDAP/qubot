# qubot

Monorepo for machine edge services and shared drivers.

## Packages

- `edges/first` — First machine edge service (serial ports for qubot and Sartorius). `MACHINE_ID=first`
- `edges/capper` — Capper machine edge service (HTTP to qubot). `MACHINE_ID=capper`
- `edges/syringequbot` — Syringe Qubot edge service (HTTP to the same gantry as Capper, passive syringe). `MACHINE_ID=syringequbot`
- `edges/pipqubot-mof` — MOF PipQuBot edge service (serial ports for the GRBL gantry and Sartorius pipette). `MACHINE_ID=pipqubot_mof`
- `edges/pipqubot-xl` — PipQuBot XL edge service (serial gantry, Sartorius pipette, and an A-axis capper head). `MACHINE_ID=pipqubot-xl`
- `edges/miniqubot` — MiniQubot edge service (one GRBL serial gantry, empty head; startup homes). `MACHINE_ID=miniqubot`
- `edges/pescador` — Pescador PipQuBot edge service (WebSocket gantry and Sartorius pipette). `MACHINE_ID=pescador-pipqubot`
- `edges/pipqubot-v3` — Preserved legacy V3 implementation; no configured service or deployment entrypoint
- `driver` — Shared controllers, position/deck/labware utilities, and logging only

Machine implementations live directly in their owning edge folders as `driver.py`. Each configured edge's `main.py` imports its adjacent driver. Public hardware methods are marked `@command` so PUDA can advertise them.

| Owning folder | Import |
| --- | --- |
| `edges/first` | `from driver import First` |
| `edges/capper` | `from driver import Capper` |
| `edges/miniqubot` | `from driver import MiniQubot` |
| `edges/pescador` | `from driver import Pipette`; `from pescador import Pescador` |
| `edges/pipqubot-mof` | `from driver import PipQuBotMOF` |
| `edges/pipqubot-xl` | `from driver import PipQuBotXL` |
| `edges/syringequbot` | `from driver import SyringeQubot` |
| `edges/pipqubot-v3` | `from driver import PipQuBotV3` |

The former machine imports from the shared driver library are removed (no compatibility shims). Edges are non-package (virtual) workspace members: sync their dependencies, then run from the owning edge folder. Docker retains that edge's directory and the shared driver source on `PYTHONPATH`. Do not put several edge directories on one import path; offline tests load each local driver under a unique importlib alias using root `conftest.py`. `Pescador` is the gantry-only variant of the Pescador pipetting machine and is retained beside `Pipette`; its existing service still uses `Pipette`. V3 retains its separate calibration and is not substituted for MOF.

Each edge README names that edge's environment variables, whether startup moves hardware, and the start command. If upgrading an existing checkout, move the untracked `.env` to its matching `edges/<name>/` before using the new Compose file (`pescador-pipqubot-edge/` becomes `edges/pescador/`). Compose project names, container names, Python package names, and image tags are unchanged. Rebuild with the new Compose file so the image and its `.env` mount use the same paths; schedule any live recreation separately.

## Offline development checks

```bash
uv sync --all-packages --group dev --frozen
uv run --all-packages --group dev --frozen pytest
```

Root pytest configuration collects controller/labware tests and edge unit tests only. Manual machine-motion scripts live under the owning edge's `examples/` and must not be run without operator approval. Imports alone do not initialize hardware; starting an edge or running an example can home or move it. After approval, run an example from its owning edge folder with that folder on the import path, for example `PYTHONPATH=. uv run python examples/first.py` in `edges/first`.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.14+ and `uv` (for baremetal mode)
- For `edges/first`, the gantry and Sartorius serial devices available
- For `edges/pipqubot-mof`, the GRBL gantry and Sartorius pipette serial devices available
- For `edges/pipqubot-xl`, the RepRap gantry and Sartorius pipette serial devices available

## Run with Docker

From the edge directory, after copying `.env.example` to `.env`:

```bash
docker compose up -d --build
docker compose logs -f
docker compose down
```

## Run baremetal

From the repository root:

```bash
uv sync --all-packages
uv run --package first-edge python edges/first/main.py
uv run --package capper-edge python edges/capper/main.py
uv run --package syringequbot-edge python edges/syringequbot/main.py
uv run --package pipqubot-mof-edge python edges/pipqubot-mof/main.py
uv run --package pipqubot-xl-edge python edges/pipqubot-xl/main.py
uv run --package pescador-pipqubot-edge python edges/pescador/main.py
```

On Windows, the XL edge can also be started from its directory with `.\start_edge.bat`.

## Build and push image

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
docker compose -f edges/first/compose.yml build
docker compose -f edges/capper/compose.yml build
docker compose -f edges/syringequbot/compose.yml build
docker compose -f edges/pipqubot-mof/compose.yml build
docker compose -f edges/pipqubot-xl/compose.yml build
docker compose -f edges/pescador/compose.yml build
docker compose -f edges/first/compose.yml push
docker compose -f edges/capper/compose.yml push
docker compose -f edges/syringequbot/compose.yml push
docker compose -f edges/pipqubot-mof/compose.yml push
docker compose -f edges/pipqubot-xl/compose.yml push
docker compose -f edges/pescador/compose.yml push
```

## Notes

- Docker build context is the repository root (`../..` from each edge directory).
- Each Compose file references the Dockerfile in its edge directory.
- If a serial edge cannot open its port, add the user to `dialout` and start a new login: `sudo usermod -aG dialout $USER`.
