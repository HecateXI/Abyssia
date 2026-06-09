from __future__ import annotations

from dataclasses import dataclass

import discord
from discord.ext import commands

from core.theme import GOLD_COLOR, asset_emoji, dark_embed


HOME_VALUE = "__home__"
PAGE_SIZE = 25

CATEGORY_LABELS: dict[str, str] = {
    "RPGHunting": "Hunting",
    "RPGProfile": "Profile & Inventory",
    "RPGBestiary": "Bestiary",
    "RPGEconomy": "Economy & Market",
    "RPGShop": "Crates & Selling",
    "RPGEquipment": "Weapons",
    "RPGBattle": "Battle & Raids",
    "RPGSummoning": "Summoning",
    "RPGTrade": "Trading",
    "Buffs": "Sigils & Charms",
    "Admin": "Server Config",
    "Moderation": "Moderation",
    "Boosters": "Booster Roles",
    "Utility": "Utility",
    "HelpGuide": "Help",
}

CATEGORY_ORDER = [
    "Hunting",
    "Profile & Inventory",
    "Bestiary",
    "Economy & Market",
    "Crates & Selling",
    "Weapons",
    "Battle & Raids",
    "Summoning",
    "Trading",
    "Sigils & Charms",
    "Server Config",
    "Moderation",
    "Booster Roles",
    "Utility",
    "Help",
    "Other",
]

CATEGORY_STYLES: dict[str, dict[str, object]] = {
    "Hunting": {
        "emoji": "🩸",
        "asset": ("ui", "hunt"),
        "summary": "Hunt, explore zones, and run autohunts.",
        "featured": ["hunt", "explore", "zones", "autohunt", "use"],
    },
    "Profile & Inventory": {
        "emoji": "🎒",
        "asset": ("ui", "inventory"),
        "summary": "Profile, inventory, quests, daily rewards, and achievements.",
        "featured": ["profile", "inventory", "daily", "checklist", "quests", "bestiary", "zoodense"],
    },
    "Bestiary": {
        "emoji": "📖",
        "asset": ("ui", "profile"),
        "summary": "Inspect creature details and rarity data.",
        "featured": ["dex"],
    },
    "Economy & Market": {
        "emoji": "💰",
        "asset": ("currency", "souls"),
        "summary": "Souls, shops, selling, market listings, and player payments.",
        "featured": ["souls", "give", "shop", "shop buy", "sell", "market", "trade"],
    },
    "Crates & Selling": {
        "emoji": "📦",
        "asset": ("crate", "cache"),
        "summary": "Open crates, buy shard crates, salvage, and release extras.",
        "featured": ["open", "crateshop", "shardcrate", "salvage", "sellall", "release"],
    },
    "Weapons": {
        "emoji": "⚔️",
        "asset": ("weapons", "sword"),
        "summary": "Inspect, equip, reroll, and manage creature weapons.",
        "featured": ["weapons", "weaponequip", "weaponunequip", "wr", "weaponshards", "wdex"],
    },
    "Battle & Raids": {
        "emoji": "🔥",
        "asset": ("ui", "battle"),
        "summary": "Teams, arena battles, revenge fights, bosses, and raids.",
        "featured": ["team", "team set", "battle", "arena", "leaderboard", "raid", "boss"],
    },
    "Summoning": {
        "emoji": "✨",
        "asset": ("ui", "crafting"),
        "summary": "Summon special creatures and ritual rewards.",
        "featured": ["summon"],
    },
    "Trading": {
        "emoji": "🤝",
        "asset": ("ui", "marketplace"),
        "summary": "Exchange items and player-to-player trade tools.",
        "featured": ["exchange"],
    },
    "Sigils & Charms": {
        "emoji": "🔮",
        "asset": ("buffs", "lesser_void"),
        "summary": "Activate temporary sigils and charms, then check buffs.",
        "featured": ["sigils", "sigil", "charms", "charm", "buffs"],
    },
    "Server Config": {
        "emoji": "⚙️",
        "asset": ("ui", "settings"),
        "summary": "Prefix, modlog, welcome, emoji setup, and server settings.",
        "featured": ["config", "config prefix", "config setup-emojis", "config reload-emojis", "config modlog"],
    },
    "Moderation": {
        "emoji": "🛡️",
        "asset": ("ui", "settings"),
        "summary": "Kick, ban, timeout, purge, and channel moderation.",
        "featured": ["kick", "ban", "timeout", "purge", "slowmode"],
    },
    "Booster Roles": {
        "emoji": "💎",
        "asset": ("currency", "gems"),
        "summary": "Manage custom booster role rewards.",
        "featured": ["booster", "booster create", "booster color", "booster sync"],
    },
    "Utility": {
        "emoji": "📡",
        "asset": ("ui", "leaderboard"),
        "summary": "Small bot utility commands.",
        "featured": ["ping"],
    },
    "Help": {
        "emoji": "❔",
        "asset": ("ui", "quest"),
        "summary": "Browse commands and open detailed command pages.",
        "featured": ["help", "commands"],
    },
    "Other": {
        "emoji": "❔",
        "asset": None,
        "summary": "Miscellaneous loaded commands.",
        "featured": [],
    },
}


