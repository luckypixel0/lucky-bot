import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
from collections import defaultdict

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # ── Anti-Nuke Settings ─────────────────
        self.antinuke_enabled = {}       # per guild toggle
        self.antinuke_whitelist = {}     # whitelisted user IDs per guild
        self.antinuke_action = {}        # ban/kick/strip per guild

        # ── Anti-Raid Settings ─────────────────
        self.antiraid_enabled = {}
        self.raid_join_tracker = defaultdict(list)  # guild_id: [join timestamps]
        self.raid_mode_active = {}       # is raid mode currently on?

        # ── Anti-Spam Settings ─────────────────
        self.antispam_enabled = {}
        self.spam_tracker = defaultdict(list)  # user_id: [message timestamps]
        self.spam_threshold = {}         # messages per 5 seconds before action

        # ── Anti-Bot Settings ──────────────────
        self.antibot_enabled = {}        # auto kick unverified bots

        # ── Verification Settings ──────────────
        self.verification_enabled = {}
        self.verification_channel = {}
        self.verification_role = {}
        self.pending_verification = {}   # user_id: True/False

        # ── Nuke action tracker ────────────────
        # Tracks dangerous actions per user in short timeframe
        self.action_tracker = defaultdict(lambda: defaultdict(list))
        # structure: action_tracker[guild_id][user_id] = [timestamps]

        # Thresholds — how many actions before triggering anti-nuke
        self.nuke_thresholds = {
            'channel_delete': 2,
            'channel_create': 4,
            'role_delete': 2,
            'role_create': 4,
            'ban': 3,
            'kick': 3,
            'webhook_create': 3,
        }

    # ══════════════════════════════════════════
    #   HELPERS
    # ══════════════════════════════════════════

    async def send_log(self, guild, embed):
        log_channel = discord.utils.get(guild.text_channels, name='mod-logs') or \
                      discord.utils.get(guild.text_channels, name='logs') or \
                      discord.utils.get(guild.text_channels, name='security-logs')
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except:
                pass

    def is_whitelisted(self, guild_id, user_id):
        wl = self.antinuke_whitelist.get(guild_id, set())
        return user_id in wl

    async def punish_nuker(self, guild, user, reason):
        """Ban/kick/strip roles from a detected nuker"""
        action = self.antinuke_action.get(guild.id, 'ban')
        try:
            if action == 'ban':
                await guild.ban(user, reason=f"[Anti-Nuke] {reason}", delete_message_days=0)
            elif action == 'kick':
                member = guild.get_member(user.id)
                if member:
                    await member.kick(reason=f"[Anti-Nuke] {reason}")
            elif action == 'strip':
                member = guild.get_member(user.id)
                if member:
                    safe_roles = [r for r in member.roles if r.name == "@everyone"]
                    await member.edit(roles=safe_roles, reason=f"[Anti-Nuke] {reason}")
        except Exception as e:
            print(f"Anti-nuke punish error: {e}")

        embed = discord.Embed(
            title="🛡️ ANTI-NUKE TRIGGERED",
            description=f"**Nuker detected and punished!**",
            color=0xff0000,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="User", value=f"{user} ({user.id})")
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Action Taken", value=action.upper())
        embed.set_footer(text="Lucky Bot Security")
        await self.send_log(guild, embed)

    async def track_action(self, guild, user, action_type):
        """Track dangerous actions and trigger anti-nuke if threshold exceeded"""
        if not self.antinuke_enabled.get(guild.id, False):
            return
        if self.is_whitelisted(guild.id, user.id):
            return
        # Ignore bot itself and server owner
        if user.id == self.bot.user.id:
            return
        if user.id == guild.owner_id:
            return

        now = datetime.datetime.utcnow().timestamp()
        self.action_tracker[guild.id][user.id].append((action_type, now))

        # Clean up actions older than 10 seconds
        self.action_tracker[guild.id][user.id] = [
            (a, t) for a, t in self.action_tracker[guild.id][user.id]
            if now - t < 10
        ]

        # Count this specific action type in last 10 seconds
        recent = [
            a for a, t in self.action_tracker[guild.id][user.id]
            if a == action_type and now - t < 10
        ]

        threshold = self.nuke_thresholds.get(action_type, 3)
        if len(recent) >= threshold:
            # Clear tracker to avoid double punishment
            self.action_tracker[guild.id][user.id] = []
            await self.punish_nuker(
                guild, user,
                f"Exceeded {action_type} threshold ({len(recent)} in 10s)"
            )

    # ══════════════════════════════════════════
    #   ANTI-NUKE LISTENERS
    # ══════════════════════════════════════════

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            await self.track_action(channel.guild, entry.user, 'channel_delete')

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            await self.track_action(channel.guild, entry.user, 'channel_create')

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            await self.track_action(role.guild, entry.user, 'role_delete')

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            await self.track_action(role.guild, entry.user, 'role_create')

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                await self.track_action(guild, entry.user, 'ban')

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                await self.track_action(member.guild, entry.user, 'kick')

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
            await self.track_action(channel.guild, entry.user, 'webhook_create')

    # ══════════════════════════════════════════
    #   ANTI-RAID LISTENER
    # ══════════════════════════════════════════

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild

        # ── Anti-Bot check ─────────────────────
        if self.antibot_enabled.get(guild.id, False):
            if member.bot:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
                    if not self.is_whitelisted(guild.id, entry.user.id):
                        try:
                            await member.kick(reason="[Anti-Bot] Unauthorized bot added")
                            embed = discord.Embed(
                                title="🤖 Anti-Bot Triggered",
                                description=f"Unauthorized bot **{member}** was kicked!\nAdded by: {entry.user.mention}",
                                color=0xff6600,
                                timestamp=datetime.datetime.utcnow()
                            )
                            await self.send_log(guild, embed)
                        except:
                            pass
                        return

        # ── Anti-Raid check ────────────────────
        if not self.antiraid_enabled.get(guild.id, False):
            return

        now = datetime.datetime.utcnow().timestamp()
        self.raid_join_tracker[guild.id].append(now)

        # Keep only joins from last 10 seconds
        self.raid_join_tracker[guild.id] = [
            t for t in self.raid_join_tracker[guild.id]
            if now - t < 10
        ]

        recent_joins = len(self.raid_join_tracker[guild.id])

        # 8 or more joins in 10 seconds = raid
        if recent_joins >= 8 and not self.raid_mode_active.get(guild.id, False):
            self.raid_mode_active[guild.id] = True
            embed = discord.Embed(
                title="🚨 RAID DETECTED — LOCKDOWN ACTIVATED",
                description=(
                    f"**{recent_joins} members joined in 10 seconds!**\n\n"
                    "✅ Server is now in lockdown mode.\n"
                    "All new members will be kicked automatically.\n\n"
                    "Use `!antiraid off` to disable lockdown."
                ),
                color=0xff0000,
                timestamp=datetime.datetime.utcnow()
            )
            await self.send_log(guild, embed)

            # Lock all channels
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(guild.default_role, send_messages=False)
                except:
                    pass

        # If raid mode active, kick new joins
        if self.raid_mode_active.get(guild.id, False):
            try:
                await member.kick(reason="[Anti-Raid] Server is in lockdown mode")
            except:
                pass

        # ── Verification check ─────────────────
        if self.verification_enabled.get(guild.id, False):
            ver_channel_id = self.verification_channel.get(guild.id)
            ver_channel = guild.get_channel(ver_channel_id) if ver_channel_id else None
            if ver_channel:
                try:
                    # Remove all roles from new member until verified
                    await member.send(
                        f"👋 Welcome to **{guild.name}**!\n"
                        f"Please go to {ver_channel.mention} and type `!verify` to gain access."
                    )
                except:
                    pass

    # ══════════════════════════════════════════
    #   ANTI-SPAM LISTENER
    # ══════════════════════════════════════════

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if not self.antispam_enabled.get(message.guild.id, False):
            return
        if message.author.guild_permissions.manage_messages:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = datetime.datetime.utcnow().timestamp()

        key = f"{guild_id}:{user_id}"
        self.spam_tracker[key].append(now)

        # Keep only messages from last 5 seconds
        self.spam_tracker[key] = [
            t for t in self.spam_tracker[key]
            if now - t < 5
        ]

        threshold = self.spam_threshold.get(guild_id, 5)

        if len(self.spam_tracker[key]) >= threshold:
            self.spam_tracker[key] = []
            # Timeout for 5 minutes
            until = discord.utils.utcnow() + datetime.timedelta(minutes=5)
            try:
                await message.author.timeout(until, reason="[Anti-Spam] Spamming messages")
                embed = discord.Embed(
                    title="🔇 Anti-Spam Triggered",
                    description=f"{message.author.mention} was muted for 5 minutes for spamming!",
                    color=0xff6600,
                    timestamp=datetime.datetime.utcnow()
                )
                embed.add_field(name="Messages", value=f"{threshold} messages in 5 seconds")
                embed.add_field(name="Channel", value=message.channel.mention)
                await self.send_log(message.guild, embed)
                try:
                    await message.channel.send(
                        f"🔇 {message.author.mention} slow down! You've been muted for 5 minutes.",
                        delete_after=5
                    )
                except:
                    pass
            except:
                pass

    # ══════════════════════════════════════════
    #   ANTI-NUKE COMMANDS
    # ══════════════════════════════════════════

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx):
        """
        Anti-Nuke system.
        Usage: !antinuke on/off/status/whitelist/action
        """
        status = self.antinuke_enabled.get(ctx.guild.id, False)
        action = self.antinuke_action.get(ctx.guild.id, 'ban')
        wl = self.antinuke_whitelist.get(ctx.guild.id, set())
        wl_mentions = [f"<@{uid}>" for uid in wl] or ["None"]
        embed = discord.Embed(
            title="🛡️ Anti-Nuke Status",
            color=0x2ecc71 if status else 0xe74c3c
        )
        embed.add_field(name="Status", value="✅ ON" if status else "❌ OFF")
        embed.add_field(name="Punishment", value=action.upper())
        embed.add_field(name="Whitelisted", value=", ".join(wl_mentions))
        embed.add_field(
            name="Thresholds",
            value=(
                "Channel delete: 2 in 10s\n"
                "Channel create: 4 in 10s\n"
                "Role delete: 2 in 10s\n"
                "Mass ban: 3 in 10s\n"
                "Mass kick: 3 in 10s"
            ),
            inline=False
        )
        embed.add_field(
            name="Commands",
            value=(
                "`!antinuke on` — enable\n"
                "`!antinuke off` — disable\n"
                "`!antinuke whitelist @user` — whitelist a user\n"
                "`!antinuke unwhitelist @user` — remove from whitelist\n"
                "`!antinuke action ban/kick/strip` — set punishment"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @antinuke.command(name='on')
    @commands.has_permissions(administrator=True)
    async def antinuke_on(self, ctx):
        self.antinuke_enabled[ctx.guild.id] = True
        embed = discord.Embed(
            title="🛡️ Anti-Nuke ENABLED",
            description=(
                "Your server is now protected!\n\n"
                "Any user who attempts to:\n"
                "• Mass delete channels\n"
                "• Mass delete roles\n"
                "• Mass ban/kick members\n"
                "• Mass create webhooks\n\n"
                "...will be automatically punished."
            ),
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        log = discord.Embed(title="🛡️ Anti-Nuke Enabled", color=0x2ecc71,
            timestamp=datetime.datetime.utcnow())
        log.add_field(name="Enabled by", value=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @antinuke.command(name='off')
    @commands.has_permissions(administrator=True)
    async def antinuke_off(self, ctx):
        self.antinuke_enabled[ctx.guild.id] = False
        await ctx.reply("⚠️ Anti-Nuke has been **disabled**. Your server is unprotected!")

    @antinuke.command(name='whitelist')
    @commands.has_permissions(administrator=True)
    async def antinuke_whitelist(self, ctx, member: discord.Member):
        """Whitelist a trusted user. Usage: !antinuke whitelist @user"""
        guild_id = ctx.guild.id
        if guild_id not in self.antinuke_whitelist:
            self.antinuke_whitelist[guild_id] = set()
        self.antinuke_whitelist[guild_id].add(member.id)
        await ctx.reply(f"✅ {member.mention} is now **whitelisted** from anti-nuke!")

    @antinuke.command(name='unwhitelist')
    @commands.has_permissions(administrator=True)
    async def antinuke_unwhitelist(self, ctx, member: discord.Member):
        """Remove from whitelist. Usage: !antinuke unwhitelist @user"""
        guild_id = ctx.guild.id
        if guild_id in self.antinuke_whitelist:
            self.antinuke_whitelist[guild_id].discard(member.id)
        await ctx.reply(f"✅ {member.mention} removed from whitelist!")

    @antinuke.command(name='action')
    @commands.has_permissions(administrator=True)
    async def antinuke_action_cmd(self, ctx, action: str):
        """
        Set punishment for nukers.
        Usage: !antinuke action ban
               !antinuke action kick
               !antinuke action strip
        """
        action = action.lower()
        if action not in ('ban', 'kick', 'strip'):
            return await ctx.reply("❌ Choose: `ban`, `kick`, or `strip`")
        self.antinuke_action[ctx.guild.id] = action
        descriptions = {
            'ban': 'Nukers will be permanently banned',
            'kick': 'Nukers will be kicked from the server',
            'strip': 'Nukers will have all roles removed'
        }
        await ctx.reply(f"✅ Anti-nuke action set to **{action.upper()}**\n{descriptions[action]}")

    # ══════════════════════════════════════════
    #   ANTI-RAID COMMANDS
    # ══════════════════════════════════════════

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antiraid(self, ctx):
        """
        Anti-Raid system.
        Usage: !antiraid on/off/status/lockdown
        """
        raid_on = self.antiraid_enabled.get(ctx.guild.id, False)
        lockdown = self.raid_mode_active.get(ctx.guild.id, False)
        embed = discord.Embed(title="🚨 Anti-Raid Status", color=0x2ecc71 if raid_on else 0xe74c3c)
        embed.add_field(name="Status", value="✅ ON" if raid_on else "❌ OFF")
        embed.add_field(name="Lockdown Active", value="🔴 YES" if lockdown else "🟢 No")
        embed.add_field(name="Trigger", value="8+ joins in 10 seconds")
        embed.add_field(
            name="Commands",
            value=(
                "`!antiraid on` — enable\n"
                "`!antiraid off` — disable\n"
                "`!antiraid lockdown` — manually lock server\n"
                "`!antiraid unlock` — end lockdown"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @antiraid.command(name='on')
    @commands.has_permissions(administrator=True)
    async def antiraid_on(self, ctx):
        self.antiraid_enabled[ctx.guild.id] = True
        embed = discord.Embed(
            title="🚨 Anti-Raid ENABLED",
            description=(
                "Server is now protected from raids!\n\n"
                "If **8+ members** join within **10 seconds**:\n"
                "• Server goes into lockdown\n"
                "• All channels get locked\n"
                "• New joins get kicked automatically\n"
                "• You get alerted in mod-logs\n\n"
                "Use `!antiraid unlock` to end lockdown."
            ),
            color=0x2ecc71
        )
        await ctx.send(embed=embed)

    @antiraid.command(name='off')
    @commands.has_permissions(administrator=True)
    async def antiraid_off(self, ctx):
        self.antiraid_enabled[ctx.guild.id] = False
        self.raid_mode_active[ctx.guild.id] = False
        await ctx.reply("⚠️ Anti-Raid has been **disabled**!")

    @antiraid.command(name='lockdown')
    @commands.has_permissions(administrator=True)
    async def antiraid_lockdown(self, ctx):
        """Manually lock the entire server. Usage: !antiraid lockdown"""
        self.raid_mode_active[ctx.guild.id] = True
        locked = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=False)
                locked += 1
            except:
                pass
        embed = discord.Embed(
            title="🔴 SERVER LOCKDOWN",
            description=(
                f"**Manual lockdown activated by {ctx.author.mention}**\n\n"
                f"Locked **{locked}** channels.\n"
                "New joins will be kicked.\n\n"
                "Use `!antiraid unlock` to end lockdown."
            ),
            color=0xff0000
        )
        await ctx.send(embed=embed)
        await self.send_log(ctx.guild, embed)

    @antiraid.command(name='unlock')
    @commands.has_permissions(administrator=True)
    async def antiraid_unlock(self, ctx):
        """End lockdown. Usage: !antiraid unlock"""
        self.raid_mode_active[ctx.guild.id] = False
        unlocked = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=True)
                unlocked += 1
            except:
                pass
        embed = discord.Embed(
            title="🟢 Lockdown Ended",
            description=(
                f"Lockdown ended by {ctx.author.mention}\n"
                f"Unlocked **{unlocked}** channels.\n"
                "Server is back to normal!"
            ),
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        await self.send_log(ctx.guild, embed)

    # ══════════════════════════════════════════
    #   ANTI-SPAM COMMANDS
    # ══════════════════════════════════════════

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antispam(self, ctx):
        """
        Anti-Spam system.
        Usage: !antispam on/off/threshold
        """
        status = self.antispam_enabled.get(ctx.guild.id, False)
        threshold = self.spam_threshold.get(ctx.guild.id, 5)
        embed = discord.Embed(title="💬 Anti-Spam Status", color=0x2ecc71 if status else 0xe74c3c)
        embed.add_field(name="Status", value="✅ ON" if status else "❌ OFF")
        embed.add_field(name="Threshold", value=f"{threshold} messages / 5 seconds")
        embed.add_field(name="Action", value="Timeout for 5 minutes")
        embed.add_field(
            name="Commands",
            value=(
                "`!antispam on` — enable\n"
                "`!antispam off` — disable\n"
                "`!antispam threshold 5` — set message limit"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @antispam.command(name='on')
    @commands.has_permissions(administrator=True)
    async def antispam_on(self, ctx):
        self.antispam_enabled[ctx.guild.id] = True
        await ctx.reply("✅ Anti-Spam **enabled**! Anyone sending too many messages will be auto-muted.")

    @antispam.command(name='off')
    @commands.has_permissions(administrator=True)
    async def antispam_off(self, ctx):
        self.antispam_enabled[ctx.guild.id] = False
        await ctx.reply("⚠️ Anti-Spam **disabled**!")

    @antispam.command(name='threshold')
    @commands.has_permissions(administrator=True)
    async def antispam_threshold(self, ctx, amount: int):
        """Set spam threshold. Usage: !antispam threshold 5"""
        if amount < 3 or amount > 20:
            return await ctx.reply("❌ Threshold must be between 3 and 20!")
        self.spam_threshold[ctx.guild.id] = amount
        await ctx.reply(f"✅ Spam threshold set to **{amount} messages per 5 seconds**!")

    # ══════════════════════════════════════════
    #   ANTI-BOT COMMANDS
    # ══════════════════════════════════════════

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antibot(self, ctx):
        """
        Anti-Bot system — kicks unauthorized bots.
        Usage: !antibot on/off
        """
        status = self.antibot_enabled.get(ctx.guild.id, False)
        embed = discord.Embed(title="🤖 Anti-Bot Status", color=0x2ecc71 if status else 0xe74c3c)
        embed.add_field(name="Status", value="✅ ON" if status else "❌ OFF")
        embed.add_field(name="Action", value="Auto-kick unauthorized bots")
        embed.add_field(
            name="Note",
            value="Whitelist trusted bot adders with `!antinuke whitelist @user`",
            inline=False
        )
        embed.add_field(
            name="Commands",
            value="`!antibot on` — enable\n`!antibot off` — disable",
            inline=False
        )
        await ctx.send(embed=embed)

    @antibot.command(name='on')
    @commands.has_permissions(administrator=True)
    async def antibot_on(self, ctx):
        self.antibot_enabled[ctx.guild.id] = True
        await ctx.reply(
            "✅ Anti-Bot **enabled**!\n"
            "Any bot added by a non-whitelisted user will be kicked.\n"
            "Use `!antinuke whitelist @user` to allow someone to add bots."
        )

    @antibot.command(name='off')
    @commands.has_permissions(administrator=True)
    async def antibot_off(self, ctx):
        self.antibot_enabled[ctx.guild.id] = False
        await ctx.reply("⚠️ Anti-Bot **disabled**!")

    # ══════════════════════════════════════════
    #   SECURITY STATUS
    # ══════════════════════════════════════════

    def _build_security_embed(self, guild):
        guild_id = guild.id

        def status(val):
            return "✅ ON" if val else "❌ OFF"

        embed = discord.Embed(
            title="🔐 Security Overview",
            description=f"Full security status for **{guild.name}**",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name="🛡️ Anti-Nuke",
            value=(
                f"Status: {status(self.antinuke_enabled.get(guild_id, False))}\\n"
                f"Action: {self.antinuke_action.get(guild_id, 'ban').upper()}\\n"
                f"Whitelist: {len(self.antinuke_whitelist.get(guild_id, set()))} users"
            ),
        )
        embed.add_field(
            name="🚨 Anti-Raid",
            value=(
                f"Status: {status(self.antiraid_enabled.get(guild_id, False))}\\n"
                f"Lockdown: {'🔴 ACTIVE' if self.raid_mode_active.get(guild_id, False) else '🟢 Inactive'}"
            ),
        )
        embed.add_field(
            name="💬 Anti-Spam",
            value=(
                f"Status: {status(self.antispam_enabled.get(guild_id, False))}\\n"
                f"Threshold: {self.spam_threshold.get(guild_id, 5)} msgs/5s"
            ),
        )
        embed.add_field(
            name="🤖 Anti-Bot",
            value=f"Status: {status(self.antibot_enabled.get(guild_id, False))}",
        )
        embed.add_field(
            name="Quick Enable All",
            value=(
                "`!antinuke on`\\n"
                "`!antiraid on`\\n"
                "`!antispam on`\\n"
                "`!antibot on`"
            ),
            inline=False,
        )
        embed.set_footer(text="Lucky Bot Security")
        return embed

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def security(self, ctx):
        """Full security overview. Usage: !security"""
        await ctx.send(embed=self._build_security_embed(ctx.guild))

    @app_commands.command(name='security', description='Show server security overview')
    async def security_slash(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Admin Only",
                    description="You need Administrator permission to use this command.",
                    color=0xe74c3c,
                ),
                ephemeral=True,
            )
        await interaction.response.send_message(embed=self._build_security_embed(interaction.guild))

async def setup(bot):
    await bot.add_cog(Security(bot))
