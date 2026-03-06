import asyncio
import os
from pathlib import Path
from typing import List

import discord
from discord.ext import commands

from keep_alive import keep_alive

DEFAULT_PREFIX = "!"
PHASE_ONE_COGS: List[str] = [
    "cogs.prefix",
    "cogs.help",
    "cogs.bot_status",
    "cogs.moderation",
    "cogs.security",
]


def build_prefix_callable(default_prefix: str = DEFAULT_PREFIX):
    async def _get_prefix(bot: commands.Bot, message: discord.Message):
        base = commands.when_mentioned(bot, message)
        guild_id = message.guild.id if message.guild else None
        custom = bot.custom_prefixes.get(guild_id, default_prefix)

        # Allow approved users to run commands without typing a prefix.
        if message.author.id in bot.no_prefix_users:
            return base + ["", custom]

        return base + [custom]

    return _get_prefix


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True



def discover_cogs() -> List[str]:
    cog_dir = Path(__file__).parent / "cogs"
    discovered = []
    for path in sorted(cog_dir.glob("*.py")):
        if path.stem.startswith("_"):
            continue
        if path.stem == "__init__":
            continue
        discovered.append(f"cogs.{path.stem}")
    return discovered


COGS_TO_LOAD: List[str] = discover_cogs()


def build_prefix_callable(default_prefix: str = DEFAULT_PREFIX):
    async def _get_prefix(bot: commands.Bot, message: discord.Message):
        base = commands.when_mentioned(bot, message)
        guild_id = message.guild.id if message.guild else None
        custom = bot.custom_prefixes.get(guild_id, default_prefix)

        # Allow approved users to run commands without typing a prefix.
        if message.author.id in bot.no_prefix_users:
            return base + ["", custom]

        return base + [custom]

    return _get_prefix


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=build_prefix_callable(DEFAULT_PREFIX),
    intents=intents,
    help_command=None,
    case_insensitive=True,
)

# Shared stores (in-memory for Phase 1)
bot.custom_prefixes = {}  # guild_id -> prefix
bot.no_prefix_users = set()  # user_id set
bot.BOT_OWNER_ID = None
bot.DEFAULT_PREFIX = DEFAULT_PREFIX


@bot.event
async def on_ready():
    app_info = await bot.application_info()
    bot.BOT_OWNER_ID = app_info.owner.id
    bot.owner_id = app_info.owner.id

    print("\n🍀 Lucky Bot is online")
    print(f"👤 Bot User: {bot.user} ({bot.user.id})")
    print(f"👑 Owner ID: {bot.BOT_OWNER_ID}")
    print(f"🏠 Guilds: {len(bot.guilds)}")
    print(f"🧩 Loaded Cogs: {', '.join(bot.cogs.keys()) or 'None'}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as exc:
        print(f"❌ Slash sync failed: {exc}")

    # Guild sync makes slash commands show up quickly in joined servers.
    guild_sync_ok = 0
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            guild_synced = await bot.tree.sync(guild=guild)
            guild_sync_ok += 1
            print(f"✅ Synced {len(guild_synced)} guild command(s) to {guild.name} ({guild.id})")
        except Exception as exc:
            print(f"❌ Guild slash sync failed for {guild.name} ({guild.id}): {exc}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} global slash command(s)")
    except Exception as exc:
        print(f"❌ Global slash sync failed: {exc}")

    if bot.guilds and guild_sync_ok == 0:
        print("⚠️ No guild command sync succeeded; slash commands may not appear immediately.")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="⚠️ Missing Argument",
            description=f"You missed: `{error.param.name}`",
            color=discord.Color.orange(),
        )
        await ctx.reply(embed=embed)
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.reply(
            embed=discord.Embed(
                title="❌ Server Only",
                description="This command can only be used inside a server.",
                color=discord.Color.red(),
            )
        )
        return

    await ctx.reply(
        embed=discord.Embed(
            title="❌ Command Error",
            description=f"`{error}`",
            color=discord.Color.red(),
        )
    )


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing in environment variables.")

    keep_alive()

    async with bot:
        for ext in PHASE_ONE_COGS:
        for ext in COGS_TO_LOAD:
            try:
                await bot.load_extension(ext)
                print(f"✅ Loaded extension: {ext}")
            except Exception as exc:
                print(f"❌ Failed to load {ext}: {exc}")

        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
