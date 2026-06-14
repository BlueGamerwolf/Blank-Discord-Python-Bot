from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import (
    ADMIN_ROLE_ID,
    DEFAULT_ROLE_ID,
    GUILD_ID,
    LOG_CHANNEL_ID,
    MOD_ROLE_ID,
    SUPPORT_ROLE_ID,
    TICKET_CATEGORY_ID,
)
from utils import ticket_manager
from utils.embeds import basic_embed, error_embed, success_embed
from utils.permissions import is_server_admin
from utils.transcripts import collect_channel_transcript, post_owner_transcript


TICKET_CATEGORY_NAME = "Tickets"


def _ticket_name(ticket_number: int) -> str:
    return f"ticket-{ticket_number:04d}"


def _next_available_ticket_name(guild: discord.Guild) -> tuple[int, str]:
    while True:
        ticket_number = ticket_manager.get_next_ticket_number(guild.id)
        ticket_name = _ticket_name(ticket_number)

        if discord.utils.get(guild.text_channels, name=ticket_name) is None:
            return ticket_number, ticket_name


def _configured_roles(guild: discord.Guild) -> list[discord.Role]:
    roles = []

    for role_id in (SUPPORT_ROLE_ID, MOD_ROLE_ID, ADMIN_ROLE_ID, DEFAULT_ROLE_ID):
        if role_id is None:
            continue

        role = guild.get_role(role_id)
        if role and role not in roles:
            roles.append(role)

    return roles


def is_ticket_staff(member: discord.Member | discord.User) -> bool:
    if is_server_admin(member):
        return True

    if not isinstance(member, discord.Member):
        return False

    configured_ids = {role_id for role_id in (SUPPORT_ROLE_ID, MOD_ROLE_ID) if role_id}
    return any(role.id in configured_ids for role in member.roles)


def _is_ticket_owner(ticket: dict | None, user: discord.Member | discord.User) -> bool:
    return bool(ticket and ticket.get("owner_id") == user.id)


def _get_ticket_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    if TICKET_CATEGORY_ID is not None:
        category = guild.get_channel(TICKET_CATEGORY_ID)
        if isinstance(category, discord.CategoryChannel):
            ticket_manager.set_ticket_category(guild.id, category.id)
            return category

    stored_category_id = ticket_manager.get_ticket_category_id(guild.id)
    if stored_category_id is not None:
        category = guild.get_channel(stored_category_id)
        if isinstance(category, discord.CategoryChannel):
            return category

    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if isinstance(category, discord.CategoryChannel):
        ticket_manager.set_ticket_category(guild.id, category.id)
        return category

    return None


async def ensure_ticket_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    category = _get_ticket_category(guild)
    if category is not None:
        return category

    return await ensure_ticket_start_category(guild)


async def ensure_ticket_start_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if isinstance(category, discord.CategoryChannel):
        ticket_manager.set_ticket_category(guild.id, category.id)
        return category

    try:
        category = await guild.create_category(
            TICKET_CATEGORY_NAME,
            reason="Ticket category setup",
        )
    except discord.Forbidden:
        return None

    ticket_manager.set_ticket_category(guild.id, category.id)
    return category


async def ensure_ticket_categories(bot: commands.Bot) -> None:
    for guild in bot.guilds:
        if GUILD_ID and guild.id != GUILD_ID:
            continue

        await ensure_ticket_category(guild)


async def write_ticket_transcript(
    channel: discord.TextChannel,
    ticket: dict,
    closed_by: discord.Member | discord.User,
) -> str | None:
    closed_at = datetime.now(timezone.utc)
    header_lines = [
        f"Ticket transcript: #{channel.name}",
        f"Channel ID: {channel.id}",
        f"Guild: {channel.guild.name} ({channel.guild.id})",
        f"Ticket Number: {ticket.get('ticket_number')}",
        f"Owner ID: {ticket.get('owner_id')}",
        f"Claimed By: {ticket.get('claimed_by')}",
        f"Created At: {ticket.get('created_at')}",
        f"Closed By: {closed_by} ({closed_by.id})",
        f"Closed At: {closed_at.isoformat()}",
    ]
    message_lines = await collect_channel_transcript(channel)
    ticket_number = ticket.get("ticket_number", channel.id)
    title = f"ticket-{ticket_number}-owner-{ticket['owner_id']}-{closed_at.strftime('%Y%m%d-%H%M%S')}"

    return await post_owner_transcript(
        channel.guild,
        transcript_type="ticket",
        owner_id=ticket["owner_id"],
        title=title,
        header_lines=header_lines,
        message_lines=message_lines,
    )


def _base_overwrites(guild: discord.Guild, user: discord.Member) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
    }

    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True,
        )

    for role in _configured_roles(guild):
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )

    return overwrites


def _locked_overwrite() -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(
        view_channel=True,
        send_messages=False,
        read_message_history=True,
        attach_files=False,
        embed_links=False,
    )


async def _send_response(
    target: commands.Context | discord.Interaction,
    *,
    embed: discord.Embed | None = None,
    content: str | None = None,
    ephemeral: bool = False,
) -> None:
    if isinstance(target, discord.Interaction):
        if target.response.is_done():
            await target.followup.send(content=content, embed=embed, ephemeral=ephemeral) # type: ignore
        else:
            await target.response.send_message(content=content, embed=embed, ephemeral=ephemeral) # type: ignore
        return

    await target.send(content=content, embed=embed) # type: ignore


async def log_ticket(guild: discord.Guild, message: str) -> None:
    if LOG_CHANNEL_ID is None:
        return

    channel = guild.get_channel(LOG_CHANNEL_ID)

    if isinstance(channel, discord.TextChannel):
        await channel.send(message)


