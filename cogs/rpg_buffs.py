from __future__ import annotations

import discord
from discord.ext import commands

from core.rpg import activate_buff, award_currency, ensure_player, get_active_buffs
from core.rpg_data import CHARMS, SIGILS, normalize_key
from core.theme import asset_emoji, buff_label, currency_label, dark_embed, status_embed


def _button_emoji(kind: str, key: str) -> discord.PartialEmoji | str | None:
    raw = asset_emoji(kind, key) if kind else key
    if not raw:
        return None
    try:
        return discord.PartialEmoji.from_str(raw)
    except (ValueError, TypeError):
        return raw if len(raw) <= 8 else None


def _buff_icon(key: str) -> str:
    return asset_emoji("buffs", key) or ""


def _buff_options() -> list[tuple[str, object]]:
    return [(f"sigil:{item.key}", item) for item in SIGILS] + [(f"charm:{item.key}", item) for item in CHARMS]


def _find_buff(kind: str, key: str):
    pool = SIGILS if kind == "sigil" else CHARMS if kind == "charm" else ()
    wanted = normalize_key(key)
    return next((item for item in pool if normalize_key(item.key) == wanted or normalize_key(item.name) == wanted), None)


def _effect_text(kind: str, item: object) -> str:
    extra = int(getattr(item, "extra_monsters", 0))
    charges = int(getattr(item, "charges", 0))
    cost = int(getattr(item, "cost_souls", 0))
    if kind == "sigil":
        effect = f"+{extra} monster{'s' if extra != 1 else ''} per hunt"
    else:
        rarity = int(float(getattr(item, "rarity_bonus", 0.0)) * 100)
        effect = f"+{extra} monster{'s' if extra != 1 else ''} per hunt, +{rarity}% rarity"
    return f"{effect} | `{charges}` hunts | {currency_label('gold')} `{cost:,}`"


class BuffSelect(discord.ui.Select):
    def __init__(self) -> None:
        options: list[discord.SelectOption] = []
        for value, item in _buff_options():
            kind, key = value.split(":", 1)
            options.append(
                discord.SelectOption(
                    label=str(item.name),
                    value=value,
                    description=_effect_text(kind, item)[:100],
                    emoji=_button_emoji("buffs", key),
                )
            )
        super().__init__(placeholder="Activate a sigil or charm...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, BuffsPanelView):
            await interaction.response.send_message("This buffs panel expired.", ephemeral=True)
            return
        kind, key = self.values[0].split(":", 1)
        item = _find_buff(kind, key)
        if item is None:
            await interaction.response.send_message("That buff is no longer available.", ephemeral=True)
            return

        player = await ensure_player(interaction.client.db, interaction.user.id, interaction.user.display_name)
        cost = int(getattr(item, "cost_souls", 0))
        if int(player["gold"]) < cost:
            await interaction.response.send_message(
                f"Need {currency_label('gold')} **{cost:,}**, you have **{int(player['gold']):,}**.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        await award_currency(interaction.client.db, interaction.user.id, gold=-cost)
        await activate_buff(interaction.client.db, interaction.user.id, str(item.key), kind, int(item.charges))
        refreshed = await ensure_player(interaction.client.db, interaction.user.id, interaction.user.display_name)
        active = await get_active_buffs(interaction.client.db, interaction.user.id)
        notice = f"{buff_label(str(item.key), str(item.name))} activated for `{int(item.charges)}` hunts."
        await interaction.edit_original_response(
            view=BuffsPanelView(interaction.user.id, interaction.user.display_name, refreshed, active, notice=notice)
        )


class BuffsPanelView(discord.ui.LayoutView):
    def __init__(
        self,
        owner_id: int,
        display_name: str,
        player,
        active: dict[str, int],
        *,
        notice: str | None = None,
    ) -> None:
        super().__init__(timeout=180)
        self.owner_id = owner_id

        souls = int(player["gold"])
        container = discord.ui.Container(accent_colour=discord.Color.purple())
        container.add_item(discord.ui.TextDisplay(f"## Hunt Buffs\n{display_name}"))

        # --- Active buffs ---
        if active:
            active_lines: list[str] = []
            for key, charges in active.items():
                item = _find_buff("sigil", key) or _find_buff("charm", key)
                if item is None:
                    continue
                active_lines.append(
                    f"{_buff_icon(key)} **{item.name}**\n"
                    f"> `{int(charges)}` hunts remaining"
                )
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay("**Active Buffs**\n" + "\n".join(active_lines)))

        # --- Sigils ---
        sigil_lines = []
        for s in SIGILS:
            sigil_lines.append(
                f"{_buff_icon(s.key)} **{s.name}**\n"
                f"> +{s.extra_monsters} monster{'s' if s.extra_monsters != 1 else ''} per hunt\n"
                f"> `{s.charges}` hunts \u2022 `{s.cost_souls:,}` souls"
            )
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay("**Sigils**\n" + "\n".join(sigil_lines)))

        # --- Charms ---
        charm_lines = []
        for c in CHARMS:
            rarity_pct = int(float(c.rarity_bonus) * 100)
            charm_lines.append(
                f"{_buff_icon(c.key)} **{c.name}**\n"
                f"> +{c.extra_monsters} monster{'s' if c.extra_monsters != 1 else ''} per hunt, +{rarity_pct}% rarity\n"
                f"> `{c.charges}` hunts \u2022 `{c.cost_souls:,}` souls"
            )
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay("**Charms**\n" + "\n".join(charm_lines)))

        if notice:
            container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(f"**Result**\n{notice}"))

        # --- Cost summary ---
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"\U0001f4b0 **Your Souls:** `{souls:,}`"))

        row = discord.ui.ActionRow()
        row.add_item(BuffSelect())
        container.add_item(row)
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("This buffs panel belongs to another hunter.", ephemeral=True)
        return False


