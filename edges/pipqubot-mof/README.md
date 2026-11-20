# MOF PipQuBot edge

PUDA edge for the MOF PipQuBot. It connects the GRBL gantry and a Sartorius pipette, then publishes commands and telemetry.

## Configure

Copy `.env.example` to `.env`. Set `MACHINE_ID`, `NATS_SERVERS`, `QUBOT_PORT`, and `SATORIUS_PORT`. Use a `/dev/serial/by-id/` path for each serial device.

## Run

From this directory:

```bash
docker compose up -d --build
```

Starting connects both controllers, homes the gantry, and initializes the pipette.

Live commands: `puda machine commands pipqubot_mof`.
