from __future__ import annotations

import discord
from discord.ext import commands

from core.progression import get_current_stage
from core.rpg import ensure_player
from core.theme import GOLD_COLOR, BLOOD_COLOR, dark_embed, status_embed, ui_label


CATEGORIES = [
    {
        "key": "hunting",
        "emoji": "🔍",
        "name": "Hunting",
        "desc": "Hunt creatures, earn XP, and progress your daily checklist",
        "commands": [
            ("`b hunt`", "Hunt for creatures. Your current team also gains XP"),
            ("`b use` or `b use sword`", "Activate a Hunt Sword for +1 roll per hunt (20 min)"),
            ("`b sigils`", "Short active hunt boosts that add extra monster rolls"),
            ("`b charms`", "Short active hunt boosts that add monsters and improve rarity odds"),
            ("`b autohunt`", "Check your autohunt status"),
            ("`b autohunt start [h] [zone]`", "Start an autohunt (1, 4, 8, 12, or 24 hours)"),
            ("`b autohunt claim`", "Claim rewards from your completed autohunt"),
        ],
    },
    {
        "key": "collection",
        "emoji": "📚",
        "name": "Collection",
        "desc": "View your creatures, bestiary, and inventory",
        "commands": [
            ("`b profile [@user]`", "View your hunter profile and stats"),
            ("`b monsters`", "View all your caught monsters"),
            ("`b bestiary`", "List every species you've caught"),
            ("`b dex [name]`", "View detailed stats for any creature"),
            ("`b creature [id]`", "View detailed info on a specific creature you own"),
            ("`b inventory`", "View items with buttons to open crates and use Hunt Swords"),
            ("`b achievements`", "View unlocked achievements"),
        ],
    },
    {
        "key": "economy",
        "emoji": "💰",
        "name": "Economy",
        "desc": "Earn souls, sell creatures, and trade",
        "commands": [
            ("`b daily`", "Claim daily reward and progress your checklist"),
            ("`b checklist` / `b cl`", "View daily checklist progress and claim the completion reward"),
            ("`b sell [id] [qty]`", "Sell/release a creature for souls"),
            ("`b sellall [rarity]`", "Sell all duplicates of a rarity (keeps top 3)"),
            ("`b release [id]`", "Sell/release a single creature for souls"),
            ("`b market`", "Browse the player market"),
            ("`b market sell [type] [item] [qty] [souls]`", "List an item on the market"),
            ("`b trade @user`", "Offer a trade to another hunter"),
            ("`b quests`", "View legacy daily quest progress"),
            ("`b quests claim`", "Claim completed quest rewards"),
        ],
    },
    {
        "key": "weapons",
        "emoji": "⚔️",
        "name": "Weapons",
        "desc": "Equip weapons and manage your armory",
        "commands": [
            ("`b weapons`", "View your compact weapon list with IDs, icons, names, and quality"),
            ("`b weapons [id]`", "Inspect one weapon by ID"),
            ("`b weaponequip [id] [creature]`", "Equip a weapon to a creature"),
            ("`b weaponunequip [id]`", "Unequip a weapon from its creature"),
            ("`b wrr [id] stat`", "Reroll numeric stats, mana, affix values, and passive value"),
            ("`b wrr [id] passive`", "Reroll the passive type and passive value"),
            ("`b salvage [id|rarity|all]`", "Dismantle one weapon, a rarity, or all unequipped weapons into Weapon Shards"),
            ("`b shards`", "Check your Weapon Shard balance"),
            ("`b shardcrate [cache|relic|treasure]`", "Buy and open a weapon crate with Weapon Shards"),
            ("`b open [crate]`", "Open a crate you already own"),
            ("`b open`", "Open the owned-crate picker dropdown"),
            ("`b crateshop`", "Browse shard-priced weapon crates"),
        ],
        "extra": (
            "**Weapon loop:** Open crates -> keep strong rolls -> salvage weak weapons -> spend Weapon Shards on rerolls or shard crates.\n"
            "**Crate currency:** Weapon Shards only. Souls are not the weapon crate currency.\n"
            "**Stat reroll:** Keeps the weapon and passive type, rerolls numbers.\n"
            "**Passive reroll:** Keeps the weapon, rerolls the passive type and passive value.\n"
            "**Weapon IDs matter:** duplicate weapon types can have different quality, wear, stats, and passives."
        ),
    },
    {
        "key": "battle",
        "emoji": "⚡",
        "name": "Battle & Arena",
        "desc": "Fight other hunters and climb the ranks",
        "commands": [
            ("`b team`", "View your battle team"),
            ("`b team set [slot] [creature name]`", "Assign a creature to a team slot by name"),
            ("`b team clear`", "Remove all creatures from your team"),
            ("`b battle`", "Enter the global matchmaking queue"),
            ("`b revenge`", "Rematch against your last opponent"),
            ("`b history`", "View your recent battle history"),
            ("`b arena`", "Check your arena rating, rank, and streak"),
            ("`b leaderboard [cat]`", "View rankings (rating, streak, wins, level, souls)"),
        ],
    },
    {
        "key": "raids",
        "emoji": "👑",
        "name": "Raids & Bosses",
        "desc": "Fight server-wide bosses for big rewards",
        "commands": [
            ("`b raid`", "Show the active server raid"),
            ("`b raid awaken`", "Summon a raid boss"),
            ("`b raid attack`", "Attack the raid boss"),
            ("`b boss`", "Show the active server boss"),
            ("`b boss awaken`", "Summon a world boss"),
            ("`b boss attack`", "Attack the world boss"),
        ],
    },
    {
        "key": "trading",
        "emoji": "🤝",
        "name": "Trading",
        "desc": "Trade weapons, creatures, and currency with other hunters",
        "commands": [
            ("`b exchange @player`", "Initiate a trade with another player"),
            ("Add weapons, creatures, souls, or gems", "Both players confirm to complete the trade"),
        ],
    },
    {
        "key": "buffs",
        "emoji": "💎",
        "name": "Sigils & Charms",
        "desc": "Activate temporary hunting buffs for extra monsters and better odds",
        "commands": [
            ("`b sigils`", "View and activate Blood Sigils (extra monsters per hunt)"),
            ("`b sigil [key]`", "Activate a specific sigil"),
            ("`b charms`", "View and activate Void Charms (+2 to +8 monsters and improved rarity odds)"),
            ("`b charm [key]`", "Activate a specific charm"),
            ("`b buffs`", "View all active sigils and charms"),
        ],
    },
    {
        "key": "server",
        "emoji": "⚙️",
        "name": "Server & Moderation",
        "desc": "Server config, moderation, and utility",
        "commands": [
            ("`b config`", "View server configuration"),
            ("`b config prefix [prefix]`", "Change the bot's prefix"),
            ("`b config modlog [#channel]`", "Set the mod log channel"),
            ("`b config welcome [#channel]`", "Set the welcome message channel"),
            ("`b config booster-base [role]`", "Set the base booster role"),
            ("`b config setup-emojis [true]`", "Upload generated Application Emojis, including every creature icon"),
            ("`b config reload-emojis`", "Refresh cached Application Emoji IDs after portal uploads"),
            ("`b kick @user [reason]`", "Kick a member"),
            ("`b ban @user [reason]`", "Ban a member"),
            ("`b timeout @user [minutes] [reason]`", "Timeout a member"),
            ("`b purge [count]`", "Bulk delete messages"),
            ("`b slowmode [seconds]`", "Set channel slowmode"),
            ("`b booster create [name] [#color]`", "Create a custom booster role"),
            ("`b ping`", "Check bot latency"),
        ],
    },
]


