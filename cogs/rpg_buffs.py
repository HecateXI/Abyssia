from __future__ import annotations

import discord
from discord.ext import commands

from core.cards import render_buffs_card
from core.rpg import (
    activate_buff,
    award_currency,
    ensure_player,
    get_active_buffs,
    now_ts,
)
from core.rpg_data import CHARMS, SIGILS
from core.theme import GOLD_COLOR, buff_label, currency_label, dark_embed, status_embed


class SigilActivateView(discord.ui.View):
    def __init__(self, ctx: commands.Context, player, sigils) -> None:
        super().__init__(timeout=60)
        self.ctx = ctx
        self.player = player
        self.sigils = sigils

    @discord.ui.select(
        placeholder="🩸 Select a sigil to activate...",
        options=[
            discord.SelectOption(
                label=s.name,
                value=s.key,
                description=f"+{s.extra_monsters}/hunt, {s.charges} hunts, {s.cost_souls:,} souls",
                emoji="🩸",
            )
            for s in SIGILS
        ],
    )
    async def sigil_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        sigil_key = select.values[0]
        sigil = next(s for s in SIGILS if s.key == sigil_key)
        db = interaction.client.db
        souls = int(self.player["gold"])
        if souls < sigil.cost_souls:
            await interaction.response.send_message(f"Need {currency_label('gold')} **{sigil.cost_souls:,}**, you have **{souls:,}**.", ephemeral=True)
            return

        await award_currency(db, interaction.user.id, gold=-sigil.cost_souls)
        await activate_buff(db, interaction.user.id, sigil.key, "sigil", sigil.charges)
        self.sigil_select.disabled = True
        await interaction.response.edit_message(
            embed=status_embed(f"{buff_label(sigil.key, sigil.name)} Activated", f"Active for **{sigil.charges}** hunts.\n+{sigil.extra_monsters} extra monster{'s' if sigil.extra_monsters != 1 else ''} per hunt."),
            view=self,
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id


class CharmActivateView(discord.ui.View):
    def __init__(self, ctx: commands.Context, player) -> None:
        super().__init__(timeout=60)
        self.ctx = ctx
        self.player = player

    @discord.ui.select(
        placeholder="🔮 Select a charm to activate...",
        options=[
            discord.SelectOption(
                label=c.name,
                value=c.key,
                description=f"+{c.extra_monsters}/hunt, +{int(c.rarity_bonus*100)}% rarity, {c.charges} hunts",
                emoji="🔮",
            )
            for c in CHARMS
        ],
    )
    async def charm_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        charm_key = select.values[0]
        charm = next(c for c in CHARMS if c.key == charm_key)
        souls = int(self.player["gold"])
        if souls < charm.cost_souls:
            await interaction.response.send_message(f"Need {currency_label('gold')} **{charm.cost_souls:,}**, you have **{souls:,}**.", ephemeral=True)
            return

        db = interaction.client.db
        await award_currency(db, interaction.user.id, gold=-charm.cost_souls)
        await activate_buff(db, interaction.user.id, charm.key, "charm", charm.charges)
        self.charm_select.disabled = True
        await interaction.response.edit_message(
            embed=status_embed(f"{buff_label(charm.key, charm.name)} Activated", f"Active for **{charm.charges}** hunts.\n+{charm.extra_monsters} extra monsters per hunt.\n+{int(charm.rarity_bonus * 100)}% improved rare monster odds."),
            view=self,
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id


class Buffs(commands.Cog):
    """Temporary hunting buffs — sigils and charms."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="sigils")
    async def sigils_list(self, ctx: commands.Context) -> None:
        """View and activate Blood Sigils (extra monsters per hunt)."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        active = await get_active_buffs(self.bot.db, ctx.author.id)

        image = render_buffs_card(ctx.author.display_name, "sigils", list(SIGILS), active)
        file = discord.File(image, filename="abyssia_sigils.png")
        view = SigilActivateView(ctx, player, SIGILS)
        await ctx.reply(file=file, view=view, mention_author=False)

    @commands.hybrid_command(name="charms")
    async def charms_list(self, ctx: commands.Context) -> None:
        """View and activate Void Charms (better rare monster odds)."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        active = await get_active_buffs(self.bot.db, ctx.author.id)

        image = render_buffs_card(ctx.author.display_name, "charms", list(CHARMS), active)
        file = discord.File(image, filename="abyssia_charms.png")
        view = CharmActivateView(ctx, player)
        await ctx.reply(file=file, view=view, mention_author=False)

    @commands.hybrid_command(name="sigil")
    async def sigil_activate(self, ctx: commands.Context, sigil_key: str) -> None:
        """Activate a Blood Sigil. Use b sigils to see available sigils."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)

        sigil = next((s for s in SIGILS if s.key == sigil_key), None)
        if not sigil:
            keys = ", ".join(s.key for s in SIGILS)
            raise commands.BadArgument(f"Unknown sigil. Choose: {keys}")

        souls = int(player["gold"])
        if souls < sigil.cost_souls:
            raise commands.BadArgument(f"Need {currency_label('gold')} **{sigil.cost_souls:,}**, you have **{souls:,}**.")

        await award_currency(self.bot.db, ctx.author.id, gold=-sigil.cost_souls)
        await activate_buff(self.bot.db, ctx.author.id, sigil.key, "sigil", sigil.charges)

        await ctx.reply(
            embed=status_embed(
                f"{buff_label(sigil.key, sigil.name)} Activated",
                f"Active for **{sigil.charges}** hunts.\n+{sigil.extra_monsters} extra monster{'s' if sigil.extra_monsters != 1 else ''} per hunt.",
            ),
            mention_author=False,
        )

    @commands.hybrid_command(name="charm")
    async def charm_activate(self, ctx: commands.Context, charm_key: str) -> None:
        """Activate a Void Charm. Use b charms to see available charms."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)

        charm = next((c for c in CHARMS if c.key == charm_key), None)
        if not charm:
            keys = ", ".join(c.key for c in CHARMS)
            raise commands.BadArgument(f"Unknown charm. Choose: {keys}")

        souls = int(player["gold"])
        if souls < charm.cost_souls:
            raise commands.BadArgument(f"Need {currency_label('gold')} **{charm.cost_souls:,}**, you have **{souls:,}**.")

        await award_currency(self.bot.db, ctx.author.id, gold=-charm.cost_souls)
        await activate_buff(self.bot.db, ctx.author.id, charm.key, "charm", charm.charges)

        await ctx.reply(
            embed=status_embed(
                f"{buff_label(charm.key, charm.name)} Activated",
                f"Active for **{charm.charges}** hunts.\n+{charm.extra_monsters} extra monsters per hunt.\n+{int(charm.rarity_bonus * 100)}% improved rare monster odds.",
            ),
            mention_author=False,
        )

    @commands.hybrid_command(name="buffs", aliases=["active"])
    async def active_buffs(self, ctx: commands.Context) -> None:
        """Show your active sigils and charms."""
        assert ctx.guild is not None
        await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        active = await get_active_buffs(self.bot.db, ctx.author.id)

        if not active:
            raise commands.BadArgument("No active buffs. Use `b sigils` or `b charms` to activate one.")

        lines = []
        for key, charges in active.items():
            sigil = next((s for s in SIGILS if s.key == key), None)
            charm = next((c for c in CHARMS if c.key == key), None)
            item = sigil or charm
            if item:
                effect = f"+{sigil.extra_monsters} monster/hunt" if sigil else f"+{charm.extra_monsters} monster/hunt, +{int(charm.rarity_bonus * 100)}% rarity"
                lines.append(f"{buff_label(key, item.name)} - {effect} - `{charges}` left")

        embed = dark_embed("Active Buffs", "\n".join(lines))
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Buffs(bot))
