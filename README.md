# qubot

Monorepo for machine edge services and shared drivers.

## Packages

- `first-edge` — First machine edge service (serial ports for qubot and satorius)
- `capper-edge` — Capper machine edge service (HTTP to qubot)
- `pipqubot-mof-edge` — MOF PipQuBot edge service (serial ports for the GRBL gantry and Sartorius pipette)
- `miniqubot-edge` — MiniQubot edge service (one GRBL serial gantry, empty head; startup homes)
- `pescador-pipqubot-edge` — Pescador PipQuBot edge service (WebSocket gantry and Sartorius pipette)
- `driver` — Shared machine drivers

Each edge's `main.py` wraps the matching class in `qubot_drivers.machines`. Public hardware methods are marked `@command` so PUDA can advertise them.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.14+ and `uv` (for baremetal mode)
- For `first-edge`, devices available:
  - `/dev/ttyACM0` (qubot)
  - `/dev/ttyUSB0` (satorius)
- For `pipqubot-mof-edge`, the GRBL gantry and Sartorius pipette serial devices available

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
uv run --package pipqubot-mof-edge python pipqubot-mof-edge/main.py
uv run --package pescador-pipqubot-edge python pescador-pipqubot-edge/main.py
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
docker compose -f pipqubot-mof-edge/compose.yml build
docker compose -f pescador-pipqubot-edge/compose.yml build
```

Push:

```bash
docker push ghcr.io/PUDAP/first-edge:latest
docker push ghcr.io/PUDAP/capper-edge:latest
docker push ghcr.io/pudap/pipqubot-mof-edge:latest
docker push ghcr.io/pudap/pescador-pipqubot-edge:latest
```

Or with Compose:

```bash
docker compose -f first-edge/compose.yml push
docker compose -f capper-edge/compose.yml push
docker compose -f pipqubot-mof-edge/compose.yml push
docker compose -f pescador-pipqubot-edge/compose.yml push
```

## Notes

- Docker build context is workspace root (`..` in each `compose.yml`).
- Dockerfile paths are `first-edge/Dockerfile`, `capper-edge/Dockerfile`, and `pipqubot-mof-edge/Dockerfile`.
- If serial access fails on `first-edge` or `pipqubot-mof-edge`, add your user to `dialout`:
  - `sudo usermod -aG dialout $USER`
