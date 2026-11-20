# Syringe Qubot edge

PUDA edge for the Qubot gantry with a passive syringe. It uses `RepRapHTTPController` from `qubot-drivers`, the same HTTP connection as the old capper. The syringe has no actuator. Liquid is drawn by a separate pump edge.

## Configure

Copy `.env.example` to `.env`. Set `MACHINE_ID`, `NATS_SERVERS`, and `QUBOT_IP`.

## Run

From this directory:

```bash
docker compose up -d --build
```

Starting connects to the RepRap board and does not home. `safe_move_to` retracts to Z 0 before XY movement.

Live commands: `puda machine commands syringequbot`.
