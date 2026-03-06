import discord
from discord.ext import commands
from discord import app_commands
import datetime

class BotStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_status = 'online'
        self.current_activity_type = 'watching'
        self.current_activity_text = 'over the server 👁️ | !help'

    def is_bot_owner(self, user_id):
        return user_id == self.bot.BOT_OWNER_ID

    # ══════════════════════════════════════════
    #   HELPERS
    # ══════════════════════════════════════════

    def get_status_obj(self, status_str):
        return {
            'online':    discord.Status.online,
            'idle':      discord.Status.idle,
            'dnd':       discord.Status.dnd,
            'invisible': discord.Status.invisible,
            'offline':   discord.Status.invisible,
        }.get(status_str.lower(), discord.Status.online)

    def get_activity_obj(self, activity_type, text):
        # ⚠️ Bots CANNOT use CustomActivity — Discord blocks it
        # Only these work for bots: playing, watching, listening, competing, streaming
        t = activity_type.lower()
        if t == 'playing':
            return discord.Game(name=text)
        elif t == 'listening':
            return discord.Activity(type=discord.ActivityType.listening, name=text)
        elif t == 'watching':
            return discord.Activity(type=discord.ActivityType.watching, name=text)
        elif t == 'competing':
            return discord.Activity(type=discord.ActivityType.competing, name=text)
        elif t == 'streaming':
            # Must be a real twitch or youtube URL
            return discord.Streaming(name=text, url='https://www.twitch.tv/lucky_bot')
        elif t == 'none':
            return None
        # Default fallback
        return discord.Activity(type=discord.ActivityType.watching, name=text)

    def status_emoji(self, status):
        return {
            'online': '🟢', 'idle': '🟡',
            'dnd': '🔴', 'invisible': '⚫', 'offline': '⚫'
        }.get(status, '🟢')

    # ══════════════════════════════════════════
    #   BOT STATUS OVERVIEW
    # ══════════════════════════════════════════

    @commands.command(name='botstatus')
    async def botstatus_prefix(self, ctx):
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only",
                description="Only the **bot creator** can manage bot status!",
                color=0xe74c3c
            ))
        await ctx.send(embed=self._build_status_overview())

    @app_commands.command(name='botstatus', description='Show current bot status settings')
    async def botstatus_slash(self, interaction: discord.Interaction):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        await interaction.response.send_message(embed=self._build_status_overview())

    def _build_status_overview(self):
        emoji = self.status_emoji(self.current_status)
        embed = discord.Embed(
            title="🤖 Bot Status Overview",
            color=0x3498db,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Bot Name",      value=self.bot.user.name)
        embed.add_field(name="Bot ID",        value=f"`{self.bot.user.id}`")
        embed.add_field(name="Status",        value=f"{emoji} `{self.current_status}`")
        embed.add_field(name="Activity Type", value=f"`{self.current_activity_type}`")
        embed.add_field(name="Activity Text", value=f"`{self.current_activity_text}`")
        embed.add_field(name="Servers",       value=str(len(self.bot.guilds)))
        embed.add_field(name="Ping",          value=f"`{round(self.bot.latency * 1000)}ms`")
        embed.add_field(
            name="📋 Commands",
            value=(
                "`!setstatus` — online/idle/dnd/invisible\n"
                "`!setactivity` — change activity\n"
                "`!setbotname` — change username\n"
                "`!resetstatus` — reset to default\n"
                "`!botinfo` — public bot info"
            ),
            inline=False
        )
        embed.add_field(
            name="⚠️ Bot Limitations",
            value=(
                "• No custom status (Discord blocks it for bots)\n"
                "• Username changes: max **2 per hour**\n"
                "• Profile picture changes: max **2 per hour**"
            ),
            inline=False
        )
        embed.set_footer(text="Lucky Bot • Bot Owner Only")
        return embed

    # ══════════════════════════════════════════
    #   SET STATUS
    # ══════════════════════════════════════════

    @commands.command(name='setstatus')
    async def setstatus_prefix(self, ctx, status: str):
        """
        Change bot online status.
        Usage: !setstatus online
               !setstatus idle
               !setstatus dnd
               !setstatus invisible
        """
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))

        valid = ['online', 'idle', 'dnd', 'invisible', 'offline']
        if status.lower() not in valid:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Invalid Status",
                description=(
                    f"Valid options:\n"
                    f"🟢 `online` • 🟡 `idle` • 🔴 `dnd` • ⚫ `invisible`"
                ),
                color=0xe74c3c
            ))

        try:
            status_obj   = self.get_status_obj(status)
            activity_obj = self.get_activity_obj(
                self.current_activity_type, self.current_activity_text)
            await self.bot.change_presence(status=status_obj, activity=activity_obj)
            self.current_status = status.lower()

            emoji = self.status_emoji(status.lower())
            embed = discord.Embed(
                title="✅ Status Updated",
                color=0x2ecc71,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="New Status", value=f"{emoji} `{status}`")
            embed.add_field(
                name="All Status Types",
                value=(
                    "🟢 `online` — normal green dot\n"
                    "🟡 `idle` — yellow crescent\n"
                    "🔴 `dnd` — red do not disturb\n"
                    "⚫ `invisible` — appears offline"
                ),
                inline=False
            )
            embed.set_footer(text="Lucky Bot • Bot Owner Only")
            await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(embed=discord.Embed(
                title="❌ Failed to Change Status",
                description=f"Error: `{e}`",
                color=0xe74c3c
            ))

    @app_commands.command(name='setstatus', description='Change bot online status (bot owner only)')
    @app_commands.describe(status='New status')
    @app_commands.choices(status=[
        app_commands.Choice(name='🟢 Online',                   value='online'),
        app_commands.Choice(name='🟡 Idle',                     value='idle'),
        app_commands.Choice(name='🔴 Do Not Disturb',           value='dnd'),
        app_commands.Choice(name='⚫ Invisible (appears offline)', value='invisible'),
    ])
    async def setstatus_slash(self, interaction: discord.Interaction, status: str):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        try:
            status_obj   = self.get_status_obj(status)
            activity_obj = self.get_activity_obj(
                self.current_activity_type, self.current_activity_text)
            await self.bot.change_presence(status=status_obj, activity=activity_obj)
            self.current_status = status
            emoji = self.status_emoji(status)
            await interaction.response.send_message(embed=discord.Embed(
                title="✅ Status Updated",
                description=f"Bot is now {emoji} `{status}`",
                color=0x2ecc71
            ))
        except Exception as e:
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Failed", description=f"`{e}`", color=0xe74c3c), ephemeral=True)

    # ══════════════════════════════════════════
    #   SET ACTIVITY
    # ══════════════════════════════════════════

    @commands.command(name='setactivity')
    async def setactivity_prefix(self, ctx, activity_type: str, *, text: str = "Lucky Bot 🍀"):
        """
        Change bot activity.
        Usage: !setactivity watching over the server
               !setactivity playing Lucky Bot
               !setactivity listening to music
               !setactivity competing in tournaments
               !setactivity streaming live now
               !setactivity none
        ⚠️ Custom status is NOT supported for bots by Discord!
        """
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))

        valid_types = ['playing', 'watching', 'listening', 'competing', 'streaming', 'none']
        if activity_type.lower() not in valid_types:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Invalid Activity Type",
                description=(
                    f"**Valid types:**\n"
                    f"`playing` `watching` `listening` `competing` `streaming` `none`\n\n"
                    f"⚠️ `custom` is **not supported** by Discord for bots!\n\n"
                    f"**Example:** `!setactivity watching over the server`"
                ),
                color=0xe74c3c
            ))

        try:
            status_obj   = self.get_status_obj(self.current_status)
            activity_obj = self.get_activity_obj(activity_type, text)
            await self.bot.change_presence(status=status_obj, activity=activity_obj)
            self.current_activity_type = activity_type.lower()
            self.current_activity_text = text

            embed = discord.Embed(
                title="✅ Activity Updated",
                color=0x2ecc71,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Type", value=f"`{activity_type}`")
            embed.add_field(name="Text", value=f"`{text}`")
            embed.add_field(
                name="Looks like in Discord",
                value=f"**{activity_type.capitalize()}** {text}",
                inline=False
            )
            embed.set_footer(text="Lucky Bot • Bot Owner Only")
            await ctx.reply(embed=embed)

        except Exception as e:
            await ctx.reply(embed=discord.Embed(
                title="❌ Failed to Change Activity",
                description=f"Error: `{e}`",
                color=0xe74c3c
            ))

    @app_commands.command(name='setactivity', description='Change bot activity (bot owner only)')
    @app_commands.describe(activity_type='Type of activity', text='Text to display')
    @app_commands.choices(activity_type=[
        app_commands.Choice(name='🎮 Playing',       value='playing'),
        app_commands.Choice(name='👁️ Watching',      value='watching'),
        app_commands.Choice(name='🎵 Listening to',  value='listening'),
        app_commands.Choice(name='🏆 Competing in',  value='competing'),
        app_commands.Choice(name='🔴 Streaming',     value='streaming'),
        app_commands.Choice(name='❌ None (remove)', value='none'),
    ])
    async def setactivity_slash(self, interaction: discord.Interaction,
                                activity_type: str, text: str = "Lucky Bot 🍀"):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        try:
            status_obj   = self.get_status_obj(self.current_status)
            activity_obj = self.get_activity_obj(activity_type, text)
            await self.bot.change_presence(status=status_obj, activity=activity_obj)
            self.current_activity_type = activity_type
            self.current_activity_text = text
            embed = discord.Embed(title="✅ Activity Updated", color=0x2ecc71)
            embed.add_field(name="Type", value=f"`{activity_type}`")
            embed.add_field(name="Text", value=f"`{text}`")
            embed.add_field(
                name="Looks like in Discord",
                value=f"**{activity_type.capitalize()}** {text}",
                inline=False
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Failed", description=f"`{e}`", color=0xe74c3c), ephemeral=True)

    # ══════════════════════════════════════════
    #   SET BOT NAME
    # ══════════════════════════════════════════

    @commands.command(name='setbotname')
    async def setbotname_prefix(self, ctx, *, new_name: str):
        """
        Change bot username.
        Usage: !setbotname Lucky Bot
        ⚠️ Discord allows max 2 changes per hour!
        """
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))
        if len(new_name) < 2 or len(new_name) > 32:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Invalid Name",
                description="Name must be **2–32 characters**!",
                color=0xe74c3c
            ))
        old_name = self.bot.user.name
        try:
            await self.bot.user.edit(username=new_name)
            embed = discord.Embed(
                title="✅ Bot Name Updated",
                color=0x2ecc71,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Old Name", value=old_name)
            embed.add_field(name="New Name", value=new_name)
            embed.add_field(
                name="⚠️ Rate Limit",
                value="Discord only allows **2 username changes per hour**!",
                inline=False
            )
            embed.set_footer(text="Lucky Bot • Bot Owner Only")
            await ctx.reply(embed=embed)
        except discord.HTTPException as e:
            if '50035' in str(e) or 'rate' in str(e).lower():
                await ctx.reply(embed=discord.Embed(
                    title="❌ Rate Limited by Discord",
                    description=(
                        "Discord limits bot username changes to **2 per hour**!\n"
                        "Please wait and try again later."
                    ),
                    color=0xe74c3c
                ))
            else:
                await ctx.reply(embed=discord.Embed(
                    title="❌ Failed",
                    description=f"Discord error: `{e}`",
                    color=0xe74c3c
                ))

    @app_commands.command(name='setbotname', description='Change bot username (bot owner only, 2x per hour)')
    @app_commands.describe(new_name='New username (2-32 characters)')
    async def setbotname_slash(self, interaction: discord.Interaction, new_name: str):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        if len(new_name) < 2 or len(new_name) > 32:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Invalid Name",
                description="Name must be **2–32 characters**!",
                color=0xe74c3c
            ), ephemeral=True)
        old_name = self.bot.user.name
        try:
            await self.bot.user.edit(username=new_name)
            embed = discord.Embed(title="✅ Bot Name Updated", color=0x2ecc71)
            embed.add_field(name="Old Name", value=old_name)
            embed.add_field(name="New Name", value=new_name)
            embed.add_field(
                name="⚠️ Rate Limit",
                value="Max **2 changes per hour** by Discord!",
                inline=False
            )
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException as e:
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Failed",
                description=f"Discord error: `{e}`",
                color=0xe74c3c
            ), ephemeral=True)

    # ══════════════════════════════════════════
    #   RESET STATUS
    # ══════════════════════════════════════════

    @commands.command(name='resetstatus')
    async def resetstatus_prefix(self, ctx):
        """Reset bot to default status. Usage: !resetstatus"""
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))
        try:
            await self.bot.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="over the server 👁️ | !help"
                )
            )
            self.current_status        = 'online'
            self.current_activity_type = 'watching'
            self.current_activity_text = 'over the server 👁️ | !help'
            await ctx.reply(embed=discord.Embed(
                title="✅ Status Reset to Default",
                description=(
                    "🟢 **Status:** Online\n"
                    "👁️ **Activity:** Watching over the server 👁️ | !help"
                ),
                color=0x2ecc71
            ))
        except Exception as e:
            await ctx.reply(embed=discord.Embed(
                title="❌ Failed", description=f"`{e}`", color=0xe74c3c))

    @app_commands.command(name='resetstatus', description='Reset bot to default status (bot owner only)')
    async def resetstatus_slash(self, interaction: discord.Interaction):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        try:
            await self.bot.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="over the server 👁️ | !help"
                )
            )
            self.current_status        = 'online'
            self.current_activity_type = 'watching'
            self.current_activity_text = 'over the server 👁️ | !help'
            await interaction.response.send_message(embed=discord.Embed(
                title="✅ Status Reset",
                description="🟢 Online • 👁️ Watching over the server",
                color=0x2ecc71
            ))
        except Exception as e:
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Failed", description=f"`{e}`", color=0xe74c3c), ephemeral=True)

    # ══════════════════════════════════════════
    #   BOT INFO (public)
    # ══════════════════════════════════════════

    @commands.command(name='botinfo')
    async def botinfo_prefix(self, ctx):
        """Public bot info. Usage: !botinfo"""
        await ctx.send(embed=self._build_botinfo())

    @app_commands.command(name='botinfo', description='Show bot information')
    async def botinfo_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._build_botinfo())

    def _build_botinfo(self):
        emoji         = self.status_emoji(self.current_status)
        total_members = sum(g.member_count for g in self.bot.guilds)
        embed = discord.Embed(
            title=f"🍀 {self.bot.user.name}",
            description="A powerful, fully-featured Discord moderation bot!",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Bot Name",      value=self.bot.user.name)
        embed.add_field(name="Bot ID",        value=f"`{self.bot.user.id}`")
        embed.add_field(name="Status",        value=f"{emoji} `{self.current_status}`")
        embed.add_field(name="Activity",      value=f"`{self.current_activity_type}` {self.current_activity_text}")
        embed.add_field(name="Servers",       value=str(len(self.bot.guilds)))
        embed.add_field(name="Total Members", value=str(total_members))
        embed.add_field(name="Cogs Loaded",   value=str(len(self.bot.cogs)))
        embed.add_field(name="Ping",          value=f"`{round(self.bot.latency * 1000)}ms`")
        embed.add_field(
            name="Features",
            value=(
                "🛡️ Moderation • 🔒 Security\n"
                "🎫 Tickets • 🎵 Music\n"
                "💰 Economy • ⭐ Leveling\n"
                "🎁 Giveaway • 😂 Fun"
            ),
            inline=False
        )
        embed.set_footer(text="Lucky Bot • Made with ❤️ • lucky.unaux.com")
        return embed


async def setup(bot):
    await bot.add_cog(BotStatus(bot))
