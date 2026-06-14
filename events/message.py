"""
on_message event example.

Because this listener uses @bot.listen instead of @bot.event, it does not
replace discord.py's built-in command handling. Prefix commands still work.
"""

from __future__ import annotations

import logging

from discord.ext import commands


logger = logging.getLogger("bot.events.message")


def setup(bot: commands.Bot) -> None:
    """Register message-related listeners."""

    @bot.listen("on_message")
    async def on_message(message) -> None:
        # Ignore bots so your bot does not respond to itself or other bots.
        if message.author.bot:
            return

        # This is intentionally small. It shows where message monitoring code
        # belongs without spamming every message into your logs.
        if bot.user and bot.user in message.mentions:
            logger.info("%s mentioned the bot in #%s", message.author, message.channel)
