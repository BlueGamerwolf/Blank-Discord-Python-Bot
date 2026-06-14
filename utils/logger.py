"""
Shared logging setup for the bot.

Logging is your best friend when learning bot development. Print statements are
fine for tiny tests, but logging gives you timestamps, levels, and log files.
"""

from __future__ import annotations

import logging
from pathlib import Path


LOG_FOLDER = Path("storage/logs")
LOG_FILE = LOG_FOLDER / "bot.log"


def setup_logging() -> None:
    """Configure logging once for the whole project."""
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
