# Pescador PipQuBot edge

The running service uses `Pipette` from `driver.py`. The gantry-only `Pescador` class in `pescador.py` is not a second service.

## Configure

Copy `.env.example` to `.env`. Set `MACHINE_ID`, `NATS_SERVERS`, `QUBOT_IP`, and `SATORIUS_PORT`. Set the rLine model for the installed head. The preserved constructor does not name that model, and this edge does not guess one.

## Run

From this directory:

```bash
docker compose up -d --build
```

Imports do not connect to hardware. Starting can home the gantry and initialize the pipette. `examples/pipette.py` is a manual hardware operation.

Live commands: `puda machine commands pescador-pipqubot`.
