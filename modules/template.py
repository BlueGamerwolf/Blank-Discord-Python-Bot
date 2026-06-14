"""
Copy this file when you want to create a new command module.

Steps:
1. Copy modules/template.py to modules/my_command.py.
2. Rename template_command to your command name.
3. Restart the bot so bot.py loads the new file.
"""

from __future__ import annotations

from discord.ext import commands

from utils.embeds import basic_embed


def setup(bot: commands.Bot) -> None:
    """Register template commands."""

    @bot.command(name="template")
    async def template_command(ctx: commands.Context) -> None:
        """Show where new command code should go."""
        await ctx.send(
            embed=basic_embed(
                "Template Command",
                "Copy `modules/template.py` when you want to build a new command.",
            )
        )
