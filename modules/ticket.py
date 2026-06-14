from __future__ import annotations

import discord
from discord.ext import commands

from config import PREFIX
from events.ticket_buttons import (
    TICKET_CATEGORY_NAME,
    TicketPanel,
    close_ticket_channel,
    ensure_ticket_start_category,
    is_ticket_staff,
)
from utils import ticket_manager
from utils.embeds import basic_embed, error_embed, success_embed


@commands.command()
@commands.has_permissions(administrator=True)
async def ticketpanel(ctx):
    """Post the support ticket panel."""
    if ctx.guild is None:
        await ctx.send(embed=error_embed("This command can only be used in a server."))
        return

    embed = discord.Embed(
        title="Support Tickets",
        description="Use the button below to open a private support ticket.",
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="A staff member will respond as soon as possible.")

    await ctx.send(embed=embed, view=TicketPanel())


@commands.command(name="ticket_start")
@commands.has_permissions(administrator=True)
async def ticket_start(ctx):
    """Create or save the ticket_start category for tickets."""
    if ctx.guild is None:
        await ctx.send(embed=error_embed("This command can only be used in a server."))
        return

    category = await ensure_ticket_start_category(ctx.guild)
    if category is None:
        await ctx.send(embed=error_embed("I need Manage Channels permission to create the ticket category."))
        return

    ticket_manager.set_ticket_category(ctx.guild.id, category.id)
    await ctx.send(
        embed=success_embed(
            f"Ticket category is ready: `{TICKET_CATEGORY_NAME}`. New tickets will be created there."
        )
    )


@commands.command()
async def close(ctx):
    """Close the current ticket channel."""
    if ctx.guild is None:
        await ctx.send(embed=error_embed("This command can only be used in a server."))
        return

    await close_ticket_channel(ctx, ctx.author)


@commands.command()
async def adduser(ctx, member: discord.Member | None = None):
    """Add a member to the current ticket."""
    if ctx.guild is None:
        await ctx.send(embed=error_embed("This command can only be used in a server."))
        return

    if member is None:
        await ctx.send(embed=error_embed(f"Usage: `{PREFIX}adduser @member`"))
        return

    if not is_ticket_staff(ctx.author):
        await ctx.send(embed=error_embed("Only staff can add users to tickets."))
        return

    if not isinstance(ctx.channel, discord.TextChannel) or ticket_manager.get_ticket(ctx.channel.id) is None:
        await ctx.send(embed=error_embed("This command can only be used in a ticket channel."))
        return

    await ctx.channel.set_permissions(
        member,
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        attach_files=True,
        embed_links=True,
    )
    await ctx.send(embed=basic_embed("Ticket Updated", f"{member.mention} was added to this ticket."))


@commands.command()
async def removeuser(ctx, member: discord.Member | None = None):
    """Remove a member from the current ticket."""
    if ctx.guild is None:
        await ctx.send(embed=error_embed("This command can only be used in a server."))
        return

    if member is None:
        await ctx.send(embed=error_embed(f"Usage: `{PREFIX}removeuser @member`"))
        return

    if not is_ticket_staff(ctx.author):
        await ctx.send(embed=error_embed("Only staff can remove users from tickets."))
        return

    if not isinstance(ctx.channel, discord.TextChannel) or ticket_manager.get_ticket(ctx.channel.id) is None:
        await ctx.send(embed=error_embed("This command can only be used in a ticket channel."))
        return

    await ctx.channel.set_permissions(member, overwrite=None)
    await ctx.send(embed=basic_embed("Ticket Updated", f"{member.mention} was removed from this ticket."))


def setup(bot):
    bot.add_command(ticketpanel)
    bot.add_command(ticket_start)
    bot.add_command(close)
    bot.add_command(adduser)
    bot.add_command(removeuser)
