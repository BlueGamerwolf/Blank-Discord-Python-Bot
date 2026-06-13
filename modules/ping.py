"""
Example command module.

Every file in modules/ can define setup(bot). bot.py imports the file and calls
setup(bot), which is where commands are attached to the bot.
"""

from __future__ import annotations

from discord.ext import commands

from utils.embeds import basic_embed


def setup(bot: commands.Bot) -> None:
    """Register commands from this file."""

    @bot.command(name="ping")
    async def ping(ctx: commands.Context) -> None:
        """Check whether the bot is alive and see its websocket latency."""
        latency_ms = round(bot.latency * 1000)
        embed = basic_embed(
            "Pong!",
            f"The bot is online.\nLatency: `{latency_ms}ms`",
        )
        await ctx.send(embed=embed)
