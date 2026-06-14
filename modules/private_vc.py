from __future__ import annotations

from discord.ext import commands

from utils import vc


def setup(bot: commands.Bot) -> None:
    vc.setup(bot)
