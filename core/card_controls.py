from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import discord


@dataclass(frozen=True)
class CardShortcut:
    label: str
    command: str
    description: str = ""
    style: discord.ButtonStyle = discord.ButtonStyle.secondary
    emoji: str | None = None


@dataclass(frozen=True)
class _Route:
    cog_name: str
    command_name: str
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] | None = None


class ButtonContext:
    """Small Context-shaped adapter for buttons that open existing card commands."""

    def __init__(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        self.bot = interaction.client
        self.author = interaction.user
        self.user = interaction.user
        self.guild = interaction.guild
        self.channel = interaction.channel
        self.message = interaction.message
        self.prefix = "b "

    async def defer(self, *, ephemeral: bool = True, **_: Any) -> None:
        if not self.interaction.response.is_done():
            await self.interaction.response.defer(ephemeral=ephemeral, thinking=True)

    async def reply(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.pop("mention_author", None)
        kwargs.setdefault("ephemeral", True)
        return await self._send(*args, **kwargs)

    async def send(self, *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("ephemeral", True)
        return await self._send(*args, **kwargs)

    async def _send(self, *args: Any, **kwargs: Any) -> Any:
        if self.interaction.response.is_done():
            return await self.interaction.followup.send(*args, **kwargs)
        return await self.interaction.response.send_message(*args, **kwargs)

    @asynccontextmanager
    async def typing(self):
        yield


SAFE_ROUTES: dict[str, _Route] = {
    "b profile": _Route("RPGProfile", "profile"),
    "b profilecustomize": _Route("RPGProfile", "profilecustomize"),
    "b pcard": _Route("RPGProfile", "profilecustomize"),
    "b inventory": _Route("RPGProfile", "inventory"),
    "b inv": _Route("RPGProfile", "inventory"),
    "b daily": _Route("RPGProfile", "daily"),
    "b checklist": _Route("RPGProfile", "checklist"),
    "b tasks": _Route("RPGProfile", "checklist"),
    "b quests": _Route("RPGProfile", "quests"),
    "b quest": _Route("RPGProfile", "quest"),
    "b quests claim": _Route("RPGProfile", "claim_quests"),
    "b quest claim": _Route("RPGProfile", "claim_quests"),
    "b quests reroll": _Route("RPGProfile", "reroll_quest"),
    "b quest reroll": _Route("RPGProfile", "reroll_quest"),
    "b zoo": _Route("RPGProfile", "bestiary"),
    "b bestiary": _Route("RPGProfile", "bestiary"),
    "b team": _Route("RPGBattle", "team"),
    "b weapons": _Route("RPGEquipment", "weapons", (None,)),
    "b weapon": _Route("RPGEquipment", "weapons", (None,)),
    "b w": _Route("RPGEquipment", "weapons", (None,)),
    "b open": _Route("RPGShop", "open_crate_cmd"),
    "b unbox": _Route("RPGShop", "open_crate_cmd"),
    "b openall": _Route("RPGShop", "openall"),
    "b massopen": _Route("RPGShop", "openall"),
    "b crateshop": _Route("RPGShop", "crateshop"),
    "b crates": _Route("RPGShop", "crateshop"),
    "b explore": _Route("RPGHunting", "explore", kwargs={"zone": None}),
    "b incursion": _Route("RPGIncursion", "incursion_status"),
    "b inc": _Route("RPGIncursion", "incursion_status"),
    "b raid": _Route("RPGIncursion", "incursion_status"),
    "b boss": _Route("RPGIncursion", "incursion_status"),
    "b upgrade": _Route("RPGProfile", "upgrade_creature", kwargs={"creature": None}),
    "b creatureupgrade": _Route("RPGProfile", "upgrade_creature", kwargs={"creature": None}),
    "b levelpet": _Route("RPGProfile", "upgrade_creature", kwargs={"creature": None}),
    "b petupgrade": _Route("RPGProfile", "upgrade_creature", kwargs={"creature": None}),
}

BLOCKED_ACTION_PREFIXES = (
    "b hunt",
    "bh",
    "b battle",
    "bb",
    "b autohunt start",
    "b raid attack",
    "b boss attack",
    "bincursion strike",
    "bincursion focus",
    "bincursion guard",
    "bincursion cleanse",
    "bincursion channel",
    "bincursion attack",
)


def _normalize_command(command: str) -> str:
    return " ".join(command.strip().split()).lower()


SHORTCUT_EMOJIS: dict[str, str] = {
    "battle": "⚔️",
    "boss": "💀",
    "customize": "🎨",
    "equip": "🗡️",
    "explore": "🧭",
    "favorite": "⭐",
    "inventory": "🎒",
    "profile": "📜",
    "raid": "🩸",
    "team": "⚔️",
    "vault": "🗡️",
    "weapons": "🗡️",
    "upgrade": "⬆️",
    "zoo": "🔮",
}


def _shortcut_emoji(shortcut: CardShortcut) -> str | None:
    if shortcut.emoji:
        return shortcut.emoji
    text = f"{shortcut.label} {shortcut.command}".lower()
    if "daily" in text:
        return "\U0001f4c5"
    if "quest" in text or "checklist" in text or "task" in text:
        return "\U0001f4dc"
    if "bulk" in text or "open all" in text or "openall" in text or "mass" in text:
        return "\U0001f4e6"
    if "open" in text or "crate" in text or "box" in text:
        return "\U0001f381"
    if "slot 1" in text:
        return "\u0031\ufe0f\u20e3"
    if "slot 2" in text:
        return "\u0032\ufe0f\u20e3"
    if "slot 3" in text:
        return "\u0033\ufe0f\u20e3"
    for key, emoji in SHORTCUT_EMOJIS.items():
        if key in text:
            return emoji
    return "◆"


def _command_callback(command: Any) -> Callable[..., Awaitable[Any]] | None:
    callback = getattr(command, "callback", None)
    if callback is not None:
        return callback
    if callable(command):
        return command
    return None


async def _invoke_route(interaction: discord.Interaction, route: _Route) -> None:
    cog = interaction.client.get_cog(route.cog_name)
    if cog is None:
        raise RuntimeError(f"{route.cog_name} is not loaded.")
    command = getattr(cog, route.command_name, None)
    callback = _command_callback(command)
    if callback is None:
        raise RuntimeError(f"{route.command_name} is not callable.")
    ctx = ButtonContext(interaction)
    kwargs = dict(route.kwargs or {})
    if getattr(command, "callback", None) is not None:
        await callback(cog, ctx, *route.args, **kwargs)
    else:
        await callback(ctx, *route.args, **kwargs)


async def _invoke_dynamic_route(interaction: discord.Interaction, command: str) -> bool:
    parts = command.strip().split()
    lower = [part.lower() for part in parts]
    if len(lower) >= 4 and lower[:2] in (["b", "w"], ["b", "weapon"]):
        try:
            weapon_id = int(lower[2].lstrip("#"))
            slot = int(lower[3])
        except ValueError:
            return False
        await _invoke_route(interaction, _Route("RPGEquipment", "w_shortcut", (weapon_id, slot)))
        return True
    if len(lower) >= 3 and lower[:2] in (["b", "favorite"], ["b", "fav"], ["b", "star"]):
        try:
            weapon_id = int(lower[2].lstrip("#"))
        except ValueError:
            return False
        await _invoke_route(interaction, _Route("RPGEquipment", "favorite", (weapon_id,)))
        return True
    if len(lower) >= 5 and lower[:3] == ["b", "team", "set"]:
        try:
            slot = int(lower[3])
        except ValueError:
            return False
        creature_name = " ".join(parts[4:])
        await _invoke_route(interaction, _Route("RPGBattle", "team_set", (slot,), {"creature_name": creature_name}))
        return True
    return False


class CommandShortcutButton(discord.ui.Button):
    def __init__(self, shortcut: CardShortcut) -> None:
        super().__init__(label=shortcut.label[:80], style=shortcut.style, emoji=_shortcut_emoji(shortcut))
        self.shortcut = shortcut

    async def callback(self, interaction: discord.Interaction) -> None:
        normalized = _normalize_command(self.shortcut.command)
        if any(normalized == blocked or normalized.startswith(f"{blocked} ") for blocked in BLOCKED_ACTION_PREFIXES):
            await interaction.response.send_message(
                "That action stays command-only to prevent one-click farming.",
                ephemeral=True,
            )
            return
        try:
            route = SAFE_ROUTES.get(normalized)
            if route is not None:
                await interaction.response.defer(ephemeral=True, thinking=True)
                await _invoke_route(interaction, route)
                return
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=True)
            if await _invoke_dynamic_route(interaction, self.shortcut.command):
                return
        except Exception as exc:
            if interaction.response.is_done():
                await interaction.followup.send(f"Button action failed: `{exc}`", ephemeral=True)
            else:
                await interaction.response.send_message(f"Button action failed: `{exc}`", ephemeral=True)
            return
        if interaction.response.is_done():
            await interaction.followup.send("This card action is not wired yet.", ephemeral=True)
        else:
            await interaction.response.send_message("This card action is not wired yet.", ephemeral=True)


class CommandShortcutView(discord.ui.View):
    def __init__(self, owner_id: int | None, shortcuts: list[CardShortcut], *, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        for shortcut in shortcuts[:10]:
            self.add_item(CommandShortcutButton(shortcut))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.owner_id is None or interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("These card controls belong to another hunter.", ephemeral=True)
        return False


BLOCKED_SHORTCUT_LABELS = frozenset({"profile", "team", "inventory"})


def shortcut_label_blocked(label: str) -> bool:
    return str(label).strip().casefold() in BLOCKED_SHORTCUT_LABELS


def shortcut_view(owner_id: int | None, shortcuts: list[tuple[str, str] | tuple[str, str, str]]) -> CommandShortcutView:
    items = [
        CardShortcut(label=item[0], command=item[1], description=item[2] if len(item) > 2 else "")
        for item in shortcuts
        if not shortcut_label_blocked(item[0])
    ]
    return CommandShortcutView(owner_id, items)


def add_shortcuts(
    view: discord.ui.View,
    shortcuts: list[tuple[str, str] | tuple[str, str, str]],
    *,
    max_children: int = 25,
) -> discord.ui.View:
    for item in shortcuts:
        if shortcut_label_blocked(item[0]):
            continue
        if len(view.children) >= max_children:
            break
        view.add_item(
            CommandShortcutButton(
                CardShortcut(label=item[0], command=item[1], description=item[2] if len(item) > 2 else "")
            )
        )
    return view
