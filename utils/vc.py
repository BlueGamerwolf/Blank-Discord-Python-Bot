import discord
from discord.ext import commands
import json
import os
import asyncio
import re
import unicodedata
from datetime import datetime, timezone

from utils.transcripts import (
    append_lines_to_transcript,
    append_message_to_transcript,
    collect_channel_transcript,
    create_live_transcript_thread,
    post_owner_transcript,
)
from utils.embeds import error_embed, success_embed

HUB_CHANNEL_NAME = "Hub - Join to Create"
WAITING_ROOM_NAME = "Waiting Room"
SETTINGS_FILE = "vc_settings.json"
VC_ROLE_NAME = "🎧 In VC"

# vc_id -> {"owner": user_id, "text": channel_id, "transcript": thread_id | None}
TEMP_VCS = {}

# vc_id -> set(user_ids)
VC_BLOCKED = {}

# user_id -> saved settings
VC_SETTINGS = {}

# ---------------------------------------------------------
# LOAD / SAVE SETTINGS
# ---------------------------------------------------------
def load_settings():
    global VC_SETTINGS
    if not os.path.exists(SETTINGS_FILE):
        VC_SETTINGS = {}
        return
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            VC_SETTINGS = json.load(f)
    except (json.JSONDecodeError, OSError):
        VC_SETTINGS = {}

def save_settings():
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(VC_SETTINGS, f, indent=4)

# ---------------------------------------------------------
# VC ROLE
# ---------------------------------------------------------
async def get_vc_role(guild: discord.Guild):
    role = discord.utils.get(guild.roles, name=VC_ROLE_NAME)
    if role:
        return role
    return await guild.create_role(
        name=VC_ROLE_NAME,
        reason="Temporary VC access role"
    )

# ---------------------------------------------------------
# NAME VALIDATION
# ---------------------------------------------------------
BAD_WORDS = {"nigger", "faggot", "retard", "kys", "rape"}

def clean_name(name: str) -> str | None:
    name = name.strip()
    if not 1 <= len(name) <= 32:
        return None
    if "@everyone" in name or "@here" in name:
        return None
    if re.search(r"https?://|www\.", name.lower()):
        return None
    normalized = unicodedata.normalize("NFKC", name)
    if not any(c.isalnum() for c in normalized):
        return None
    if re.fullmatch(r"[^\w\s\-]{6,}", normalized):
        return None
    lowered = normalized.lower()
    for bad in BAD_WORDS:
        if bad in lowered:
            return None
    return normalized

