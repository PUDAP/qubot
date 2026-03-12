# qubot

Monorepo for the First edge service and shared drivers.

## What It Does

- Runs the First machine edge service.
- Connects to NATS and translates commands into machine actions.
- Uses local hardware devices (serial ports and camera).

## Prerequisites

- Docker and Docker Compose installed
- Python 3.14+ and `uv` (for baremetal mode)
- Devices available:
  - `/dev/ttyACM0` (qubot)
  - `/dev/ttyUSB0` (sartorius)
  - `/dev/video0` (camera)

## Environment Setup

From repo root:

```bash
cp edge/.env.example edge/.env
```

Edit `edge/.env` and configure:

- `MACHINE_ID`
- `NATS_SERVERS`
- `QUBOT_PORT`
- `SARTORIUS_PORT`
- `CAMERA_INDEX`

## Run With Docker (Recommended)

All commands below are run from repo root.

Build and start:

```bash
docker compose -f edge/compose.yml up -d --build
```

View logs:

```bash
docker compose -f edge/compose.yml logs -f
```

Stop:

```bash
docker compose -f edge/compose.yml down
```

## Run Baremetal (uv)

From repo root:

```bash
uv sync --all-packages
uv run --package first-edge python edge/main.py
```

## Build and Push Image (GHCR)

Login:

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

Build:

```bash
docker compose -f edge/compose.yml build
```

Push:

```bash
docker push ghcr.io/PUDAP/first-edge:latest
```

Or with Compose:

```bash
docker compose -f edge/compose.yml push
```

## Notes

- Docker build context is workspace root (`..` in `edge/compose.yml`).
- Dockerfile path is `edge/Dockerfile`.
- If serial access fails, add your user to `dialout`:
  - `sudo usermod -aG dialout $USER`

