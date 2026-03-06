import discord
from discord.ext import commands
from discord import app_commands
import datetime

class BotStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Store current status settings
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
        activity_type = activity_type.lower()
        if activity_type == 'playing':
            return discord.Game(name=text)
        elif activity_type == 'listening':
            return discord.Activity(type=discord.ActivityType.listening, name=text)
        elif activity_type == 'watching':
            return discord.Activity(type=discord.ActivityType.watching, name=text)
        elif activity_type == 'competing':
            return discord.Activity(type=discord.ActivityType.competing, name=text)
        elif activity_type == 'streaming':
            return discord.Streaming(name=text, url='https://twitch.tv/placeholder')
        elif activity_type == 'custom':
            return discord.CustomActivity(name=text)
        elif activity_type == 'none':
            return None
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
        """Show current bot status settings. Usage: !botstatus"""
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only",
                description="Only the **bot creator** can manage bot status!",
                color=0xe74c3c
            ))
        await self._send_status_overview(ctx)

    @app_commands.command(name='botstatus', description='Show current bot status settings')
    async def botstatus_slash(self, interaction: discord.Interaction):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        embed = self._build_status_overview()
        await interaction.response.send_message(embed=embed)

    async def _send_status_overview(self, ctx):
        embed = self._build_status_overview()
        await ctx.send(embed=embed)

    def _build_status_overview(self):
        emoji = self.status_emoji(self.current_status)
        embed = discord.Embed(
            title="🤖 Bot Status Overview",
            color=0x3498db,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Bot Name", value=self.bot.user.name)
        embed.add_field(name="Bot ID", value=self.bot.user.id)
        embed.add_field(
            name="Status",
            value=f"{emoji} `{self.current_status}`"
        )
        embed.add_field(
            name="Activity Type",
            value=f"`{self.current_activity_type}`"
        )
        embed.add_field(
            name="Activity Text",
            value=f"`{self.current_activity_text}`"
        )
        embed.add_field(
            name="Servers",
            value=str(len(self.bot.guilds))
        )
        embed.add_field(
            name="📋 Commands",
            value=(
                "`!setstatus` — change online/idle/dnd\n"
                "`!setactivity` — change activity text\n"
                "`!setname` — change bot username\n"
                "`!resetstatus` — reset to default"
            ),
            inline=False
        )
        embed.set_footer(text="Lucky Bot • Bot Owner Only")
        return embed

    # ══════════════════════════════════════════
    #   SET STATUS (online/idle/dnd/invisible)
    # ══════════════════════════════════════════

    @commands.command(name='setstatus')
    async def setstatus_prefix(self, ctx, status: str):
        """
        Change bot's online status.
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
                description=f"Valid options: `{'`, `'.join(valid)}`",
                color=0xe74c3c
            ))

        status_obj = self.get_status_obj(status)
        activity = self.get_activity_obj(
            self.current_activity_type, self.current_activity_text)
        await self.bot.change_presence(status=status_obj, activity=activity)
        self.current_status = status.lower()

        emoji = self.status_emoji(status.lower())
        embed = discord.Embed(
            title="✅ Status Updated",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="New Status", value=f"{emoji} `{status}`")
        embed.add_field(
            name="Status Types",
            value=(
                "🟢 `online` — normal green dot\n"
                "🟡 `idle` — yellow crescent moon\n"
                "🔴 `dnd` — red do not disturb\n"
                "⚫ `invisible` — appears offline"
            ),
            inline=False
        )
        embed.set_footer(text="Lucky Bot • Bot Owner Only")
        await ctx.reply(embed=embed)

    @app_commands.command(name='setstatus', description='Change bot online status (bot owner only)')
    @app_commands.describe(status='New status to set')
    @app_commands.choices(status=[
        app_commands.Choice(name='🟢 Online', value='online'),
        app_commands.Choice(name='🟡 Idle', value='idle'),
        app_commands.Choice(name='🔴 Do Not Disturb', value='dnd'),
        app_commands.Choice(name='⚫ Invisible (appears offline)', value='invisible'),
    ])
    async def setstatus_slash(self, interaction: discord.Interaction, status: str):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        status_obj = self.get_status_obj(status)
        activity = self.get_activity_obj(
            self.current_activity_type, self.current_activity_text)
        await self.bot.change_presence(status=status_obj, activity=activity)
        self.current_status = status
        emoji = self.status_emoji(status)
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Status Updated",
            description=f"Bot is now {emoji} `{status}`",
            color=0x2ecc71
        ))

    # ══════════════════════════════════════════
    #   SET ACTIVITY
    # ══════════════════════════════════════════

    @commands.command(name='setactivity')
    async def setactivity_prefix(self, ctx, activity_type: str, *, text: str):
        """
        Change bot's activity.
        Usage: !setactivity watching over the server
               !setactivity playing Lucky Bot
               !setactivity listening to music
               !setactivity competing in tournaments
               !setactivity streaming live now
               !setactivity custom 🍀 Lucky Bot
               !setactivity none
        """
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))

        valid_types = ['playing', 'watching', 'listening',
                       'competing', 'streaming', 'custom', 'none']
        if activity_type.lower() not in valid_types:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Invalid Activity Type",
                description=(
                    f"Valid types: `{'`, `'.join(valid_types)}`\n\n"
                    f"Example: `!setactivity watching over the server`"
                ),
                color=0xe74c3c
            ))

        status_obj = self.get_status_obj(self.current_status)
        activity = self.get_activity_obj(activity_type, text)
        await self.bot.change_presence(status=status_obj, activity=activity)
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
            name="How it looks in Discord",
            value=f"**{activity_type.capitalize()}** {text}",
            inline=False
        )
        embed.set_footer(text="Lucky Bot • Bot Owner Only")
        await ctx.reply(embed=embed)

    @app_commands.command(name='setactivity', description='Change bot activity text (bot owner only)')
    @app_commands.describe(
        activity_type='Type of activity',
        text='Activity text to display'
    )
    @app_commands.choices(activity_type=[
        app_commands.Choice(name='🎮 Playing', value='playing'),
        app_commands.Choice(name='👁️ Watching', value='watching'),
        app_commands.Choice(name='🎵 Listening to', value='listening'),
        app_commands.Choice(name='🏆 Competing in', value='competing'),
        app_commands.Choice(name='🔴 Streaming', value='streaming'),
        app_commands.Choice(name='💬 Custom', value='custom'),
        app_commands.Choice(name='❌ None (remove activity)', value='none'),
    ])
    async def setactivity_slash(self, interaction: discord.Interaction,
                                activity_type: str, text: str = "Lucky Bot 🍀"):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        status_obj = self.get_status_obj(self.current_status)
        activity = self.get_activity_obj(activity_type, text)
        await self.bot.change_presence(status=status_obj, activity=activity)
        self.current_activity_type = activity_type
        self.current_activity_text = text
        embed = discord.Embed(
            title="✅ Activity Updated",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Type", value=f"`{activity_type}`")
        embed.add_field(name="Text", value=f"`{text}`")
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════
    #   SET BOT NAME
    # ══════════════════════════════════════════

    @commands.command(name='setbotname')
    async def setbotname_prefix(self, ctx, *, new_name: str):
        """
        Change bot's username.
        Usage: !setbotname Lucky Bot
        ⚠️ Discord limits this to 2 times per hour!
        Bot owner only.
        """
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))
        if len(new_name) < 2 or len(new_name) > 32:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Invalid Name",
                description="Bot name must be **2–32 characters**!",
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
                name="⚠️ Rate Limit Warning",
                value="Discord only allows **2 username changes per hour**!",
                inline=False
            )
            embed.set_footer(text="Lucky Bot • Bot Owner Only")
            await ctx.reply(embed=embed)
        except discord.HTTPException as e:
            if 'rate limited' in str(e).lower() or '50035' in str(e):
                await ctx.reply(embed=discord.Embed(
                    title="❌ Rate Limited",
                    description=(
                        "Discord limits bot name changes to **2 per hour**!\n"
                        "Please wait before trying again."
                    ),
                    color=0xe74c3c
                ))
            else:
                await ctx.reply(embed=discord.Embed(
                    title="❌ Failed",
                    description=f"Error: `{e}`",
                    color=0xe74c3c
                ))

    @app_commands.command(name='setbotname', description='Change bot username (bot owner only, 2x per hour limit)')
    @app_commands.describe(new_name='New bot username (2-32 characters)')
    async def setbotname_slash(self, interaction: discord.Interaction, new_name: str):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        if len(new_name) < 2 or len(new_name) > 32:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Invalid Name",
                description="Bot name must be **2–32 characters**!",
                color=0xe74c3c
            ), ephemeral=True)
        old_name = self.bot.user.name
        try:
            await self.bot.user.edit(username=new_name)
            embed = discord.Embed(
                title="✅ Bot Name Updated", color=0x2ecc71)
            embed.add_field(name="Old Name", value=old_name)
            embed.add_field(name="New Name", value=new_name)
            embed.add_field(
                name="⚠️ Warning",
                value="Discord allows only **2 name changes per hour**!",
                inline=False
            )
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException:
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Rate Limited",
                description="Discord limits name changes to **2 per hour**! Wait before retrying.",
                color=0xe74c3c
            ), ephemeral=True)

    # ══════════════════════════════════════════
    #   RESET STATUS TO DEFAULT
    # ══════════════════════════════════════════

    @commands.command(name='resetstatus')
    async def resetstatus_prefix(self, ctx):
        """Reset bot status and activity to default. Usage: !resetstatus"""
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over the server 👁️ | !help"
            )
        )
        self.current_status = 'online'
        self.current_activity_type = 'watching'
        self.current_activity_text = 'over the server 👁️ | !help'
        await ctx.reply(embed=discord.Embed(
            title="✅ Status Reset",
            description=(
                "Bot status reset to default!\n\n"
                "🟢 **Online**\n"
                "👁️ **Watching** over the server | !help"
            ),
            color=0x2ecc71
        ))

    @app_commands.command(name='resetstatus', description='Reset bot status to default (bot owner only)')
    async def resetstatus_slash(self, interaction: discord.Interaction):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c), ephemeral=True)
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over the server 👁️ | !help"
            )
        )
        self.current_status = 'online'
        self.current_activity_type = 'watching'
        self.current_activity_text = 'over the server 👁️ | !help'
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Status Reset",
            description="Bot status reset to default! 🟢 Online",
            color=0x2ecc71
        ))

    # ══════════════════════════════════════════
    #   BOT INFO
    # ══════════════════════════════════════════

    @commands.command(name='botinfo')
    async def botinfo_prefix(self, ctx):
        """Show detailed bot info. Usage: !botinfo"""
        embed = self._build_botinfo()
        await ctx.send(embed=embed)

    @app_commands.command(name='botinfo', description='Show detailed bot information')
    async def botinfo_slash(self, interaction: discord.Interaction):
        embed = self._build_botinfo()
        await interaction.response.send_message(embed=embed)

    def _build_botinfo(self):
        emoji = self.status_emoji(self.current_status)
        total_members = sum(g.member_count for g in self.bot.guilds)
        embed = discord.Embed(
            title=f"🍀 {self.bot.user.name}",
            description="A powerful, fully-featured Discord moderation bot!",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Bot Name", value=self.bot.user.name)
        embed.add_field(name="Bot ID", value=f"`{self.bot.user.id}`")
        embed.add_field(
            name="Status",
            value=f"{emoji} `{self.current_status}`"
        )
        embed.add_field(
            name="Activity",
            value=f"`{self.current_activity_type}` {self.current_activity_text}"
        )
        embed.add_field(
            name="Servers",
            value=str(len(self.bot.guilds))
        )
        embed.add_field(
            name="Total Members",
            value=str(total_members)
        )
        embed.add_field(
            name="Cogs Loaded",
            value=str(len(self.bot.cogs))
        )
        embed.add_field(
            name="Latency",
            value=f"`{round(self.bot.latency * 1000)}ms`"
        )
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
        embed.set_footer(text="Lucky Bot • Made with ❤️")
        return embed


async def setup(bot):
    await bot.add_cog(BotStatus(bot))
