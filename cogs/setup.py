import discord
from discord.ext import commands
from discord import app_commands
import datetime


# ══════════════════════════════════════════════════════════
#   SETUP COG — Modular Lucky Bot Setup System
#   Usage:
#     !setup             → show menu
#     !setup basic       → permission roles only
#     !setup moderation  → mod roles + mod-logs
#     !setup security    → security-logs + antiraid/nuke info
#     !setup tickets     → ticket-logs + ticket channel
#     !setup welcome     → welcome + goodbye channels
#     !setup economy     → economy-logs
#     !setup leveling    → leveling-logs
#     !setup giveaway    → giveaway-logs
#     !setup music       → music-logs
#     !setup all         → everything above
#
#   !channelbind <key> #channel   → reassign a channel
#   !channelbind list             → show all current bindings
#   !channelbind reset <key>      → reset one binding to default name
#   !channelbind reset all        → reset every binding
# ══════════════════════════════════════════════════════════

PERMISSION_ROLES = [
    # (name, hex_color, description)
    ('ban.exe',         0xc0392b, 'Can ban, kick, mute, warn'),
    ('kick.exe',        0xe67e22, 'Can kick, mute, warn'),
    ('mute.exe',        0xf39c12, 'Can mute, warn'),
    ('warn.exe',        0xf1c40f, 'Can warn only'),
    ('purge.exe',       0x3498db, 'Can purge messages'),
    ('lock.exe',        0x9b59b6, 'Can lock/unlock channels + slowmode'),
    ('nick.exe',        0x1abc9c, 'Can change nicknames'),
    ('announce.exe',    0x2ecc71, 'Can send announcements + polls'),
    ('audit.viewer',    0x95a5a6, 'Can view all log channels'),
    ('role.giver.god',  0xe91e63, 'Can give/take Lucky Bot roles'),
    ('god.bypass',      0xffd700, 'Immune to all bot moderation'),
]

LOG_CHANNELS = {
    'mod-logs':      ('🛡️', 'Moderation action logs — Lucky Bot'),
    'security-logs': ('🔒', 'Antinuke and antiraid alerts — Lucky Bot'),
    'ticket-logs':   ('🎫', 'Ticket open/close/transcript — Lucky Bot'),
    'music-logs':    ('🎵', 'Music activity — Lucky Bot'),
    'economy-logs':  ('💰', 'Economy transactions — Lucky Bot'),
    'leveling-logs': ('⭐', 'Level-up events — Lucky Bot'),
    'giveaway-logs': ('🎁', 'Giveaway events — Lucky Bot'),
    'server-logs':   ('📋', 'Joins, leaves, edits — Lucky Bot'),
}

# ──────────────────────────────────────────────────────────
#   ALL BINDABLE CHANNEL KEYS  →  (default name, description)
# ──────────────────────────────────────────────────────────
BINDABLE_CHANNELS = {
    # Log channels
    'mod-logs':      ('mod-logs',      '🛡️  Where moderation actions are logged'),
    'security-logs': ('security-logs', '🔒  Antinuke / antiraid alerts'),
    'ticket-logs':   ('ticket-logs',   '🎫  Ticket open / close / transcripts'),
    'music-logs':    ('music-logs',    '🎵  Music activity'),
    'economy-logs':  ('economy-logs',  '💰  Economy transactions'),
    'leveling-logs': ('leveling-logs', '⭐  Level-up events'),
    'giveaway-logs': ('giveaway-logs', '🎁  Giveaway events'),
    'server-logs':   ('server-logs',   '📋  Member joins, leaves, edits'),
    # Feature channels
    'welcome':       ('welcome',       '👋  Welcome message channel'),
    'goodbye':       ('goodbye',       '👋  Goodbye / leave message channel'),
    'rules':         ('rules',         '📋  Server rules channel'),
    'tickets':       ('create-ticket', '🎫  Where members open tickets'),
    'giveaway':      ('giveaways',     '🎁  Where giveaways are announced'),
    'music':         ('music',         '🎵  Music request channel'),
    'announcements': ('announcements', '📢  Announcements channel'),
    'events':        ('events',        '🗓️  Events channel'),
}


