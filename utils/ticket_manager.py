from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from json import JSONDecodeError


TICKET_FILE = "storage/tickets.json"
TICKET_SETTINGS_FILE = "storage/ticket_settings.json"


def _load() -> dict[str, dict]:
    if not os.path.exists(TICKET_FILE):
        return {}

    try:
        with open(TICKET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (JSONDecodeError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def _save(data: dict[str, dict]) -> None:
    os.makedirs("storage", exist_ok=True)
    with open(TICKET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def _load_settings() -> dict:
    if not os.path.exists(TICKET_SETTINGS_FILE):
        return {}

    try:
        with open(TICKET_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (JSONDecodeError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def _save_settings(data: dict) -> None:
    os.makedirs("storage", exist_ok=True)
    with open(TICKET_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def set_ticket_category(guild_id: int, category_id: int) -> None:
    data = _load_settings()
    guild_key = str(guild_id)
    guild_settings = data.get(guild_key, {})

    if not isinstance(guild_settings, dict):
        guild_settings = {}

    guild_settings["ticket_category_id"] = category_id
    data[guild_key] = guild_settings
    _save_settings(data)


def get_ticket_category_id(guild_id: int) -> int | None:
    data = _load_settings()
    guild_settings = data.get(str(guild_id), {})

    if not isinstance(guild_settings, dict):
        return None

    category_id = guild_settings.get("ticket_category_id")
    return category_id if isinstance(category_id, int) else None


def get_next_ticket_number(guild_id: int) -> int:
    data = _load_settings()
    guild_key = str(guild_id)
    guild_settings = data.get(guild_key, {})

    if not isinstance(guild_settings, dict):
        guild_settings = {}

    next_ticket_number = guild_settings.get("next_ticket_number", 1)
    if not isinstance(next_ticket_number, int) or next_ticket_number < 1:
        next_ticket_number = 1

    guild_settings["next_ticket_number"] = next_ticket_number + 1
    data[guild_key] = guild_settings
    _save_settings(data)
    return next_ticket_number


def create_ticket(channel_id: int, user_id: int, ticket_type: str, ticket_number: int) -> dict:
    data = _load()

    ticket = {
        "owner_id": user_id,
        "claimed_by": None,
        "type": ticket_type,
        "ticket_number": ticket_number,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "closed_at": None,
    }
    data[str(channel_id)] = ticket

    _save(data)
    return ticket


def get_ticket(channel_id: int) -> dict | None:
    data = _load()
    return data.get(str(channel_id))


def get_open_ticket_for_user(user_id: int) -> tuple[int, dict] | None:
    data = _load()

    for channel_id, ticket in data.items():
        if ticket.get("owner_id") == user_id:
            return int(channel_id), ticket

    return None


def claim_ticket(channel_id: int, user_id: int) -> bool:
    data = _load()

    if str(channel_id) not in data:
        return False

    data[str(channel_id)]["claimed_by"] = user_id
    _save(data)
    return True


def close_ticket(channel_id: int) -> dict | None:
    data = _load()

    ticket = data.pop(str(channel_id), None)
    _save(data)
    return ticket


def rename_ticket(channel, new_name: str):
    return channel.edit(name=new_name)


def add_user(channel, user):
    return channel.set_permissions(
        user,
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        attach_files=True,
        embed_links=True,
    )


def remove_user(channel, user):
    return channel.set_permissions(user, overwrite=None)
