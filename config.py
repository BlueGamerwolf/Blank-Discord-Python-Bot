"""
Configuration values loaded from .env.

Keep secrets out of code. Your bot token belongs in .env, not in bot.py and
not in any file you plan to upload publicly.
"""

import os

from dotenv import load_dotenv


# load_dotenv() reads the .env file in this folder and adds those values to
# environment variables so os.getenv can find them.
load_dotenv()

# Required: Discord bot token from the Discord Developer Portal.
TOKEN = os.getenv("TOKEN")

# Optional: command prefix. If .env does not define PREFIX, the bot uses !.
PREFIX = os.getenv("PREFIX", "!")


def optional_int(name: str) -> int | None:
    """
    Read an optional Discord ID from .env.

    Discord IDs are large numbers. Keep them as plain digits in .env, like:
        WELCOME_CHANNEL_ID=123456789012345678

    Leave the value blank when you do not want that feature enabled.
    """
    raw_value = os.getenv(name, "").strip()

    if not raw_value:
        return None

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a Discord ID number, not {raw_value!r}.") from exc


# ---------------------------------------------------------
# DISCORD IDS
# ---------------------------------------------------------
# Put every server/channel/role/user ID that your bot needs here.
# This keeps IDs out of command files, which makes the bot easier to configure.

# Optional: your main testing/server ID. Useful when you later add slash commands.
GUILD_ID = optional_int("GUILD_ID")

# Optional: user who owns or manages this bot. This user can pass helper checks.
OWNER_USER_ID = optional_int("OWNER_USER_ID")

# Optional: role IDs used by permission helpers.
ADMIN_ROLE_ID = optional_int("ADMIN_ROLE_ID")
MOD_ROLE_ID = optional_int("MOD_ROLE_ID")

# Optional: channel IDs used by example events/commands.
WELCOME_CHANNEL_ID = optional_int("WELCOME_CHANNEL_ID")
LOG_CHANNEL_ID = optional_int("LOG_CHANNEL_ID")

# Optional: role to give new members when they join.
MEMBER_ROLE_ID = optional_int("MEMBER_ROLE_ID")