@dataclass(frozen=True)
class CommandEntry:
    category: str
    command: commands.Command

    @property
    def name(self) -> str:
        return self.command.qualified_name

    def usage(self, prefix: str) -> str:
        signature = (self.command.signature or "").strip()
        return f"{prefix}{self.name} {signature}".strip()

    @property
    def short_description(self) -> str:
        text = self.command.short_doc or self.command.help or "No description available."
        return " ".join(text.split())[:100]


def _category_for(command: commands.Command) -> str:
    cog_name = command.cog.qualified_name if command.cog else "Other"
    return CATEGORY_LABELS.get(cog_name, cog_name or "Other")


def _all_entries(bot: commands.Bot) -> list[CommandEntry]:
    entries: list[CommandEntry] = []
    seen: set[str] = set()
    for command in bot.walk_commands():
        if command.hidden or not command.enabled:
            continue
        if command.qualified_name in seen:
            continue
        seen.add(command.qualified_name)
        entries.append(CommandEntry(_category_for(command), command))
    return sorted(entries, key=lambda entry: (CATEGORY_ORDER.index(entry.category) if entry.category in CATEGORY_ORDER else 999, entry.name))


def _grouped_entries(bot: commands.Bot) -> dict[str, list[CommandEntry]]:
    grouped: dict[str, list[CommandEntry]] = {}
    for entry in _all_entries(bot):
        grouped.setdefault(entry.category, []).append(entry)
    return grouped


def _category_sort_key(category: str) -> tuple[int, str]:
    return (CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else 999, category)


