import discord
from discord.ext import commands
import asyncio

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warn_db = {}  # stores warnings

    # ── KICK ──────────────────────────────────
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Kick a member. Usage: !kick @user reason"""
        if member.top_role >= ctx.author.top_role:
            return await ctx.reply("❌ You can't kick someone with equal or higher role!")
        await member.kick(reason=reason)
        embed = discord.Embed(title="👢 Member Kicked", color=0xe74c3c)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        try:
            await member.send(f"👢 You were kicked from **{ctx.guild.name}**\nReason: {reason}")
        except:
            pass

    # ── BAN ───────────────────────────────────
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Ban a member. Usage: !ban @user reason"""
        if member.top_role >= ctx.author.top_role:
            return await ctx.reply("❌ You can't ban someone with equal or higher role!")
        await member.ban(reason=reason)
        embed = discord.Embed(title="🔨 Member Banned", color=0xc0392b)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        try:
            await member.send(f"🔨 You were banned from **{ctx.guild.name}**\nReason: {reason}")
        except:
            pass

    # ── UNBAN ─────────────────────────────────
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, username):
        """Unban a user. Usage: !unban username#0000"""
        banned = [entry async for entry in ctx.guild.bans()]
        for entry in banned:
            if str(entry.user) == username:
                await ctx.guild.unban(entry.user)
                embed = discord.Embed(title="✅ Member Unbanned", color=0x2ecc71)
                embed.add_field(name="User", value=entry.user.mention)
                embed.add_field(name="Moderator", value=ctx.author.mention)
                return await ctx.send(embed=embed)
        await ctx.reply(f"❌ Couldn't find banned user: `{username}`")

    # ── TIMEOUT ───────────────────────────────
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
        """Timeout a member. Usage: !timeout @user 10 spamming"""
        if member.top_role >= ctx.author.top_role:
            return await ctx.reply("❌ You can't timeout someone with equal or higher role!")
        duration = discord.utils.utcnow() + asyncio.timeout.__class__.__mro__[0].__subclasshook__.__func__.__globals__['timedelta'](minutes=minutes) if False else None
        import datetime
        duration = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        embed = discord.Embed(title="⏰ Member Timed Out", color=0xe67e22)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Duration", value=f"{minutes} minutes")
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)

    # ── UNTIMEOUT ─────────────────────────────
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        """Remove timeout. Usage: !untimeout @user"""
        await member.timeout(None)
        embed = discord.Embed(title="✅ Timeout Removed", color=0x2ecc71)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)

    # ── WARN ──────────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Warn a member. Usage: !warn @user reason"""
        guild_id = ctx.guild.id
        user_id = member.id
        if guild_id not in self.warn_db:
            self.warn_db[guild_id] = {}
        if user_id not in self.warn_db[guild_id]:
            self.warn_db[guild_id][user_id] = []
        self.warn_db[guild_id][user_id].append(reason)
        count = len(self.warn_db[guild_id][user_id])
        embed = discord.Embed(title="⚠️ Member Warned", color=0xf39c12)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Total Warnings", value=str(count))
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        try:
            await member.send(f"⚠️ You were warned in **{ctx.guild.name}**\nReason: {reason}\nTotal warnings: {count}")
        except:
            pass
        if count >= 3:
            await ctx.send(f"⚠️ **{member.display_name}** now has {count} warnings! Consider taking action.")

    # ── WARNINGS ──────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member):
        """Check warnings. Usage: !warnings @user"""
        guild_id = ctx.guild.id
        user_id = member.id
        warns = self.warn_db.get(guild_id, {}).get(user_id, [])
        if not warns:
            return await ctx.reply(f"✅ {member.mention} has no warnings!")
        embed = discord.Embed(title=f"⚠️ Warnings for {member.display_name}", color=0xf39c12)
        for i, w in enumerate(warns, 1):
            embed.add_field(name=f"Warning {i}", value=w, inline=False)
        await ctx.send(embed=embed)

    # ── CLEARWARN ─────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearwarn(self, ctx, member: discord.Member):
        """Clear all warnings. Usage: !clearwarn @user"""
        guild_id = ctx.guild.id
        user_id = member.id
        if guild_id in self.warn_db and user_id in self.warn_db[guild_id]:
            self.warn_db[guild_id][user_id] = []
        await ctx.reply(f"✅ Cleared all warnings for {member.mention}!")

    # ── PURGE ─────────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete messages. Usage: !purge 10"""
        if amount > 100:
            return await ctx.reply("❌ Max 100 messages at once!")
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🗑️ Deleted **{len(deleted)-1}** messages!")
        await msg.delete(delay=3)

    # ── SLOWMODE ──────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        """Set slowmode. Usage: !slowmode 5"""
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.reply("✅ Slowmode disabled!")
        else:
            await ctx.reply(f"✅ Slowmode set to **{seconds}** seconds!")

    # ── LOCK ──────────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Lock a channel. Usage: !lock #channel"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(f"🔒 **{channel.name}** has been locked!")

    # ── UNLOCK ────────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock a channel. Usage: !unlock #channel"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(f"🔓 **{channel.name}** has been unlocked!")

    # ── MUTE ROLE ─────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Mute a member. Usage: !mute @user reason"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        await member.add_roles(mute_role, reason=reason)
        embed = discord.Embed(title="🔇 Member Muted", color=0x95a5a6)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)

    # ── UNMUTE ────────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member. Usage: !unmute @user"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if mute_role in member.roles:
            await member.remove_roles(mute_role)
            await ctx.reply(f"🔊 {member.mention} has been unmuted!")
        else:
            await ctx.reply(f"❌ {member.mention} is not muted!")

    # ── NICK ──────────────────────────────────
    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, nickname):
        """Change nickname. Usage: !nick @user NewName"""
        await member.edit(nick=nickname)
        await ctx.reply(f"✅ Changed **{member.name}'s** nickname to **{nickname}**!")

    # ── USERINFO ──────────────────────────────
    @commands.command()
    async def userinfo(self, ctx, member: discord.Member = None):
        """Get user info. Usage: !userinfo @user"""
        member = member or ctx.author
        embed = discord.Embed(title=f"👤 {member.display_name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member))
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y"))
        embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"))
        embed.add_field(name="Top Role", value=member.top_role.mention)
        embed.add_field(name="Roles", value=len(member.roles)-1)
        await ctx.send(embed=embed)

    # ── SERVERINFO ────────────────────────────
    @commands.command()
    async def serverinfo(self, ctx):
        """Get server info. Usage: !serverinfo"""
        g = ctx.guild
        embed = discord.Embed(title=f"🏠 {g.name}", color=0x3498db)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=g.owner.mention)
        embed.add_field(name="Members", value=g.member_count)
        embed.add_field(name="Channels", value=len(g.channels))
        embed.add_field(name="Roles", value=len(g.roles))
        embed.add_field(name="Created", value=g.created_at.strftime("%b %d, %Y"))
        embed.add_field(name="Boost Level", value=g.premium_tier)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
