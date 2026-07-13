# first

Monorepo for machine edge services and shared drivers.

## Packages

- `first-edge` — First machine edge service (serial ports for qubot and satorius)
- `capper-edge` — Capper machine edge service (HTTP to qubot)
- `driver` — Shared machine drivers

## Prerequisites

- Docker and Docker Compose installed
- Python 3.14+ and `uv` (for baremetal mode)
- For `first-edge`, devices available:
  - `/dev/ttyACM0` (qubot)
  - `/dev/ttyUSB0` (satorius)

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

## Run Baremetal (uv)

From repo root:

```bash
uv sync --all-packages
uv run --package first-edge python first-edge/main.py
uv run --package capper-edge python capper-edge/main.py
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
```

Push:

```bash
docker push ghcr.io/PUDAP/first-edge:latest
docker push ghcr.io/PUDAP/capper-edge:latest
```

Or with Compose:

```bash
docker compose -f first-edge/compose.yml push
docker compose -f capper-edge/compose.yml push
```

## Notes

- Docker build context is workspace root (`..` in each `compose.yml`).
- Dockerfile paths are `first-edge/Dockerfile` and `capper-edge/Dockerfile`.
- If serial access fails on `first-edge`, add your user to `dialout`:
  - `sudo usermod -aG dialout $USER`
