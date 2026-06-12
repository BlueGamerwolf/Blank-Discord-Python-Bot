import logging
import inspect

# ---------------------------------------------------------
# LOGGING (ONLY ONCE, MUST BE FIRST)
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("discord.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("bot")


# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------

import discord
from discord.ext import commands

from config import TOKEN

# ---------------------------------------------------------
# BOT SETUP
# ---------------------------------------------------------

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="v!", intents=intents)
bot.remove_command("help")

console_started = False

# ---------------------------------------------------------
# REGISTER COMMAND MODULES
# ---------------------------------------------------------


# Commands are registered by importing their modules, which contain setup functions that add commands to the bot.
# This allows for better organization and separation of command code.
# The actual command definitions are in their respective modules (e.g., backup.py, vc.py, etc.).
# The setup functions are called when the module is imported, and they use the bot instance to register commands.
# This approach keeps the main bot file clean and focused on setup and event handling, while command logic is encapsulated in separate files.
logger.info("========== REGISTERED COMMANDS ==========")

for cmd in bot.commands:
    try:
        logger.info(
            "%s -> %s",
            cmd.name,
            inspect.getfile(cmd.callback)
        )
    except Exception as e:
        logger.info(
            "%s -> Unknown (%s)",
            cmd.name,
            e
        )

logger.info("=========================================")

# ---------------------------------------------------------
# RUN BOT
# ---------------------------------------------------------

bot.run(TOKEN)