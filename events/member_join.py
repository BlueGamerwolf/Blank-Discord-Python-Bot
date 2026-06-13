"""
on_member_join event example.

This event requires the Server Members Intent to be enabled in the Discord
Developer Portal and in bot.py. If welcome messages do not work, check that
intent first.
"""

from __future__ import annotations

import logging

from discord.ext import commands

from config import MEMBER_ROLE_ID, WELCOME_CHANNEL_ID

logger = logging.getLogger("bot.events.member_join")


def setup(bot: commands.Bot) -> None:
    """Register member join listeners."""

    @bot.listen("on_member_join")
    async def on_member_join(member) -> None:
        logger.info("%s joined %s", member, member.guild)

        # MEMBER_ROLE_ID is optional. If it is configured, the bot will try to
        # give that role to new members. The bot's role must be above this role.
        if MEMBER_ROLE_ID is not None:
            role = member.guild.get_role(MEMBER_ROLE_ID)

            if role is None:
                logger.warning("MEMBER_ROLE_ID=%s was not found in %s", MEMBER_ROLE_ID, member.guild)
            else:
                await member.add_roles(role, reason="Configured auto-role for new members")

        # WELCOME_CHANNEL_ID is optional. If it is blank, we fall back to the
        # server's system channel because that works for simple test servers.
        welcome_channel = None

        if WELCOME_CHANNEL_ID is not None:
            welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

            if welcome_channel is None:
                logger.warning(
                    "WELCOME_CHANNEL_ID=%s was not found in %s",
                    WELCOME_CHANNEL_ID,
                    member.guild,
                )

        if welcome_channel is None:
            welcome_channel = member.guild.system_channel

        if welcome_channel is not None:
            await welcome_channel.send(
                f"Welcome {member.mention}! Type `{bot.command_prefix}help` to see what I can do."
            )
