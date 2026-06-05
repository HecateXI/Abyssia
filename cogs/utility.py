import logging
import traceback

import discord
from discord.ext import commands

from core.theme import GOLD_COLOR, dark_embed, status_embed, ui_label

log = logging.getLogger(__name__)


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command()
    async def ping(self, ctx: commands.Context) -> None:
        """Show bot latency."""
        await ctx.reply(embed=status_embed("Pong", f"`{round(self.bot.latency * 1000)}ms`"), mention_author=False)

    # @commands.hybrid_command(aliases=["zzhelp", "commands", "guidebook"])
    # async def help(self, ctx: commands.Context, category: str | None = None) -> None:
    #     """Show command list."""
    #     prefix = "!"
    #     if ctx.guild is not None:
    #         prefix = await self.bot.db.get_setting(ctx.guild.id, "prefix") or prefix
    #     pages = {
    #         "start": (
    #             ui_label("profile", "Start"),
    #             f"`{prefix}start [name]`\n`{prefix}tutorial`\n`{prefix}profile [@member]`\n`{prefix}stats`\n`{prefix}stats allocate <stat> [points]`",
    #         ),
    #         "hunt": (
    #             ui_label("hunt", "Hunting"),
    #             f"`{prefix}hunt [amount] [zone]` - free pack hunt, extra rolls spend Hunt Swords\n"
    #             f"`{prefix}h [amount] [zone]` - short alias\n"
    #             f"`{prefix}explore [zone]`\n`{prefix}zones`\n"
    #             f"`{prefix}autohunt start <1|4|8|12|24> [zone]`\n`{prefix}autohunt claim`",
    #         ),
    #         "collection": (
    #             ui_label("inventory", "Collection"),
    #             f"`{prefix}monsters [@member]`\n`{prefix}bestiary [@member]`\n`{prefix}summon [1|5|10]`\n"
    #             f"`{prefix}inventory`\n`{prefix}equipment`\n`{prefix}inspect <item>`",
    #         ),
    #         "craft": (
    #             ui_label("crafting", "Crafting"),
    #             f"`{prefix}recipes`\n`{prefix}craft <item>`\n`{prefix}equip <item>`\n"
    #             "Weapons and charms modify catch rates, rarity odds, autohunt speed, and battle stats.",
    #         ),
    #         "economy": (
    #             ui_label("marketplace", "Economy"),
    #             f"`{prefix}daily` - Souls, gems, and Hunt Swords\n`{prefix}shop`\n`{prefix}shop buy <item> [qty]`\n"
    #             f"`{prefix}sell <item|monster_id> [qty]`\n`{prefix}market`\n"
    #             f"`{prefix}market sell <type> <item> <qty> <souls>`\n`{prefix}market buy <listing_id>`\n`{prefix}trade @user ...`",
    #         ),
    #         "battle": (
    #             ui_label("battle", "Battle"),
    #             f"`{prefix}team`\n`{prefix}team set <slot> <monster_id>`\n`{prefix}team clear`\n"
    #             f"`{prefix}battle @user` - animated turn battle\n`{prefix}duel @user`\n"
    #             f"`{prefix}arena`\n`{prefix}leaderboard [rating|level|souls|gems|hunts]`",
    #         ),
    #         "boss": (
    #             ui_label("boss_raid", "Bosses"),
    #             f"`{prefix}boss`\n`{prefix}boss awaken`\n`{prefix}boss attack`\n"
    #             f"`{prefix}raid`\n`{prefix}raid awaken`\n`{prefix}raid attack`",
    #         ),
    #         "staff": (
    #             "Staff",
    #             f"`{prefix}kick`, `{prefix}ban`, `{prefix}unban`, `{prefix}timeout`, `{prefix}untimeout`\n"
    #             f"`{prefix}purge`, `{prefix}slowmode`\n`{prefix}config prefix <prefix>`\n"
    #             f"`{prefix}config modlog [#channel]`\n`{prefix}config welcome [#channel]`\n"
    #             f"`{prefix}booster create <name> [#hex]`",
    #         ),
    #     }
    #     key = (category or "").lower().strip()
    #     if key in {"", "all", "menu"}:
    #         embed = dark_embed(
    #             "Abyssia Help",
    #             f"Use `{prefix}help <category>` for a focused page.\n"
    #             f"Categories: `start`, `hunt`, `collection`, `craft`, `economy`, `battle`, `boss`, `staff`.",
    #             color=GOLD_COLOR,
    #         )
    #         embed.add_field(name="Core Loop", value=f"`{prefix}daily` -> `{prefix}hunt 6` -> `{prefix}monsters` -> `{prefix}team` -> `{prefix}battle @user`", inline=False)
    #         for page_key in ["hunt", "collection", "economy", "battle"]:
    #             title, body = pages[page_key]
    #             embed.add_field(name=title, value=body.split("\n")[0], inline=True)
    #     elif key in pages:
    #         title, body = pages[key]
    #         embed = dark_embed(f"Abyssia Help: {title}", body, color=GOLD_COLOR)
    #         embed.set_footer(text=f"Use {prefix}help to return to the command hub.")
    #     else:
    #         raise commands.BadArgument("Unknown help category. Try `hunt`, `battle`, `economy`, `collection`, `craft`, `boss`, or `staff`.")
    #     await ctx.reply(embed=embed, mention_author=False)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.HybridCommandError):
            error = error.original
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.MissingPermissions):
            message = "You do not have permission to use that command."
        elif isinstance(error, commands.BotMissingPermissions):
            message = f"I am missing permissions: {', '.join(error.missing_permissions)}"
        elif isinstance(error, commands.BadArgument):
            message = str(error)
        elif isinstance(error, commands.MissingRequiredArgument):
            message = f"Missing required argument: `{error.param.name}`"
        elif isinstance(error, commands.CheckFailure) and str(error) == "duplicate-invocation":
            return
        elif isinstance(error, commands.CheckFailure):
            message = "You cannot use that command here."
        else:
            message = f"Unexpected error: `{type(error).__name__}: {error}`"
        log.error("Command error in %s: %s", ctx.command, traceback.format_exception(type(error), error, error.__traceback__))
        await ctx.reply(embed=status_embed("Command Error", message, color=discord.Color.dark_red()), mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
