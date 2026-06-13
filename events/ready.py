"""
on_ready event example.

Discord sends on_ready after the bot has connected and finished initial setup.
This can run more than once if Discord reconnects, so keep it lightweight.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands


logger = logging.getLogger("bot.events.ready")


def setup(bot: commands.Bot) -> None:
    """Register the ready listener."""

    @bot.listen("on_ready")
    async def on_ready() -> None:
        logger.info("Logged in as %s (ID: %s)", bot.user, bot.user.id if bot.user else "unknown")

        # Presence is the text under the bot's name in Discord.
        # Change this to fit your own bot once you start customizing.
        await bot.change_presence(
            activity=discord.Game(name=f"{bot.command_prefix}help")
        )
