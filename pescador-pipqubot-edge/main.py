"""
Main entry point for the Pescador PipQuBot machine edge service.

This module provides the main event loop for the pipette machine, handling command
execution via NATS messaging, telemetry publishing, and connection management.
"""
import asyncio
import logging
import sys
import time
from pathlib import Path

import psutil
from pydantic_settings import BaseSettings, SettingsConfigDict
from qubot_drivers.machines.pipette import Pipette
from puda import EdgeNatsClient, EdgeRunner

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
    qubot_ip: str
    satorius_port: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def nats_server_list(self) -> list[str]:
        return [s.strip() for s in self.nats_servers.split(",") if s.strip()]


def load_config() -> Config:
    """Load and validate configuration; exit process on failure."""
    try:
        return Config()
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        sys.exit(1)


async def main():
    """Initialize the Pipette machine driver and NATS client, then run the edge runner."""
    config = load_config()
    logger.info("Config loaded for %s", config.machine_id)
    logger.info("Full config: %s", config.model_dump())

    logger.info("Initializing machine driver")
    driver = Pipette(
        qubot_ip=config.qubot_ip,
        satorius_port=config.satorius_port,
    )
    driver.startup()
    logger.info("Pescador PipQuBot machine initialized successfully")

    logger.info("Connecting to NATS at %s", config.nats_servers)
    edge_nats_client = EdgeNatsClient(
        servers=config.nats_server_list,
        machine_id=config.machine_id,
    )

    async def telemetry_handler():
        await edge_nats_client.publish_heartbeat()
        await edge_nats_client.publish_position(await driver.get_position())
        all_temps = psutil.sensors_temperatures()
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
    )
    await runner.connect()
    logger.info("NATS client initialized successfully")
    logger.info(
        "==================== %s Edge Service Ready. Publishing telemetry... ====================",
        config.machine_id,
    )
    await runner.run()


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.warning("Received KeyboardInterrupt, but continuing to run...")
            time.sleep(1)
        except Exception as e:
            logger.error("Fatal error: %s", e, exc_info=True)
            time.sleep(5)
