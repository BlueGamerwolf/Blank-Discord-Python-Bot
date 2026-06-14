from __future__ import annotations

from datetime import datetime, timezone
import re

import discord

from config import ADMIN_ROLE_ID, MOD_ROLE_ID, SUPPORT_ROLE_ID, TRANSCRIPT_CATEGORY_ID
from utils import ticket_manager


TRANSCRIPT_CATEGORY_NAME = "Transcripts"
TRANSCRIPT_FORUM_NAMES = {
    "ticket": "ticket-transcript",
    "vc": "vc-transcript",
}
TRANSCRIPT_FORUM_ALIASES = {
    "ticket": ("ticket-transcript", "ticket-transcripts", "Ticket Transcript", "Ticket Transcripts"),
    "vc": ("vc-transcript", "vc-transcripts", "VC Transcript", "VC Transcripts"),
}
MAX_POST_LENGTH = 1900
EMBED_DESCRIPTION_LIMIT = 3900
TRANSCRIPT_CHUNK_LIMIT = 3400


def format_message_for_transcript(message: discord.Message) -> list[str]:
    created_at = message.created_at.astimezone(timezone.utc).isoformat()
    author = f"{message.author} ({message.author.id})"
    lines = [f"[{created_at}] {author}"]

    if message.content:
        lines.append(message.content)

    for attachment in message.attachments:
        lines.append(f"[attachment] {attachment.filename}: {attachment.url}")

    if message.embeds:
        lines.append(f"[embeds] {len(message.embeds)} embed(s)")

    lines.append("")
    return lines


async def collect_channel_transcript(channel: discord.TextChannel) -> list[str]:
    lines: list[str] = []

    try:
        async for message in channel.history(limit=None, oldest_first=True):
            lines.extend(format_message_for_transcript(message))
    except (discord.Forbidden, discord.HTTPException) as exc:
        return [f"[transcript unavailable] Could not read channel history: {exc}"]

    return lines


def _staff_transcript_overwrites(guild: discord.Guild) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
    }

    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            create_public_threads=True,
            send_messages_in_threads=True,
            manage_channels=True,
            manage_threads=True,
        )

    for role_id in (SUPPORT_ROLE_ID, MOD_ROLE_ID, ADMIN_ROLE_ID):
        if role_id is None:
            continue

        role = guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                create_public_threads=True,
                send_messages_in_threads=True,
                manage_threads=True,
            )

    return overwrites


async def ensure_transcript_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    if TRANSCRIPT_CATEGORY_ID is not None:
        channel = guild.get_channel(TRANSCRIPT_CATEGORY_ID)
        if isinstance(channel, discord.CategoryChannel):
            return channel

    category = discord.utils.get(guild.categories, name=TRANSCRIPT_CATEGORY_NAME)
    if isinstance(category, discord.CategoryChannel):
        return category

    try:
        return await guild.create_category(
            TRANSCRIPT_CATEGORY_NAME,
            overwrites=_staff_transcript_overwrites(guild),
            reason="Transcript category setup",
        )
    except discord.Forbidden:
        return None


def _normalize_channel_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return normalized


async def ensure_transcript_forum(
    guild: discord.Guild,
    *,
    transcript_type: str,
) -> discord.ForumChannel | None:
    category = await ensure_transcript_category(guild)
    if category is None:
        return None

    stored_forum_id = ticket_manager.get_transcript_forum_id(guild.id, transcript_type)
    if stored_forum_id is not None:
        stored_forum = guild.get_channel(stored_forum_id)
        if isinstance(stored_forum, discord.ForumChannel):
            return stored_forum

    forum_name = TRANSCRIPT_FORUM_NAMES.get(transcript_type, f"{transcript_type.title()} Transcripts")
    candidate_names = TRANSCRIPT_FORUM_ALIASES.get(transcript_type, (forum_name,))
    normalized_candidates = {_normalize_channel_name(candidate_name) for candidate_name in candidate_names}

    for existing in guild.forums:
        if _normalize_channel_name(existing.name) in normalized_candidates:
            ticket_manager.set_transcript_forum_id(guild.id, transcript_type, existing.id)
            return existing

    try:
        forum = await guild.create_forum(
            forum_name,
            topic=f"{transcript_type.title()} transcript posts. Each thread includes the owner ID.",
            category=category,
            overwrites=_staff_transcript_overwrites(guild),
            default_auto_archive_duration=10080,
            reason=f"{transcript_type.title()} transcript forum setup",
        )
        ticket_manager.set_transcript_forum_id(guild.id, transcript_type, forum.id)
        return forum
    except discord.Forbidden:
        return None


