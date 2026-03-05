# ================================================
#   LUCKY BOT — All-in-One Discord Bot
#   Built for lucky.unaux.com
# ================================================

import discord
from discord.ext import commands
import os
import asyncio
from keep_alive import keep_alive

# ── Bot Setup ──────────────────────────────────
intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None,
    case_insensitive=True,
    owner_ids={} # We'll add your Discord user ID here later
)

# ── All feature modules ────────────────────────
COGS = [
    'cogs.moderation',
    'cogs.security',
    'cogs.tickets',
    'cogs.music',
    'cogs.games',
    'cogs.utility',
    'cogs.fun',
    'cogs.economy',
    'cogs.leveling',
    'cogs.logging_cog',
    'cogs.automod',
    'cogs.welcome',
    'cogs.giveaway',
]

# ── Bot Ready Event ────────────────────────────
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'')
    print(f'  ✅  {bot.user.name} is ONLINE')
    print(f'  🌐  Dashboard: https://lucky.unaux.com')
    print(f'  🤖  Servers: {len(bot.guilds)}')
    print(f'')
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the server 👁️ | !help"
        )
    )

# ── Global Error Handler ───────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply('❌ You don\'t have permission to use that command!')
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.reply('❌ I don\'t have permission to do that! Give me the right roles.')
    elif isinstance(error, commands.MemberNotFound):
        await ctx.reply('❌ I couldn\'t find that member!')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f'❌ You\'re missing something! Use `!help {ctx.command}` to see how.')
    elif isinstance(error, commands.CommandNotFound):
        pass  # Silently ignore unknown commands
    else:
        print(f'Error in {ctx.command}: {error}')

# ── Help Command ───────────────────────────────
@bot.command(name='help')
async def help_cmd(ctx, category: str = None):
    if category is None:
        embed = discord.Embed(
            title='🍀 Lucky Bot — Command Menu',
            description='Your all-in-one Discord companion!\nUse `!help <category>` for details.',
            color=0x2ecc71
        )
        embed.add_field(name='🛡️ Moderation', value='`!help mod`', inline=True)
        embed.add_field(name='🔒 Security', value='`!help security`', inline=True)
        embed.add_field(name='🎫 Tickets', value='`!help tickets`', inline=True)
        embed.add_field(name='🎵 Music', value='`!help music`', inline=True)
        embed.add_field(name='🎮 Games', value='`!help games`', inline=True)
        embed.add_field(name='🔧 Utility', value='`!help utility`', inline=True)
        embed.add_field(name='😂 Fun', value='`!help fun`', inline=True)
        embed.add_field(name='💰 Economy', value='`!help economy`', inline=True)
        embed.add_field(name='⭐ Leveling', value='`!help level`', inline=True)
        embed.add_field(name='📋 Logging', value='`!help log`', inline=True)
        embed.add_field(name='🤖 Auto-Mod', value='`!help automod`', inline=True)
        embed.add_field(name='🎁 Giveaway', value='`!help giveaway`', inline=True)
        embed.set_footer(text='Lucky Bot • lucky.unaux.com')
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        await ctx.send(embed=embed)

# ── Load everything and start ──────────────────
async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f'  ✅  Loaded: {cog}')
            except Exception as e:
                print(f'  ❌  Failed: {cog} → {e}')
        keep_alive()
        await bot.start(os.environ['DISCORD_TOKEN'])

asyncio.run(main())
