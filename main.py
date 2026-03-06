import discord
from discord.ext import commands
import os
import asyncio
from flask import Flask
from threading import Thread

# ── Keep Alive ─────────────────────────────────
app = Flask('')

@app.route('/')
def home():
    return "Lucky Bot is alive! 🍀"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

# ══════════════════════════════════════════════
#   PREFIX SYSTEM
#   (commands are in cogs/prefix.py)
# ══════════════════════════════════════════════

async def get_prefix(bot, message):
    base = commands.when_mentioned(bot, message)
    if message.author.id in bot.no_prefix_users:
        return base + ['', bot.custom_prefixes.get(
            message.guild.id if message.guild else None, '!')]
    prefix = bot.custom_prefixes.get(
        message.guild.id if message.guild else None, '!')
    return base + [prefix]

# ══════════════════════════════════════════════
#   BOT SETUP
# ══════════════════════════════════════════════

intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# Shared data stores — accessible from all cogs via bot.*
bot.custom_prefixes = {}     # guild_id: prefix string
bot.no_prefix_users = set()  # user_ids with no-prefix access
bot.BOT_OWNER_ID = None      # set on_ready

# ══════════════════════════════════════════════
#   COGS
# ══════════════════════════════════════════════

COGS = [
    'cogs.help',
    'cogs.prefix',
    'cogs.bot_status',
    'cogs.moderation',
    'cogs.security',
    # 'cogs.tickets',
    # 'cogs.music',
    # 'cogs.games',
    # 'cogs.fun',
    # 'cogs.economy',
    # 'cogs.leveling',
    # 'cogs.welcome',
    # 'cogs.automod',
    # 'cogs.giveaway',
]

# ══════════════════════════════════════════════
#   EVENTS
# ══════════════════════════════════════════════

@bot.event
async def on_ready():
    app_info = await bot.application_info()
    bot.BOT_OWNER_ID = app_info.owner.id
    bot.owner_id = bot.BOT_OWNER_ID

    print(f'')
    print(f'  ✅  {bot.user.name} is ONLINE')
    print(f'  👑  Owner ID: {bot.BOT_OWNER_ID}')
    print(f'  📡  Servers: {len(bot.guilds)}')
    print(f'  🧩  Cogs: {len(bot.cogs)}')
    print(f'')

    try:
        synced = await bot.tree.sync()
        print(f'  ✅  Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'  ❌  Slash sync failed: {e}')

# ══════════════════════════════════════════════
#   LOAD COGS AND START
# ══════════════════════════════════════════════

async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f'  ✅  Loaded: {cog}')
            except Exception as e:
                print(f'  ❌  Failed: {cog} → {e}')
        await bot.start(os.environ['DISCORD_TOKEN'])

asyncio.run(main())
