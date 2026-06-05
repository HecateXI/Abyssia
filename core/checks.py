import discord
from discord.ext import commands

from core.theme import status_embed


def is_staff():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return False
        perms = ctx.author.guild_permissions
        return perms.manage_guild or perms.administrator or perms.moderate_members

    return commands.check(predicate)


def has_boosted(member: discord.Member) -> bool:
    return member.premium_since is not None


async def send_ok(ctx: commands.Context, message: str) -> None:
    await ctx.reply(embed=status_embed("Done", message), mention_author=False)
