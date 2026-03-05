import discord
from discord.ext import commands
import asyncio
import datetime
import re

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warn_db = {}
        self.notes_db = {}
        self.afk_db = {}
        self.snipe_db = {}
        self.editsnipe_db = {}
        self.massban_enabled = {}  # per server toggle

    # ══════════════════════════════════════════
    #   HELPERS
    # ══════════════════════════════════════════

    def parse_time(self, text):
        units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        match = re.fullmatch(r'(\d+)([smhd])', text.lower())
        if match:
            return int(match.group(1)) * units[match.group(2)]
        return None

    def format_time(self, seconds):
        if seconds < 60: return f"{seconds}s"
        elif seconds < 3600: return f"{seconds//60}m"
        elif seconds < 86400: return f"{seconds//3600}h"
        else: return f"{seconds//86400}d"

    async def send_log(self, guild, embed):
        log_channel = discord.utils.get(guild.text_channels, name='mod-logs') or \
                      discord.utils.get(guild.text_channels, name='logs') or \
                      discord.utils.get(guild.text_channels, name='audit-log')
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except:
                pass

    def log_embed(self, title, color, **fields):
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        for name, value in fields.items():
            embed.add_field(name=name.replace('_', ' ').title(), value=value, inline=True)
        embed.set_footer(text="Lucky Bot Logs")
        return embed

    # ══════════════════════════════════════════
    #   SETUP COMMAND
    # ══════════════════════════════════════════

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        """
        Automatically sets up everything Lucky Bot needs.
        Usage: !setup
        Creates mod-logs channel, sets permissions, configures everything.
        """
        embed = discord.Embed(
            title="⚙️ Lucky Bot Setup",
            description="Setting everything up... please wait!",
            color=0x3498db
        )
        status_msg = await ctx.send(embed=embed)
        results = []
        guild = ctx.guild

        # ── Step 1: Create mod-logs channel ───
        try:
            existing = discord.utils.get(guild.text_channels, name='mod-logs')
            if existing:
                results.append("✅ `#mod-logs` already exists — skipped")
                log_channel = existing
            else:
                # Make it private — only mods/admins can see it
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=False,
                        send_messages=False
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        embed_links=True
                    ),
                    ctx.author: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=False
                    )
                }
                # Give access to all roles with manage_messages or above
                for role in guild.roles:
                    if role.permissions.manage_messages or \
                       role.permissions.administrator or \
                       role.permissions.manage_guild:
                        overwrites[role] = discord.PermissionOverwrite(
                            view_channel=True,
                            send_messages=False
                        )

                # Find or create a Mod category
                mod_category = discord.utils.get(guild.categories, name='Mod')
                if not mod_category:
                    mod_category = discord.utils.get(guild.categories, name='Staff')
                if not mod_category:
                    mod_category = discord.utils.get(guild.categories, name='Admin')

                log_channel = await guild.create_text_channel(
                    name='mod-logs',
                    overwrites=overwrites,
                    category=mod_category,
                    topic='🔒 Private mod logs — Lucky Bot'
                )
                results.append("✅ Created private `#mod-logs` channel")
        except Exception as e:
            results.append(f"❌ Failed to create `#mod-logs`: {e}")
            log_channel = None

        # ── Step 2: Create Muted role ──────────
        try:
            muted_role = discord.utils.get(guild.roles, name='Muted')
            if muted_role:
                results.append("✅ `Muted` role already exists — skipped")
            else:
                muted_role = await guild.create_role(
                    name='Muted',
                    color=discord.Color.greyple(),
                    reason="Lucky Bot setup"
                )
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(muted_role,
                            send_messages=False,
                            speak=False,
                            add_reactions=False
                        )
                    except:
                        pass
                results.append("✅ Created `Muted` role and applied to all channels")
        except Exception as e:
            results.append(f"❌ Failed to create `Muted` role: {e}")

        # ── Step 3: Create welcome channel ────
        try:
            existing_welcome = discord.utils.get(guild.text_channels, name='welcome')
            if existing_welcome:
                results.append("✅ `#welcome` already exists — skipped")
            else:
                await guild.create_text_channel(
                    name='welcome',
                    topic='👋 Welcome to the server!'
                )
                results.append("✅ Created `#welcome` channel")
        except Exception as e:
            results.append(f"❌ Failed to create `#welcome`: {e}")

        # ── Step 4: Create rules channel ──────
        try:
            existing_rules = discord.utils.get(guild.text_channels, name='rules')
            if existing_rules:
                results.append("✅ `#rules` already exists — skipped")
            else:
                rules_channel = await guild.create_text_channel(
                    name='rules',
                    topic='📋 Server rules'
                )
                results.append("✅ Created `#rules` channel")
        except Exception as e:
            results.append(f"❌ Failed to create `#rules`: {e}")

        # ── Step 5: Check bot permissions ─────
        missing_perms = []
        bot_member = guild.me
        needed = [
            ('kick_members', 'Kick Members'),
            ('ban_members', 'Ban Members'),
            ('manage_roles', 'Manage Roles'),
            ('manage_channels', 'Manage Channels'),
            ('manage_messages', 'Manage Messages'),
            ('moderate_members', 'Timeout Members'),
            ('view_audit_log', 'View Audit Log'),
        ]
        for perm, name in needed:
            if not getattr(bot_member.guild_permissions, perm):
                missing_perms.append(name)

        if missing_perms:
            results.append(f"⚠️ Missing permissions: {', '.join(missing_perms)}")
        else:
            results.append("✅ Bot has all required permissions")

        # ── Step 6: Massban is OFF by default ─
        self.massban_enabled[guild.id] = False
        results.append("✅ `!massban` is **disabled** by default (use `!massban enable` to turn on)")

        # ── Final status message ───────────────
        embed = discord.Embed(
            title="✅ Lucky Bot Setup Complete!",
            description="\n".join(results),
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(
            name="📋 What was set up",
            value=(
                "`#mod-logs` — private, mods only\n"
                "`Muted` role — blocks all channels\n"
                "`#welcome` channel\n"
                "`#rules` channel\n"
                "Bot permissions checked\n"
                "Massban locked by default"
            ),
            inline=False
        )
        embed.add_field(
            name="🔒 mod-logs access",
            value="Only roles with `Manage Messages`, `Administrator`, or `Manage Server` can see it.",
            inline=False
        )
        embed.set_footer(text=f"Set up by {ctx.author} • Lucky Bot")
        await status_msg.edit(embed=embed)

        # Send welcome message to mod-logs
        if log_channel:
            welcome_log = discord.Embed(
                title="🍀 Lucky Bot is ready!",
                description=f"Set up by {ctx.author.mention}\nAll mod actions will be logged here.",
                color=0x2ecc71,
                timestamp=datetime.datetime.utcnow()
            )
            welcome_log.set_footer(text="Lucky Bot • mod-logs")
            await log_channel.send(embed=welcome_log)

    # ══════════════════════════════════════════
    #   MASSBAN TOGGLE
    # ══════════════════════════════════════════

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def massban(self, ctx, action: str = None, *members: discord.Member):
        """
        Massban — disabled by default!
        Usage: !massban enable       ← turn on massban
               !massban disable      ← turn off massban
               !massban status       ← check if enabled
               !massban @u1 @u2 @u3  ← ban multiple (only if enabled)
        """
        guild_id = ctx.guild.id

        # ── Toggle commands ────────────────────
        if action == "enable":
            self.massban_enabled[guild_id] = True
            embed = discord.Embed(
                title="🔓 Massban ENABLED",
                description="⚠️ Massban is now **ON**.\nUse `!massban @user1 @user2 ...` to ban multiple members.\nUse `!massban disable` to turn it off again.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            log = self.log_embed("🔓 Massban Enabled", 0xe74c3c,
                enabled_by=str(ctx.author),
                warning="Dangerous feature — monitor use"
            )
            await self.send_log(ctx.guild, log)
            return

        if action == "disable":
            self.massban_enabled[guild_id] = False
            embed = discord.Embed(
                title="🔒 Massban DISABLED",
                description="Massban is now **OFF**. Safe!",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)
            return

        if action == "status":
            status = self.massban_enabled.get(guild_id, False)
            embed = discord.Embed(
                title="📊 Massban Status",
                description=f"Massban is currently **{'🔓 ENABLED' if status else '🔒 DISABLED'}**",
                color=0xe74c3c if status else 0x2ecc71
            )
            await ctx.send(embed=embed)
            return

        # ── Actual massban ────────────────────
        if not self.massban_enabled.get(guild_id, False):
            embed = discord.Embed(
                title="🔒 Massban is Disabled",
                description=(
                    "Massban is **turned off** for safety.\n\n"
                    "To enable it, an administrator must run:\n"
                    "`!massban enable`\n\n"
                    "⚠️ Only enable it when you actually need it, then disable after!"
                ),
                color=0xe74c3c
            )
            return await ctx.send(embed=embed)

        # Massban is enabled — do the bans
        if not members and action:
            # action might be a member mention
            try:
                first = await commands.MemberConverter().convert(ctx, action)
                members = (first,) + members
            except:
                return await ctx.reply("❌ Mention members to ban! Usage: `!massban @u1 @u2 @u3`")

        if not members:
            return await ctx.reply("❌ Mention at least one member! Usage: `!massban @u1 @u2 @u3`")

        # Confirmation
        names = ", ".join([m.display_name for m in members])
        confirm_embed = discord.Embed(
            title="⚠️ Confirm Massban",
            description=f"You're about to ban **{len(members)}** members:\n`{names}`\n\nReply `yes` to confirm.",
            color=0xe74c3c
        )
        await ctx.send(embed=confirm_embed)
        def check(m): return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
        try:
            await self.bot.wait_for('message', check=check, timeout=20)
        except asyncio.TimeoutError:
            return await ctx.reply("❌ Massban cancelled — timed out!")

        banned = []
        failed = []
        for member in members:
            try:
                if member.top_role < ctx.author.top_role:
                    await member.ban(reason=f"Massban by {ctx.author}")
                    banned.append(str(member))
                else:
                    failed.append(f"{member} (higher role)")
            except:
                failed.append(f"{member} (error)")

        embed = discord.Embed(title="🔨 Mass Ban Complete", color=0xc0392b)
        if banned:
            embed.add_field(name=f"✅ Banned ({len(banned)})", value="\n".join(banned), inline=False)
        if failed:
            embed.add_field(name=f"❌ Failed ({len(failed)})", value="\n".join(failed), inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        log = self.log_embed("🔨 Mass Ban", 0xc0392b,
            banned=", ".join(banned) or "None",
            failed=", ".join(failed) or "None",
            moderator=str(ctx.author)
        )
        await self.send_log(ctx.guild, log)

    # ══════════════════════════════════════════
    #   LISTENERS
    # ══════════════════════════════════════════

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            cmd = ctx.message.content.split()[0][1:]
            embed = discord.Embed(
                title="❓ Unknown Command",
                description=f"`!{cmd}` doesn't exist!\nDid you make a typo? Use `!help` to see all commands.",
                color=0xe74c3c
            )
            embed.set_footer(text="Lucky Bot • !help for full list")
            msg = await ctx.send(embed=embed)
            await msg.delete(delay=5)
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission for that!")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.reply("❌ I don't have enough permissions to do that!")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply("❌ Member not found! Make sure you @mention them.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"❌ Missing something! Use `!help` to check the correct usage.")
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Something looks wrong! Check the format and try again.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author.id in self.afk_db:
            del self.afk_db[message.author.id]
            try:
                await message.author.edit(nick=message.author.display_name.replace('[AFK] ', ''))
            except:
                pass
            msg = await message.channel.send(f"👋 Welcome back {message.author.mention}! Removed your AFK.")
            await msg.delete(delay=5)
        for user in message.mentions:
            if user.id in self.afk_db:
                afk_data = self.afk_db[user.id]
                embed = discord.Embed(
                    title="💤 User is AFK",
                    description=f"{user.mention} is currently AFK.",
                    color=0x95a5a6
                )
                embed.add_field(name="Reason", value=afk_data['reason'])
                embed.add_field(name="Since", value=f"<t:{afk_data['time']}:R>")
                await message.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        self.snipe_db[message.channel.id] = {
            'content': message.content or '[No text content]',
            'author': message.author,
            'time': datetime.datetime.utcnow(),
            'attachments': [a.url for a in message.attachments]
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return
        if before.content == after.content:
            return
        self.editsnipe_db[before.channel.id] = {
            'before': before.content or '[No text]',
            'after': after.content or '[No text]',
            'author': before.author,
            'time': datetime.datetime.utcnow()
        }

    # ══════════════════════════════════════════
    #   ALL OTHER MOD COMMANDS
    # ══════════════════════════════════════════

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, args=""):
        """Kick a member. Usage: !kick @user ?r reason"""
        reason = "No reason provided"
        if "?r" in args:
            reason = args.split("?r", 1)[1].strip()
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
        log = self.log_embed("👢 Member Kicked", 0xe74c3c,
            user=f"{member} ({member.id})", reason=reason, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, args=""):
        """Ban a member. Usage: !ban @user ?r reason"""
        reason = "No reason provided"
        if "?r" in args:
            reason = args.split("?r", 1)[1].strip()
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
        log = self.log_embed("🔨 Member Banned", 0xc0392b,
            user=f"{member} ({member.id})", reason=reason, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, username):
        """Unban a user. Usage: !unban username"""
        banned = [entry async for entry in ctx.guild.bans()]
        matches = [e for e in banned if username.lower() in str(e.user).lower()]
        if not matches:
            return await ctx.reply(f"❌ No banned user found matching `{username}`")
        if len(matches) == 1:
            await ctx.guild.unban(matches[0].user)
            embed = discord.Embed(title="✅ Member Unbanned", color=0x2ecc71)
            embed.add_field(name="User", value=str(matches[0].user))
            embed.add_field(name="Moderator", value=ctx.author.mention)
            await ctx.send(embed=embed)
            log = self.log_embed("✅ Member Unbanned", 0x2ecc71,
                user=f"{matches[0].user} ({matches[0].user.id})", moderator=str(ctx.author))
            await self.send_log(ctx.guild, log)
            return
        desc = "\n".join([f"`{i+1}.` {e.user} (`{e.user.id}`)" for i, e in enumerate(matches[:10])])
        embed = discord.Embed(title="🔍 Multiple matches", description=f"{desc}\n\nReply with a number:", color=0xe67e22)
        await ctx.send(embed=embed)
        def check(m): return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            index = int(msg.content) - 1
            if 0 <= index < len(matches):
                await ctx.guild.unban(matches[index].user)
                await ctx.reply(f"✅ Unbanned **{matches[index].user}**!")
            else:
                await ctx.reply("❌ Invalid number!")
        except asyncio.TimeoutError:
            await ctx.reply("⏰ Timed out!")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx, member: discord.Member, time: str, *, args=""):
        """Tempban. Usage: !tempban @user 1h ?r reason"""
        reason = "No reason provided"
        if "?r" in args:
            reason = args.split("?r", 1)[1].strip()
        seconds = self.parse_time(time)
        if not seconds:
            return await ctx.reply("❌ Invalid time! Use: `30s`, `10m`, `2h`, `1d`")
        if member.top_role >= ctx.author.top_role:
            return await ctx.reply("❌ You can't ban someone with equal or higher role!")
        await member.ban(reason=f"[Tempban: {time}] {reason}")
        unban_time = int((datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)).timestamp())
        embed = discord.Embed(title="⏳ Member Tempbanned", color=0xc0392b)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Duration", value=time)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Unban at", value=f"<t:{unban_time}:R>")
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        try:
            await member.send(f"⏳ You were tempbanned from **{ctx.guild.name}** for **{time}**\nReason: {reason}")
        except:
            pass
        log = self.log_embed("⏳ Tempban", 0xc0392b,
            user=f"{member} ({member.id})", duration=time, reason=reason, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)
        await asyncio.sleep(seconds)
        try:
            await ctx.guild.unban(member, reason="Tempban expired")
            await self.send_log(ctx.guild, self.log_embed("✅ Tempban Expired", 0x2ecc71, user=str(member)))
        except:
            pass

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, *, args=""):
        """
        Mute a member.
        Usage: !mute @user
               !mute @user ?t 10m
               !mute @user ?r reason
               !mute @user ?t 1h ?r being rude
        """
        if member.top_role >= ctx.author.top_role:
            return await ctx.reply("❌ You can't mute someone with equal or higher role!")
        reason = "No reason provided"
        duration_seconds = 600
        duration_text = "10m (default)"
        if "?r" in args:
            parts = args.split("?r", 1)
            args = parts[0].strip()
            r_part = parts[1]
            if "?t" in r_part:
                r_split = r_part.split("?t", 1)
                reason = r_split[0].strip()
                args += " " + r_split[1].strip()
            else:
                reason = r_part.strip()
        if "?t" in args:
            t_part = args.split("?t", 1)[1].strip().split()[0]
            parsed = self.parse_time(t_part)
            if parsed:
                if parsed > 86400 * 28:
                    return await ctx.reply("❌ Max mute is 28 days!")
                duration_seconds = parsed
                duration_text = t_part
            else:
                return await ctx.reply("❌ Invalid time! Use: `30s`, `10m`, `2h`, `1d`")
        until = discord.utils.utcnow() + datetime.timedelta(seconds=duration_seconds)
        await member.timeout(until, reason=reason)
        embed = discord.Embed(title="🔇 Member Muted", color=0x95a5a6)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Duration", value=duration_text)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Unmuted", value=f"<t:{int(until.timestamp())}:R>")
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        try:
            await member.send(f"🔇 Muted in **{ctx.guild.name}** for **{duration_text}**\nReason: {reason}")
        except:
            pass
        log = self.log_embed("🔇 Member Muted", 0x95a5a6,
            user=f"{member} ({member.id})", duration=duration_text,
            reason=reason, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member. Usage: !unmute @user"""
        await member.timeout(None)
        embed = discord.Embed(title="🔊 Member Unmuted", color=0x2ecc71)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        log = self.log_embed("🔊 Unmuted", 0x2ecc71,
            user=f"{member} ({member.id})", moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, args=""):
        """Warn a member. Usage: !warn @user ?r reason"""
        reason = "No reason provided"
        if "?r" in args:
            reason = args.split("?r", 1)[1].strip()
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
        embed.add_field(name="Total Warnings", value=f"⚠️ {count}")
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        try:
            await member.send(f"⚠️ Warned in **{ctx.guild.name}**\nReason: {reason}\nTotal: {count} warnings")
        except:
            pass
        if count >= 3:
            await ctx.send(f"🚨 {member.mention} now has **{count} warnings!**")
        log = self.log_embed("⚠️ Member Warned", 0xf39c12,
            user=f"{member} ({member.id})", reason=reason,
            total_warnings=str(count), moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member):
        """Check warnings. Usage: !warnings @user"""
        warns = self.warn_db.get(ctx.guild.id, {}).get(member.id, [])
        if not warns:
            return await ctx.reply(f"✅ {member.mention} has no warnings!")
        embed = discord.Embed(title=f"⚠️ Warnings for {member.display_name}", color=0xf39c12)
        for i, w in enumerate(warns, 1):
            embed.add_field(name=f"Warning #{i}", value=w, inline=False)
        embed.set_footer(text=f"Total: {len(warns)} warnings")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unwarn(self, ctx, member: discord.Member, number: int = None):
        """Remove a warning. Usage: !unwarn @user  or  !unwarn @user 2"""
        guild_id = ctx.guild.id
        user_id = member.id
        warns = self.warn_db.get(guild_id, {}).get(user_id, [])
        if not warns:
            return await ctx.reply(f"✅ {member.mention} has no warnings!")
        if number is None:
            removed = warns.pop()
        else:
            if number < 1 or number > len(warns):
                return await ctx.reply(f"❌ Invalid! {member.mention} has {len(warns)} warnings.")
            removed = warns.pop(number - 1)
        self.warn_db[guild_id][user_id] = warns
        embed = discord.Embed(title="✅ Warning Removed", color=0x2ecc71)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Removed", value=removed)
        embed.add_field(name="Remaining", value=str(len(warns)))
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearwarn(self, ctx, member: discord.Member):
        """Clear all warnings. Usage: !clearwarn @user"""
        if ctx.guild.id in self.warn_db and member.id in self.warn_db[ctx.guild.id]:
            self.warn_db[ctx.guild.id][member.id] = []
        await ctx.reply(f"🧹 Cleared all warnings for {member.mention}!")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int, member: discord.Member = None):
        """Delete messages. Usage: !purge 10  or  !purge 10 @user"""
        if amount > 100:
            return await ctx.reply("❌ Max 100 at once!")
        if member:
            deleted = await ctx.channel.purge(limit=amount * 5, check=lambda m: m.author == member)
            deleted = deleted[:amount]
        else:
            deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🗑️ Deleted **{len(deleted)}** messages!")
        await msg.delete(delay=3)
        log = self.log_embed("🗑️ Purge", 0xe74c3c,
            channel=ctx.channel.mention, deleted=str(len(deleted)),
            target=str(member) if member else "All", moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def nuke(self, ctx, channel: discord.TextChannel = None):
        """Wipe a channel completely. Usage: !nuke or !nuke #channel"""
        channel = channel or ctx.channel
        embed = discord.Embed(
            title="☢️ NUKE CHANNEL?",
            description=f"Wipe **#{channel.name}** completely?\nReply `yes` to confirm.",
            color=0xe74c3c
        )
        await ctx.send(embed=embed)
        def check(m): return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
        try:
            await self.bot.wait_for('message', check=check, timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("❌ Nuke cancelled!")
        pos = channel.position
        new_ch = await channel.clone(reason=f"Nuked by {ctx.author}")
        await channel.delete()
        await new_ch.edit(position=pos)
        await new_ch.send(embed=discord.Embed(
            title="☢️ Channel Nuked",
            description=f"Wiped by {ctx.author.mention}",
            color=0xe74c3c
        ))
        log = self.log_embed("☢️ Channel Nuked", 0xe74c3c,
            channel=f"#{channel.name}", moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, time: str = "0"):
        """Set slowmode. Usage: !slowmode 5m  or  !slowmode 0"""
        if time in ("0", "off"):
            await ctx.channel.edit(slowmode_delay=0)
            return await ctx.reply("✅ Slowmode disabled!")
        seconds = self.parse_time(time)
        if not seconds:
            return await ctx.reply("❌ Invalid! Use: `30s`, `5m`, `1h`")
        if seconds > 21600:
            return await ctx.reply("❌ Max slowmode is 6 hours!")
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.reply(f"✅ Slowmode set to **{time}**!")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Lock a channel. Usage: !lock or !lock #channel"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(f"🔒 **#{channel.name}** locked!")
        log = self.log_embed("🔒 Channel Locked", 0xe74c3c,
            channel=channel.mention, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock a channel. Usage: !unlock or !unlock #channel"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(f"🔓 **#{channel.name}** unlocked!")
        log = self.log_embed("🔓 Channel Unlocked", 0x2ecc71,
            channel=channel.mention, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, member: discord.Member, *, role: discord.Role):
        """Add/remove a role. Usage: !role @user RoleName"""
        if role.position >= ctx.author.top_role.position:
            return await ctx.reply("❌ That role is higher than yours!")
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.reply(f"✅ Removed **{role.name}** from {member.mention}!")
            action = "removed"
        else:
            await member.add_roles(role)
            await ctx.reply(f"✅ Added **{role.name}** to {member.mention}!")
            action = "added"
        log = self.log_embed("🏷️ Role Updated", 0x3498db,
            user=f"{member} ({member.id})", role=role.name,
            action=action, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, nickname):
        """Change nickname. Usage: !nick @user NewName"""
        old = member.display_name
        await member.edit(nick=nickname)
        await ctx.reply(f"✅ Changed **{old}'s** nickname to **{nickname}**!")

    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def resetnick(self, ctx, member: discord.Member):
        """Reset nickname. Usage: !resetnick @user"""
        await member.edit(nick=None)
        await ctx.reply(f"✅ Reset **{member.name}'s** nickname!")

    @commands.command()
    async def afk(self, ctx, *, reason="AFK"):
        """Set AFK. Usage: !afk  or  !afk doing homework"""
        self.afk_db[ctx.author.id] = {
            'reason': reason,
            'time': int(datetime.datetime.utcnow().timestamp())
        }
        try:
            await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}"[:32])
        except:
            pass
        embed = discord.Embed(
            title="💤 AFK Set",
            description=f"{ctx.author.mention} is now AFK\nReason: **{reason}**",
            color=0x95a5a6
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def snipe(self, ctx):
        """Show last deleted message. Usage: !snipe"""
        data = self.snipe_db.get(ctx.channel.id)
        if not data:
            return await ctx.reply("❌ Nothing to snipe here!")
        embed = discord.Embed(
            title="🕵️ Sniped Message",
            description=data['content'],
            color=0x3498db,
            timestamp=data['time']
        )
        embed.set_author(name=str(data['author']), icon_url=data['author'].display_avatar.url)
        if data['attachments']:
            embed.add_field(name="Attachments", value="\n".join(data['attachments']))
        embed.set_footer(text=f"Sniped by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command()
    async def editsnipe(self, ctx):
        """Show last edited message. Usage: !editsnipe"""
        data = self.editsnipe_db.get(ctx.channel.id)
        if not data:
            return await ctx.reply("❌ Nothing to editsnipe here!")
        embed = discord.Embed(title="👁️ Edit Sniped", color=0x9b59b6, timestamp=data['time'])
        embed.set_author(name=str(data['author']), icon_url=data['author'].display_avatar.url)
        embed.add_field(name="Before", value=data['before'], inline=False)
        embed.add_field(name="After", value=data['after'], inline=False)
        embed.set_footer(text=f"Sniped by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, channel: discord.TextChannel, *, args):
        """
        Send an announcement.
        Usage: !announce #channel Title | Message
               !announce #channel Just a message
        """
        if "|" in args:
            parts = args.split("|", 1)
            title = parts[0].strip()
            content = parts[1].strip()
        else:
            title = "📢 Announcement"
            content = args.strip()
        embed = discord.Embed(
            title=f"📢 {title}",
            description=content,
            color=0x3498db,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"Announced by {ctx.author} • {ctx.guild.name}")
        await channel.send(embed=embed)
        await ctx.reply(f"✅ Announcement sent to {channel.mention}!")
        log = self.log_embed("📢 Announcement", 0x3498db,
            channel=channel.mention, title=title, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def poll(self, ctx, *, question):
        """Create a poll. Usage: !poll Should we add a new channel?"""
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=0x3498db,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Vote!", value="✅ Yes  |  ❌ No")
        embed.set_footer(text=f"Poll by {ctx.author}")
        msg = await ctx.send(embed=embed)
        await ctx.message.delete()
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def note(self, ctx, member: discord.Member, *, note: str):
        """Add a private mod note. Usage: !note @user they were verbally warned"""
        guild_id = ctx.guild.id
        user_id = member.id
        if guild_id not in self.notes_db:
            self.notes_db[guild_id] = {}
        if user_id not in self.notes_db[guild_id]:
            self.notes_db[guild_id][user_id] = []
        self.notes_db[guild_id][user_id].append({
            'note': note,
            'by': str(ctx.author),
            'time': datetime.datetime.utcnow().strftime("%b %d %Y %H:%M")
        })
        count = len(self.notes_db[guild_id][user_id])
        await ctx.reply(f"📝 Note #{count} added for {member.mention}!")
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def notes(self, ctx, member: discord.Member):
        """View mod notes. Usage: !notes @user"""
        notes = self.notes_db.get(ctx.guild.id, {}).get(member.id, [])
        if not notes:
            return await ctx.reply(f"📝 No notes for {member.mention}!")
        embed = discord.Embed(title=f"📝 Mod Notes — {member.display_name}", color=0x9b59b6)
        for i, n in enumerate(notes, 1):
            embed.add_field(
                name=f"Note #{i} • {n['by']} • {n['time']}",
                value=n['note'],
                inline=False
            )
        try:
            await ctx.author.send(embed=embed)
            await ctx.reply("📬 Notes sent to your DMs!")
        except:
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearnotes(self, ctx, member: discord.Member):
        """Clear all notes. Usage: !clearnotes @user"""
        if ctx.guild.id in self.notes_db and member.id in self.notes_db[ctx.guild.id]:
            self.notes_db[ctx.guild.id][member.id] = []
        await ctx.reply(f"🧹 Cleared all notes for {member.mention}!")

    @commands.command()
    async def find(self, ctx, *, query: str):
        """Search for a member. Usage: !find john"""
        results = [
            m for m in ctx.guild.members
            if query.lower() in m.name.lower() or query.lower() in m.display_name.lower()
        ][:20]
        if not results:
            return await ctx.reply(f"❌ No members found matching `{query}`")
        embed = discord.Embed(
            title=f"🔍 Search: `{query}`",
            description=f"Found **{len(results)}** member(s)",
            color=0x3498db
        )
        status_icons = {"online":"🟢","idle":"🟡","dnd":"🔴","offline":"⚫"}
        lines = [f"{status_icons.get(str(m.status),'⚫')} {m.mention} — `{m.id}`" for m in results]
        embed.add_field(name="Results", value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=['ui', 'whois'])
    async def userinfo(self, ctx, member: discord.Member = None):
        """Get user info. Usage: !userinfo @user"""
        member = member or ctx.author
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        embed = discord.Embed(
            title=f"👤 {member.display_name}",
            color=member.color if member.color.value else 0x3498db
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member))
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Bot?", value="Yes 🤖" if member.bot else "No 👤")
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y"))
        embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"))
        embed.add_field(name="Top Role", value=member.top_role.mention)
        warns = len(self.warn_db.get(ctx.guild.id, {}).get(member.id, []))
        notes_count = len(self.notes_db.get(ctx.guild.id, {}).get(member.id, []))
        embed.add_field(name="Warnings", value=f"⚠️ {warns}")
        embed.add_field(name="Mod Notes", value=f"📝 {notes_count}")
        embed.add_field(name="AFK", value="💤 Yes" if member.id in self.afk_db else "No")
        if roles:
            embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles[:8]), inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=['si', 'server'])
    async def serverinfo(self, ctx):
        """Get server info. Usage: !serverinfo"""
        g = ctx.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        embed = discord.Embed(title=f"🏠 {g.name}", color=0x3498db)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=g.owner.mention)
        embed.add_field(name="Members", value=f"👤 {humans} humans\n🤖 {bots} bots")
        embed.add_field(name="Channels", value=f"💬 {len(g.text_channels)} text\n🔊 {len(g.voice_channels)} voice")
        embed.add_field(name="Roles", value=len(g.roles))
        embed.add_field(name="Created", value=g.created_at.strftime("%b %d, %Y"))
        embed.add_field(name="Boost Level", value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)")
        embed.set_footer(text=f"ID: {g.id}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
