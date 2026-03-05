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

# ── Bot Setup ──────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# ── All Cogs ───────────────────────────────────
# As we build new cogs, they are already listed here
# Comment out any that don't exist yet with #
COGS = [
    'cogs.moderation',
    'cogs.security',
    # 'cogs.tickets',    ← uncomment when we build it
    # 'cogs.music',
    # 'cogs.games',
    # 'cogs.fun',
    # 'cogs.economy',
    # 'cogs.leveling',
    # 'cogs.welcome',
    # 'cogs.automod',
    # 'cogs.giveaway',
]

# ── On Ready ───────────────────────────────────
@bot.event
async def on_ready():
    print(f'')
    print(f'  ✅  {bot.user.name} is ONLINE')
    print(f'  📡  Servers: {len(bot.guilds)}')
    print(f'  🧩  Cogs loaded: {len(bot.cogs)}')
    print(f'')
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the server 👁️ | !help"
        )
    )

#--ping---------------------------
@bot.command()    
async def ping(ctx):
    await ctx.reply(f'🏓pong! ahh micky dheere!!! `{round(bot.latency * 1000)}ms`')
    
# ── Load Cogs and Start ────────────────────────
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