def _cat_title(cat: dict) -> str:
    icon_key = {
        "hunting": "hunt",
        "collection": "profile",
        "economy": "marketplace",
        "weapons": "battle",
        "battle": "battle",
        "raids": "boss_raid",
        "trading": "marketplace",
        "buffs": "inventory",
        "server": "crafting",
    }.get(str(cat["key"]), "profile")
    return ui_label(icon_key, str(cat["name"]))


class HelpView(discord.ui.View):
    def __init__(self, ctx: commands.Context) -> None:
        super().__init__(timeout=180)
        self.ctx = ctx
        self._update_placeholder("home")

    def _update_placeholder(self, current: str) -> None:
        if current == "home":
            self.category_select.placeholder = "Select a category..."
        else:
            cat = next(c for c in CATEGORIES if c["key"] == current)
            self.category_select.placeholder = str(cat["name"])

    def _build_page(self, key: str) -> discord.Embed:
        if key == "home":
            return self._home_page()
        cat = next(c for c in CATEGORIES if c["key"] == key)
        return self._category_page(cat)

    def _home_page(self) -> discord.Embed:
        embed = discord.Embed(
            title="⬡ ABYSSIA COMMANDS",
            description="Pick a category from the dropdown below.\nPrefix works as `b`, `B`, or `b `.\nUse `b guide` for your personalized progression guide.",
            color=GOLD_COLOR,
        )
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar.url)

        half = len(CATEGORIES) // 2
        left = CATEGORIES[:half]
        right = CATEGORIES[half:]

        for cat in left:
            embed.add_field(
                name=_cat_title(cat),
                value=f"{cat['desc']}",
                inline=True,
            )
        embed.add_field(name="", value="", inline=True)
        for cat in right:
            embed.add_field(
                name=_cat_title(cat),
                value=f"{cat['desc']}",
                inline=True,
            )

        embed.set_footer(text="Select a category above to view commands")
        embed.color = GOLD_COLOR
        return embed

    def _category_page(self, cat: dict) -> discord.Embed:
        embed = discord.Embed(
            title=_cat_title(cat),
            description=cat["desc"],
            color=GOLD_COLOR,
        )
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar.url)

        for cmd, desc in cat["commands"]:
            embed.add_field(name=cmd, value=desc, inline=False)

        extra = cat.get("extra")
        if extra:
            embed.add_field(name="Details", value=str(extra)[:1024], inline=False)

        embed.set_footer(text="Use the dropdown to switch categories")
        return embed

    @discord.ui.select(
        placeholder="Select a category...",
        options=[
            discord.SelectOption(label="Home", value="home", emoji="🏠", description="Back to the main menu"),
            *[discord.SelectOption(label=cat["name"], value=cat["key"], emoji=cat["emoji"], description=cat["desc"]) for cat in CATEGORIES],
        ],
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        self._update_placeholder(select.values[0])
        await interaction.response.edit_message(embed=self._build_page(select.values[0]), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This is not your help menu.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass


class HelpGuide(commands.Cog):
    """Command reference and progression guide."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="help")
    async def help_command(self, ctx: commands.Context, *, category: str | None = None) -> None:
        """Browse all commands organized by category. Use b help <category> for details."""
        assert ctx.guild is not None
        prefix = "b"

        if category:
            cat_lower = category.lower().strip()
            cat = next((c for c in CATEGORIES if c["key"] == cat_lower or c["name"].lower() == cat_lower), None)
            if not cat:
                cats = ", ".join(c["key"] for c in CATEGORIES)
                raise commands.BadArgument(f"Unknown category. Try: {cats}")
            embed = discord.Embed(
                title=_cat_title(cat),
                description=cat["desc"],
                color=GOLD_COLOR,
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            for cmd, desc in cat["commands"]:
                embed.add_field(name=cmd, value=desc, inline=False)
            extra = cat.get("extra")
            if extra:
                embed.add_field(name="Details", value=str(extra)[:1024], inline=False)
            embed.set_footer(text=f"Use {prefix}help to return to the home page")
            await ctx.reply(embed=embed, mention_author=False)
            return

        page_keys = ["home"] + [c["key"] for c in CATEGORIES]
        view = HelpView(ctx)
        embed = view._build_page("home")
        msg = await ctx.reply(embed=embed, view=view, mention_author=False)
        view.message = msg

    @commands.hybrid_command(name="commands", aliases=["cmd", "cmds"])
    async def commands_list(self, ctx: commands.Context) -> None:
        """Show a compact list of all commands by category."""
        assert ctx.guild is not None
        embed = discord.Embed(
            title="ABYSSIA COMMANDS",
            description="Use `b help [category]` for detailed info.",
            color=GOLD_COLOR,
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        for cat in CATEGORIES:
            cmds = [cmd for cmd, _ in cat["commands"]]
            embed.add_field(
                name=_cat_title(cat),
                value=" ".join(cmds),
                inline=False,
            )

        embed.set_footer(text="Use b help for an interactive guide!")
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="guide")
    async def progression_guide(self, ctx: commands.Context) -> None:
        """View your personalized progression guide."""
        assert ctx.guild is not None
        player = await ensure_player(self.bot.db, ctx.author.id, ctx.author.display_name)
        stage = get_current_stage(player)

        embed = discord.Embed(
            title="⬡ ABYSSIA PROGRESSION GUIDE",
            description="",
            color=GOLD_COLOR,
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        embed.add_field(
            name="📍 Current Goal",
            value=f"**{stage.title}**\n{stage.goal}",
            inline=False,
        )

        steps_text = ""
        for step_name, step_desc in stage.steps:
            steps_text += f"✔ **{step_name}**\n   {step_desc}\n"
        embed.add_field(name="🎯 Recommended Steps", value=steps_text, inline=False)

        embed.add_field(
            name="➜ Next Action",
            value=f"**{stage.next_command}**",
            inline=False,
        )

        embed.add_field(
            name="🎁 Stage Reward",
            value=f"+{stage.reward_souls} Souls • +{stage.reward_gems} Gems",
            inline=False,
        )

        embed.set_footer(text="Complete steps to unlock next stage!")
        embed.color = BLOOD_COLOR
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpGuide(bot))
