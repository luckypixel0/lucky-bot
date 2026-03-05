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
# ══════════════════════════════════════════════

# guild_id: custom prefix
custom_prefixes = {}

# user_ids who can use NO prefix (set by owner)
no_prefix_users = set()

# guild_id: owner's Discord user ID
# We store bot owner separately
BOT_OWNER_ID = None  # will be set on_ready

async def get_prefix(bot, message):
    """
    Dynamic prefix system:
    - No prefix users: command works with or without prefix
    - Custom prefix: per server
    - Default: !
    """
    # Always allow mentions as prefix
    base = commands.when_mentioned(bot, message)

    # No-prefix users — commands work without any prefix
    if message.author.id in no_prefix_users:
        # Return empty string so everything works without prefix
        return base + ['', custom_prefixes.get(message.guild.id if message.guild else None, '!')]

    # Custom prefix for this server
    prefix = custom_prefixes.get(message.guild.id if message.guild else None, '!')
    return base + [prefix]

# ── Bot Setup ──────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# Store these on bot so cogs can access them
bot.custom_prefixes = custom_prefixes
bot.no_prefix_users = no_prefix_users

# ══════════════════════════════════════════════
#   ALL COGS
# ══════════════════════════════════════════════

COGS = [
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
    global BOT_OWNER_ID
    app_info = await bot.application_info()
    BOT_OWNER_ID = app_info.owner.id
    bot.owner_id = BOT_OWNER_ID

    print(f'')
    print(f'  ✅  {bot.user.name} is ONLINE')
    print(f'  👑  Owner ID: {BOT_OWNER_ID}')
    print(f'  📡  Servers: {len(bot.guilds)}')
    print(f'  🧩  Cogs: {len(bot.cogs)}')
    print(f'')

    try:
        synced = await bot.tree.sync()
        print(f'  ✅  Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'  ❌  Slash sync failed: {e}')

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the server 👁️ | !help"
        )
    )

# ══════════════════════════════════════════════
#   BUILT-IN COMMANDS (prefix + slash)
# ══════════════════════════════════════════════

# ── PING ──────────────────────────────────────
@bot.command(name='ping')
async def ping_prefix(ctx):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: `{round(bot.latency * 1000)}ms`",
        color=0x2ecc71
    )
    await ctx.reply(embed=embed)

@bot.tree.command(name='ping', description='Check bot latency')
async def ping_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: `{round(bot.latency * 1000)}ms`",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed)

# ── SET PREFIX ────────────────────────────────
@bot.command(name='setprefix')
async def setprefix_prefix(ctx, new_prefix: str):
    # Only server owner or bot owner
    if ctx.author.id != ctx.guild.owner_id and ctx.author.id != BOT_OWNER_ID:
        embed = discord.Embed(
            title="❌ No Permission",
            description="Only the **server owner** can change the prefix!",
            color=0xe74c3c
        )
        return await ctx.reply(embed=embed)
    if len(new_prefix) > 5:
        embed = discord.Embed(
            title="❌ Too Long",
            description="Prefix must be **5 characters or less**!",
            color=0xe74c3c
        )
        return await ctx.reply(embed=embed)
    custom_prefixes[ctx.guild.id] = new_prefix
    bot.custom_prefixes = custom_prefixes
    embed = discord.Embed(
        title="✅ Prefix Updated",
        description=f"New prefix: `{new_prefix}`\nExample: `{new_prefix}ping`",
        color=0x2ecc71
    )
    embed.set_footer(text="Lucky Bot")
    await ctx.reply(embed=embed)

@bot.tree.command(name='setprefix', description='Change the bot prefix for this server')
async def setprefix_slash(interaction: discord.Interaction, prefix: str):
    if interaction.user.id != interaction.guild.owner_id and interaction.user.id != BOT_OWNER_ID:
        embed = discord.Embed(
            title="❌ No Permission",
            description="Only the **server owner** can change the prefix!",
            color=0xe74c3c
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    if len(prefix) > 5:
        return await interaction.response.send_message("❌ Prefix must be 5 characters or less!", ephemeral=True)
    custom_prefixes[interaction.guild.id] = prefix
    embed = discord.Embed(
        title="✅ Prefix Updated",
        description=f"New prefix: `{prefix}`\nExample: `{prefix}ping`",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed)

# ── NO PREFIX ─────────────────────────────────
@bot.command(name='noprefix')
async def noprefix_prefix(ctx, action: str, member: discord.Member = None):
    """
    Grant/revoke no-prefix mode.
    Only bot owner can use this.
    Usage: !noprefix add @user
           !noprefix remove @user
           !noprefix list
    """
    if ctx.author.id != BOT_OWNER_ID:
        embed = discord.Embed(
            title="❌ Bot Owner Only",
            description="Only the **bot owner** (you, the creator of Lucky Bot) can grant no-prefix access!",
            color=0xe74c3c
        )
        return await ctx.reply(embed=embed)

    if action == 'add':
        if not member:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Missing Member",
                description="Usage: `!noprefix add @user`",
                color=0xe74c3c
            ))
        no_prefix_users.add(member.id)
        bot.no_prefix_users = no_prefix_users
        embed = discord.Embed(
            title="✅ No-Prefix Granted",
            description=(
                f"{member.mention} can now use all commands **without any prefix**!\n"
                f"They can type `ping` instead of `!ping` etc."
            ),
            color=0x2ecc71
        )
        await ctx.reply(embed=embed)

    elif action == 'remove':
        if not member:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Missing Member",
                description="Usage: `!noprefix remove @user`",
                color=0xe74c3c
            ))
        no_prefix_users.discard(member.id)
        bot.no_prefix_users = no_prefix_users
        embed = discord.Embed(
            title="✅ No-Prefix Revoked",
            description=f"{member.mention} now needs to use the prefix again.",
            color=0x2ecc71
        )
        await ctx.reply(embed=embed)

    elif action == 'list':
        if not no_prefix_users:
            return await ctx.reply(embed=discord.Embed(
                title="📋 No-Prefix Users",
                description="No users have no-prefix access yet.",
                color=0x3498db
            ))
        mentions = [f"<@{uid}>" for uid in no_prefix_users]
        embed = discord.Embed(
            title="📋 No-Prefix Users",
            description="\n".join(mentions),
            color=0x3498db
        )
        await ctx.reply(embed=embed)

    else:
        embed = discord.Embed(
            title="❌ Invalid Action",
            description="Usage:\n`!noprefix add @user`\n`!noprefix remove @user`\n`!noprefix list`",
            color=0xe74c3c
        )
        await ctx.reply(embed=embed)

