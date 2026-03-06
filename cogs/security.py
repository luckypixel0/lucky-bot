import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import asyncio
import collections


# ══════════════════════════════════════════════════════════════════════════════
#   LUCKY BOT — security.py
#   Features:
#     ANTINUKE  → anti-ban, anti-kick, anti-channel, anti-role, anti-webhook,
#                 anti-prune, anti-everyone, anti-guild, anti-bot, anti-mention,
#                 anti-emoji, anti-sticker, anti-thread, anti-vc, anti-integration
#     ANTIRAID  → mass-join detection, account age filter, no-avatar filter,
#                 bot-raid filter, join lockdown, auto-punish raiders
#     EXTRAS    → panic mode, recovery mode, whitelist, punish settings,
#                 per-action thresholds, stats, log channel, wizard
# ══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────
#   DEFAULT CONFIGS
# ─────────────────────────────────────────

DEFAULT_ANTINUKE = {
    'enabled': False,
    'log_channel': None,          # channel ID
    'punish': 'ban',              # ban | kick | mute | strip | derank
    'whitelist': set(),           # user IDs exempt from antinuke
    # Individual module toggles
    'anti_ban': True,
    'anti_kick': True,
    'anti_channel': True,
    'anti_role': True,
    'anti_webhook': True,
    'anti_prune': True,
    'anti_everyone': True,
    'anti_guild': True,
    'anti_bot': True,
    'anti_mention': True,
    'anti_emoji': True,
    'anti_sticker': True,
    'anti_thread': True,
    'anti_vc': True,
    'anti_integration': True,
    # Per-action thresholds (actions within 10 seconds)
    'thresholds': {
        'ban': 2,
        'kick': 3,
        'channel_delete': 2,
        'channel_create': 4,
        'role_delete': 2,
        'role_create': 4,
        'role_dangerous': 1,    # give admin/dangerous perms
        'webhook_create': 2,
        'prune': 1,
        'everyone': 2,
        'emoji_delete': 5,
        'sticker_delete': 3,
        'thread_create': 5,
        'vc_delete': 2,
        'integration_create': 1,
    },
}

DEFAULT_ANTIRAID = {
    'enabled': False,
    'log_channel': None,
    'punish': 'kick',             # ban | kick | mute
    'whitelist': set(),
    'join_threshold': 10,         # joins in window = raid trigger
    'join_window': 10,            # seconds
    'min_account_age': 0,         # days (0 = disabled)
    'no_avatar': False,           # block users with no avatar
    'no_bio': False,              # block users with no bio (heuristic)
    'anti_bot_raid': True,        # block bot accounts during raid
    'lockdown_on_raid': True,     # auto-lockdown server on raid detection
    'lockdown_active': False,
}

DANGEROUS_PERMS = (
    'administrator',
    'ban_members',
    'kick_members',
    'manage_guild',
    'manage_roles',
    'manage_channels',
    'manage_webhooks',
    'mention_everyone',
)

PUNISH_LABELS = {
    'ban':     '🔨 Banned',
    'kick':    '👢 Kicked',
    'mute':    '🔇 Muted (1h)',
    'strip':   '🎭 Roles Stripped',
    'derank':  '⬇️ Deranked (all roles removed)',
}


# ─────────────────────────────────────────
#   ACTION TRACKER  (sliding window counter)
# ─────────────────────────────────────────

class ActionTracker:
    """Tracks how many times user_id performed `action` in the last `window` seconds."""
    def __init__(self):
        # {guild_id: {user_id: {action: deque of timestamps}}}
        self._data: dict[int, dict[int, dict[str, collections.deque]]] = {}

    def record(self, guild_id: int, user_id: int, action: str) -> int:
        """Record an action and return current count within window."""
        now = datetime.datetime.utcnow().timestamp()
        window = 10  # seconds

        g = self._data.setdefault(guild_id, {})
        u = g.setdefault(user_id, {})
        q = u.setdefault(action, collections.deque())

        q.append(now)
        # Prune old
        while q and now - q[0] > window:
            q.popleft()
        return len(q)

    def reset(self, guild_id: int, user_id: int):
        """Clear all action counts for a user."""
        self._data.get(guild_id, {}).pop(user_id, None)

    def guild_reset(self, guild_id: int):
        self._data.pop(guild_id, None)


# ─────────────────────────────────────────
#   RECOVERY SNAPSHOT
# ─────────────────────────────────────────

class RecoverySnapshot:
    """Stores a snapshot of guild state so damage can be undone."""
    def __init__(self):
        # {guild_id: snapshot_dict}
        self._snaps: dict[int, dict] = {}

    def save(self, guild: discord.Guild):
        snap = {
            'name': guild.name,
            'icon': guild.icon.url if guild.icon else None,
            'description': guild.description,
            'roles': [(r.id, r.name, r.permissions.value, r.color.value, r.position)
                      for r in guild.roles if not r.managed and r != guild.default_role],
            'channels': [(c.id, c.name, str(c.type)) for c in guild.channels],
            'timestamp': datetime.datetime.utcnow(),
        }
        self._snaps[guild.id] = snap

    def get(self, guild_id: int) -> dict | None:
        return self._snaps.get(guild_id)


# ══════════════════════════════════════════════════════════════════════════════
#   COG
# ══════════════════════════════════════════════════════════════════════════════

