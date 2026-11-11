# Capper edge

PUDA edge for the Qubot capper. The entrypoint is `main.py`. The machine class is `Capper` in `driver.py`. It uses `RepRapHTTPController` from `qubot-drivers`.

## Configure

Copy `.env.example` to `.env`. Set `MACHINE_ID`, `NATS_SERVERS`, and `QUBOT_IP`.

## Run

From this directory:

```bash
docker compose up -d --build
```

Starting can home the gantry. `examples/home_capper.py` is a manual hardware operation and must not be run without operator approval.

Live commands: `puda machine commands capper`.