async def close_ticket_channel(target: commands.Context | discord.Interaction, actor: discord.Member | discord.User) -> None:
    channel = target.channel

    if not isinstance(channel, discord.TextChannel):
        await _send_response(target, embed=error_embed("This is not a ticket channel."), ephemeral=True)
        return

    ticket = ticket_manager.get_ticket(channel.id)

    if ticket is None:
        await _send_response(target, embed=error_embed("This channel is not registered as a ticket."), ephemeral=True)
        return

    if not (is_ticket_staff(actor) or _is_ticket_owner(ticket, actor)):
        await _send_response(target, embed=error_embed("Only the ticket owner or staff can close this ticket."), ephemeral=True)
        return

    await _send_response(target, embed=success_embed("Closing ticket..."))
    transcript_url = await write_ticket_transcript(channel, ticket, actor)
    ticket_manager.close_ticket(channel.id)

    if channel.guild:
        transcript_label = transcript_url or "transcript forum post failed"
        await log_ticket(
            channel.guild,
            f"Ticket closed: #{channel.name} by {actor} ({actor.id}). Transcript: {transcript_label}",
        )

    await channel.delete(reason=f"Ticket closed by {actor} ({actor.id})")


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green,
        custom_id="ticket_create",
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "This can only be used in a server.",
                ephemeral=True,
            )

        guild = interaction.guild
        user = interaction.user

        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message(
                "Tickets can only be created in a text channel.",
                ephemeral=True,
            )

        if GUILD_ID and guild.id != GUILD_ID:
            return await interaction.response.send_message(
                "This bot is not enabled for this server.",
                ephemeral=True,
            )

        if not isinstance(user, discord.Member):
            return await interaction.response.send_message(
                "Could not create a ticket for this user.",
                ephemeral=True,
            )

        existing_ticket = ticket_manager.get_open_ticket_for_user(user.id)

        if existing_ticket:
            channel_id, _ticket = existing_ticket
            existing_channel = guild.get_channel(channel_id)
            if isinstance(existing_channel, discord.TextChannel):
                return await interaction.response.send_message(
                    f"You already have a ticket: {existing_channel.mention}",
                    ephemeral=True,
                )

            ticket_manager.close_ticket(channel_id)

        ticket_number, ticket_name = _next_available_ticket_name(guild)

        ticket_channel = await guild.create_text_channel(
            name=ticket_name,
            category=_get_ticket_category(guild),
            overwrites=_base_overwrites(guild, user), # type: ignore
            topic=f"Support ticket for {user} ({user.id})",
            reason=f"Ticket opened by {user} ({user.id})",
        )

        ticket_manager.create_ticket(ticket_channel.id, user.id, "General", ticket_number)

        embed = basic_embed(
            "Support Ticket",
            f"{user.mention}, describe what you need help with. Staff will respond here.",
        )
        embed.add_field(name="Opened By", value=f"{user.mention}\n`{user.id}`", inline=True)
        embed.add_field(name="Ticket Number", value=f"`{ticket_number:04d}`", inline=True)
        embed.add_field(name="Status", value="Open", inline=True)

        await ticket_channel.send(
            content=user.mention,
            embed=embed,
            view=TicketControlView(),
        )

        await interaction.response.send_message(
            f"Ticket created: {ticket_channel.mention}",
            ephemeral=True,
        )

        await log_ticket(guild, f"Ticket created: {ticket_channel.mention} by {user} ({user.id})")


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple, custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        if not is_ticket_staff(interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Only staff can claim tickets."),
                ephemeral=True,
            )

        ticket = ticket_manager.get_ticket(channel.id)
        if ticket is None:
            return await interaction.response.send_message(
                embed=error_embed("This channel is not registered as a ticket."),
                ephemeral=True,
            )

        if ticket.get("claimed_by") and ticket["claimed_by"] != interaction.user.id:
            claimed_member = channel.guild.get_member(ticket["claimed_by"]) if channel.guild else None
            claimed_label = claimed_member.mention if claimed_member else f"`{ticket['claimed_by']}`"
            return await interaction.response.send_message(
                embed=error_embed(f"This ticket is already claimed by {claimed_label}."),
                ephemeral=True,
            )

        ticket_manager.claim_ticket(channel.id, interaction.user.id)

        await interaction.response.send_message(
            embed=success_embed(f"Ticket claimed by {interaction.user.mention}."),
        )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await close_ticket_channel(interaction, interaction.user)

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.gray, custom_id="ticket_lock")
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        guild = interaction.guild
        if guild is None:
            return

        if not is_ticket_staff(interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Only staff can lock tickets."),
                ephemeral=True,
            )

        ticket = ticket_manager.get_ticket(channel.id)
        if ticket is None:
            return await interaction.response.send_message(
                embed=error_embed("This channel is not registered as a ticket."),
                ephemeral=True,
            )

        owner = guild.get_member(ticket["owner_id"])
        if owner:
            await channel.set_permissions(owner, overwrite=_locked_overwrite())

        await interaction.response.send_message(embed=success_embed("Ticket locked."))

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.green, custom_id="ticket_unlock")
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        guild = interaction.guild
        if guild is None:
            return

        if not is_ticket_staff(interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Only staff can unlock tickets."),
                ephemeral=True,
            )

        ticket = ticket_manager.get_ticket(channel.id)
        if ticket is None:
            return await interaction.response.send_message(
                embed=error_embed("This channel is not registered as a ticket."),
                ephemeral=True,
            )

        owner = guild.get_member(ticket["owner_id"])
        if owner:
            await channel.set_permissions(
                owner,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            )

        await interaction.response.send_message(embed=success_embed("Ticket unlocked."))


def setup(bot: commands.Bot):
    pass
