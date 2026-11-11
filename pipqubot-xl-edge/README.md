# PipQuBot XL edge

PUDA edge for the PipQuBot XL. The head is a Sartorius rLine 50–1000 µL. The volume step is stated in the driver.

## Configure

Copy `.env.example` to `.env`. Set `NATS_SERVERS`, `QUBOT_IP`, and `SATORIUS_PORT`. Use a `/dev/serial/by-id/` path for the pipette.

`HOME_GANTRY_ON_STARTUP` and `INITIALIZE_PIPETTE_ON_STARTUP` start motion when they are true. Keep both `false` for a connect-only start.

## Run

On Windows, from this directory:

```powershell
.\start_edge.bat
```

With Docker, from this directory:

```powershell
docker compose up -d --build
```

Starting with either gate set homes the gantry or initializes the pipette.

Live commands: `puda machine commands pipqubot-xl`.