@bot.tree.command(name='noprefix', description='Grant/revoke no-prefix mode (bot owner only)')
async def noprefix_slash(
    interaction: discord.Interaction,
    action: str,
    member: discord.Member = None
):
    if interaction.user.id != BOT_OWNER_ID:
        return await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Bot Owner Only",
                description="Only the **bot owner** can grant no-prefix access!",
                color=0xe74c3c
            ),
            ephemeral=True
        )
    if action == 'add' and member:
        no_prefix_users.add(member.id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ No-Prefix Granted",
                description=f"{member.mention} can now use commands without prefix!",
                color=0x2ecc71
            )
        )
    elif action == 'remove' and member:
        no_prefix_users.discard(member.id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ No-Prefix Revoked",
                description=f"{member.mention} needs prefix again.",
                color=0x2ecc71
            )
        )
    elif action == 'list':
        mentions = [f"<@{uid}>" for uid in no_prefix_users] or ["None"]
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📋 No-Prefix Users",
                description="\n".join(mentions),
                color=0x3498db
            )
        )

# ── PREFIX INFO ───────────────────────────────
@bot.command(name='prefix')
async def prefix_cmd(ctx):
    """Show current prefix. Usage: !prefix"""
    current = custom_prefixes.get(ctx.guild.id if ctx.guild else None, '!')
    embed = discord.Embed(
        title="⚙️ Current Prefix",
        color=0x3498db
    )
    embed.add_field(name="Prefix", value=f"`{current}`")
    embed.add_field(name="Example", value=f"`{current}ping`")
    embed.add_field(
        name="Change it",
        value=f"`{current}setprefix <new>` — server owner only",
        inline=False
    )
    embed.set_footer(text="Lucky Bot")
    await ctx.reply(embed=embed)

@bot.tree.command(name='prefix', description='Show current bot prefix')
async def prefix_slash(interaction: discord.Interaction):
    current = custom_prefixes.get(interaction.guild.id if interaction.guild else None, '!')
    embed = discord.Embed(title="⚙️ Current Prefix", color=0x3498db)
    embed.add_field(name="Prefix", value=f"`{current}`")
    embed.add_field(name="Example", value=f"`{current}ping`")
    await interaction.response.send_message(embed=embed)

# ── HELP ──────────────────────────────────────
@bot.command(name='help')
async def help_prefix(ctx, category: str = None):
    prefix = custom_prefixes.get(ctx.guild.id if ctx.guild else None, '!')
    embed = discord.Embed(
        title="🍀 Lucky Bot — Command Menu",
        description=f"Current prefix: `{prefix}` | Also works with `/`",
        color=0x2ecc71
    )
    embed.add_field(name="🛡️ Moderation", value=f"`{prefix}help mod`", inline=True)
    embed.add_field(name="🔒 Security", value=f"`{prefix}help security`", inline=True)
    embed.add_field(name="🎫 Tickets", value=f"`{prefix}help tickets`", inline=True)
    embed.add_field(name="🎵 Music", value=f"`{prefix}help music`", inline=True)
    embed.add_field(name="🎮 Games", value=f"`{prefix}help games`", inline=True)
    embed.add_field(name="😂 Fun", value=f"`{prefix}help fun`", inline=True)
    embed.add_field(name="💰 Economy", value=f"`{prefix}help economy`", inline=True)
    embed.add_field(name="⭐ Leveling", value=f"`{prefix}help level`", inline=True)
    embed.add_field(name="🎁 Giveaway", value=f"`{prefix}help giveaway`", inline=True)
    embed.add_field(
        name="⚙️ Settings",
        value=(
            f"`{prefix}setprefix` — change prefix\n"
            f"`{prefix}noprefix` — no-prefix mode\n"
            f"`{prefix}extraowner` — extra owners"
        ),
        inline=False
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text="Lucky Bot • lucky.unaux.com")
    await ctx.send(embed=embed)

@bot.tree.command(name='help', description='Show all Lucky Bot commands')
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🍀 Lucky Bot — Command Menu",
        description="Use `/` or `!` for all commands",
        color=0x2ecc71
    )
    embed.add_field(name="🛡️ Moderation", value="warn, mute, ban, kick, purge...", inline=True)
    embed.add_field(name="🔒 Security", value="antinuke, antiraid, antispam...", inline=True)
    embed.add_field(name="🎫 Tickets", value="ticket, close, add, remove...", inline=True)
    embed.add_field(name="🎵 Music", value="play, skip, queue, pause...", inline=True)
    embed.add_field(name="🎮 Games", value="trivia, slots, rps...", inline=True)
    embed.add_field(name="😂 Fun", value="meme, 8ball, roast...", inline=True)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text="Lucky Bot • lucky.unaux.com")
    await interaction.response.send_message(embed=embed)

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
