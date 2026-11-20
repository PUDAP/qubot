"""Manual integration test for the Pescador PipQuBot machine."""

import asyncio
import logging

from qubot_drivers import setup_logging
from driver import Pipette

import importlib.util
from pathlib import Path

# Load the owning edge explicitly; do not resolve another edge's global main.
spec = importlib.util.spec_from_file_location(
    "pescador_edge_main", Path(__file__).resolve().parents[1] / "main.py"
)
assert spec and spec.loader
edge_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(edge_main)
load_config = edge_main.load_config

TRANSFER_VOLUME = 20  # µL

setup_logging(
    enable_file_logging=False,
    log_level=logging.INFO,
)


async def main():
    config = load_config()
    driver = Pipette(
        qubot_ip=config.qubot_ip,
        satorius_port=config.satorius_port,
    )

    driver.qubot.connect()
    driver.pipette.connect()

    try:
        driver.home()

        print(driver.get_position())

        driver.aspirate_from(TRANSFER_VOLUME)
        driver.dispense_to(TRANSFER_VOLUME)
        driver.drop_tip()
    finally:
        driver.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
