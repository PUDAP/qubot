"""PUDA edge service for the empty-head MiniQubot."""

import asyncio
import logging
import sys
import time
import psutil
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from puda import EdgeNatsClient, EdgeRunner
from qubot_drivers.machines.miniqubot import MiniQubot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logging.getLogger("qubot_drivers").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Config(BaseSettings):
    machine_id: str
    nats_servers: str
    qubot_port: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def nats_server_list(self) -> list[str]:
        return [s.strip() for s in self.nats_servers.split(",") if s.strip()]


def load_config() -> Config:
    try:
        return Config()
    except Exception as exc:
        logger.error("Failed to load configuration: %s", exc.__class__.__name__)
        sys.exit(1)


async def main():
    config = load_config()
    logger.info("Config loaded for %s", config.machine_id)
    logger.info("Startup connects one GRBL controller and homes all axes")

    driver = MiniQubot(qubot_port=config.qubot_port)
    driver.startup()
    logger.info("Machine driver initialized")

    edge_nats_client = EdgeNatsClient(
        servers=config.nats_server_list,
        machine_id=config.machine_id,
    )

    async def telemetry_handler():
        await edge_nats_client.publish_heartbeat()
        sensor = None
        if hasattr(psutil, "sensors_temperatures"):
            all_temps = psutil.sensors_temperatures() or {}
            sensor = next(
                (
                    v[0]
                    for k in ("coretemp", "cpu_thermal", "k10temp", "acpitz")
                    if (v := all_temps.get(k))
                ),
                None,
            )
        await edge_nats_client.publish_health(
            {
                "cpu": psutil.cpu_percent(interval=None),
                "mem": psutil.virtual_memory().percent,
                "temp": sensor.current if sensor else None,
            }
        )

    runner = EdgeRunner(
        nats_client=edge_nats_client,
        machine_driver=driver,
        telemetry_handler=telemetry_handler,
        state_handler=lambda: {"homed": driver._homed},
    )
    await runner.connect()
    logger.info("%s edge service ready", config.machine_id)
    await runner.run()


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.warning("Stopping")
            sys.exit(0)
        except Exception as exc:
            logger.error("Fatal error: %s", exc.__class__.__name__, exc_info=True)
            time.sleep(5)