def _chunk_lines(lines: list[str], max_length: int = TRANSCRIPT_CHUNK_LIMIT) -> list[str]:
    chunks: list[str] = []
    current = ""

    for line in lines:
        addition = f"{line}\n"
        if len(addition) > max_length:
            if current:
                chunks.append(current.rstrip())
                current = ""

            for index in range(0, len(addition), max_length):
                chunks.append(addition[index:index + max_length].rstrip())
            continue

        if current and len(current) + len(addition) > max_length:
            chunks.append(current.rstrip())
            current = ""

        current += addition

    if current.strip():
        chunks.append(current.rstrip())

    return chunks or ["No messages were found in this channel."]


def _transcript_embed(
    title: str,
    description: str,
    *,
    color: discord.Colour | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=title[:256],
        description=description[:EMBED_DESCRIPTION_LIMIT],
        color=color or discord.Colour.blurple(),
        timestamp=datetime.now(timezone.utc),
    )
    return embed


async def _send_transcript_embed(
    thread: discord.Thread,
    *,
    title: str,
    description: str,
    color: discord.Colour | None = None,
    content: str | None = None,
) -> bool:
    try:
        await thread.send(
            content=content,
            embed=_transcript_embed(title, description, color=color),
            allowed_mentions=discord.AllowedMentions(users=True),
        )
    except (discord.Forbidden, discord.HTTPException):
        return False

    return True


def _message_embeds(message: discord.Message) -> list[discord.Embed]:
    content = message.content or "[no text content]"
    chunks = _chunk_lines([content])
    embeds: list[discord.Embed] = []

    for index, chunk in enumerate(chunks, start=1):
        suffix = f" ({index}/{len(chunks)})" if len(chunks) > 1 else ""
        embed = discord.Embed(
            title=f"Message{suffix}",
            description=chunk[:EMBED_DESCRIPTION_LIMIT],
            color=discord.Colour.dark_teal(),
            timestamp=message.created_at,
        )
        embed.add_field(name="Author", value=f"{message.author}\n`{message.author.id}`", inline=True)
        embed.add_field(name="Channel", value=f"#{message.channel}", inline=True)

        if message.attachments:
            attachments = "\n".join(f"[{item.filename}]({item.url})" for item in message.attachments)
            embed.add_field(name="Attachments", value=attachments[:1024], inline=False)

        if message.embeds:
            embed.add_field(name="Embeds", value=str(len(message.embeds)), inline=True)

        display_avatar = getattr(message.author, "display_avatar", None)
        if display_avatar:
            embed.set_author(name=str(message.author), icon_url=display_avatar.url)
        else:
            embed.set_author(name=str(message.author))

        embeds.append(embed)

    return embeds


