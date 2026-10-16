"""PUDA edge service for the syringe Qubot gantry."""

import asyncio
import logging
import sys
import time
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from puda import EdgeNatsClient, EdgeRunner
from qubot_drivers.machines.syringequbot import SyringeQubot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logging.getLogger("qubot_drivers").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """Environment configuration for the syringe Qubot edge."""

    machine_id: str
    nats_servers: str
    qubot_ip: str
    puda_nats_ca: str = ""
    puda_e2e_key_file: str = ""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def nats_server_list(self) -> list[str]:
        """Return configured NATS servers as a non-empty list."""
        servers = [server.strip() for server in self.nats_servers.split(",") if server.strip()]
        if not servers:
            raise ValueError("NATS_SERVERS must contain at least one server")
        return servers


def load_config() -> Config:
    """Load and validate configuration; exit the process on failure."""
    try:
        return Config()
    except Exception as exc:
        logger.error("Failed to load configuration: %s", exc, exc_info=True)
        sys.exit(1)


async def main() -> None:
    """Connect the gantry, then run the PUDA edge."""
    config = load_config()
    logger.info("Config loaded for %s at %s", config.machine_id, config.qubot_ip)

    driver = SyringeQubot(qubot_ip=config.qubot_ip)
    driver.startup()
    logger.info("Gantry controller connected")

    edge_nats_client = EdgeNatsClient(
        servers=config.nats_server_list,
        machine_id=config.machine_id,
        ca_file=config.puda_nats_ca or None,
        e2e_key_file=config.puda_e2e_key_file or None,
    )
    runner = EdgeRunner(nats_client=edge_nats_client, machine_driver=driver)
    await runner.connect()
    logger.info("%s edge service ready", config.machine_id)
    await runner.run()


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.warning("Gracefully stopping")
            sys.exit(0)
        except Exception as exc:
            logger.error("Fatal error: %s", exc, exc_info=True)
            time.sleep(5)