class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # channel_binds[guild_id][key] = channel_id
        # Stored in-memory; replace with DB later
        if not hasattr(bot, 'channel_binds'):
            bot.channel_binds = {}

    # ══════════════════════════════════════════
    #   HELPERS — channel bind lookups
    # ══════════════════════════════════════════

    def _get_channel(self, guild: discord.Guild, key: str) -> discord.TextChannel | None:
        """
        Returns the bound channel for `key` in this guild.
        Falls back to the default channel name if no bind is set.
        """
        binds = self.bot.channel_binds.get(guild.id, {})
        if key in binds:
            ch = guild.get_channel(binds[key])
            if ch:
                return ch
        # Fall back: find by default name
        default_name, _ = BINDABLE_CHANNELS.get(key, (key, ''))
        return discord.utils.get(guild.text_channels, name=default_name)

    # ══════════════════════════════════════════
    #   PERMISSION CHECK
    # ══════════════════════════════════════════

    def _is_god_tier(self, ctx_or_member, guild=None):
        if isinstance(ctx_or_member, commands.Context):
            member = ctx_or_member.author
            guild = ctx_or_member.guild
        else:
            member = ctx_or_member
        if member.id == guild.owner_id:
            return True
        mod_cog = self.bot.get_cog('Moderation')
        if mod_cog and member.id in mod_cog.extraowners.get(guild.id, set()):
            return True
        return False

    # ══════════════════════════════════════════
    #   SHARED HELPERS
    # ══════════════════════════════════════════

    async def _create_roles(self, guild, roles_list):
        results = []
        for role_name, color, desc in roles_list:
            existing = discord.utils.get(guild.roles, name=role_name)
            if existing:
                results.append(f'✅ `{role_name}` already exists')
            else:
                try:
                    await guild.create_role(
                        name=role_name,
                        color=discord.Color(color),
                        reason=f'Lucky Bot setup — {desc}'
                    )
                    results.append(f'✨ Created `{role_name}`')
                except Exception as e:
                    results.append(f'❌ Failed `{role_name}`: {e}')
        return results

    async def _ensure_logs_category(self, guild):
        cat = (
            discord.utils.get(guild.categories, name='Logs') or
            discord.utils.get(guild.categories, name='logs')
        )
        if cat:
            return cat, '✅ `Logs` category already exists'
        try:
            cat = await guild.create_category('Logs', reason='Lucky Bot setup')
            return cat, '✨ Created `Logs` category'
        except Exception as e:
            return None, f'❌ Failed `Logs` category: {e}'

    async def _create_log_channel(self, guild, ch_name, emoji, topic, category):
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if existing:
            return f'✅ `#{ch_name}` already exists'
        audit_role = discord.utils.get(guild.roles, name='audit.viewer')
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True),
        }
        if audit_role:
            overwrites[audit_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=False, read_message_history=True)
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
        try:
            await guild.create_text_channel(
                name=ch_name, overwrites=overwrites,
                category=category, topic=f'{emoji} {topic}')
            return f'✨ Created private `#{ch_name}`'
        except Exception as e:
            return f'❌ Failed `#{ch_name}`: {e}'

    async def _create_public_channel(self, guild, ch_name, topic):
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if existing:
            return f'✅ `#{ch_name}` already exists'
        try:
            await guild.create_text_channel(name=ch_name, topic=topic)
            return f'✨ Created `#{ch_name}`'
        except Exception as e:
            return f'❌ Failed `#{ch_name}`: {e}'

    def _result_embed(self, title, results, color=0x2ecc71, next_steps=None):
        embed = discord.Embed(
            title=title,
            description='\n'.join(results),
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        if next_steps:
            embed.add_field(name='⚡ Next Steps', value=next_steps, inline=False)
        embed.set_footer(text='Lucky Bot Setup')
        return embed

    # ══════════════════════════════════════════
    #   SETUP MODULES  (unchanged logic)
    # ══════════════════════════════════════════

    async def _run_basic(self, guild):
        results = await self._create_roles(guild, PERMISSION_ROLES)
        return results, (
            '1. Give `role.giver.god` to your admins\n'
            '2. Give `ban.exe` to your moderators\n'
            '3. Use `!extraowner add @user` for trusted people'
        )

    async def _run_moderation(self, guild):
        results = await self._create_roles(guild, PERMISSION_ROLES)
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['mod-logs']
        results.append(await self._create_log_channel(guild, 'mod-logs', emoji, topic, cat))
        mod_cog = self.bot.get_cog('Moderation')
        if mod_cog:
            mod_cog.massban_enabled.setdefault(guild.id, False)
            results.append('✅ Massban locked by default')
        return results, (
            '1. Give `ban.exe` to your moderators\n'
            '2. Check `#mod-logs` — all actions will appear there\n'
            '3. Run `!extraowner add @user` for trusted admins'
        )

    async def _run_security(self, guild):
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['security-logs']
        results.append(await self._create_log_channel(guild, 'security-logs', emoji, topic, cat))
        return results, (
            '1. Run `!antinuke wizard` — guided 4-step setup\n'
            '   OR `!antinuke setup` — quick-enable with safe defaults\n'
            '2. Run `!antiraid on` — enable raid detection\n'
            '3. Run `!antiraid minage 7` — block accounts under 7 days old\n'
            '4. Run `!antinuke whitelist @user` — whitelist trusted staff\n'
            '5. Run `!antinuke punish ban` — set punishment (ban/kick/mute/strip/derank)\n'
            '6. See all options: `!help` → 🔐 Security'
        )

    async def _run_tickets(self, guild):
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['ticket-logs']
        results.append(await self._create_log_channel(guild, 'ticket-logs', emoji, topic, cat))
        results.append(await self._create_public_channel(
            guild, 'create-ticket', '🎫 Click the button below to open a support ticket'))
        return results, (
            '1. Once `cogs/tickets.py` is built, run `!ticket setup #create-ticket`\n'
            '2. Ticket logs will appear in `#ticket-logs`'
        )

    async def _run_welcome(self, guild):
        results = []
        results.append(await self._create_public_channel(guild, 'welcome', '👋 Welcome to the server!'))
        results.append(await self._create_public_channel(guild, 'goodbye', '👋 A member has left'))
        results.append(await self._create_public_channel(guild, 'rules', '📋 Server rules'))
        return results, (
            '1. Once `cogs/welcome.py` is built, run `!welcome set #welcome`\n'
            '2. Customise messages with `!welcome message Your text here`'
        )

    async def _run_economy(self, guild):
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['economy-logs']
        results.append(await self._create_log_channel(guild, 'economy-logs', emoji, topic, cat))
        return results, 'Economy system coming soon — `cogs/economy.py`'

    async def _run_leveling(self, guild):
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['leveling-logs']
        results.append(await self._create_log_channel(guild, 'leveling-logs', emoji, topic, cat))
        return results, 'Leveling system coming soon — `cogs/leveling.py`'

    async def _run_giveaway(self, guild):
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['giveaway-logs']
        results.append(await self._create_log_channel(guild, 'giveaway-logs', emoji, topic, cat))
        return results, 'Giveaway system coming soon — `cogs/giveaway.py`'

    async def _run_music(self, guild):
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['music-logs']
        results.append(await self._create_log_channel(guild, 'music-logs', emoji, topic, cat))
        return results, 'Music system coming soon — `cogs/music.py`'

    async def _run_all(self, guild):
        results = []
        role_results, _ = await self._run_basic(guild)
        results += role_results
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        for ch_name, (emoji, topic) in LOG_CHANNELS.items():
            results.append(await self._create_log_channel(guild, ch_name, emoji, topic, cat))
        results.append(await self._create_public_channel(guild, 'welcome', '👋 Welcome to the server!'))
        results.append(await self._create_public_channel(guild, 'goodbye', '👋 A member has left'))
        results.append(await self._create_public_channel(guild, 'rules', '📋 Server rules'))
        results.append(await self._create_public_channel(
            guild, 'create-ticket', '🎫 Click the button below to open a support ticket'))
        mod_cog = self.bot.get_cog('Moderation')
        if mod_cog:
            mod_cog.massban_enabled.setdefault(guild.id, False)
            results.append('✅ Massban locked by default')
        return results, (
            '1. Give `role.giver.god` to admins\n'
            '2. Give `ban.exe` to moderators\n'
            '3. Run `!extraowner add @user` for trusted people\n'
            '4. Run `!antinuke wizard` — set up server protection\n'
            '5. Run `!antiraid on` + `!antiraid minage 7` — raid protection\n'
            '6. Use `!channelbind list` to see / change channel assignments'
        )

    # ══════════════════════════════════════════
    #   MENU EMBED
    # ══════════════════════════════════════════

    def _menu_embed(self):
        embed = discord.Embed(
            title='⚙️ Lucky Bot — Setup Menu',
            description=(
                'Use one of the subcommands below to set up specific parts of Lucky Bot.\n'
                'Each module only creates what it needs — run them independently or all at once!\n\n'
                '💡 After setup, use `!channelbind` to point Lucky Bot at any existing channel.'
            ),
            color=0x3498db
        )
        embed.add_field(
            name='🔑 Core',
            value=(
                '`!setup basic` — permission roles only\n'
                '`!setup moderation` — mod roles + `#mod-logs`\n'
                '`!setup security` — `#security-logs` + next steps\n'
                '↳ After security setup: run `!antinuke wizard` to configure'
            ),
            inline=False
        )
        embed.add_field(
            name='🌐 Server',
            value=(
                '`!setup welcome` — `#welcome` · `#goodbye` · `#rules`\n'
                '`!setup tickets` — `#ticket-logs` · `#create-ticket`'
            ),
            inline=False
        )
        embed.add_field(
            name='🎮 Features',
            value=(
                '`!setup economy` — `#economy-logs`\n'
                '`!setup leveling` — `#leveling-logs`\n'
                '`!setup giveaway` — `#giveaway-logs`\n'
                '`!setup music` — `#music-logs`'
            ),
            inline=False
        )
        embed.add_field(
            name='🚀 Everything',
            value='`!setup all` — runs every module above in one go',
            inline=False
        )
        embed.add_field(
            name='🔗 Channel Binding',
            value=(
                '`!channelbind list` — see every current channel assignment\n'
                '`!channelbind <key> #channel` — point a feature at your own channel\n'
                '`!channelbind reset <key|all>` — go back to default channel name'
            ),
            inline=False
        )
        embed.set_footer(text='Only Owner / ExtraOwner can run setup commands')
        return embed

    # ══════════════════════════════════════════
    #   CHANNELBIND COMMAND
    # ══════════════════════════════════════════

    @commands.group(name='channelbind', invoke_without_command=True)
    async def channelbind_group(self, ctx: commands.Context, key: str = None, channel: discord.TextChannel = None):
        """
        !channelbind <key> #channel  → bind a feature to any channel
        !channelbind list            → show all bindings
        !channelbind reset <key|all> → reset to defaults
        """
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can use `!channelbind`.',
                color=0xe74c3c
            ))

        # No args → show help embed
        if key is None:
            return await ctx.reply(embed=self._channelbind_help_embed(ctx.prefix or '!'))

        # Key + channel → bind
        if channel is None:
            return await ctx.reply(embed=discord.Embed(
                title='❌ Missing Channel',
                description=f'Please mention a channel.\n**Usage:** `{ctx.prefix}channelbind {key} #channel`',
                color=0xe74c3c
            ))

        key = key.lower()
        if key not in BINDABLE_CHANNELS:
            valid = ', '.join(f'`{k}`' for k in BINDABLE_CHANNELS)
            return await ctx.reply(embed=discord.Embed(
                title='❌ Unknown Key',
                description=f'`{key}` is not a valid channel key.\n\n**Valid keys:**\n{valid}',
                color=0xe74c3c
            ))

        guild_id = ctx.guild.id
        self.bot.channel_binds.setdefault(guild_id, {})[key] = channel.id

        _, desc = BINDABLE_CHANNELS[key]
        embed = discord.Embed(
            title='🔗 Channel Bound!',
            color=0x2ecc71
        )
        embed.add_field(name='Feature', value=f'`{key}`\n{desc}', inline=True)
        embed.add_field(name='Now points to', value=channel.mention, inline=True)
        embed.set_footer(text=f'Reset with: {ctx.prefix}channelbind reset {key}')
        await ctx.reply(embed=embed)

    @channelbind_group.command(name='list')
    async def channelbind_list(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can use `!channelbind`.',
                color=0xe74c3c
            ))

        binds = self.bot.channel_binds.get(ctx.guild.id, {})
        guild = ctx.guild

        log_lines = []
        feature_lines = []

        for key, (default_name, desc) in BINDABLE_CHANNELS.items():
            if key in binds:
                ch = guild.get_channel(binds[key])
                status = ch.mention if ch else f'⚠️ Deleted channel (was `{binds[key]}`)'
                tag = '🔗 Custom'
            else:
                ch = discord.utils.get(guild.text_channels, name=default_name)
                status = ch.mention if ch else f'`#{default_name}` *(not created yet)*'
                tag = '📌 Default'

            line = f'`{key}` → {status} _{tag}_'

            # Split into log vs feature
            if key.endswith('-logs'):
                log_lines.append(line)
            else:
                feature_lines.append(line)

        embed = discord.Embed(
            title='📋 Channel Bindings — ' + guild.name,
            description=(
                'Shows where Lucky Bot sends every type of message.\n'
                '🔗 Custom = manually bound · 📌 Default = using default channel name'
            ),
            color=0x3498db,
            timestamp=datetime.datetime.utcnow()
        )
        if log_lines:
            embed.add_field(name='📋 Log Channels', value='\n'.join(log_lines), inline=False)
        if feature_lines:
            embed.add_field(name='🌐 Feature Channels', value='\n'.join(feature_lines), inline=False)

        embed.set_footer(text=f'Change with: {ctx.prefix}channelbind <key> #channel')
        await ctx.reply(embed=embed)

    @channelbind_group.command(name='reset')
    async def channelbind_reset(self, ctx: commands.Context, key: str = None):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can use `!channelbind`.',
                color=0xe74c3c
            ))

        if key is None:
            return await ctx.reply(embed=discord.Embed(
                title='❌ Missing Key',
                description=f'Usage: `{ctx.prefix}channelbind reset <key>` or `{ctx.prefix}channelbind reset all`',
                color=0xe74c3c
            ))

        guild_id = ctx.guild.id
        binds = self.bot.channel_binds.get(guild_id, {})

        if key.lower() == 'all':
            self.bot.channel_binds[guild_id] = {}
            return await ctx.reply(embed=discord.Embed(
                title='♻️ All Bindings Reset',
                description='All channel bindings have been reset to their default names.',
                color=0x2ecc71
            ))

        key = key.lower()
        if key not in BINDABLE_CHANNELS:
            return await ctx.reply(embed=discord.Embed(
                title='❌ Unknown Key',
                description=f'`{key}` is not a valid channel key.',
                color=0xe74c3c
            ))

        if key in binds:
            del self.bot.channel_binds[guild_id][key]
            default_name, _ = BINDABLE_CHANNELS[key]
            return await ctx.reply(embed=discord.Embed(
                title='♻️ Binding Reset',
                description=f'`{key}` will now use the default channel name `#{default_name}`.',
                color=0x2ecc71
            ))
        else:
            return await ctx.reply(embed=discord.Embed(
                title='ℹ️ Nothing to Reset',
                description=f'`{key}` was already using its default channel name.',
                color=0x95a5a6
            ))

    def _channelbind_help_embed(self, prefix: str) -> discord.Embed:
        embed = discord.Embed(
            title='🔗 Channel Binding — Help',
            description=(
                'After running `!setup`, Lucky Bot uses its default channel names.\n'
                'Use `!channelbind` to point any feature at **your own existing channels** instead.\n\n'
                '**You never have to rename your channels!**'
            ),
            color=0x3498db
        )
        embed.add_field(
            name='📖 Commands',
            value=(
                f'`{prefix}channelbind list` — see every current assignment\n'
                f'`{prefix}channelbind <key> #channel` — bind a feature to any channel\n'
                f'`{prefix}channelbind reset <key>` — reset one binding to default\n'
                f'`{prefix}channelbind reset all` — reset every binding to defaults'
            ),
            inline=False
        )
        log_keys = '\n'.join(
            f'`{k}` — {d}' for k, (_, d) in BINDABLE_CHANNELS.items() if k.endswith('-logs')
        )
        feat_keys = '\n'.join(
            f'`{k}` — {d}' for k, (_, d) in BINDABLE_CHANNELS.items() if not k.endswith('-logs')
        )
        embed.add_field(name='📋 Log Channel Keys', value=log_keys, inline=False)
        embed.add_field(name='🌐 Feature Channel Keys', value=feat_keys, inline=False)
        embed.add_field(
            name='💡 Example',
            value=(
                f'You have a `#staff-logs` channel and want mod actions there:\n'
                f'→ `{prefix}channelbind mod-logs #staff-logs`\n\n'
                f'You have a `#server-events` channel for giveaways:\n'
                f'→ `{prefix}channelbind giveaway #server-events`'
            ),
            inline=False
        )
        embed.set_footer(text='Only Owner / ExtraOwner can use channelbind')
        return embed

    # ══════════════════════════════════════════
    #   SLASH — channelbind
    # ══════════════════════════════════════════

    @app_commands.command(name='channelbind', description='Bind a Lucky Bot feature to any channel')
    @app_commands.describe(
        key='The feature key (e.g. mod-logs, welcome, tickets)',
        channel='The channel to bind it to (leave empty to see all bindings)',
    )
    async def channelbind_slash(
        self,
        interaction: discord.Interaction,
        key: str | None = None,
        channel: discord.TextChannel | None = None,
    ):
        if not self._is_god_tier(interaction.user, interaction.guild):
            return await interaction.response.send_message(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can use `/channelbind`.',
                color=0xe74c3c
            ), ephemeral=True)

        # No args → help
        if key is None:
            return await interaction.response.send_message(
                embed=self._channelbind_help_embed('/'), ephemeral=True)

        key = key.lower()
        if key not in BINDABLE_CHANNELS:
            valid = ', '.join(f'`{k}`' for k in BINDABLE_CHANNELS)
            return await interaction.response.send_message(embed=discord.Embed(
                title='❌ Unknown Key',
                description=f'`{key}` is not valid.\n\n**Valid keys:**\n{valid}',
                color=0xe74c3c
            ), ephemeral=True)

        if channel is None:
            return await interaction.response.send_message(embed=discord.Embed(
                title='❌ Missing Channel',
                description=f'Please pick a channel to bind `{key}` to.',
                color=0xe74c3c
            ), ephemeral=True)

        guild_id = interaction.guild.id
        self.bot.channel_binds.setdefault(guild_id, {})[key] = channel.id
        _, desc = BINDABLE_CHANNELS[key]
        embed = discord.Embed(title='🔗 Channel Bound!', color=0x2ecc71)
        embed.add_field(name='Feature', value=f'`{key}`\n{desc}', inline=True)
        embed.add_field(name='Now points to', value=channel.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════
    #   PREFIX SETUP COMMAND GROUP
    # ══════════════════════════════════════════

    @commands.group(name='setup', invoke_without_command=True)
    async def setup_group(self, ctx: commands.Context):
        await ctx.send(embed=self._menu_embed())

    @setup_group.command(name='basic')
    async def setup_basic(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(title='⚙️ Setting up roles...', color=0x3498db))
        results, next_steps = await self._run_basic(ctx.guild)
        await msg.edit(embed=self._result_embed('✅ Basic Setup Complete — Permission Roles', results, next_steps=next_steps))

    @setup_group.command(name='moderation')
    async def setup_moderation(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(title='⚙️ Setting up moderation...', color=0x3498db))
        results, next_steps = await self._run_moderation(ctx.guild)
        await msg.edit(embed=self._result_embed('✅ Moderation Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='security')
    async def setup_security(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(title='⚙️ Setting up security...', color=0x3498db))
        results, next_steps = await self._run_security(ctx.guild)
        await msg.edit(embed=self._result_embed('✅ Security Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='tickets')
    async def setup_tickets(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(title='⚙️ Setting up tickets...', color=0x3498db))
        results, next_steps = await self._run_tickets(ctx.guild)
        await msg.edit(embed=self._result_embed('✅ Ticket Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='welcome')
    async def setup_welcome(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(title='⚙️ Setting up welcome channels...', color=0x3498db))
        results, next_steps = await self._run_welcome(ctx.guild)
        await msg.edit(embed=self._result_embed('✅ Welcome Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='economy')
    async def setup_economy(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(title='⚙️ Setting up economy...', color=0x3498db))
        results, next_steps = await self._run_economy(ctx.guild)
        await msg.edit(embed=self._result_embed('✅ Economy Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='leveling')
    async def setup_leveling(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(title='⚙️ Setting up leveling...', color=0x3498db))
        results, next_steps = await self._run_leveling(ctx.guild)
        await msg.edit(embed=self._result_embed('✅ Leveling Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='giveaway')
    async def setup_giveaway(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(title='⚙️ Setting up giveaways...', color=0x3498db))
        results, next_steps = await self._run_giveaway(ctx.guild)
        await msg.edit(embed=self._result_embed('✅ Giveaway Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='music')
    async def setup_music(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(title='⚙️ Setting up music...', color=0x3498db))
        results, next_steps = await self._run_music(ctx.guild)
        await msg.edit(embed=self._result_embed('✅ Music Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='all')
    async def setup_all(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Running full Lucky Bot setup...', color=0x3498db,
            description='Creating all roles, channels and log categories. Please wait!'))
        results, next_steps = await self._run_all(ctx.guild)
        embed = self._result_embed('✅ Full Setup Complete!', results, next_steps=next_steps)
        embed.add_field(
            name='📊 Role Hierarchy',
            value='`ban.exe` → ban+kick+mute+warn\n`kick.exe` → kick+mute+warn\n`mute.exe` → mute+warn\n`warn.exe` → warn only',
            inline=True
        )
        embed.add_field(
            name='🔑 Independent Roles',
            value='`purge.exe` · `lock.exe` · `nick.exe`\n`announce.exe` · `audit.viewer`\n`role.giver.god` · `god.bypass`',
            inline=True
        )
        await msg.edit(embed=embed)
        mod_logs = discord.utils.get(ctx.guild.text_channels, name='mod-logs')
        if mod_logs:
            await mod_logs.send(embed=discord.Embed(
                title='🍀 Lucky Bot is Ready!',
                description=(
                    f'Full setup run by {ctx.author.mention}\n'
                    'All moderation actions will be logged here.\n'
                    'Only `audit.viewer` and admins can see this channel.'
                ),
                color=0x2ecc71
            ))

    # ══════════════════════════════════════════
    #   SLASH — setup
    # ══════════════════════════════════════════

    setup_choices = [
        app_commands.Choice(name='📋 Show menu',               value='menu'),
        app_commands.Choice(name='🔑 Basic — permission roles', value='basic'),
        app_commands.Choice(name='🛡️ Moderation',              value='moderation'),
        app_commands.Choice(name='🔒 Security',                 value='security'),
        app_commands.Choice(name='🎫 Tickets',                  value='tickets'),
        app_commands.Choice(name='👋 Welcome',                  value='welcome'),
        app_commands.Choice(name='💰 Economy',                  value='economy'),
        app_commands.Choice(name='⭐ Leveling',                  value='leveling'),
        app_commands.Choice(name='🎁 Giveaway',                 value='giveaway'),
        app_commands.Choice(name='🎵 Music',                    value='music'),
        app_commands.Choice(name='🚀 All — run everything',     value='all'),
    ]

    @app_commands.command(name='setup', description='Set up Lucky Bot (Owner/ExtraOwner only)')
    @app_commands.describe(module='Which part of Lucky Bot to set up')
    @app_commands.choices(module=setup_choices)
    async def setup_slash(self, interaction: discord.Interaction,
                          module: app_commands.Choice[str] = None):
        if module is None or module.value == 'menu':
            return await interaction.response.send_message(embed=self._menu_embed(), ephemeral=True)
        if not self._is_god_tier(interaction.user, interaction.guild):
            return await interaction.response.send_message(embed=discord.Embed(
                title='❌ No Permission', description='Only **Owner** or **ExtraOwners** can run setup!', color=0xe74c3c
            ), ephemeral=True)
        await interaction.response.defer()
        runners = {
            'basic':      (self._run_basic,      '✅ Basic Setup Complete'),
            'moderation': (self._run_moderation, '✅ Moderation Setup Complete'),
            'security':   (self._run_security,   '✅ Security Setup Complete'),
            'tickets':    (self._run_tickets,     '✅ Ticket Setup Complete'),
            'welcome':    (self._run_welcome,     '✅ Welcome Setup Complete'),
            'economy':    (self._run_economy,     '✅ Economy Setup Complete'),
            'leveling':   (self._run_leveling,    '✅ Leveling Setup Complete'),
            'giveaway':   (self._run_giveaway,    '✅ Giveaway Setup Complete'),
            'music':      (self._run_music,       '✅ Music Setup Complete'),
            'all':        (self._run_all,         '✅ Full Setup Complete!'),
        }
        runner, title = runners[module.value]
        results, next_steps = await runner(interaction.guild)
        await interaction.followup.send(embed=self._result_embed(title, results, next_steps=next_steps))


async def setup(bot: commands.Bot):
    await bot.add_cog(Setup(bot))
