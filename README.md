# qubot

Monorepo for machine edge services and shared drivers.

## Packages

- `first-edge` — First machine edge service (serial ports for qubot and satorius)
- `capper-edge` — Capper machine edge service (HTTP to qubot)
- `syringequbot-edge` — Syringe Qubot edge service (HTTP to the same gantry as capper-edge, passive syringe)
- `pipqubot-mof-edge` — MOF PipQuBot edge service (serial ports for the GRBL gantry and Sartorius pipette)
- `pipqubot-xl-edge` — PipQuBot XL edge service (serial gantry, Sartorius pipette, and an A-axis capper head)
- `miniqubot-edge` — MiniQubot edge service (one GRBL serial gantry, empty head; startup homes)
- `pescador-pipqubot-edge` — Pescador PipQuBot edge service (WebSocket gantry and Sartorius pipette)
- `pipqubot-v3-edge` — Preserved legacy V3 implementation; no configured service or deployment entrypoint
- `driver` — Shared controllers, position/deck/labware utilities, and logging only

Machine implementations live directly in their owning edge folders as
`driver.py`. Each configured edge's `main.py` imports its adjacent driver.
Public hardware methods are marked `@command` so PUDA can advertise them.

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

The former machine imports from the shared driver library are removed (no
compatibility shims). Edges are non-package (virtual) workspace members: sync
their dependencies, then run from the owning edge folder. Docker retains that
edge's directory and the shared driver source on `PYTHONPATH`. Do not put several
edge directories on one import path; offline tests load each local driver under
a unique importlib alias using root `conftest.py`.
`Pescador` is the gantry-only variant of the Pescador pipetting machine
and is retained beside `Pipette`; its existing service still uses `Pipette`.
V3 retains its separate calibration and is not substituted for MOF.

## Offline development checks

```bash
uv sync --all-packages --group dev --frozen
uv run --all-packages --group dev --frozen pytest
```

Root pytest configuration collects controller/labware tests and edge unit tests
only. Manual machine-motion scripts live under the owning edge's `examples/`
and must not be run without operator approval. Imports alone do not initialize
hardware; starting an edge or running an example can home or move it.
After approval, run an example from its owning edge folder with that folder on
the import path, e.g. `PYTHONPATH=. uv run python examples/first.py` in `first-edge`.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.14+ and `uv` (for baremetal mode)
- For `first-edge`, devices available:
  - `/dev/ttyACM0` (qubot)
  - `/dev/ttyUSB0` (satorius)
- For `pipqubot-mof-edge`, the GRBL gantry and Sartorius pipette serial devices available
- For `pipqubot-xl-edge`, the RepRap gantry and Sartorius pipette serial devices available

## Environment Setup

### first-edge

From repo root:

```bash
cp first-edge/.env.example first-edge/.env
```

Edit `first-edge/.env` and configure:

- `MACHINE_ID`
- `NATS_SERVERS`
- `QUBOT_PORT`
- `SATORIUS_PORT`

### capper-edge

From repo root:

```bash
cp capper-edge/.env.example capper-edge/.env
```

Edit `capper-edge/.env` and configure:

- `MACHINE_ID`
- `NATS_SERVERS`
- `QUBOT_IP`

### syringequbot-edge

From repo root:

```bash
cp syringequbot-edge/.env.example syringequbot-edge/.env
```

Edit `syringequbot-edge/.env` and configure:

- `MACHINE_ID`
- `NATS_SERVERS`
- `QUBOT_IP`

Starting this service connects to the RepRap board and does not home.

### pipqubot-mof-edge

From repo root:

```bash
cp pipqubot-mof-edge/.env.example pipqubot-mof-edge/.env
```

Edit `pipqubot-mof-edge/.env` and configure:

- `MACHINE_ID`
- `NATS_SERVERS`
- `QUBOT_PORT` (GRBL gantry serial port)
- `SATORIUS_PORT` (Sartorius pipette serial port)

The Compose configuration maps stable `/dev/serial/by-id/...` device paths to the container paths configured by `QUBOT_PORT` and `SATORIUS_PORT`. Update `pipqubot-mof-edge/compose.yml` if your devices have different IDs.

### pipqubot-xl-edge

From repo root:

```bash
cp pipqubot-xl-edge/.env.example pipqubot-xl-edge/.env
```

On Windows PowerShell:

```powershell
Copy-Item pipqubot-xl-edge/.env.example pipqubot-xl-edge/.env
```

Edit `pipqubot-xl-edge/.env` and configure:

- `MACHINE_ID` (defaults to `pipqubot-xl`)
- `NATS_SERVERS`
- `QUBOT_PORT` (RepRap gantry serial port)
- `SATORIUS_PORT` (Sartorius pipette serial port)

