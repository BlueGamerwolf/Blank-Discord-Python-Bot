"""
Permission helpers for commands.

Discord.py has built-in permission checks, but beginners often find it helpful
to see the logic in one small place before using decorators everywhere.
"""

from __future__ import annotations

import discord

from config import ADMIN_ROLE_ID, MOD_ROLE_ID, OWNER_USER_ID


def has_configured_role(member: discord.Member, role_id: int | None) -> bool:
    """Return True when a member has the configured role ID."""
    if role_id is None:
        return False

    return any(role.id == role_id for role in member.roles)


def is_server_admin(member: discord.Member | discord.User) -> bool:
    """Return True when a member is the owner, has ADMIN_ROLE_ID, or has Administrator."""
    if OWNER_USER_ID is not None and member.id == OWNER_USER_ID:
        return True

    if not isinstance(member, discord.Member):
        return False

    return member.guild_permissions.administrator or has_configured_role(member, ADMIN_ROLE_ID)


def can_manage_messages(member: discord.Member | discord.User) -> bool:
    """Return True when a member can delete/moderate messages or has MOD_ROLE_ID."""
    if not isinstance(member, discord.Member):
        return False

    return (
        member.guild_permissions.manage_messages
        or is_server_admin(member)
        or has_configured_role(member, MOD_ROLE_ID)
    )