# ---------------------------------------------------------
# SETUP
# ---------------------------------------------------------
def setup(bot: commands.Bot):

    load_settings()

    # ---------------------------------------------------------
    # VOICE STATE LISTENER
    # ---------------------------------------------------------
    async def vc_voice_state_update(member, before, after):
        guild = member.guild
        vc_role = await get_vc_role(guild)

        # BLOCK ENFORCEMENT
        if after.channel and after.channel.id in VC_BLOCKED:
            if member.id in VC_BLOCKED[after.channel.id]:
                try:
                    await member.move_to(None)
                except discord.Forbidden:
                    pass
                return

        # JOIN HUB → CREATE VC + TEXT
        if after.channel and after.channel.name == HUB_CHANNEL_NAME:
            user_id = str(member.id)
            category = after.channel.category

            settings = VC_SETTINGS.get(user_id, {
                "name": f"{member.name}'s VC",
                "limit": 0,
                "locked": False
            })

            vc = await guild.create_voice_channel(
                name=settings["name"],
                category=category,
                user_limit=settings["limit"]
            )

            await vc.set_permissions(
                guild.default_role,
                connect=not settings["locked"]
            )

            await vc.set_permissions(
                member,
                connect=True,
                speak=True,
                stream=True,
                move_members=True,
                mute_members=True,
                deafen_members=True,
                manage_channels=True
            )

            tc = await guild.create_text_channel(
                name=vc.name,
                category=category,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    vc_role: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True
                    ),
                    member: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        manage_channels=True
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        manage_channels=True
                    )
                }
            )

            await tc.edit(sync_permissions=False)

            created_at = datetime.now(timezone.utc)
            transcript_thread = await create_live_transcript_thread(
                guild,
                transcript_type="vc",
                owner_id=member.id,
                title=f"vc-{member.id}-{vc.id}-{created_at.strftime('%Y%m%d-%H%M%S')}",
                header_lines=[
                    f"Private call transcript: {vc.name}",
                    f"Voice Channel ID: {vc.id}",
                    f"Text Channel ID: {tc.id}",
                    f"Guild: {guild.name} ({guild.id})",
                    f"Owner: {member} ({member.id})",
                    f"Created At: {created_at.isoformat()}",
                ],
            )

            TEMP_VCS[vc.id] = {
                "owner": member.id,
                "text": tc.id,
                "transcript": transcript_thread.id if transcript_thread else None,
            }
            VC_BLOCKED[vc.id] = set()

            await member.add_roles(vc_role)
            await member.move_to(vc)

        # USER JOINS TEMP VC → ADD ROLE
        if after.channel and after.channel.id in TEMP_VCS:
            try:
                await member.add_roles(vc_role)
            except discord.Forbidden:
                pass

        # USER LEAVES TEMP VC → REMOVE ROLE
        if before.channel and before.channel.id in TEMP_VCS:
            if not after.channel or after.channel.id not in TEMP_VCS:
                try:
                    await member.remove_roles(vc_role)
                except discord.Forbidden:
                    pass

            if len(before.channel.members) == 0:
                data = TEMP_VCS.pop(before.channel.id)
                VC_BLOCKED.pop(before.channel.id, None)

                VC_SETTINGS[str(data["owner"])] = {
                    "name": before.channel.name,
                    "limit": before.channel.user_limit,
                    "locked": not before.channel.permissions_for(
                        guild.default_role
                    ).connect
                }
                save_settings()

                tc = guild.get_channel(data["text"])
                thread = guild.get_thread(data["transcript"]) if data.get("transcript") else None
                if thread:
                    closed_at = datetime.now(timezone.utc)
                    await append_lines_to_transcript(thread, [
                        "",
                        "Call Closed",
                        "===========",
                        f"Voice Channel: {before.channel.name} ({before.channel.id})",
                        f"Closed At: {closed_at.isoformat()}",
                    ])
                elif isinstance(tc, discord.TextChannel):
                    closed_at = datetime.now(timezone.utc)
                    message_lines = await collect_channel_transcript(tc)
                    await post_owner_transcript(
                        guild,
                        transcript_type="vc",
                        owner_id=data["owner"],
                        title=f"vc-{data['owner']}-{before.channel.id}-{closed_at.strftime('%Y%m%d-%H%M%S')}",
                        header_lines=[
                            f"Private call transcript: {before.channel.name}",
                            f"Voice Channel ID: {before.channel.id}",
                            f"Text Channel ID: {tc.id}",
                            f"Guild: {guild.name} ({guild.id})",
                            f"Owner ID: {data['owner']}",
                            f"Closed At: {closed_at.isoformat()}",
                        ],
                        message_lines=message_lines,
                    )

                await before.channel.delete()
                if tc:
                    await tc.delete()

    bot.add_listener(vc_voice_state_update, "on_voice_state_update")

    async def vc_message_transcript(message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return

        for data in TEMP_VCS.values():
            if data["text"] != message.channel.id:
                continue

            thread = message.guild.get_thread(data["transcript"]) if message.guild and data.get("transcript") else None
            if thread:
                await append_message_to_transcript(thread, message)
            return

    bot.add_listener(vc_message_transcript, "on_message")

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def get_owned_vc(ctx):
        if not ctx.author.voice:
            return None, None
        vc = ctx.author.voice.channel
        data = TEMP_VCS.get(vc.id)
        if not data or data["owner"] != ctx.author.id:
            return None, None
        return vc, ctx.guild.get_channel(data["text"])

    # ---------------------------------------------------------
    # COMMANDS
    # ---------------------------------------------------------
    @bot.command()
    async def rename(ctx, *, name):
        vc, tc = get_owned_vc(ctx)
        if not vc:
            return await ctx.send(embed=error_embed("You are not the VC owner."))
        safe = clean_name(name)
        if not safe:
            return await ctx.send(embed=error_embed("Invalid name."))
        await vc.edit(name=safe)
        if tc:
            await tc.edit(name=safe)
        await ctx.send(embed=success_embed(f"Renamed to **{safe}**."))

    @bot.command()
    async def limit(ctx, amount: int):
        vc, _ = get_owned_vc(ctx)
        if not vc:
            return await ctx.send(embed=error_embed("You are not the VC owner."))
        await vc.edit(user_limit=max(0, min(99, amount)))
        await ctx.send(embed=success_embed(f"Limit set to **{amount}**."))

    @bot.command()
    async def lock(ctx):
        vc, _ = get_owned_vc(ctx)
        if not vc:
            return await ctx.send(embed=error_embed("You are not the VC owner."))
        await vc.set_permissions(ctx.guild.default_role, connect=False)
        await ctx.send(embed=success_embed("Locked."))

    @bot.command()
    async def unlock(ctx):
        vc, _ = get_owned_vc(ctx)
        if not vc:
            return await ctx.send(embed=error_embed("You are not the VC owner."))
        await vc.set_permissions(ctx.guild.default_role, connect=True)
        await ctx.send(embed=success_embed("Unlocked."))

    @bot.command()
    async def block(ctx, member: discord.Member):
        vc, _ = get_owned_vc(ctx)
        if not vc:
            return await ctx.send(embed=error_embed("You are not the VC owner."))
        VC_BLOCKED[vc.id].add(member.id)
        await vc.set_permissions(member, connect=False)
        if member.voice and member.voice.channel == vc:
            await member.move_to(None)
        await ctx.send(embed=success_embed(f"Blocked **{member.display_name}**."))

    @bot.command()
    async def unblock(ctx, member: discord.Member):
        vc, _ = get_owned_vc(ctx)
        if not vc:
            return await ctx.send(embed=error_embed("You are not the VC owner."))
        VC_BLOCKED[vc.id].discard(member.id)
        await vc.set_permissions(member, overwrite=None)
        await ctx.send(embed=success_embed(f"Unblocked **{member.display_name}**."))

    @bot.command()
    async def invite(ctx, member: discord.Member):
        vc, _ = get_owned_vc(ctx)
        if not vc:
            return await ctx.send(embed=error_embed("You are not the VC owner."))
        try:
            await member.send(embed=success_embed(f"You were invited to **{vc.name}**."))
            await ctx.send(embed=success_embed("Invite sent."))
        except discord.Forbidden:
            await ctx.send(embed=error_embed("Cannot DM user."))
