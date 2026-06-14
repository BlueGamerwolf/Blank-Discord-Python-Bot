"""
Custom help command.

Discord.py includes a default help command, but bot.py removes it so this file
can show a simpler example that is easy to customize.
"""

from __future__ import annotations

from discord.ext import commands

from config import PREFIX
from utils.embeds import basic_embed


def setup(bot: commands.Bot) -> None:
    """Register the help command."""

    @bot.command(name="help")
    async def help_command(ctx: commands.Context) -> None:
        """List available commands."""
        lines = []

        for command in sorted(bot.commands, key=lambda item: item.name):
            if command.hidden:
                continue

            summary = command.help or "No description yet."
            lines.append(f"`{PREFIX}{command.name}` - {summary}")

        embed = basic_embed(
            "Bot Help",
            "\n".join(lines) if lines else "No commands are loaded.",
        )
        await ctx.send(embed=embed)
