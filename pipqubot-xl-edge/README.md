# PipQuBot XL Edge

PUDA edge service for the `PipQuBotXL` driver.

## Configure

Copy `.env.example` to `.env`, then set the NATS servers and both serial ports
for the host. Windows serial ports can be specified as `COM3`, `COM4`, and so
on.

## Run on Windows

```powershell
.\start_edge.bat
```

## Run with Docker

From this directory:

```powershell
docker compose up --build
```