def _clip(value: str, limit: int) -> str:
    value = " ".join(str(value).split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _category_style(category: str) -> dict[str, object]:
    return CATEGORY_STYLES.get(category, CATEGORY_STYLES["Other"])


def _category_emoji(category: str, *, custom: bool = True) -> str:
    style = _category_style(category)
    if custom:
        asset = style.get("asset")
        if isinstance(asset, tuple) and len(asset) == 2:
            emoji = asset_emoji(str(asset[0]), str(asset[1]))
            if emoji:
                return emoji
    return str(style.get("emoji") or "❔")


def _category_name(category: str) -> str:
    return f"{_category_emoji(category)} {category}"


def _featured_entries(category: str, entries: list[CommandEntry]) -> list[CommandEntry]:
    by_name = {entry.name: entry for entry in entries}
    ordered: list[CommandEntry] = []
    seen: set[str] = set()
    for name in _category_style(category).get("featured", []):
        if not isinstance(name, str):
            continue
        entry = by_name.get(name)
        if entry and entry.name not in seen:
            ordered.append(entry)
            seen.add(entry.name)
    for entry in entries:
        if entry.name not in seen:
            ordered.append(entry)
            seen.add(entry.name)
        if len(ordered) >= 6:
            break
    return ordered[:6]


def _display_prefix(ctx: commands.Context) -> str:
    prefix = str(getattr(ctx, "clean_prefix", None) or getattr(ctx, "prefix", None) or "b")
    if prefix.lower() == "b":
        return "b "
    return prefix


def _command_query_variants(value: str) -> list[str]:
    query = " ".join(value.lower().strip().split())
    if not query:
        return []
    variants = [query]
    if query.startswith("b "):
        variants.append(query[2:].strip())
    if query.startswith("b") and " " not in query and len(query) > 1:
        variants.append(query[1:])
    return list(dict.fromkeys(v for v in variants if v))


def _command_alias_usages(command: commands.Command, prefix: str) -> list[str]:
    parent = f"{command.parent.qualified_name} " if command.parent else ""
    return [f"{prefix}{parent}{alias}" for alias in command.aliases]


def _command_by_name(bot: commands.Bot, qualified_name: str) -> commands.Command | None:
    for query in _command_query_variants(qualified_name):
        command = bot.get_command(query)
        if command and not command.hidden and command.enabled:
            return command

    for command in bot.walk_commands():
        if command.hidden or not command.enabled:
            continue
        names = {command.qualified_name.lower(), command.name.lower()}
        if command.parent:
            names.update(f"{command.parent.qualified_name.lower()} {alias.lower()}" for alias in command.aliases)
        else:
            names.update(alias.lower() for alias in command.aliases)
        if any(query in names for query in _command_query_variants(qualified_name)):
            return command
    return None


class DynamicHelpView(discord.ui.View):
    def __init__(self, ctx: commands.Context) -> None:
        super().__init__(timeout=180)
        self.ctx = ctx
        self.prefix = _display_prefix(ctx)
        self.grouped = _grouped_entries(ctx.bot)
        self.category: str | None = None
        self.page = 0
        self.message: discord.Message | None = None
        self._sync_controls()

    def _categories(self) -> list[str]:
        return sorted(self.grouped, key=_category_sort_key)

    def _entries(self) -> list[CommandEntry]:
        if not self.category:
            return []
        return self.grouped.get(self.category, [])

    def _page_count(self) -> int:
        total = len(self._entries())
        return max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    def _page_entries(self) -> list[CommandEntry]:
        start = self.page * PAGE_SIZE
        return self._entries()[start:start + PAGE_SIZE]

    def _sync_controls(self) -> None:
        category_options = [
            discord.SelectOption(label="Home", value=HOME_VALUE, description="Command category overview", emoji="🏠"),
        ]
        category_options.extend(
            discord.SelectOption(
                label=_clip(category, 100),
                value=category,
                description=f"{len(self.grouped[category])} command(s)",
                emoji=_category_emoji(category, custom=False),
            )
            for category in self._categories()
        )
        self.category_select.options = category_options[:25]
        self.category_select.placeholder = self.category or "Choose a command category"

        page_entries = self._page_entries()
        if page_entries:
            self.command_select.disabled = False
            self.command_select.placeholder = f"Choose a command ({self.page + 1}/{self._page_count()})"
            self.command_select.options = [
                discord.SelectOption(
                    label=_clip(entry.name, 100),
                    value=entry.name,
                    description=_clip(entry.short_description, 100),
                )
                for entry in page_entries
            ]
        else:
            self.command_select.disabled = True
            self.command_select.placeholder = "Choose a category first"
            self.command_select.options = [discord.SelectOption(label="No command selected", value="noop")]

        self.prev_page.disabled = not self.category or self.page <= 0
        self.next_page.disabled = not self.category or self.page >= self._page_count() - 1

    def _home_embed(self) -> discord.Embed:
        total = sum(len(entries) for entries in self.grouped.values())
        embed = dark_embed(
            "Abyssia Help",
            f"{_category_emoji('Hunting')} **Begin in the dark:** `{self.prefix}hunt`  •  `{self.prefix}profile`  •  `{self.prefix}inventory`\n"
            f"{_category_emoji('Battle & Raids')} **Fight back:** `{self.prefix}team`  •  `{self.prefix}battle`  •  `{self.prefix}raid`\n"
            f"{_category_emoji('Economy & Market')} **Spend wisely:** `{self.prefix}souls`  •  `{self.prefix}shop`  •  `{self.prefix}market`\n\n"
            f"Showing **{total}** loaded command entries. Pick a category, then pick a command for full details.\n"
            f"Text commands work as `{self.prefix}command`"
            + (" or attached to the prefix, like `bhunt`." if self.prefix == "b " else "."
              ) + "\n\n📬 **Support Server:** [Join the Abyssia Discord](https://discord.gg/CwRRA98Kx5)",
            color=GOLD_COLOR,
        )
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar.url)
        for category in self._categories():
            entries = self.grouped[category]
            sample_entries = _featured_entries(category, entries)
            sample = "  ".join(f"`{self.prefix}{entry.name}`" for entry in sample_entries)
            if len(entries) > len(sample_entries):
                sample += f"  +{len(entries) - len(sample_entries)} more"
            summary = str(_category_style(category).get("summary") or "Loaded commands.")
            embed.add_field(
                name=f"{_category_name(category)} ({len(entries)})",
                value=f"{summary}\n{sample or 'No commands'}",
                inline=False,
            )
        embed.set_footer(text="The home screen is curated; dropdowns are generated from the bot's actual loaded commands.")
        return embed

    def _category_embed(self) -> discord.Embed:
        entries = self._entries()
        embed = dark_embed(
            f"{_category_name(self.category or 'Other')} Commands",
            f"Page **{self.page + 1}/{self._page_count()}**. Pick a command from the second dropdown for separate info.",
            color=GOLD_COLOR,
        )
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar.url)
        lines = [f"`{entry.usage(self.prefix)}` - {entry.short_description}" for entry in self._page_entries()]
        embed.add_field(name=f"{len(entries)} command(s)", value="\n".join(lines)[:1024] or "No commands.", inline=False)
        return embed

    def _command_embed(self, command: commands.Command) -> discord.Embed:
        entry = CommandEntry(_category_for(command), command)
        description = command.help or command.short_doc or "No description available."
        embed = dark_embed(f"Command: {self.prefix}{command.qualified_name}", description, color=GOLD_COLOR)
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar.url)
        embed.add_field(name="Usage", value=f"`{entry.usage(self.prefix)}`", inline=False)
        if command.aliases:
            aliases = ", ".join(f"`{alias}`" for alias in _command_alias_usages(command, self.prefix))
            embed.add_field(name="Aliases", value=aliases[:1024], inline=False)
        if command.parent:
            embed.add_field(name="Parent Group", value=f"`{self.prefix}{command.parent.qualified_name}`", inline=True)
        embed.add_field(name="Category", value=entry.category, inline=True)
        subcommands = list(getattr(command, "commands", []) or [])
        if subcommands:
            value = "\n".join(f"`{self.prefix}{sub.qualified_name}` - {_clip(sub.short_doc or 'No description.', 80)}" for sub in subcommands)
            embed.add_field(name="Subcommands", value=value[:1024], inline=False)
        if getattr(command, "checks", None):
            embed.set_footer(text="This command may require permissions, roles, cooldowns, or other checks.")
        return embed

    @discord.ui.select(placeholder="Choose a command category", options=[discord.SelectOption(label="Home", value=HOME_VALUE)])
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        value = select.values[0]
        if value == HOME_VALUE:
            self.category = None
            self.page = 0
            self._sync_controls()
            await interaction.response.edit_message(embed=self._home_embed(), view=self)
            return
        self.category = value
        self.page = 0
        self._sync_controls()
        await interaction.response.edit_message(embed=self._category_embed(), view=self)

    @discord.ui.select(placeholder="Choose a category first", options=[discord.SelectOption(label="No command selected", value="noop")], disabled=True)
    async def command_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        if select.values[0] == "noop":
            await interaction.response.defer()
            return
        command = _command_by_name(self.ctx.bot, select.values[0])
        if command is None:
            await interaction.response.send_message("That command is no longer loaded.", ephemeral=True)
            return
        self._sync_controls()
        await interaction.response.edit_message(embed=self._command_embed(command), view=self)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = max(0, self.page - 1)
        self._sync_controls()
        await interaction.response.edit_message(embed=self._category_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, disabled=True)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.page = min(self._page_count() - 1, self.page + 1)
        self._sync_controls()
        await interaction.response.edit_message(embed=self._category_embed(), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your help menu.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class HelpGuide(commands.Cog):
    """Dynamic command reference."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="help")
    async def help_command(self, ctx: commands.Context, *, command_or_category: str | None = None) -> None:
        """Browse every loaded command with dropdowns and detailed command pages."""
        assert ctx.guild is not None
        view = DynamicHelpView(ctx)

        if command_or_category:
            query = command_or_category.strip().lower()
            category = next((cat for cat in view._categories() if cat.lower() == query), None)
            command = _command_by_name(self.bot, query)
            if category:
                view.category = category
                view.page = 0
                view._sync_controls()
                embed = view._category_embed()
            elif command:
                view.category = _category_for(command)
                names = [entry.name for entry in view._entries()]
                view.page = max(0, names.index(command.qualified_name) // PAGE_SIZE) if command.qualified_name in names else 0
                view._sync_controls()
                embed = view._command_embed(command)
            else:
                embed = view._home_embed()
                embed.description = f"No command or category matched `{command_or_category}`.\n\n{embed.description}"
        else:
            embed = view._home_embed()

        message = await ctx.reply(embed=embed, view=view, mention_author=False)
        view.message = message

    @commands.hybrid_command(name="commands", aliases=["cmd", "cmds"])
    async def commands_list(self, ctx: commands.Context) -> None:
        """Show all loaded commands grouped by category."""
        assert ctx.guild is not None
        grouped = _grouped_entries(self.bot)
        prefix = _display_prefix(ctx)
        embeds: list[discord.Embed] = []
        current = dark_embed("Abyssia Command List", f"Use `{prefix}help` for dropdown details.", color=GOLD_COLOR)
        field_count = 0
        for category in sorted(grouped, key=_category_sort_key):
            entries = grouped[category]
            lines = [f"`{prefix}{entry.name}`" for entry in entries]
            value = ", ".join(lines)
            while len(value) > 1024:
                split_at = value.rfind(",", 0, 1000)
                if split_at <= 0:
                    split_at = 1000
                current.add_field(name=f"{category} (continued)", value=value[:split_at], inline=False)
                field_count += 1
                value = value[split_at + 1:].lstrip()
                if field_count >= 24:
                    embeds.append(current)
                    current = dark_embed("Abyssia Command List", color=GOLD_COLOR)
                    field_count = 0
            current.add_field(name=f"{category} ({len(entries)})", value=value or "No commands", inline=False)
            field_count += 1
            if field_count >= 24:
                embeds.append(current)
                current = dark_embed("Abyssia Command List", color=GOLD_COLOR)
                field_count = 0
        embeds.append(current)
        for index, embed in enumerate(embeds):
            await ctx.reply(embed=embed, mention_author=False) if index == 0 else await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpGuide(bot))
