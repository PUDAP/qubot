# PipQuBot XL Edge

PUDA edge service for the `PipQuBotXL` driver.

## Configure

Copy `.env.example` to `.env`, then set the NATS servers, Duet/RepRap controller
IP, and Sartorius serial port. `HOME_GANTRY_ON_STARTUP` and
`INITIALIZE_PIPETTE_ON_STARTUP` are explicit startup-motion gates; keep both
`false` for a connect-only deployment.

## Run on Windows

```powershell
.\start_edge.bat
```

## Run with Docker

From this directory:

```powershell
docker compose up --build
```