class Security(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Per-guild config  {guild_id: config_dict}
        self.antinuke_config:  dict[int, dict] = {}
        self.antiraid_config:  dict[int, dict] = {}

        # Stats  {guild_id: {action: count}}
        self.stats: dict[int, dict] = {}

        # Recent join timestamps for raid detection  {guild_id: deque}
        self.join_log: dict[int, collections.deque] = {}

        # Recovery & tracker
        self.tracker   = ActionTracker()
        self.snapshots = RecoverySnapshot()

        # Panic mode set of guild IDs
        self.panic_guilds: set[int] = set()

        # Currently being punished (prevent duplicate punishment loops)
        self._punishing: set[tuple[int, int]] = set()

        # Auto-snapshot task
        self.auto_snapshot.start()

    def cog_unload(self):
        self.auto_snapshot.cancel()

    # ══════════════════════════════════════
    #   HELPERS
    # ══════════════════════════════════════

    def _an_cfg(self, guild_id: int) -> dict:
        if guild_id not in self.antinuke_config:
            import copy
            self.antinuke_config[guild_id] = copy.deepcopy(DEFAULT_ANTINUKE)
        return self.antinuke_config[guild_id]

    def _ar_cfg(self, guild_id: int) -> dict:
        if guild_id not in self.antiraid_config:
            import copy
            self.antiraid_config[guild_id] = copy.deepcopy(DEFAULT_ANTIRAID)
        return self.antiraid_config[guild_id]

    def _bump_stat(self, guild_id: int, action: str):
        self.stats.setdefault(guild_id, {})
        self.stats[guild_id][action] = self.stats[guild_id].get(action, 0) + 1

    def _is_whitelisted(self, guild_id: int, user_id: int) -> bool:
        cfg = self._an_cfg(guild_id)
        if user_id in cfg['whitelist']:
            return True
        # Also check ExtraOwner / bot owner
        mod_cog = self.bot.get_cog('Moderation')
        if mod_cog:
            guild = self.bot.get_guild(guild_id)
            if guild and user_id == guild.owner_id:
                return True
            if user_id in mod_cog.extraowners.get(guild_id, set()):
                return True
        if user_id == self.bot.BOT_OWNER_ID:
            return True
        return False

    async def _get_log_channel(self, guild: discord.Guild, mode='antinuke') -> discord.TextChannel | None:
        cfg = self._an_cfg(guild.id) if mode == 'antinuke' else self._ar_cfg(guild.id)
        ch_id = cfg.get('log_channel')
        if ch_id:
            ch = guild.get_channel(ch_id)
            if ch:
                return ch
        # Fall back to setup.py channel bind or default name
        setup_cog = self.bot.get_cog('Setup')
        if setup_cog:
            return setup_cog._get_channel(guild, 'security-logs')
        return discord.utils.get(guild.text_channels, name='security-logs')

    async def _log(self, guild: discord.Guild, embed: discord.Embed, mode='antinuke'):
        ch = await self._get_log_channel(guild, mode)
        if ch:
            try:
                await ch.send(embed=embed)
            except Exception:
                pass

    async def _punish(self, guild: discord.Guild, member: discord.Member,
                      reason: str, action: str, cfg: dict):
        key = (guild.id, member.id)
        if key in self._punishing:
            return
        self._punishing.add(key)
        punish = cfg.get('punish', 'ban')
        try:
            if punish == 'ban':
                await guild.ban(member, reason=f'🛡️ Lucky Antinuke: {reason}', delete_message_days=0)
            elif punish == 'kick':
                await member.kick(reason=f'🛡️ Lucky Antinuke: {reason}')
            elif punish == 'mute':
                until = discord.utils.utcnow() + datetime.timedelta(hours=1)
                await member.timeout(until, reason=f'🛡️ Lucky Antinuke: {reason}')
            elif punish in ('strip', 'derank'):
                removable = [r for r in member.roles if r != guild.default_role and not r.managed]
                await member.remove_roles(*removable, reason=f'🛡️ Lucky Antinuke: {reason}')
        except Exception:
            pass
        finally:
            self._punishing.discard(key)
            self.tracker.reset(guild.id, member.id)

    def _action_embed(self, title: str, description: str,
                      color=discord.Color.red()) -> discord.Embed:
        embed = discord.Embed(title=title, description=description, color=color,
                              timestamp=datetime.datetime.utcnow())
        embed.set_footer(text='🛡️ Lucky Bot Security')
        return embed

    # ══════════════════════════════════════
    #   AUTO-SNAPSHOT TASK  (every 30 min)
    # ══════════════════════════════════════

    @tasks.loop(minutes=30)
    async def auto_snapshot(self):
        for guild in self.bot.guilds:
            cfg = self._an_cfg(guild.id)
            if cfg.get('enabled'):
                self.snapshots.save(guild)

    @auto_snapshot.before_loop
    async def before_snapshot(self):
        await self.bot.wait_until_ready()

    # ══════════════════════════════════════
    #   ANTINUKE — AUDIT LOG HELPER
    # ══════════════════════════════════════

    async def _get_executor(self, guild: discord.Guild,
                            action: discord.AuditLogAction,
                            target_id: int | None = None) -> discord.Member | None:
        """Fetch the executor of a recent audit log entry."""
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if target_id is None or (entry.target and entry.target.id == target_id):
                    if (datetime.datetime.utcnow() - entry.created_at.replace(tzinfo=None)).seconds < 8:
                        return guild.get_member(entry.user_id)
        except Exception:
            pass
        return None

    # ══════════════════════════════════════
    #   ANTINUKE EVENTS
    # ══════════════════════════════════════

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_ban']:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.ban, user.id)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        count = self.tracker.record(guild.id, executor.id, 'ban')
        threshold = cfg['thresholds']['ban']
        self._bump_stat(guild.id, 'anti_ban')
        if count >= threshold:
            embed = self._action_embed(
                '🚨 Anti-Ban Triggered',
                f'**{executor}** (`{executor.id}`) banned **{count}** members in 10s '
                f'(threshold: {threshold})\n\n**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
            )
            await self._log(guild, embed)
            member = guild.get_member(executor.id)
            if member:
                await self._punish(guild, member, f'Mass ban ({count} bans)', 'ban', cfg)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_kick']:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.kick, member.id)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        count = self.tracker.record(guild.id, executor.id, 'kick')
        threshold = cfg['thresholds']['kick']
        self._bump_stat(guild.id, 'anti_kick')
        if count >= threshold:
            embed = self._action_embed(
                '🚨 Anti-Kick Triggered',
                f'**{executor}** kicked **{count}** members in 10s '
                f'(threshold: {threshold})\n**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
            )
            await self._log(guild, embed)
            exec_member = guild.get_member(executor.id)
            if exec_member:
                await self._punish(guild, exec_member, f'Mass kick ({count} kicks)', 'kick', cfg)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_channel']:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.channel_delete, channel.id)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        count = self.tracker.record(guild.id, executor.id, 'channel_delete')
        threshold = cfg['thresholds']['channel_delete']
        self._bump_stat(guild.id, 'anti_channel')
        if count >= threshold:
            embed = self._action_embed(
                '🚨 Anti-Channel Triggered',
                f'**{executor}** deleted **{count}** channels in 10s '
                f'(threshold: {threshold})\n**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
            )
            await self._log(guild, embed)
            member = guild.get_member(executor.id)
            if member:
                await self._punish(guild, member, f'Mass channel delete ({count})', 'channel_delete', cfg)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_channel']:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.channel_create, channel.id)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        count = self.tracker.record(guild.id, executor.id, 'channel_create')
        threshold = cfg['thresholds']['channel_create']
        if count >= threshold:
            embed = self._action_embed(
                '⚠️ Anti-Channel (Create) Triggered',
                f'**{executor}** created **{count}** channels in 10s (threshold: {threshold})',
            )
            await self._log(guild, embed)
            member = guild.get_member(executor.id)
            if member:
                await self._punish(guild, member, f'Mass channel create ({count})', 'channel_create', cfg)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_role']:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.role_delete, role.id)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        count = self.tracker.record(guild.id, executor.id, 'role_delete')
        threshold = cfg['thresholds']['role_delete']
        self._bump_stat(guild.id, 'anti_role')
        if count >= threshold:
            embed = self._action_embed(
                '🚨 Anti-Role Triggered',
                f'**{executor}** deleted **{count}** roles in 10s (threshold: {threshold})\n'
                f'**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
            )
            await self._log(guild, embed)
            member = guild.get_member(executor.id)
            if member:
                await self._punish(guild, member, f'Mass role delete ({count})', 'role_delete', cfg)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        guild = after.guild
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_role']:
            return
        # Check if dangerous permissions were added
        new_perms = set()
        for perm in DANGEROUS_PERMS:
            if not getattr(before.permissions, perm) and getattr(after.permissions, perm):
                new_perms.add(perm)
        if not new_perms:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.role_update, after.id)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        self._bump_stat(guild.id, 'anti_role_dangerous')
        embed = self._action_embed(
            '🚨 Dangerous Role Permission Added',
            f'**{executor}** gave `{after.name}` dangerous perms: '
            f'`{", ".join(new_perms)}`\n**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
        )
        await self._log(guild, embed)
        member = guild.get_member(executor.id)
        if member:
            # Revert the permission change
            try:
                await after.edit(permissions=before.permissions,
                                 reason='🛡️ Lucky Antinuke: dangerous perm revert')
            except Exception:
                pass
            await self._punish(guild, member, f'Dangerous role edit ({", ".join(new_perms)})',
                               'role_dangerous', cfg)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_webhook']:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.webhook_create)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        count = self.tracker.record(guild.id, executor.id, 'webhook_create')
        threshold = cfg['thresholds']['webhook_create']
        self._bump_stat(guild.id, 'anti_webhook')
        if count >= threshold:
            embed = self._action_embed(
                '🚨 Anti-Webhook Triggered',
                f'**{executor}** created **{count}** webhooks in 10s (threshold: {threshold})\n'
                f'**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
            )
            await self._log(guild, embed)
            member = guild.get_member(executor.id)
            if member:
                await self._punish(guild, member, f'Mass webhook create ({count})', 'webhook', cfg)
            # Auto-delete the webhooks
            try:
                hooks = await channel.webhooks()
                for h in hooks:
                    if h.user and h.user.id == executor.id:
                        await h.delete(reason='🛡️ Lucky Antinuke: webhook removed')
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        cfg = self._an_cfg(after.id)
        if not cfg['enabled'] or not cfg['anti_guild']:
            return
        changed = []
        if before.name != after.name:
            changed.append(f'Name: `{before.name}` → `{after.name}`')
        if before.icon != after.icon:
            changed.append('Icon changed')
        if before.description != after.description:
            changed.append(f'Description changed')
        if before.banner != after.banner:
            changed.append('Banner changed')
        if before.splash != after.splash:
            changed.append('Invite splash changed')
        if not changed:
            return
        executor = await self._get_executor(after, discord.AuditLogAction.guild_update)
        if not executor or executor.bot or self._is_whitelisted(after.id, executor.id):
            return
        self._bump_stat(after.id, 'anti_guild')
        embed = self._action_embed(
            '🚨 Anti-Guild Update Triggered',
            f'**{executor}** changed server settings:\n' + '\n'.join(f'• {c}' for c in changed) +
            f'\n**Punishment:** Muted 2 minutes',
        )
        await self._log(after, embed)
        member = after.get_member(executor.id)
        if member:
            until = discord.utils.utcnow() + datetime.timedelta(minutes=2)
            try:
                await member.timeout(until, reason='🛡️ Lucky Antinuke: unauthorized server edit')
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg = self._an_cfg(guild.id)
        ar_cfg = self._ar_cfg(guild.id)

        # ── ANTINUKE: anti-bot ──
        if cfg['enabled'] and cfg['anti_bot'] and member.bot:
            executor = await self._get_executor(guild, discord.AuditLogAction.bot_add, member.id)
            if executor and not executor.bot and not self._is_whitelisted(guild.id, executor.id):
                self._bump_stat(guild.id, 'anti_bot')
                embed = self._action_embed(
                    '🚨 Anti-Bot Triggered',
                    f'**{executor}** added bot **{member}** without authorization.\n'
                    f'**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
                )
                await self._log(guild, embed)
                exec_member = guild.get_member(executor.id)
                if exec_member:
                    await self._punish(guild, exec_member, f'Unauthorized bot add ({member})', 'bot', cfg)
                # Kick the bot
                try:
                    await member.kick(reason='🛡️ Lucky Antinuke: unauthorized bot')
                except Exception:
                    pass
                return

        # ── ANTIRAID ──
        if not ar_cfg['enabled']:
            return

        now = datetime.datetime.utcnow().timestamp()

        # Panic mode — block all joins
        if guild.id in self.panic_guilds:
            try:
                await member.kick(reason='🛡️ Lucky Bot: Panic mode active — all joins blocked')
            except Exception:
                pass
            return

        # Lockdown active
        if ar_cfg['lockdown_active']:
            try:
                await member.kick(reason='🛡️ Lucky Bot: Server lockdown active')
            except Exception:
                pass
            return

        # Account age check
        min_age = ar_cfg.get('min_account_age', 0)
        if min_age > 0:
            age_days = (datetime.datetime.utcnow() - member.created_at.replace(tzinfo=None)).days
            if age_days < min_age:
                self._bump_stat(guild.id, 'antiraid_age_kick')
                try:
                    await member.kick(reason=f'🛡️ Lucky Antiraid: account too new ({age_days}d < {min_age}d)')
                except Exception:
                    pass
                embed = self._action_embed(
                    '⚠️ Antiraid — New Account Blocked',
                    f'**{member}** (`{member.id}`) was kicked — account age {age_days} days '
                    f'(minimum: {min_age} days)',
                    color=discord.Color.orange(),
                )
                await self._log(guild, embed, mode='antiraid')
                return

        # No avatar check
        if ar_cfg.get('no_avatar') and not member.avatar:
            self._bump_stat(guild.id, 'antiraid_noavatar_kick')
            try:
                await member.kick(reason='🛡️ Lucky Antiraid: no profile picture (suspicious)')
            except Exception:
                pass
            embed = self._action_embed(
                '⚠️ Antiraid — No Avatar Blocked',
                f'**{member}** (`{member.id}`) was kicked — no profile picture',
                color=discord.Color.orange(),
            )
            await self._log(guild, embed, mode='antiraid')
            return

        # Anti-bot-raid (bots joining without being whitelisted)
        if ar_cfg.get('anti_bot_raid') and member.bot and member.id not in ar_cfg['whitelist']:
            try:
                await member.kick(reason='🛡️ Lucky Antiraid: bot blocked during raid protection')
            except Exception:
                pass
            return

        # Mass-join detection
        q = self.join_log.setdefault(guild.id, collections.deque())
        q.append(now)
        # Prune old entries outside window
        window = ar_cfg['join_window']
        while q and now - q[0] > window:
            q.popleft()

        threshold = ar_cfg['join_threshold']
        if len(q) >= threshold:
            self._bump_stat(guild.id, 'antiraid_massjoin')
            if ar_cfg['lockdown_on_raid'] and not ar_cfg['lockdown_active']:
                ar_cfg['lockdown_active'] = True
                embed = self._action_embed(
                    '🚨 RAID DETECTED — Server Locked Down',
                    f'**{len(q)} members** joined in **{window} seconds** (threshold: {threshold})\n\n'
                    '🔒 Server is now in **lockdown** — new joins will be kicked.\n'
                    f'Lift with `!antiraid lockdown off`',
                    color=discord.Color.dark_red(),
                )
                await self._log(guild, embed, mode='antiraid')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        guild = message.guild
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled']:
            return

        # ── Anti-everyone ──
        if cfg['anti_everyone'] and (message.mention_everyone):
            if not self._is_whitelisted(guild.id, message.author.id):
                count = self.tracker.record(guild.id, message.author.id, 'everyone')
                threshold = cfg['thresholds']['everyone']
                self._bump_stat(guild.id, 'anti_everyone')
                if count >= threshold:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    embed = self._action_embed(
                        '🚨 Anti-Everyone Triggered',
                        f'**{message.author}** pinged @everyone/@here **{count}x** in 10s\n'
                        f'**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
                    )
                    await self._log(guild, embed)
                    member = guild.get_member(message.author.id)
                    if member:
                        await self._punish(guild, member, f'Mass @everyone ping ({count}x)', 'everyone', cfg)

        # ── Anti-mention (mass user mentions) ──
        if cfg['anti_mention'] and len(message.mentions) >= cfg['thresholds'].get('everyone', 5):
            if not self._is_whitelisted(guild.id, message.author.id):
                self._bump_stat(guild.id, 'anti_mention')
                try:
                    await message.delete()
                except Exception:
                    pass
                embed = self._action_embed(
                    '⚠️ Anti-Mass-Mention Triggered',
                    f'**{message.author}** mentioned **{len(message.mentions)}** users in one message',
                    color=discord.Color.orange(),
                )
                await self._log(guild, embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_emoji']:
            return
        deleted = [e for e in before if e not in after]
        if not deleted:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.emoji_delete)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        count = self.tracker.record(guild.id, executor.id, 'emoji_delete')
        threshold = cfg['thresholds']['emoji_delete']
        self._bump_stat(guild.id, 'anti_emoji')
        if count >= threshold:
            embed = self._action_embed(
                '🚨 Anti-Emoji Triggered',
                f'**{executor}** deleted **{count}** emojis in 10s (threshold: {threshold})\n'
                f'**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
            )
            await self._log(guild, embed)
            member = guild.get_member(executor.id)
            if member:
                await self._punish(guild, member, f'Mass emoji delete ({count})', 'emoji_delete', cfg)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_sticker']:
            return
        deleted = [s for s in before if s not in after]
        if not deleted:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.sticker_delete)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        count = self.tracker.record(guild.id, executor.id, 'sticker_delete')
        threshold = cfg['thresholds']['sticker_delete']
        self._bump_stat(guild.id, 'anti_sticker')
        if count >= threshold:
            embed = self._action_embed(
                '🚨 Anti-Sticker Triggered',
                f'**{executor}** deleted **{count}** stickers in 10s (threshold: {threshold})',
            )
            await self._log(guild, embed)
            member = guild.get_member(executor.id)
            if member:
                await self._punish(guild, member, f'Mass sticker delete ({count})', 'sticker_delete', cfg)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        guild = thread.guild
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_thread']:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.thread_create, thread.id)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        count = self.tracker.record(guild.id, executor.id, 'thread_create')
        threshold = cfg['thresholds']['thread_create']
        self._bump_stat(guild.id, 'anti_thread')
        if count >= threshold:
            embed = self._action_embed(
                '⚠️ Anti-Thread Triggered',
                f'**{executor}** created **{count}** threads in 10s (threshold: {threshold})',
                color=discord.Color.orange(),
            )
            await self._log(guild, embed)

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild: discord.Guild):
        cfg = self._an_cfg(guild.id)
        if not cfg['enabled'] or not cfg['anti_integration']:
            return
        executor = await self._get_executor(guild, discord.AuditLogAction.integration_create)
        if not executor or executor.bot or self._is_whitelisted(guild.id, executor.id):
            return
        self._bump_stat(guild.id, 'anti_integration')
        embed = self._action_embed(
            '🚨 Anti-Integration Triggered',
            f'**{executor}** added a new integration/OAuth app.\n'
            f'**Punishment:** {PUNISH_LABELS[cfg["punish"]]}',
        )
        await self._log(guild, embed)
        member = guild.get_member(executor.id)
        if member:
            await self._punish(guild, member, 'Unauthorized integration add', 'integration', cfg)

    # ══════════════════════════════════════
    #   GOD-TIER CHECK HELPER
    # ══════════════════════════════════════

    def _is_god_tier(self, ctx_or_member, guild=None) -> bool:
        if isinstance(ctx_or_member, commands.Context):
            member = ctx_or_member.author
            guild = ctx_or_member.guild
        else:
            member = ctx_or_member
        if member.id == guild.owner_id:
            return True
        if member.id == getattr(self.bot, 'BOT_OWNER_ID', None):
            return True
        mod_cog = self.bot.get_cog('Moderation')
        if mod_cog and member.id in mod_cog.extraowners.get(guild.id, set()):
            return True
        return False

    def _no_perm_embed(self):
        return discord.Embed(
            title='❌ No Permission',
            description='Only **Server Owner**, **ExtraOwners**, or **Bot Owner** can use security commands.',
            color=discord.Color.red()
        )

    # ══════════════════════════════════════
    #   !antinuke  COMMAND GROUP
    # ══════════════════════════════════════

    @commands.group(name='antinuke', aliases=['an'], invoke_without_command=True)
    async def antinuke(self, ctx: commands.Context):
        """Show antinuke status overview."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        cfg = self._an_cfg(ctx.guild.id)
        p = self.bot.custom_prefixes.get(ctx.guild.id, '!')
        status = '🟢 **ENABLED**' if cfg['enabled'] else '🔴 **DISABLED**'
        punish = PUNISH_LABELS.get(cfg['punish'], cfg['punish'])
        wl_count = len(cfg['whitelist'])

        modules = [
            ('anti_ban',         '🔨 Anti-Ban'),
            ('anti_kick',        '👢 Anti-Kick'),
            ('anti_channel',     '📺 Anti-Channel'),
            ('anti_role',        '🎭 Anti-Role'),
            ('anti_webhook',     '🔗 Anti-Webhook'),
            ('anti_prune',       '🧹 Anti-Prune'),
            ('anti_everyone',    '📢 Anti-Everyone'),
            ('anti_guild',       '🏠 Anti-Guild'),
            ('anti_bot',         '🤖 Anti-Bot'),
            ('anti_mention',     '🔔 Anti-Mention'),
            ('anti_emoji',       '😀 Anti-Emoji'),
            ('anti_sticker',     '🏷️ Anti-Sticker'),
            ('anti_thread',      '🧵 Anti-Thread'),
            ('anti_vc',          '🔊 Anti-VC'),
            ('anti_integration', '🔌 Anti-Integration'),
        ]
        mod_lines = '\n'.join(
            f'{"✅" if cfg[k] else "❌"} {label}' for k, label in modules
        )
        embed = discord.Embed(title='🛡️ Antinuke — Status', color=discord.Color.green() if cfg['enabled'] else discord.Color.red())
        embed.add_field(name='Status', value=status, inline=True)
        embed.add_field(name='Punishment', value=punish, inline=True)
        embed.add_field(name='Whitelist', value=f'{wl_count} user(s)', inline=True)
        embed.add_field(name='Modules', value=mod_lines, inline=False)
        embed.add_field(
            name='Quick Commands',
            value=(
                f'`{p}antinuke on/off` · `{p}antinuke punish <action>`\n'
                f'`{p}antinuke whitelist @user` · `{p}antinuke threshold <action> <n>`\n'
                f'`{p}antinuke panic` · `{p}antinuke recover` · `{p}antinuke stats`\n'
                f'`{p}antinuke module <name> on/off` to toggle individual modules'
            ),
            inline=False,
        )
        embed.set_footer(text='Lucky Bot Security')
        await ctx.reply(embed=embed)

    @antinuke.command(name='on')
    async def antinuke_on(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        cfg = self._an_cfg(ctx.guild.id)
        cfg['enabled'] = True
        self.snapshots.save(ctx.guild)
        embed = discord.Embed(
            title='🛡️ Antinuke Enabled',
            description='Lucky Bot is now **actively protecting** this server.\nA server snapshot has been saved for recovery.',
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='off')
    async def antinuke_off(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self._an_cfg(ctx.guild.id)['enabled'] = False
        embed = discord.Embed(
            title='🔴 Antinuke Disabled',
            description='⚠️ Server protection is now **off**. Run `!antinuke on` to re-enable.',
            color=discord.Color.orange()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='setup')
    async def antinuke_setup(self, ctx: commands.Context):
        """Quick-enable antinuke with safe defaults."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        cfg = self._an_cfg(ctx.guild.id)
        cfg['enabled'] = True
        # Add bot owner and server owner to whitelist
        cfg['whitelist'].add(ctx.guild.owner_id)
        cfg['whitelist'].add(self.bot.user.id)
        self.snapshots.save(ctx.guild)
        p = self.bot.custom_prefixes.get(ctx.guild.id, '!')
        embed = discord.Embed(
            title='✅ Antinuke Quick Setup Complete',
            description=(
                '**All modules enabled with safe defaults.**\n\n'
                '• Punishment: `ban`\n'
                '• Server owner + Lucky Bot whitelisted\n'
                '• Snapshot saved for recovery\n\n'
                f'Customize with `{p}antinuke punish <action>` and `{p}antinuke whitelist @user`'
            ),
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='disable')
    async def antinuke_disable(self, ctx: commands.Context):
        """Disable antinuke and clear all config."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self.antinuke_config.pop(ctx.guild.id, None)
        embed = discord.Embed(
            title='🗑️ Antinuke Reset',
            description='All antinuke configuration has been cleared.',
            color=discord.Color.orange()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='punish')
    async def antinuke_punish(self, ctx: commands.Context, action: str):
        """Set punishment: ban | kick | mute | strip | derank"""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        action = action.lower()
        if action not in PUNISH_LABELS:
            return await ctx.reply(embed=discord.Embed(
                title='❌ Invalid Action',
                description=f'Choose from: `{" | ".join(PUNISH_LABELS.keys())}`',
                color=discord.Color.red()
            ))
        self._an_cfg(ctx.guild.id)['punish'] = action
        embed = discord.Embed(
            title='✅ Punishment Updated',
            description=f'Antinuke will now **{PUNISH_LABELS[action]}** violators.',
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='whitelist')
    async def antinuke_whitelist(self, ctx: commands.Context, user: discord.Member):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self._an_cfg(ctx.guild.id)['whitelist'].add(user.id)
        embed = discord.Embed(
            title='✅ Whitelisted',
            description=f'{user.mention} is now **exempt** from all antinuke actions.',
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='unwhitelist')
    async def antinuke_unwhitelist(self, ctx: commands.Context, user: discord.Member):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self._an_cfg(ctx.guild.id)['whitelist'].discard(user.id)
        embed = discord.Embed(
            title='✅ Un-whitelisted',
            description=f'{user.mention} is **no longer exempt** from antinuke.',
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='whitelistlist')
    async def antinuke_whitelistlist(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        cfg = self._an_cfg(ctx.guild.id)
        wl = cfg['whitelist']
        if not wl:
            desc = 'No users are whitelisted.'
        else:
            lines = []
            for uid in wl:
                member = ctx.guild.get_member(uid)
                lines.append(f'• {member.mention if member else f"`{uid}`"}')
            desc = '\n'.join(lines)
        embed = discord.Embed(
            title=f'📋 Antinuke Whitelist ({len(wl)} users)',
            description=desc,
            color=discord.Color.blurple()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='threshold')
    async def antinuke_threshold(self, ctx: commands.Context, action: str, count: int):
        """Set how many actions in 10s triggers antinuke."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        cfg = self._an_cfg(ctx.guild.id)
        action = action.lower()
        if action not in cfg['thresholds']:
            valid = ', '.join(f'`{k}`' for k in cfg['thresholds'])
            return await ctx.reply(embed=discord.Embed(
                title='❌ Unknown Action',
                description=f'Valid threshold keys:\n{valid}',
                color=discord.Color.red()
            ))
        if count < 1:
            return await ctx.reply(embed=discord.Embed(
                title='❌ Invalid Count', description='Threshold must be at least 1.', color=discord.Color.red()))
        cfg['thresholds'][action] = count
        embed = discord.Embed(
            title='✅ Threshold Updated',
            description=f'`{action}` will now trigger at **{count} actions** within 10 seconds.',
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='settings')
    async def antinuke_settings(self, ctx: commands.Context):
        """Show all thresholds and detailed settings."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        cfg = self._an_cfg(ctx.guild.id)
        th_lines = '\n'.join(f'`{k}` → **{v}** actions/10s' for k, v in cfg['thresholds'].items())
        embed = discord.Embed(
            title='⚙️ Antinuke Settings',
            color=discord.Color.blurple()
        )
        embed.add_field(name='Status', value='🟢 On' if cfg['enabled'] else '🔴 Off', inline=True)
        embed.add_field(name='Punishment', value=PUNISH_LABELS.get(cfg['punish']), inline=True)
        embed.add_field(name='Whitelist', value=f'{len(cfg["whitelist"])} users', inline=True)
        embed.add_field(name='Thresholds', value=th_lines, inline=False)
        await ctx.reply(embed=embed)

    @antinuke.command(name='module')
    async def antinuke_module(self, ctx: commands.Context, module: str, toggle: str):
        """Toggle an individual antinuke module on/off."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        cfg = self._an_cfg(ctx.guild.id)
        key = f'anti_{module.lower().replace("-", "_")}'
        if key not in cfg:
            valid = [k.replace('anti_', '') for k in cfg if k.startswith('anti_') and isinstance(cfg[k], bool)]
            return await ctx.reply(embed=discord.Embed(
                title='❌ Unknown Module',
                description='Valid modules: ' + ', '.join(f'`{v}`' for v in valid),
                color=discord.Color.red()
            ))
        state = toggle.lower() in ('on', 'true', 'enable', '1', 'yes')
        cfg[key] = state
        embed = discord.Embed(
            title=f'✅ Module {"Enabled" if state else "Disabled"}',
            description=f'`{key}` is now **{"on" if state else "off"}**.',
            color=discord.Color.green() if state else discord.Color.orange()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='panic')
    async def antinuke_panic(self, ctx: commands.Context):
        """PANIC MODE — locks server, kicks all new joins, blocks bots."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        if ctx.guild.id in self.panic_guilds:
            self.panic_guilds.discard(ctx.guild.id)
            embed = discord.Embed(
                title='✅ Panic Mode Deactivated',
                description='Server is back to normal. New members can join.',
                color=discord.Color.green()
            )
        else:
            self.panic_guilds.add(ctx.guild.id)
            embed = discord.Embed(
                title='🚨 PANIC MODE ACTIVATED',
                description=(
                    '**ALL new joins are now being auto-kicked.**\n'
                    '**All bot adds are blocked.**\n\n'
                    f'Run `{ctx.prefix}antinuke panic` again to deactivate.\n'
                    f'Run `{ctx.prefix}antinuke recover` to undo recent damage.'
                ),
                color=discord.Color.dark_red()
            )
        await ctx.reply(embed=embed)
        await self._log(ctx.guild, embed)

    @antinuke.command(name='recover')
    async def antinuke_recover(self, ctx: commands.Context):
        """Attempt to restore server from last saved snapshot."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        snap = self.snapshots.get(ctx.guild.id)
        if not snap:
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Snapshot',
                description='No recovery snapshot found. Enable antinuke first — a snapshot is taken automatically.',
                color=discord.Color.red()
            ))
        age = (datetime.datetime.utcnow() - snap['timestamp']).seconds // 60
        embed = discord.Embed(
            title='🔄 Recovery Snapshot Info',
            description=(
                f'**Saved:** {age} minute(s) ago\n'
                f'**Server Name:** {snap["name"]}\n'
                f'**Roles in snapshot:** {len(snap["roles"])}\n'
                f'**Channels in snapshot:** {len(snap["channels"])}\n\n'
                '⚠️ Full automatic recovery (re-creating deleted roles/channels) requires '
                'the bot to have **Administrator** permission.\n\n'
                'Type `yes` within 15 seconds to attempt name restore.'
            ),
            color=discord.Color.blurple()
        )
        msg = await ctx.reply(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
        try:
            await self.bot.wait_for('message', check=check, timeout=15)
        except asyncio.TimeoutError:
            return

        results = []
        # Restore server name if changed
        if ctx.guild.name != snap['name']:
            try:
                await ctx.guild.edit(name=snap['name'], reason='🛡️ Lucky Bot: antinuke recovery')
                results.append(f'✅ Server name restored to `{snap["name"]}`')
            except Exception as e:
                results.append(f'❌ Could not restore name: {e}')
        else:
            results.append('✅ Server name already matches snapshot')

        result_embed = discord.Embed(
            title='🔄 Recovery Complete',
            description='\n'.join(results),
            color=discord.Color.green()
        )
        await ctx.reply(embed=result_embed)

    @antinuke.command(name='stats')
    async def antinuke_stats(self, ctx: commands.Context):
        """Show antinuke action statistics."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        s = self.stats.get(ctx.guild.id, {})
        if not s:
            return await ctx.reply(embed=discord.Embed(
                title='📊 Antinuke Stats',
                description='No threats have been detected yet.',
                color=discord.Color.blurple()
            ))
        lines = '\n'.join(f'`{k}` → **{v}** trigger(s)' for k, v in sorted(s.items(), key=lambda x: -x[1]))
        total = sum(s.values())
        embed = discord.Embed(
            title=f'📊 Antinuke Stats — {ctx.guild.name}',
            description=f'**Total threats blocked:** {total}\n\n{lines}',
            color=discord.Color.blurple()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='reset')
    async def antinuke_reset(self, ctx: commands.Context):
        """Reset all antinuke config to defaults."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self.antinuke_config.pop(ctx.guild.id, None)
        self.stats.pop(ctx.guild.id, None)
        embed = discord.Embed(
            title='♻️ Antinuke Reset',
            description='All settings and stats cleared. Run `!antinuke setup` to start fresh.',
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='logchannel')
    async def antinuke_logchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set where antinuke alerts are sent."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self._an_cfg(ctx.guild.id)['log_channel'] = channel.id
        embed = discord.Embed(
            title='✅ Log Channel Set',
            description=f'Antinuke alerts will now be sent to {channel.mention}.',
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='antiban')
    async def antinuke_antiban(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_ban', toggle)

    @antinuke.command(name='antikick')
    async def antinuke_antikick(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_kick', toggle)

    @antinuke.command(name='antichannel')
    async def antinuke_antichannel(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_channel', toggle)

    @antinuke.command(name='antirole')
    async def antinuke_antirole(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_role', toggle)

    @antinuke.command(name='antiwebhook')
    async def antinuke_antiwebhook(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_webhook', toggle)

    @antinuke.command(name='antiprune')
    async def antinuke_antiprune(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_prune', toggle)

    @antinuke.command(name='antieveryone')
    async def antinuke_antieveryone(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_everyone', toggle)

    @antinuke.command(name='antiguild')
    async def antinuke_antiguild(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_guild', toggle)

    @antinuke.command(name='antibot')
    async def antinuke_antibot(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_bot', toggle)

    @antinuke.command(name='antimention')
    async def antinuke_antimention(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_mention', toggle)

    @antinuke.command(name='antiemoji')
    async def antinuke_antiemoji(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_emoji', toggle)

    @antinuke.command(name='antisticker')
    async def antinuke_antisticker(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_sticker', toggle)

    @antinuke.command(name='antithread')
    async def antinuke_antithread(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_thread', toggle)

    @antinuke.command(name='antivc')
    async def antinuke_antivc(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_vc', toggle)

    @antinuke.command(name='antiintegration')
    async def antinuke_antiintegration(self, ctx: commands.Context, toggle: str):
        await self._toggle_module(ctx, 'anti_integration', toggle)

    async def _toggle_module(self, ctx: commands.Context, key: str, toggle: str):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        state = toggle.lower() in ('on', 'true', 'enable', '1', 'yes')
        self._an_cfg(ctx.guild.id)[key] = state
        label = key.replace('anti_', '').replace('_', '-').title()
        embed = discord.Embed(
            title=f'✅ Anti-{label} {"Enabled" if state else "Disabled"}',
            color=discord.Color.green() if state else discord.Color.orange()
        )
        await ctx.reply(embed=embed)

    @antinuke.command(name='wizard')
    async def antinuke_wizard(self, ctx: commands.Context):
        """Interactive step-by-step antinuke setup wizard."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        cfg = self._an_cfg(ctx.guild.id)
        p = ctx.prefix or '!'

        embed = discord.Embed(
            title='🧙 Antinuke Setup Wizard',
            description=(
                'Answer the following questions to configure antinuke.\n'
                'Type `skip` to keep the current/default value.\n\n'
                '**Step 1/4** — What punishment should violators receive?\n'
                '`ban` · `kick` · `mute` · `strip` · `derank`'
            ),
            color=discord.Color.blurple()
        )
        await ctx.reply(embed=embed)

        # Step 1 — Punishment
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            if msg.content.lower() not in ('skip',) and msg.content.lower() in PUNISH_LABELS:
                cfg['punish'] = msg.content.lower()
        except asyncio.TimeoutError:
            pass

        # Step 2 — Whitelist
        embed2 = discord.Embed(
            title='🧙 Wizard — Step 2/4',
            description='Mention any users to **whitelist** (space-separated), or type `skip`.',
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed2)
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            if msg.content.lower() != 'skip':
                for mention in msg.mentions:
                    cfg['whitelist'].add(mention.id)
        except asyncio.TimeoutError:
            pass

        # Step 3 — Log channel
        embed3 = discord.Embed(
            title='🧙 Wizard — Step 3/4',
            description='Mention the **log channel** for security alerts, or type `skip` to use `#security-logs`.',
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed3)
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            if msg.content.lower() != 'skip' and msg.channel_mentions:
                cfg['log_channel'] = msg.channel_mentions[0].id
        except asyncio.TimeoutError:
            pass

        # Step 4 — Enable
        embed4 = discord.Embed(
            title='🧙 Wizard — Step 4/4',
            description='Enable antinuke now? Type `yes` or `no`.',
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed4)
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            if msg.content.lower() == 'yes':
                cfg['enabled'] = True
                self.snapshots.save(ctx.guild)
        except asyncio.TimeoutError:
            pass

        # Summary
        embed_done = discord.Embed(
            title='✅ Antinuke Wizard Complete',
            description=(
                f'**Status:** {"🟢 Enabled" if cfg["enabled"] else "🔴 Disabled"}\n'
                f'**Punishment:** {PUNISH_LABELS.get(cfg["punish"])}\n'
                f'**Whitelist:** {len(cfg["whitelist"])} user(s)\n'
                f'**Log Channel:** {"Set" if cfg["log_channel"] else "Using #security-logs default"}\n\n'
                f'Customize further with `{p}antinuke settings`'
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed_done)

    # ══════════════════════════════════════
    #   !antiraid  COMMAND GROUP
    # ══════════════════════════════════════

    @commands.group(name='antiraid', aliases=['ar'], invoke_without_command=True)
    async def antiraid(self, ctx: commands.Context):
        """Show antiraid status overview."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        cfg = self._ar_cfg(ctx.guild.id)
        p = self.bot.custom_prefixes.get(ctx.guild.id, '!')
        status = '🟢 **ENABLED**' if cfg['enabled'] else '🔴 **DISABLED**'
        lockdown = '🔒 **ACTIVE**' if cfg['lockdown_active'] else '🔓 Inactive'
        embed = discord.Embed(title='🚨 Antiraid — Status', color=discord.Color.orange())
        embed.add_field(name='Status', value=status, inline=True)
        embed.add_field(name='Punishment', value=PUNISH_LABELS.get(cfg['punish']), inline=True)
        embed.add_field(name='Lockdown', value=lockdown, inline=True)
        embed.add_field(
            name='Settings',
            value=(
                f'Join Threshold: **{cfg["join_threshold"]}** in **{cfg["join_window"]}s**\n'
                f'Min Account Age: **{cfg["min_account_age"]}** days\n'
                f'Block No-Avatar: **{"✅" if cfg["no_avatar"] else "❌"}**\n'
                f'Block Bots: **{"✅" if cfg["anti_bot_raid"] else "❌"}**\n'
                f'Auto-Lockdown: **{"✅" if cfg["lockdown_on_raid"] else "❌"}**'
            ),
            inline=False,
        )
        embed.add_field(
            name='Commands',
            value=(
                f'`{p}antiraid on/off` · `{p}antiraid punish <action>`\n'
                f'`{p}antiraid threshold <n> <seconds>` · `{p}antiraid minage <days>`\n'
                f'`{p}antiraid noavatar on/off` · `{p}antiraid lockdown on/off`\n'
                f'`{p}antiraid whitelist @user` · `{p}antiraid stats`'
            ),
            inline=False,
        )
        await ctx.reply(embed=embed)

    @antiraid.command(name='on')
    async def antiraid_on(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self._ar_cfg(ctx.guild.id)['enabled'] = True
        await ctx.reply(embed=discord.Embed(
            title='✅ Antiraid Enabled', description='Raid detection is now active.',
            color=discord.Color.green()
        ))

    @antiraid.command(name='off')
    async def antiraid_off(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self._ar_cfg(ctx.guild.id)['enabled'] = False
        await ctx.reply(embed=discord.Embed(
            title='🔴 Antiraid Disabled', description='Raid detection is now off.',
            color=discord.Color.orange()
        ))

    @antiraid.command(name='punish')
    async def antiraid_punish(self, ctx: commands.Context, action: str):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        action = action.lower()
        if action not in ('ban', 'kick', 'mute'):
            return await ctx.reply(embed=discord.Embed(
                title='❌ Invalid', description='Choose: `ban` · `kick` · `mute`', color=discord.Color.red()))
        self._ar_cfg(ctx.guild.id)['punish'] = action
        await ctx.reply(embed=discord.Embed(
            title='✅ Antiraid Punishment Set',
            description=f'Raiders will be **{PUNISH_LABELS[action]}**.', color=discord.Color.green()))

    @antiraid.command(name='threshold')
    async def antiraid_threshold(self, ctx: commands.Context, joins: int, seconds: int = 10):
        """Set raid trigger: X joins in Y seconds."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        cfg = self._ar_cfg(ctx.guild.id)
        cfg['join_threshold'] = max(1, joins)
        cfg['join_window'] = max(1, seconds)
        await ctx.reply(embed=discord.Embed(
            title='✅ Antiraid Threshold Set',
            description=f'Raid triggers at **{joins}** joins in **{seconds}** seconds.',
            color=discord.Color.green()
        ))

    @antiraid.command(name='minage')
    async def antiraid_minage(self, ctx: commands.Context, days: int):
        """Block accounts younger than X days. Set 0 to disable."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self._ar_cfg(ctx.guild.id)['min_account_age'] = max(0, days)
        msg = f'Accounts younger than **{days} days** will be auto-kicked.' if days > 0 else 'Account age filter **disabled**.'
        await ctx.reply(embed=discord.Embed(title='✅ Min Account Age Set', description=msg, color=discord.Color.green()))

    @antiraid.command(name='noavatar')
    async def antiraid_noavatar(self, ctx: commands.Context, toggle: str):
        """Block members with no profile picture."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        state = toggle.lower() in ('on', 'yes', 'true', '1')
        self._ar_cfg(ctx.guild.id)['no_avatar'] = state
        await ctx.reply(embed=discord.Embed(
            title=f'✅ No-Avatar Filter {"Enabled" if state else "Disabled"}',
            description='Members with no profile picture will be auto-kicked.' if state else 'No-avatar filter is off.',
            color=discord.Color.green() if state else discord.Color.orange()
        ))

    @antiraid.command(name='lockdown')
    async def antiraid_lockdown(self, ctx: commands.Context, toggle: str):
        """Manually toggle server lockdown."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        state = toggle.lower() in ('on', 'yes', 'true', '1')
        self._ar_cfg(ctx.guild.id)['lockdown_active'] = state
        embed = discord.Embed(
            title='🔒 Server Lockdown ACTIVE' if state else '🔓 Lockdown Lifted',
            description='All new joins are being kicked.' if state else 'Members can join again normally.',
            color=discord.Color.dark_red() if state else discord.Color.green()
        )
        await ctx.reply(embed=embed)
        await self._log(ctx.guild, embed, mode='antiraid')

    @antiraid.command(name='whitelist')
    async def antiraid_whitelist(self, ctx: commands.Context, user: discord.Member):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self._ar_cfg(ctx.guild.id)['whitelist'].add(user.id)
        await ctx.reply(embed=discord.Embed(
            title='✅ Whitelisted from Antiraid',
            description=f'{user.mention} is exempt from all antiraid checks.',
            color=discord.Color.green()
        ))

    @antiraid.command(name='stats')
    async def antiraid_stats(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        s = self.stats.get(ctx.guild.id, {})
        raid_stats = {k: v for k, v in s.items() if k.startswith('antiraid')}
        if not raid_stats:
            return await ctx.reply(embed=discord.Embed(
                title='📊 Antiraid Stats', description='No raid attempts detected yet.',
                color=discord.Color.blurple()))
        lines = '\n'.join(f'`{k}` → **{v}**' for k, v in raid_stats.items())
        await ctx.reply(embed=discord.Embed(
            title='📊 Antiraid Stats', description=lines, color=discord.Color.blurple()))

    @antiraid.command(name='logchannel')
    async def antiraid_logchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        self._ar_cfg(ctx.guild.id)['log_channel'] = channel.id
        await ctx.reply(embed=discord.Embed(
            title='✅ Antiraid Log Channel Set',
            description=f'Raid alerts → {channel.mention}',
            color=discord.Color.green()
        ))

    # ══════════════════════════════════════
    #   !security  OVERVIEW
    # ══════════════════════════════════════

    @commands.command(name='security')
    async def security_overview(self, ctx: commands.Context):
        """Full security overview for this server."""
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=self._no_perm_embed())
        an_cfg = self._an_cfg(ctx.guild.id)
        ar_cfg = self._ar_cfg(ctx.guild.id)
        p = ctx.prefix or '!'
        embed = discord.Embed(
            title=f'🔐 Lucky Bot Security — {ctx.guild.name}',
            description='Full protection overview for this server.',
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(
            name='🛡️ Antinuke',
            value=(
                f'Status: {"🟢 On" if an_cfg["enabled"] else "🔴 Off"}\n'
                f'Punishment: {PUNISH_LABELS.get(an_cfg["punish"])}\n'
                f'Whitelist: {len(an_cfg["whitelist"])} users\n'
                f'Snapshot: {"✅ Saved" if self.snapshots.get(ctx.guild.id) else "❌ None"}'
            ),
            inline=True
        )
        embed.add_field(
            name='🚨 Antiraid',
            value=(
                f'Status: {"🟢 On" if ar_cfg["enabled"] else "🔴 Off"}\n'
                f'Threshold: {ar_cfg["join_threshold"]} joins/{ar_cfg["join_window"]}s\n'
                f'Min Age: {ar_cfg["min_account_age"]}d · No-Avatar: {"✅" if ar_cfg["no_avatar"] else "❌"}\n'
                f'Lockdown: {"🔒 ACTIVE" if ar_cfg["lockdown_active"] else "🔓 Off"}'
            ),
            inline=True
        )
        total_threats = sum(self.stats.get(ctx.guild.id, {}).values())
        embed.add_field(
            name='📊 Threats Blocked (all time)',
            value=f'**{total_threats}** total',
            inline=True
        )
        embed.add_field(
            name='🚀 Quick Enable',
            value=(
                f'`{p}antinuke setup` — enable antinuke with defaults\n'
                f'`{p}antiraid on` — enable raid detection\n'
                f'`{p}antinuke wizard` — step-by-step setup\n'
                f'`{p}antinuke panic` — emergency lockdown NOW'
            ),
            inline=False
        )
        embed.set_footer(text='Lucky Bot Security')
        await ctx.reply(embed=embed)

    # ══════════════════════════════════════
    #   SLASH COMMANDS
    # ══════════════════════════════════════

    @app_commands.command(name='security', description='View Lucky Bot security overview')
    async def security_slash(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.security_overview(ctx)

    @app_commands.command(name='antinuke', description='Manage antinuke protection')
    @app_commands.describe(action='What to do', value='on/off or value')
    @app_commands.choices(action=[
        app_commands.Choice(name='on — enable antinuke',     value='on'),
        app_commands.Choice(name='off — disable antinuke',   value='off'),
        app_commands.Choice(name='setup — quick setup',      value='setup'),
        app_commands.Choice(name='stats — view stats',       value='stats'),
        app_commands.Choice(name='panic — emergency mode',   value='panic'),
        app_commands.Choice(name='whitelist — add user',     value='whitelist'),
        app_commands.Choice(name='settings — view settings', value='settings'),
    ])
    async def antinuke_slash(self, interaction: discord.Interaction,
                             action: app_commands.Choice[str]):
        if not self._is_god_tier(interaction.user, interaction.guild):
            return await interaction.response.send_message(embed=self._no_perm_embed(), ephemeral=True)
        ctx = await self.bot.get_context(interaction)
        dispatch = {
            'on':       self.antinuke_on,
            'off':      self.antinuke_off,
            'setup':    self.antinuke_setup,
            'stats':    self.antinuke_stats,
            'panic':    self.antinuke_panic,
            'settings': self.antinuke_settings,
        }
        if action.value in dispatch:
            await interaction.response.defer()
            await dispatch[action.value](ctx)
        else:
            await interaction.response.send_message(
                'Use prefix commands for advanced options like `/antinuke whitelist`.',
                ephemeral=True
            )

    @app_commands.command(name='antiraid', description='Manage antiraid protection')
    @app_commands.choices(action=[
        app_commands.Choice(name='on',       value='on'),
        app_commands.Choice(name='off',      value='off'),
        app_commands.Choice(name='stats',    value='stats'),
        app_commands.Choice(name='lockdown on',  value='lockdown_on'),
        app_commands.Choice(name='lockdown off', value='lockdown_off'),
    ])
    async def antiraid_slash(self, interaction: discord.Interaction,
                             action: app_commands.Choice[str]):
        if not self._is_god_tier(interaction.user, interaction.guild):
            return await interaction.response.send_message(embed=self._no_perm_embed(), ephemeral=True)
        await interaction.response.defer()
        ctx = await self.bot.get_context(interaction)
        if action.value == 'on':
            await self.antiraid_on(ctx)
        elif action.value == 'off':
            await self.antiraid_off(ctx)
        elif action.value == 'stats':
            await self.antiraid_stats(ctx)
        elif action.value == 'lockdown_on':
            self._ar_cfg(interaction.guild.id)['lockdown_active'] = True
            await interaction.followup.send(embed=discord.Embed(
                title='🔒 Lockdown Active', color=discord.Color.dark_red()))
        elif action.value == 'lockdown_off':
            self._ar_cfg(interaction.guild.id)['lockdown_active'] = False
            await interaction.followup.send(embed=discord.Embed(
                title='🔓 Lockdown Lifted', color=discord.Color.green()))


async def setup(bot: commands.Bot):
    await bot.add_cog(Security(bot))