Windows serial ports can be specified as `COM3`, `COM4`, and so on. Linux deployments should prefer stable `/dev/serial/by-id/...` paths.

### pescador-pipqubot-edge

From repo root:

```bash
cp pescador-pipqubot-edge/.env.example pescador-pipqubot-edge/.env
```

Edit `pescador-pipqubot-edge/.env` and configure:

- `MACHINE_ID`
- `NATS_SERVERS`
- `QUBOT_IP`
- `SATORIUS_PORT`

## Run With Docker (Recommended)

All commands below are run from repo root.

### first-edge

Build and start:

```bash
docker compose -f first-edge/compose.yml up -d --build
```

View logs:

```bash
docker compose -f first-edge/compose.yml logs -f
```

Stop:

```bash
docker compose -f first-edge/compose.yml down
```

### capper-edge

Build and start:

```bash
docker compose -f capper-edge/compose.yml up -d --build
```

View logs:

```bash
docker compose -f capper-edge/compose.yml logs -f
```

Stop:

```bash
docker compose -f capper-edge/compose.yml down
```

### syringequbot-edge

Build and start:

```bash
docker compose -f syringequbot-edge/compose.yml up -d --build
```

View logs:

```bash
docker compose -f syringequbot-edge/compose.yml logs -f
```

Stop:

```bash
docker compose -f syringequbot-edge/compose.yml down
```

### pipqubot-mof-edge

Build and start:

```bash
docker compose -f pipqubot-mof-edge/compose.yml up -d --build
```

View logs:

```bash
docker compose -f pipqubot-mof-edge/compose.yml logs -f
```

Stop:

```bash
docker compose -f pipqubot-mof-edge/compose.yml down
```

Starting this service connects both controllers, homes the gantry, and initializes the pipette.

### pipqubot-xl-edge

Build and start:

```bash
docker compose -f pipqubot-xl-edge/compose.yml up -d --build
```

View logs:

```bash
docker compose -f pipqubot-xl-edge/compose.yml logs -f
```

Stop:

```bash
docker compose -f pipqubot-xl-edge/compose.yml down
```

Starting this service connects both serial controllers, homes the gantry, and initializes the pipette. The capper head uses the A axis for vertical travel.

### pescador-pipqubot-edge

Build and start:

```bash
docker compose -f pescador-pipqubot-edge/compose.yml up -d --build
```

View logs:

```bash
docker compose -f pescador-pipqubot-edge/compose.yml logs -f
```

Stop:

```bash
docker compose -f pescador-pipqubot-edge/compose.yml down
```

## Run Baremetal (uv)

From repo root:

```bash
uv sync --all-packages
uv run --package first-edge python first-edge/main.py
uv run --package capper-edge python capper-edge/main.py
uv run --package syringequbot-edge python syringequbot-edge/main.py
uv run --package pipqubot-mof-edge python pipqubot-mof-edge/main.py
uv run --package pipqubot-xl-edge python pipqubot-xl-edge/main.py
uv run --package pescador-pipqubot-edge python pescador-pipqubot-edge/main.py
```

On Windows, you can also start the XL edge from its directory:

```powershell
cd pipqubot-xl-edge
.\start_edge.bat
```

## Build and Push Image (GHCR)

Login:

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

Build:

```bash
docker compose -f first-edge/compose.yml build
docker compose -f capper-edge/compose.yml build
docker compose -f syringequbot-edge/compose.yml build
docker compose -f pipqubot-mof-edge/compose.yml build
docker compose -f pipqubot-xl-edge/compose.yml build
docker compose -f pescador-pipqubot-edge/compose.yml build
```

Push:

```bash
docker push ghcr.io/PUDAP/first-edge:latest
docker push ghcr.io/PUDAP/capper-edge:latest
docker push ghcr.io/pudap/syringequbot-edge:latest
docker push ghcr.io/pudap/pipqubot-mof-edge:latest
docker push ghcr.io/pudap/pipqubot-xl-edge:latest
docker push ghcr.io/pudap/pescador-pipqubot-edge:latest
```

Or with Compose:

```bash
docker compose -f first-edge/compose.yml push
docker compose -f capper-edge/compose.yml push
docker compose -f syringequbot-edge/compose.yml push
docker compose -f pipqubot-mof-edge/compose.yml push
docker compose -f pipqubot-xl-edge/compose.yml push
docker compose -f pescador-pipqubot-edge/compose.yml push
```

## Notes

- Docker build context is workspace root (`..` in each `compose.yml`).
- Each Compose file references the Dockerfile in its edge package directory.
- If serial access fails on `first-edge`, `pipqubot-mof-edge`, or `pipqubot-xl-edge`, add your user to `dialout`:
  - `sudo usermod -aG dialout $USER`
