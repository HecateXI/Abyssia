import logging
import traceback

import discord
from discord.ext import commands

from core.theme import status_embed

log = logging.getLogger(__name__)


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command()
    async def ping(self, ctx: commands.Context) -> None:
        """Show bot latency."""
        await ctx.reply(embed=status_embed("Pong", f"`{round(self.bot.latency * 1000)}ms`"), mention_author=False)

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
