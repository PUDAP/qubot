"""Main entry point for the PipQuBot XL edge service."""

import asyncio
import logging
import sys
import time
from pathlib import Path

from puda import EdgeNatsClient, EdgeRunner
from pydantic_settings import BaseSettings, SettingsConfigDict
from driver import PipQuBotXL


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logging.getLogger("qubot_drivers").setLevel(logging.WARNING)
logging.getLogger("qubot_drivers.satorius").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """Environment configuration for the PipQuBot XL edge."""

    machine_id: str
    nats_servers: str
    qubot_ip: str
    satorius_port: str
    home_gantry_on_startup: bool = True
    initialize_pipette_on_startup: bool = True

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def nats_server_list(self) -> list[str]:
        """Return configured NATS servers as a non-empty list."""
        servers = [
            server.strip()
            for server in self.nats_servers.split(",")
            if server.strip()
        ]
        if not servers:
            raise ValueError("NATS_SERVERS must contain at least one server")
        return servers


def load_config() -> Config:
    """Load and validate edge configuration."""
    try:
        return Config()
    except Exception:
        logger.exception("Failed to load edge configuration")
        raise


def build_driver(config: Config) -> PipQuBotXL:
    """Create and connect the driver using explicit startup-motion gates."""
    driver = PipQuBotXL(
        qubot_ip=config.qubot_ip,
        satorius_port=config.satorius_port,
    )
    driver.startup(
        home_gantry=config.home_gantry_on_startup,
        initialize_pipette=config.initialize_pipette_on_startup,
    )
    return driver


async def main() -> None:
    """Initialize the PipQuBot XL and run its PUDA edge service."""
    config = load_config()
    logger.info("Initializing driver for %s", config.machine_id)

    driver = build_driver(config)

    nats_client = EdgeNatsClient(
        servers=config.nats_server_list,
        machine_id=config.machine_id,
    )
    runner = EdgeRunner(nats_client=nats_client, machine_driver=driver)
    await runner.connect()
    logger.info("%s edge service is ready", config.machine_id)
    await runner.run()


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("Stopping PipQuBot XL edge service")
            sys.exit(0)
        except Exception:
            logger.exception("Fatal edge error; retrying in 5 seconds")
            time.sleep(5)
