"""
Small helpers for Discord embeds.

Embeds are the rich message boxes Discord bots often send. Keeping common embed
styles here makes commands cleaner and keeps your bot looking consistent.
"""

from __future__ import annotations

import discord


DEFAULT_COLOR = discord.Color.blurple()
ERROR_COLOR = discord.Color.red()
SUCCESS_COLOR = discord.Color.green()


def basic_embed(title: str, description: str, color: discord.Color = DEFAULT_COLOR) -> discord.Embed:
    """Create a simple embed used by commands in modules/."""
    return discord.Embed(title=title, description=description, color=color)


def success_embed(description: str) -> discord.Embed:
    """Create a green success embed."""
    return basic_embed("Success", description, SUCCESS_COLOR)


def error_embed(description: str) -> discord.Embed:
    """Create a red error embed."""
    return basic_embed("Error", description, ERROR_COLOR)
