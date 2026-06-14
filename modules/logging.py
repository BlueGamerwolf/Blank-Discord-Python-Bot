"""
Example logging command.

This command demonstrates two beginner concepts:
1. restricting a command to server admins
2. writing useful activity to the bot log
"""

from __future__ import annotations

import logging

from discord.ext import commands

from config import LOG_CHANNEL_ID, PREFIX
from utils.embeds import error_embed, success_embed
from utils.permissions import is_server_admin


logger = logging.getLogger("bot.commands.logging")


def setup(bot: commands.Bot) -> None:
    """Register logging-related example commands."""

    @bot.command(name="saylog")
    async def saylog(ctx: commands.Context, *, message: str = "") -> None:
        """Write a message to storage/logs/bot.log."""
        if not is_server_admin(ctx.author):
            await ctx.send(embed=error_embed("Only server administrators can use this command."))
            return

        if not message:
            await ctx.send(embed=error_embed(f"Usage: `{PREFIX}saylog your message here`"))
            return

        logger.info("%s logged from #%s: %s", ctx.author, ctx.channel, message)

        # LOG_CHANNEL_ID is optional. If configured, the bot also posts admin
        # log messages into that Discord channel.
        if LOG_CHANNEL_ID is not None:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)

            if log_channel is None:
                logger.warning("LOG_CHANNEL_ID=%s was not found.", LOG_CHANNEL_ID)
            else:
                await log_channel.send(f"Log from {ctx.author.mention}: {message}")

        await ctx.send(embed=success_embed("Your message was written to the bot log."))
