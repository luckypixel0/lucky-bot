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


class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ══════════════════════════════════════════
    #   PERMISSION CHECK
    # ══════════════════════════════════════════

    def _is_god_tier(self, ctx_or_member, guild=None):
        """Works with both a Context and a raw Member."""
        if isinstance(ctx_or_member, commands.Context):
            member = ctx_or_member.author
            guild = ctx_or_member.guild
        else:
            member = ctx_or_member

        if member.id == guild.owner_id:
            return True
        # Check ExtraOwner list if moderation cog is loaded
        mod_cog = self.bot.get_cog('Moderation')
        if mod_cog and member.id in mod_cog.extraowners.get(guild.id, set()):
            return True
        return False

    # ══════════════════════════════════════════
    #   SHARED HELPERS
    # ══════════════════════════════════════════

    async def _create_roles(self, guild, roles_list):
        """Create permission roles if they don't exist. Returns list of result strings."""
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
        """Get or create the Logs category. Returns (category, result_string)."""
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
        """Create a single private log channel. Returns result string."""
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
                name=ch_name,
                overwrites=overwrites,
                category=category,
                topic=f'{emoji} {topic}'
            )
            return f'✨ Created private `#{ch_name}`'
        except Exception as e:
            return f'❌ Failed `#{ch_name}`: {e}'

    async def _create_public_channel(self, guild, ch_name, topic):
        """Create a public channel if it doesn't exist. Returns result string."""
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if existing:
            return f'✅ `#{ch_name}` already exists'
        try:
            await guild.create_text_channel(name=ch_name, topic=topic)
            return f'✨ Created `#{ch_name}`'
        except Exception as e:
            return f'❌ Failed `#{ch_name}`: {e}'

    def _result_embed(self, title, results, color=0x2ecc71, next_steps=None):
        """Build a clean results embed."""
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
    #   SETUP MODULES
    # ══════════════════════════════════════════

    async def _run_basic(self, guild):
        """Creates all 11 Lucky Bot permission roles."""
        results = await self._create_roles(guild, PERMISSION_ROLES)
        return results, (
            '1. Give `role.giver.god` to your admins\n'
            '2. Give `ban.exe` to your moderators\n'
            '3. Use `!extraowner add @user` for trusted people'
        )

    async def _run_moderation(self, guild):
        """Creates mod roles + the Logs category + mod-logs channel."""
        results = await self._create_roles(guild, PERMISSION_ROLES)
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['mod-logs']
        results.append(await self._create_log_channel(guild, 'mod-logs', emoji, topic, cat))
        # Prime massban lock if moderation cog is loaded
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
        """Creates Logs category + security-logs channel."""
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['security-logs']
        results.append(await self._create_log_channel(guild, 'security-logs', emoji, topic, cat))
        return results, (
            '1. Enable antinuke: `!antinuke on`\n'
            '2. Enable antiraid: `!antiraid on`\n'
            '3. Enable antispam: `!antispam on`\n'
            '4. Whitelist trusted users: `!antinuke whitelist @user`'
        )

    async def _run_tickets(self, guild):
        """Creates Logs category + ticket-logs + a #create-ticket channel."""
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['ticket-logs']
        results.append(await self._create_log_channel(guild, 'ticket-logs', emoji, topic, cat))
        # Public ticket creation channel
        results.append(await self._create_public_channel(
            guild, 'create-ticket', '🎫 Click the button below to open a support ticket'))
        return results, (
            '1. Once `cogs/tickets.py` is built, run `!ticket setup #create-ticket`\n'
            '2. Ticket logs will appear in `#ticket-logs`'
        )

    async def _run_welcome(self, guild):
        """Creates welcome, goodbye, and rules channels."""
        results = []
        results.append(await self._create_public_channel(guild, 'welcome', '👋 Welcome to the server!'))
        results.append(await self._create_public_channel(guild, 'goodbye', '👋 A member has left'))
        results.append(await self._create_public_channel(guild, 'rules', '📋 Server rules'))
        return results, (
            '1. Once `cogs/welcome.py` is built, run `!welcome set #welcome`\n'
            '2. Customise messages with `!welcome message Your text here`'
        )

    async def _run_economy(self, guild):
        """Creates economy-logs."""
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['economy-logs']
        results.append(await self._create_log_channel(guild, 'economy-logs', emoji, topic, cat))
        return results, 'Economy system coming soon — `cogs/economy.py`'

    async def _run_leveling(self, guild):
        """Creates leveling-logs."""
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['leveling-logs']
        results.append(await self._create_log_channel(guild, 'leveling-logs', emoji, topic, cat))
        return results, 'Leveling system coming soon — `cogs/leveling.py`'

    async def _run_giveaway(self, guild):
        """Creates giveaway-logs."""
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['giveaway-logs']
        results.append(await self._create_log_channel(guild, 'giveaway-logs', emoji, topic, cat))
        return results, 'Giveaway system coming soon — `cogs/giveaway.py`'

    async def _run_music(self, guild):
        """Creates music-logs."""
        results = []
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)
        emoji, topic = LOG_CHANNELS['music-logs']
        results.append(await self._create_log_channel(guild, 'music-logs', emoji, topic, cat))
        return results, 'Music system coming soon — `cogs/music.py`'

    async def _run_all(self, guild):
        """Runs every module in order."""
        results = []
        # 1. Basic roles
        role_results, _ = await self._run_basic(guild)
        results += role_results

        # 2. Logs category (shared — only create once)
        cat, cat_result = await self._ensure_logs_category(guild)
        results.append(cat_result)

        # 3. All log channels
        for ch_name, (emoji, topic) in LOG_CHANNELS.items():
            results.append(await self._create_log_channel(guild, ch_name, emoji, topic, cat))

        # 4. Public channels
        results.append(await self._create_public_channel(guild, 'welcome', '👋 Welcome to the server!'))
        results.append(await self._create_public_channel(guild, 'goodbye', '👋 A member has left'))
        results.append(await self._create_public_channel(guild, 'rules', '📋 Server rules'))
        results.append(await self._create_public_channel(
            guild, 'create-ticket', '🎫 Click the button below to open a support ticket'))

        # 5. Massban lock
        mod_cog = self.bot.get_cog('Moderation')
        if mod_cog:
            mod_cog.massban_enabled.setdefault(guild.id, False)
            results.append('✅ Massban locked by default')

        next_steps = (
            '1. Give `role.giver.god` to admins\n'
            '2. Give `ban.exe` to moderators\n'
            '3. Run `!extraowner add @user` for trusted people\n'
            '4. Enable security: `!antinuke on` · `!antiraid on` · `!antispam on`\n'
            '5. Check `!security` for full protection status'
        )
        return results, next_steps

    # ══════════════════════════════════════════
    #   MENU EMBED
    # ══════════════════════════════════════════

    def _menu_embed(self):
        embed = discord.Embed(
            title='⚙️ Lucky Bot — Setup Menu',
            description=(
                'Use one of the subcommands below to set up specific parts of Lucky Bot.\n'
                'Each module only creates what it needs — run them independently or all at once!'
            ),
            color=0x3498db
        )
        embed.add_field(
            name='🔑 Core',
            value=(
                '`!setup basic` — permission roles only\n'
                '`!setup moderation` — mod roles + `#mod-logs`\n'
                '`!setup security` — `#security-logs` + security guide'
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
        embed.set_footer(text='Only Owner / ExtraOwner can run setup commands')
        return embed

    # ══════════════════════════════════════════
    #   PREFIX COMMAND GROUP
    # ══════════════════════════════════════════

    @commands.group(name='setup', invoke_without_command=True)
    async def setup_group(self, ctx: commands.Context):
        """Show the Lucky Bot setup menu."""
        await ctx.send(embed=self._menu_embed())

    @setup_group.command(name='basic')
    async def setup_basic(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Setting up roles...', color=0x3498db))
        results, next_steps = await self._run_basic(ctx.guild)
        await msg.edit(embed=self._result_embed(
            '✅ Basic Setup Complete — Permission Roles', results, next_steps=next_steps))

    @setup_group.command(name='moderation')
    async def setup_moderation(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Setting up moderation...', color=0x3498db))
        results, next_steps = await self._run_moderation(ctx.guild)
        await msg.edit(embed=self._result_embed(
            '✅ Moderation Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='security')
    async def setup_security(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Setting up security...', color=0x3498db))
        results, next_steps = await self._run_security(ctx.guild)
        await msg.edit(embed=self._result_embed(
            '✅ Security Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='tickets')
    async def setup_tickets(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Setting up tickets...', color=0x3498db))
        results, next_steps = await self._run_tickets(ctx.guild)
        await msg.edit(embed=self._result_embed(
            '✅ Ticket Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='welcome')
    async def setup_welcome(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Setting up welcome channels...', color=0x3498db))
        results, next_steps = await self._run_welcome(ctx.guild)
        await msg.edit(embed=self._result_embed(
            '✅ Welcome Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='economy')
    async def setup_economy(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Setting up economy...', color=0x3498db))
        results, next_steps = await self._run_economy(ctx.guild)
        await msg.edit(embed=self._result_embed(
            '✅ Economy Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='leveling')
    async def setup_leveling(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Setting up leveling...', color=0x3498db))
        results, next_steps = await self._run_leveling(ctx.guild)
        await msg.edit(embed=self._result_embed(
            '✅ Leveling Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='giveaway')
    async def setup_giveaway(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Setting up giveaways...', color=0x3498db))
        results, next_steps = await self._run_giveaway(ctx.guild)
        await msg.edit(embed=self._result_embed(
            '✅ Giveaway Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='music')
    async def setup_music(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Setting up music...', color=0x3498db))
        results, next_steps = await self._run_music(ctx.guild)
        await msg.edit(embed=self._result_embed(
            '✅ Music Setup Complete', results, next_steps=next_steps))

    @setup_group.command(name='all')
    async def setup_all(self, ctx: commands.Context):
        if not self._is_god_tier(ctx):
            return await ctx.reply(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ))
        msg = await ctx.send(embed=discord.Embed(
            title='⚙️ Running full Lucky Bot setup...', color=0x3498db,
            description='Creating all roles, channels and log categories. Please wait!'))
        results, next_steps = await self._run_all(ctx.guild)
        embed = self._result_embed('✅ Full Setup Complete!', results, next_steps=next_steps)
        embed.add_field(
            name='📊 Role Hierarchy',
            value=(
                '`ban.exe` → ban + kick + mute + warn\n'
                '`kick.exe` → kick + mute + warn\n'
                '`mute.exe` → mute + warn\n'
                '`warn.exe` → warn only'
            ),
            inline=True
        )
        embed.add_field(
            name='🔑 Independent Roles',
            value=(
                '`purge.exe` · `lock.exe` · `nick.exe`\n'
                '`announce.exe` · `audit.viewer`\n'
                '`role.giver.god` · `god.bypass`'
            ),
            inline=True
        )
        await msg.edit(embed=embed)

        # Welcome message in mod-logs
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
    #   SLASH COMMANDS
    # ══════════════════════════════════════════

    setup_choices = [
        app_commands.Choice(name='📋 Show menu',              value='menu'),
        app_commands.Choice(name='🔑 Basic — permission roles only',  value='basic'),
        app_commands.Choice(name='🛡️ Moderation — roles + mod-logs', value='moderation'),
        app_commands.Choice(name='🔒 Security — security-logs',       value='security'),
        app_commands.Choice(name='🎫 Tickets — ticket-logs + channel',value='tickets'),
        app_commands.Choice(name='👋 Welcome — welcome/goodbye/rules',value='welcome'),
        app_commands.Choice(name='💰 Economy — economy-logs',         value='economy'),
        app_commands.Choice(name='⭐ Leveling — leveling-logs',        value='leveling'),
        app_commands.Choice(name='🎁 Giveaway — giveaway-logs',       value='giveaway'),
        app_commands.Choice(name='🎵 Music — music-logs',              value='music'),
        app_commands.Choice(name='🚀 All — run every module',          value='all'),
    ]

    @app_commands.command(name='setup', description='Set up Lucky Bot (Owner/ExtraOwner only)')
    @app_commands.describe(module='Which part of Lucky Bot to set up')
    @app_commands.choices(module=setup_choices)
    async def setup_slash(self, interaction: discord.Interaction,
                          module: app_commands.Choice[str] = None):

        # No module = show menu
        if module is None or module.value == 'menu':
            return await interaction.response.send_message(
                embed=self._menu_embed(), ephemeral=True)

        # Permission check
        member = interaction.user
        guild = interaction.guild
        if not self._is_god_tier(member, guild):
            return await interaction.response.send_message(embed=discord.Embed(
                title='❌ No Permission',
                description='Only **Owner** or **ExtraOwners** can run setup!',
                color=0xe74c3c
            ), ephemeral=True)

        await interaction.response.defer()

        runners = {
            'basic':      (self._run_basic,     '✅ Basic Setup Complete'),
            'moderation': (self._run_moderation,'✅ Moderation Setup Complete'),
            'security':   (self._run_security,  '✅ Security Setup Complete'),
            'tickets':    (self._run_tickets,   '✅ Ticket Setup Complete'),
            'welcome':    (self._run_welcome,   '✅ Welcome Setup Complete'),
            'economy':    (self._run_economy,   '✅ Economy Setup Complete'),
            'leveling':   (self._run_leveling,  '✅ Leveling Setup Complete'),
            'giveaway':   (self._run_giveaway,  '✅ Giveaway Setup Complete'),
            'music':      (self._run_music,     '✅ Music Setup Complete'),
            'all':        (self._run_all,       '✅ Full Setup Complete!'),
        }

        runner, title = runners[module.value]
        results, next_steps = await runner(guild)
        await interaction.followup.send(
            embed=self._result_embed(title, results, next_steps=next_steps))


async def setup(bot: commands.Bot):
    await bot.add_cog(Setup(bot))
