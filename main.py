import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Lucky Bot is alive! 🍀"

Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} is online!')
    await bot.change_presence(activity=discord.Game(name="!help | Lucky Bot 🍀"))

@bot.command()
async def ping(ctx):
    await ctx.reply(f'🏓 Pong! `{round(bot.latency * 1000)}ms`')

async def main():
    async with bot:
        await bot.load_extension('cogs.moderation')
        await bot.start(os.environ['DISCORD_TOKEN'])

import asyncio
asyncio.run(main())