class Buffs(commands.Cog):
    """Temporary hunting buffs: sigils and charms."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def build_buffs_view(self, user_id: int, display_name: str) -> BuffsPanelView:
        player = await ensure_player(self.bot.db, user_id, display_name)
        active = await get_active_buffs(self.bot.db, user_id)
        return BuffsPanelView(user_id, display_name, player, active)

    async def _reply_buffs_panel(self, ctx: commands.Context) -> None:
        assert ctx.guild is not None
        view = await self.build_buffs_view(ctx.author.id, ctx.author.display_name)
        await ctx.reply(view=view, mention_author=False)

    @commands.hybrid_command(name="sigils")
    async def sigils_list(self, ctx: commands.Context) -> None:
        """View and activate hunt sigils."""
        await self._reply_buffs_panel(ctx)

    @commands.hybrid_command(name="charms")
    async def charms_list(self, ctx: commands.Context) -> None:
        """View and activate hunt charms."""
        await self._reply_buffs_panel(ctx)

    @commands.hybrid_command(name="buffs", aliases=["active"])
    async def active_buffs(self, ctx: commands.Context) -> None:
        """View active buffs and activate sigils or charms."""
        await self._reply_buffs_panel(ctx)

    async def _activate_named(self, ctx: commands.Context, kind: str, key: str) -> None:
        assert ctx.guild is not None
        item = _find_buff(kind, key)
        if item is None:
            pool = SIGILS if kind == "sigil" else CHARMS
            valid = ", ".join(buff.key for buff in pool)
            raise commands.BadArgument(f"Unknown {kind}. Choose: {valid}")
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        cost = int(item.cost_souls)
        if int(player["gold"]) < cost:
            raise commands.BadArgument(f"Need {currency_label('gold')} **{cost:,}**, you have **{int(player['gold']):,}**.")
        await award_currency(self.bot.db, ctx.author.id, gold=-cost)
        await activate_buff(self.bot.db, ctx.author.id, item.key, kind, int(item.charges))
        await ctx.reply(
            embed=status_embed(
                f"{buff_label(item.key, item.name)} Activated",
                f"{_effect_text(kind, item)}",
            ),
            mention_author=False,
        )

    @commands.hybrid_command(name="sigil")
    async def sigil_activate(self, ctx: commands.Context, sigil_key: str) -> None:
        """Activate a hunt sigil. Use b buffs for the selector."""
        await self._activate_named(ctx, "sigil", sigil_key)

    @commands.hybrid_command(name="charm")
    async def charm_activate(self, ctx: commands.Context, charm_key: str) -> None:
        """Activate a hunt charm. Use b buffs for the selector."""
        await self._activate_named(ctx, "charm", charm_key)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Buffs(bot))
