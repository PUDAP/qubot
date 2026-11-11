# qubot

Monorepo for machine edge services and shared drivers.

## Packages

- `first-edge` — First machine edge service (serial ports for qubot and Sartorius). `MACHINE_ID=first`
- `capper-edge` — Capper machine edge service (HTTP to qubot). `MACHINE_ID=capper`
- `syringequbot-edge` — Syringe Qubot edge service (HTTP to the same gantry as capper-edge, passive syringe). `MACHINE_ID=syringequbot`
- `pipqubot-mof-edge` — MOF PipQuBot edge service (serial ports for the GRBL gantry and Sartorius pipette). `MACHINE_ID=pipqubot_mof`
- `pipqubot-xl-edge` — PipQuBot XL edge service (serial gantry, Sartorius pipette, and an A-axis capper head). `MACHINE_ID=pipqubot-xl`
- `miniqubot-edge` — MiniQubot edge service (one GRBL serial gantry, empty head; startup homes). `MACHINE_ID=miniqubot`
- `pescador-pipqubot-edge` — Pescador PipQuBot edge service (WebSocket gantry and Sartorius pipette). `MACHINE_ID=pescador-pipqubot`
- `pipqubot-v3-edge` — Preserved legacy V3 implementation; no configured service or deployment entrypoint
- `driver` — Shared controllers, position/deck/labware utilities, and logging only

Machine implementations live directly in their owning edge folders as `driver.py`. Each configured edge's `main.py` imports its adjacent driver. Public hardware methods are marked `@command` so PUDA can advertise them.

| Owning folder | Import |
| --- | --- |
| `first-edge` | `from driver import First` |
| `capper-edge` | `from driver import Capper` |
| `miniqubot-edge` | `from driver import MiniQubot` |
| `pescador-pipqubot-edge` | `from driver import Pipette`; `from pescador import Pescador` |
| `pipqubot-mof-edge` | `from driver import PipQuBotMOF` |
| `pipqubot-xl-edge` | `from driver import PipQuBotXL` |
| `syringequbot-edge` | `from driver import SyringeQubot` |
| `pipqubot-v3-edge` | `from driver import PipQuBotV3` |

The former machine imports from the shared driver library are removed (no compatibility shims). Edges are non-package (virtual) workspace members: sync their dependencies, then run from the owning edge folder. Docker retains that edge's directory and the shared driver source on `PYTHONPATH`. Do not put several edge directories on one import path; offline tests load each local driver under a unique importlib alias using root `conftest.py`. `Pescador` is the gantry-only variant of the Pescador pipetting machine and is retained beside `Pipette`; its existing service still uses `Pipette`. V3 retains its separate calibration and is not substituted for MOF.

Each edge README names that edge's environment variables, whether startup moves hardware, and the start command.

## Offline development checks

```bash
uv sync --all-packages --group dev --frozen
uv run --all-packages --group dev --frozen pytest
```

Root pytest configuration collects controller/labware tests and edge unit tests only. Manual machine-motion scripts live under the owning edge's `examples/` and must not be run without operator approval. Imports alone do not initialize hardware; starting an edge or running an example can home or move it. After approval, run an example from its owning edge folder with that folder on the import path, for example `PYTHONPATH=. uv run python examples/first.py` in `first-edge`.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.14+ and `uv` (for baremetal mode)
- For `first-edge`, the gantry and Sartorius serial devices available
- For `pipqubot-mof-edge`, the GRBL gantry and Sartorius pipette serial devices available
- For `pipqubot-xl-edge`, the RepRap gantry and Sartorius pipette serial devices available

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
uv run --package first-edge python first-edge/main.py
uv run --package capper-edge python capper-edge/main.py
uv run --package syringequbot-edge python syringequbot-edge/main.py
uv run --package pipqubot-mof-edge python pipqubot-mof-edge/main.py
uv run --package pipqubot-xl-edge python pipqubot-xl-edge/main.py
uv run --package pescador-pipqubot-edge python pescador-pipqubot-edge/main.py
```

On Windows, the XL edge can also be started from its directory with `.\start_edge.bat`.

## Build and push image

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
docker compose -f first-edge/compose.yml build
docker compose -f capper-edge/compose.yml build
docker compose -f syringequbot-edge/compose.yml build
docker compose -f pipqubot-mof-edge/compose.yml build
docker compose -f pipqubot-xl-edge/compose.yml build
docker compose -f pescador-pipqubot-edge/compose.yml build
docker compose -f first-edge/compose.yml push
docker compose -f capper-edge/compose.yml push
docker compose -f syringequbot-edge/compose.yml push
docker compose -f pipqubot-mof-edge/compose.yml push
docker compose -f pipqubot-xl-edge/compose.yml push
docker compose -f pescador-pipqubot-edge/compose.yml push
```

## Notes

- Docker build context is the repository root (`..` in each `compose.yml`).
- Each Compose file references the Dockerfile in its edge directory.
- If a serial edge cannot open its port, add the user to `dialout` and start a new login: `sudo usermod -aG dialout $USER`.
