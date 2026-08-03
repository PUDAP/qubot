"""PUDA edge entry point for the MOF PipQuBot."""

import asyncio
import logging
import sys
import time
from pathlib import Path

import psutil
from puda import EdgeNatsClient, EdgeRunner
from pydantic_settings import BaseSettings, SettingsConfigDict
from qubot_drivers.machines.pipqubot_mof import PipQuBotMOF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logging.getLogger("qubot_drivers").setLevel(logging.INFO)
logger = logging.getLogger(__name__)


class Config(BaseSettings):
    machine_id: str
    nats_servers: str
    qubot_port: str
    satorius_port: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def nats_server_list(self) -> list[str]:
        return [server.strip() for server in self.nats_servers.split(",") if server.strip()]


def load_config() -> Config:
    try:
        return Config()
    except Exception as exc:
        logger.error("Failed to load configuration: %s", exc)
        sys.exit(1)


async def main() -> None:
    config = load_config()
    logger.info("Config loaded for %s", config.machine_id)
    logger.info(
        "Using qubot_port=%s, satorius_port=%s, nats_servers=%s",
        config.qubot_port,
        config.satorius_port,
        config.nats_servers,
    )

    logger.info("Initializing MOF PipQuBot driver")
    driver = PipQuBotMOF(
        qubot_port=config.qubot_port,
        satorius_port=config.satorius_port,
    )
    driver.startup()
    logger.info("MOF PipQuBot initialized successfully")

    edge_nats_client = EdgeNatsClient(
        servers=config.nats_server_list,
        machine_id=config.machine_id,
    )

    async def telemetry_handler() -> None:
        await edge_nats_client.publish_heartbeat()
        # Do not poll either serial controller from the heartbeat loop. The
        # controllers can block for their serial timeouts and make discovery
        # intermittent; explicit get_position commands remain available.
        all_temps = psutil.sensors_temperatures()
        sensor = next(
            (v[0] for k in ("coretemp", "cpu_thermal", "k10temp", "acpitz") if (v := all_temps.get(k))),
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
        state_handler=lambda: {"deck": driver.deck.to_dict()},
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
            logger.warning("Received KeyboardInterrupt; retrying")
            time.sleep(1)
        except Exception as exc:
            logger.error("Fatal error: %s", exc, exc_info=True)
            time.sleep(5)
