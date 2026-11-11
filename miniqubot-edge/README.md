# MiniQubot edge

PUDA edge for the empty-head three-axis MiniQubot. It uses `GrblHALController` from `qubot-drivers`.

## Configure

Copy `.env.example` to `.env`. Set `MACHINE_ID`, `NATS_SERVERS`, and `QUBOT_PORT`. `HOME_ON_STARTUP` defaults to true.

## Run

From this directory:

```bash
docker compose up -d --build
```

Starting connects the GRBL serial port, checks `$I` and `$$`, then homes all axes when `HOME_ON_STARTUP` is true.

Live commands: `puda machine commands miniqubot`.