async def post_owner_transcript(
    guild: discord.Guild,
    *,
    transcript_type: str,
    owner_id: int,
    title: str,
    header_lines: list[str],
    message_lines: list[str],
) -> str | None:
    forum = await ensure_transcript_forum(guild, transcript_type=transcript_type)
    if forum is None:
        return None

    if transcript_type == "vc":
        thread = await create_live_transcript_thread(
            guild,
            transcript_type=transcript_type,
            owner_id=owner_id,
            title=title,
            header_lines=header_lines,
        )
        if thread is None:
            return None

        await append_lines_to_transcript(thread, [
            "",
            "Messages",
            "========",
            "",
            *message_lines,
        ])
        return thread.jump_url

    lines = [
        *header_lines,
        "",
        "Messages",
        "========",
        "",
        *message_lines,
    ]
    chunks = _chunk_lines(lines)
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    first_embed = _transcript_embed(
        f"{transcript_type.title()} Transcript",
        f"Transcript posted at {started_at}\nOwner ID: `{owner_id}`\n\n{chunks[0]}",
    )

    try:
        thread_with_message = await forum.create_thread(
            name=title[:100],
            embed=first_embed,
            auto_archive_duration=10080,
            reason=f"{transcript_type.title()} transcript for owner {owner_id}",
        )
        thread = thread_with_message.thread

        for index, chunk in enumerate(chunks[1:], start=2):
            await thread.send(embed=_transcript_embed(f"{transcript_type.title()} Transcript Part {index}", chunk))
    except (discord.Forbidden, discord.HTTPException):
        return None

    return thread.jump_url


async def _find_owner_thread(forum: discord.ForumChannel, thread_name: str) -> discord.Thread | None:
    thread = discord.utils.get(forum.threads, name=thread_name)
    if thread:
        return thread

    try:
        async for archived_thread in forum.archived_threads(limit=None):
            if archived_thread.name == thread_name:
                return archived_thread
    except (discord.Forbidden, discord.HTTPException):
        return None

    return None


async def _reopen_thread(thread: discord.Thread, *, reason: str) -> discord.Thread:
    if thread.archived or thread.locked:
        try:
            return await thread.edit(archived=False, locked=False, reason=reason)
        except (discord.Forbidden, discord.HTTPException):
            return thread

    return thread


async def create_live_transcript_thread(
    guild: discord.Guild,
    *,
    transcript_type: str,
    owner_id: int,
    title: str,
    header_lines: list[str],
) -> discord.Thread | None:
    forum = await ensure_transcript_forum(guild, transcript_type=transcript_type)
    if forum is None:
        return None

    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    thread_name = f"{transcript_type}-{owner_id}"
    content = "\n".join([
        f"Live transcript section started at {started_at}",
        f"Owner ID: {owner_id}",
        "",
        *header_lines,
        "",
        "Messages",
        "========",
    ])

    existing_thread = await _find_owner_thread(forum, thread_name)
    if existing_thread:
        thread = await _reopen_thread(
            existing_thread,
            reason=f"{transcript_type.title()} transcript reopened for owner {owner_id}",
        )
        lines = [
            "",
            "Call Started",
            "============",
            f"Started At: {started_at}",
            f"Owner ID: {owner_id}",
            *header_lines,
            "",
            "Messages",
            "========",
        ]
        chunks = _chunk_lines(lines)

        for index, chunk in enumerate(chunks, start=1):
            sent = await _send_transcript_embed(
                thread,
                title=f"Transcript Update {index}",
                description=chunk,
                color=discord.Colour.gold(),
                content=f"<@{owner_id}>" if index == 1 else None,
            )
            if not sent:
                return thread

        return thread

    try:
        thread_with_message = await forum.create_thread(
            name=thread_name[:100],
            content=f"<@{owner_id}>",
            embed=_transcript_embed(f"{transcript_type.title()} Live Transcript", content),
            auto_archive_duration=10080,
            allowed_mentions=discord.AllowedMentions(users=True),
            reason=f"{transcript_type.title()} live transcript for owner {owner_id}",
        )
    except (discord.Forbidden, discord.HTTPException):
        return None

    return thread_with_message.thread


async def append_message_to_transcript(thread: discord.Thread, message: discord.Message) -> None:
    if message.guild is None:
        return

    for embed in _message_embeds(message):
        try:
            await thread.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            return


async def append_lines_to_transcript(thread: discord.Thread, lines: list[str]) -> None:
    for index, chunk in enumerate(_chunk_lines(lines), start=1):
        try:
            await thread.send(embed=_transcript_embed(f"Transcript Update {index}", chunk, color=discord.Colour.gold()))
        except (discord.Forbidden, discord.HTTPException):
            return
