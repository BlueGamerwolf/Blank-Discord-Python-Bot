"""
Main entry point for the example Discord bot.

Run this file with:
    python bot.py

This project intentionally avoids advanced framework magic. Each command/event file
has a small setup(bot) function, and this file imports those setup functions.
That makes the loading process easy to follow for someone reading the code.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path

import discord
from discord.ext import commands

from config import PREFIX, TOKEN
from utils.logger import setup_logging
from events.ticket_buttons import TicketControlView, TicketPanel, ensure_ticket_categories


# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------
# Logging should be configured before the bot does meaningful work.
# This lets startup errors, module loading, and Discord connection messages
# show up both in the console and in storage/logs/bot.log.
setup_logging()
logger = logging.getLogger("bot")


# ---------------------------------------------------------
# BOT SETUP
# ---------------------------------------------------------
# Intents decide which events Discord is allowed to send your bot.
# message_content is required for prefix commands like !ping to read messages.
# members is required for on_member_join to fire.
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# The prefix comes from .env. README uses "!", but users can change PREFIX
# without editing code.
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# We provide our own beginner-friendly help command in modules/help.py.
bot.remove_command("help")


def load_setup_files(folder_name: str) -> None:
    """Import every Python file in a folder and call setup(bot) when present."""
    folder = Path(folder_name)

    if not folder.exists():
        logger.warning("Skipped missing folder: %s", folder)
        return

    for file_path in sorted(folder.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        # Convert modules/ping.py into modules.ping so Python can import it.
        module_name = ".".join(file_path.with_suffix("").parts)
        module = importlib.import_module(module_name)
        setup_function = getattr(module, "setup", None)

        if setup_function is None:
            logger.warning("%s does not have setup(bot), so it was skipped.", module_name)
            continue

        setup_function(bot)
        logger.info("Loaded %s", module_name)


def log_registered_commands() -> None:
    """Print the final command list so users can confirm their files loaded."""
    logger.info("========== REGISTERED COMMANDS ==========")

    for command in sorted(bot.commands, key=lambda item: item.name):
        try:
            location = inspect.getfile(command.callback)
        except TypeError:
            location = "Unknown file"

        logger.info("%s%s -> %s", PREFIX, command.name, location)

    logger.info("=========================================")


# ---------------------------------------------------------
# LOAD MODULES AND EVENTS
# ---------------------------------------------------------
# Commands live in modules/.
# Event listeners live in events/.
# To add your own feature, copy modules/template.py or events/message.py.
load_setup_files("modules")
load_setup_files("events")
log_registered_commands()


@bot.event
async def on_ready():
    if not hasattr(bot, "_ticket_views_loaded"):
        bot.add_view(TicketPanel())
        bot.add_view(TicketControlView())
        bot._ticket_views_loaded = True
        logger.info("Ticket views loaded safely")

    if not hasattr(bot, "_ticket_categories_loaded"):
        await ensure_ticket_categories(bot)
        bot._ticket_categories_loaded = True
        logger.info("Ticket categories loaded safely")


# ---------------------------------------------------------
# RUN BOT
# ---------------------------------------------------------
# A missing token is the most common setup mistake, so fail with a clear error
# instead of letting discord.py raise a confusing login exception.
if not TOKEN:
    raise RuntimeError("TOKEN is missing. Add TOKEN=YOUR_BOT_TOKEN to your .env file.")

bot.run(TOKEN)
