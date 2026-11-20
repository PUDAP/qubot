# First edge

PUDA edge for the original Qubot gantry and a Sartorius pipette. The entrypoint is `main.py`. The machine class is `First` in `driver.py`.

## Configure

Copy `.env.example` to `.env`. Set `MACHINE_ID`, `NATS_SERVERS`, `QUBOT_PORT`, and `SATORIUS_PORT`. Use a `/dev/serial/by-id/` path for each serial device.

## Run

From this directory:

```bash
docker compose up -d --build
```

Starting connects both controllers, homes the gantry, and initializes the pipette. Scripts in `examples/` are manual hardware operations.

Live commands: `puda machine commands first`.
