"""PUDA edge service for the empty-head MiniQubot."""

import asyncio
import logging
import sys
import time
from pathlib import Path


from pydantic_settings import BaseSettings, SettingsConfigDict
from puda import EdgeNatsClient, EdgeRunner
from qubot_edgekit import load_contract, require_filled_env
from driver import MiniQubot

_CONTRACT = load_contract(Path(__file__).resolve().parent)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logging.getLogger("gantry_001").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Config(BaseSettings):
    machine_id: str
    nats_servers: str
    qubot_port: str
    home_on_startup: bool = _CONTRACT["home_on_startup"]
    puda_nats_ca: str = ""
    puda_e2e_key_file: str = ""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def nats_server_list(self) -> list[str]:
        return [s.strip() for s in self.nats_servers.split(",") if s.strip()]


def load_config() -> Config:
    env_path = Path(__file__).resolve().parent / ".env"
    try:
        config = Config()
        require_filled_env(
            env_path,
            {
                "MACHINE_ID": config.machine_id,
                "NATS_SERVERS": config.nats_servers,
                "QUBOT_PORT": config.qubot_port,
            },
        )
        return config
    except Exception as exc:
        logger.error("Failed to load configuration: %s", exc.__class__.__name__)
        sys.exit(1)


async def main():
    config = load_config()
    logger.info("Config loaded for %s", config.machine_id)
    logger.info(
        "Startup connects one GRBL controller and homes all axes"
        if config.home_on_startup
        else "Startup connects one GRBL controller without homing"
    )

    driver = MiniQubot(qubot_port=config.qubot_port)
    driver.startup(home=config.home_on_startup)
    logger.info("Machine driver initialized")

    edge_nats_client = EdgeNatsClient(
        servers=config.nats_server_list,
        machine_id=config.machine_id,
        ca_file=config.puda_nats_ca or None,
        e2e_key_file=config.puda_e2e_key_file or None,
    )

    runner = EdgeRunner(
        nats_client=edge_nats_client,
        machine_driver=driver,
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
