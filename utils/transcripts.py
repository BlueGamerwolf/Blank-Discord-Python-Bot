from __future__ import annotations

from datetime import datetime, timezone

import discord

from config import ADMIN_ROLE_ID, MOD_ROLE_ID, SUPPORT_ROLE_ID, TRANSCRIPT_CATEGORY_ID


TRANSCRIPT_CATEGORY_NAME = "Transcripts"
MAX_POST_LENGTH = 1900


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


async def ensure_owner_forum(
    guild: discord.Guild,
    *,
    transcript_type: str,
    owner_id: int,
) -> discord.ForumChannel | None:
    category = await ensure_transcript_category(guild)
    if category is None:
        return None

    forum_name = f"{transcript_type}-transcripts-{owner_id}"
    existing = discord.utils.get(guild.forums, name=forum_name)
    if isinstance(existing, discord.ForumChannel):
        return existing

    try:
        return await guild.create_forum(
            forum_name,
            topic=f"{transcript_type.title()} transcripts bound to owner ID {owner_id}.",
            category=category,
            overwrites=_staff_transcript_overwrites(guild),
            default_auto_archive_duration=10080,
            reason=f"{transcript_type.title()} transcript forum setup for owner {owner_id}",
        )
    except discord.Forbidden:
        return None


def _chunk_lines(lines: list[str], max_length: int = MAX_POST_LENGTH) -> list[str]:
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


async def post_owner_transcript(
    guild: discord.Guild,
    *,
    transcript_type: str,
    owner_id: int,
    title: str,
    header_lines: list[str],
    message_lines: list[str],
) -> str | None:
    forum = await ensure_owner_forum(guild, transcript_type=transcript_type, owner_id=owner_id)
    if forum is None:
        return None

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
    first_chunk = f"Transcript posted at {started_at}\n\n{chunks[0]}"

    if len(first_chunk) > 2000:
        first_chunk = chunks[0]

    try:
        thread_with_message = await forum.create_thread(
            name=title[:100],
            content=first_chunk,
            auto_archive_duration=10080,
            reason=f"{transcript_type.title()} transcript for owner {owner_id}",
        )
        thread = thread_with_message.thread

        for chunk in chunks[1:]:
            await thread.send(chunk)
    except (discord.Forbidden, discord.HTTPException):
        return None

    return thread.jump_url
