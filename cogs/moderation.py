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
        self.massban_enabled = {}
        self.extraowners = {}    # guild_id: set of user_ids
        self.role_bindings = {}  # guild_id: {perm: role_name}

        # Default role names — changeable with !rolebind
        self.DEFAULT_ROLES = {
            'warn':       'warn.exe',
            'mute':       'mute.exe',
            'ban':        'ban.exe',
            'purge':      'purge.exe',
            'lock':       'lock.exe',
            'nick':       'nick.exe',
            'announce':   'announce.exe',
            'audit':      'audit.viewer',
            'role_giver': 'role.giver.god',
            'god_bypass': 'god.bypass',
        }

    # ══════════════════════════════════════════
    #   PERMISSION HELPERS
    # ══════════════════════════════════════════

    def get_role_name(self, guild_id, perm):
        """Get current role name for a permission (respects !rolebind)"""
        bindings = self.role_bindings.get(guild_id, {})
        return bindings.get(perm, self.DEFAULT_ROLES.get(perm))

    def is_god_tier(self, member):
        """Server owner or ExtraOwner — bypasses ALL restrictions"""
        if member.id == member.guild.owner_id:
            return True
        if member.id in self.extraowners.get(member.guild.id, set()):
            return True
        return False

    def has_role_perm(self, member, perm):
        """Check if member has a specific Lucky Bot role"""
        role_name = self.get_role_name(member.guild.id, perm)
        return discord.utils.get(member.roles, name=role_name) is not None

    def has_god_bypass(self, member):
        """god.bypass role — bot cannot take action on this person"""
        role_name = self.get_role_name(member.guild.id, 'god_bypass')
        return discord.utils.get(member.roles, name=role_name) is not None

    def get_hierarchy_level(self, member):
        """0=none, 1=warn.exe, 2=mute.exe, 3=ban.exe, 999=god tier"""
        if self.is_god_tier(member):
            return 999
        if self.has_role_perm(member, 'ban'):
            return 3
        if self.has_role_perm(member, 'mute'):
            return 2
        if self.has_role_perm(member, 'warn'):
            return 1
        return 0

    def can_do(self, member, action):
        """Check if member can perform an action"""
        if self.is_god_tier(member):
            return True
        hierarchy = {'warn': 1, 'mute': 2, 'kick': 3, 'ban': 3, 'tempban': 3}
        independent = {'purge', 'lock', 'nick', 'announce'}
        if action in hierarchy:
            return self.get_hierarchy_level(member) >= hierarchy[action]
        if action in independent:
            return self.has_role_perm(member, action)
        return False

    def perm_error_embed(self, action, member_level=0):
        """Returns a detailed embed explaining what role is needed"""
        needed = {
            'warn':     ('warn.exe', 'warn members', '`warn.exe`, `mute.exe`, or `ban.exe`'),
            'mute':     ('mute.exe', 'mute members', '`mute.exe` or `ban.exe`'),
            'kick':     ('ban.exe',  'kick members',  '`ban.exe`'),
            'ban':      ('ban.exe',  'ban members',   '`ban.exe`'),
            'tempban':  ('ban.exe',  'tempban members','`ban.exe`'),
            'purge':    ('purge.exe','purge messages', '`purge.exe`'),
            'lock':     ('lock.exe', 'lock channels',  '`lock.exe`'),
            'nick':     ('nick.exe', 'change nicknames','`nick.exe`'),
            'announce': ('announce.exe','make announcements','`announce.exe`'),
        }
        role, desc, needed_str = needed.get(action, ('unknown', action, 'required role'))
        embed = discord.Embed(
            title="🚫 Missing Role Permission",
            color=0xe74c3c
        )
        embed.add_field(
            name="Why was I blocked?",
            value=f"You need {needed_str} to {desc}.",
            inline=False
        )
        if member_level > 0:
            level_names = {1: 'warn.exe', 2: 'mute.exe', 3: 'ban.exe'}
            embed.add_field(
                name="Your current level",
                value=f"`{level_names.get(member_level, 'unknown')}` — not high enough for this action.",
                inline=False
            )
        embed.add_field(
            name="What to do",
            value="Ask someone with `role.giver.god` or an ExtraOwner/Owner to give you the right role.",
            inline=False
        )
        embed.set_footer(text="Lucky Bot Permission System")
        return embed

    # ══════════════════════════════════════════
    #   HELPERS
    # ══════════════════════════════════════════

    def parse_time(self, text):
        units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        match = re.fullmatch(r'(\d+)([smhd])', text.lower())
        if match:
            return int(match.group(1)) * units[match.group(2)]
        return None

    async def send_log(self, guild, embed):
        log_channel = discord.utils.get(guild.text_channels, name='mod-logs') or \
                      discord.utils.get(guild.text_channels, name='logs')
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except:
                pass

    def log_embed(self, title, color, **fields):
        embed = discord.Embed(
            title=title, color=color,
            timestamp=datetime.datetime.utcnow()
        )
        for name, value in fields.items():
            embed.add_field(
                name=name.replace('_', ' ').title(),
                value=value, inline=True
            )
        embed.set_footer(text="Lucky Bot Logs")
        return embed

    # ══════════════════════════════════════════
    #   LISTENERS
    # ══════════════════════════════════════════

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        usage = {
            'warn':      '`!warn @user` or `!warn @user ?r reason`',
            'mute':      '`!mute @user` / `!mute @user ?t 10m` / `!mute @user ?r reason` / `!mute @user ?t 1h ?r reason`\nTime: `30s` `10m` `2h` `1d`',
            'unmute':    '`!unmute @user`',
            'kick':      '`!kick @user` or `!kick @user ?r reason`',
            'ban':       '`!ban @user` or `!ban @user ?r reason`',
            'unban':     '`!unban username`',
            'tempban':   '`!tempban @user time ?r reason`\nExample: `!tempban @user 1h ?r spamming`',
            'unwarn':    '`!unwarn @user` — latest  |  `!unwarn @user 2` — specific',
            'warnings':  '`!warnings @user`',
            'clearwarn': '`!clearwarn @user`',
            'purge':     '`!purge 10` or `!purge 10 @user`',
            'slowmode':  '`!slowmode 5m` or `!slowmode 0` to disable',
            'lock':      '`!lock` or `!lock #channel`',
            'unlock':    '`!unlock` or `!unlock #channel`',
            'role':      '`!role @user RoleName`',
            'nick':      '`!nick @user NewName`',
            'resetnick': '`!resetnick @user`',
            'note':      '`!note @user text`',
            'notes':     '`!notes @user`',
            'announce':  '`!announce #channel Message` or `!announce #channel Title | Message`',
            'poll':      '`!poll question`',
            'find':      '`!find name`',
            'afk':       '`!afk` or `!afk reason`',
        }
        cmd = ctx.command.name if ctx.command else None

        if isinstance(error, commands.CommandNotFound):
            typed = ctx.message.content.split()[0][1:]
            embed = discord.Embed(
                title="❓ Unknown Command",
                description=f"`!{typed}` doesn't exist!\nUse `!help` to see all commands.",
                color=0xe74c3c
            )
            msg = await ctx.send(embed=embed)
            await msg.delete(delay=5)
            return

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title=f"❌ Missing something in `!{cmd}`",
                color=0xe74c3c
            )
            if cmd in usage:
                embed.add_field(name="📖 How to use", value=usage[cmd], inline=False)
            return await ctx.reply(embed=embed)

        if isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                title="❌ Member Not Found",
                description="Couldn't find that member! Make sure you @mention them correctly.",
                color=0xe74c3c
            )
            if cmd in usage:
                embed.add_field(name="📖 Usage", value=usage[cmd], inline=False)
            return await ctx.reply(embed=embed)

        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Wrong Format",
                description=f"Something looks wrong in `!{cmd}`!",
                color=0xe74c3c
            )
            if cmd in usage:
                embed.add_field(name="📖 Usage", value=usage[cmd], inline=False)
            return await ctx.reply(embed=embed)

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"⏰ Slow down! Try again in **{error.retry_after:.1f}s**.")
            return

        print(f'Unhandled error in !{cmd}: {error}')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        # AFK return check
        if message.author.id in self.afk_db:
            del self.afk_db[message.author.id]
            try:
                await message.author.edit(
                    nick=message.author.display_name.replace('[AFK] ', '')
                )
            except:
                pass
            msg = await message.channel.send(
                f"👋 Welcome back {message.author.mention}! AFK removed."
            )
            await msg.delete(delay=5)
        # Notify if pinging AFK user
        for user in message.mentions:
            if user.id in self.afk_db:
                data = self.afk_db[user.id]
                embed = discord.Embed(
                    title="💤 User is AFK",
                    description=f"{user.mention} is currently AFK.",
                    color=0x95a5a6
                )
                embed.add_field(name="Reason", value=data['reason'])
                embed.add_field(name="Since", value=f"<t:{data['time']}:R>")
                await message.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        self.snipe_db[message.channel.id] = {
            'content': message.content or '[No text]',
            'author': message.author,
            'time': datetime.datetime.utcnow(),
            'attachments': [a.url for a in message.attachments]
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
        self.editsnipe_db[before.channel.id] = {
            'before': before.content or '[No text]',
            'after': after.content or '[No text]',
            'author': before.author,
            'time': datetime.datetime.utcnow()
        }

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        """Auto-mute anyone who changes server profile (except owner/extraowner)"""
        changes = []
        if before.name != after.name:
            changes.append(f"Server name: `{before.name}` → `{after.name}`")
        if before.icon != after.icon:
            changes.append("Server icon was changed")
        if before.description != after.description:
            changes.append("Server description was changed")
        if before.banner != after.banner:
            changes.append("Server banner was changed")
        if before.splash != after.splash:
            changes.append("Server invite splash was changed")
        if not changes:
            return

        try:
            async for entry in after.audit_logs(
                limit=1,
                action=discord.AuditLogAction.guild_update
            ):
                user = entry.user
                member = after.get_member(user.id)
                if not member or member.bot:
                    return
                # Skip owner and extraowners
                if self.is_god_tier(member):
                    return

                change_text = "\n".join(changes)
                reason = f"[Auto-Mod] Unauthorized server profile change"

                # Mute for 2 minutes
                until = discord.utils.utcnow() + datetime.timedelta(minutes=2)
                await member.timeout(until, reason=reason)

                embed = discord.Embed(
                    title="🔒 Auto-Mute: Unauthorized Server Change",
                    color=0xff6600,
                    timestamp=datetime.datetime.utcnow()
                )
                embed.add_field(
                    name="User",
                    value=f"{member.mention} (`{member.id}`)"
                )
                embed.add_field(name="Duration", value="2 minutes")
                embed.add_field(
                    name="What They Changed",
                    value=change_text,
                    inline=False
                )
                embed.add_field(
                    name="Why Muted",
                    value=(
                        "Only the server owner and ExtraOwners are allowed "
                        "to modify the server profile."
                    ),
                    inline=False
                )
                embed.set_footer(text="Lucky Bot Auto-Mod")
                await self.send_log(after, embed)

                try:
                    await member.send(
                        f"🔒 You were automatically muted in **{after.name}** for 2 minutes.\n"
                        f"Reason: You changed the server profile.\n"
                        f"Changes made:\n{change_text}"
                    )
                except:
                    pass
        except Exception as e:
            print(f"on_guild_update error: {e}")

    # ══════════════════════════════════════════
    #   EXTRAOWNER SYSTEM
    # ══════════════════════════════════════════

    @commands.group(invoke_without_command=True)
    async def extraowner(self, ctx):
        """ExtraOwner management. Usage: !extraowner add/remove/list @user"""
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("❌ Only the **server owner** can manage ExtraOwners!")
        eos = self.extraowners.get(ctx.guild.id, set())
        mentions = [f"<@{uid}>" for uid in eos] or ["None"]
        embed = discord.Embed(
            title="👑 ExtraOwner List",
            description="\n".join(mentions),
            color=0xf1c40f
        )
        embed.add_field(
            name="Commands",
            value=(
                "`!extraowner add @user` — add ExtraOwner\n"
                "`!extraowner remove @user` — remove ExtraOwner\n"
                "`!extraowner list` — see all ExtraOwners"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @extraowner.command(name='add')
    async def extraowner_add(self, ctx, member: discord.Member):
        """Add an ExtraOwner. Usage: !extraowner add @user"""
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("❌ Only the **server owner** can add ExtraOwners!")
        if member.id == ctx.guild.owner_id:
            return await ctx.reply("❌ The server owner is already god tier!")
        guild_id = ctx.guild.id
        if guild_id not in self.extraowners:
            self.extraowners[guild_id] = set()
        self.extraowners[guild_id].add(member.id)
        embed = discord.Embed(
            title="👑 ExtraOwner Added",
            description=(
                f"{member.mention} is now an **ExtraOwner**!\n\n"
                "They can now:\n"
                "• Use all mod commands on anyone\n"
                "• Toggle anti-nuke, anti-raid etc\n"
                "• Add/remove Lucky Bot roles\n"
                "• Are immune to all bot actions"
            ),
            color=0xf1c40f
        )
        await ctx.send(embed=embed)
        log = self.log_embed("👑 ExtraOwner Added", 0xf1c40f,
            user=f"{member} ({member.id})",
            added_by=str(ctx.author)
        )
        await self.send_log(ctx.guild, log)

    @extraowner.command(name='remove')
    async def extraowner_remove(self, ctx, member: discord.Member):
        """Remove an ExtraOwner. Usage: !extraowner remove @user"""
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("❌ Only the **server owner** can remove ExtraOwners!")
        guild_id = ctx.guild.id
        if guild_id in self.extraowners:
            self.extraowners[guild_id].discard(member.id)
        await ctx.reply(f"✅ Removed {member.mention} from ExtraOwners!")

    @extraowner.command(name='list')
    async def extraowner_list(self, ctx):
        """List all ExtraOwners."""
        eos = self.extraowners.get(ctx.guild.id, set())
        mentions = [f"<@{uid}>" for uid in eos] or ["None set"]
        embed = discord.Embed(
            title="👑 ExtraOwners",
            description="\n".join(mentions),
            color=0xf1c40f
        )
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════
    #   ROLEBIND SYSTEM
    # ══════════════════════════════════════════

    @commands.command()
    async def rolebind(self, ctx, perm: str, *, role: discord.Role = None):
        """
        Reassign which role has a Lucky Bot permission.
        Usage: !rolebind warn.exe @role
               !rolebind warn.exe reset  ← reset to default
               !rolebind list            ← see all bindings
        Permissions: Owner or ExtraOwner only
        """
        if not self.is_god_tier(ctx.author):
            return await ctx.reply("❌ Only the **owner** or **ExtraOwners** can rebind roles!")

        if perm == "list":
            guild_id = ctx.guild.id
            bindings = self.role_bindings.get(guild_id, {})
            embed = discord.Embed(title="🔗 Role Bindings", color=0x3498db)
            for p, default in self.DEFAULT_ROLES.items():
                current = bindings.get(p, default)
                changed = "✏️" if p in bindings else "✅"
                embed.add_field(
                    name=f"{changed} {p}",
                    value=f"Currently: `{current}`\nDefault: `{default}`",
                    inline=True
                )
            await ctx.send(embed=embed)
            return

        valid_perms = list(self.DEFAULT_ROLES.keys())
        # Also accept the role names directly like "warn.exe"
        perm_map = {v: k for k, v in self.DEFAULT_ROLES.items()}
        if perm in perm_map:
            perm = perm_map[perm]

        if perm not in valid_perms:
            return await ctx.reply(
                f"❌ Unknown permission `{perm}`!\n"
                f"Valid: `{'`, `'.join(valid_perms)}`"
            )

        guild_id = ctx.guild.id
        if guild_id not in self.role_bindings:
            self.role_bindings[guild_id] = {}

        # Reset to default
        if role is None or (isinstance(role, str) and role == "reset"):
            self.role_bindings[guild_id].pop(perm, None)
            default = self.DEFAULT_ROLES[perm]
            return await ctx.reply(f"✅ Reset `{perm}` back to default role: `{default}`")

        self.role_bindings[guild_id][perm] = role.name
        embed = discord.Embed(title="🔗 Role Binding Updated", color=0x2ecc71)
        embed.add_field(name="Permission", value=f"`{perm}`")
        embed.add_field(name="Now bound to", value=role.mention)
        embed.add_field(
            name="Effect",
            value=f"Members with `{role.name}` now have `{perm}` powers.",
            inline=False
        )
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════
    #   ROLE GIVER SYSTEM
    # ══════════════════════════════════════════

    @commands.command(name='giverole')
    async def give_role(self, ctx, member: discord.Member, *, role_name: str):
        """
        Give a Lucky Bot permission role to a member.
        Usage: !giverole @user warn.exe
        Rules:
        - role.giver.god can give any role below their highest level
        - Independent role holders (purge.exe etc) can give that same role
        - Owner/ExtraOwner can give anything
        """
        guild_id = ctx.guild.id

        # Normalize role name
        target_role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not target_role:
            return await ctx.reply(f"❌ Role `{role_name}` not found in this server!")

        # Check if it's a Lucky Bot role
        lucky_roles = {self.get_role_name(guild_id, p): p for p in self.DEFAULT_ROLES}
        perm_key = lucky_roles.get(target_role.name)

        if not perm_key:
            return await ctx.reply(
                f"❌ `{role_name}` is not a Lucky Bot permission role!\n"
                f"Use `!rolebind list` to see all Lucky Bot roles."
            )

        # God tier can give anything
        if self.is_god_tier(ctx.author):
            await member.add_roles(target_role)
            return await ctx.reply(f"✅ Given `{target_role.name}` to {member.mention}!")

        # role.giver.god can give roles below their highest level
        if self.has_role_perm(ctx.author, 'role_giver'):
            author_level = self.get_hierarchy_level(ctx.author)
            hierarchy_map = {'warn': 1, 'mute': 2, 'ban': 3}
            target_level = hierarchy_map.get(perm_key, 0)

            # For hierarchy roles, check level
            if perm_key in hierarchy_map:
                if target_level < author_level:
                    await member.add_roles(target_role)
                    log = self.log_embed("🏷️ Role Given", 0x3498db,
                        to=f"{member} ({member.id})",
                        role=target_role.name,
                        given_by=str(ctx.author)
                    )
                    await self.send_log(ctx.guild, log)
                    return await ctx.reply(f"✅ Given `{target_role.name}` to {member.mention}!")
                else:
                    return await ctx.reply(
                        f"❌ You can only give roles **below** your level!\n"
                        f"Your highest: `{self.DEFAULT_ROLES.get('ban' if author_level==3 else 'mute' if author_level==2 else 'warn', 'none')}`"
                    )
            else:
                # Independent roles — role.giver.god can give them
                await member.add_roles(target_role)
                log = self.log_embed("🏷️ Role Given", 0x3498db,
                    to=f"{member} ({member.id})",
                    role=target_role.name,
                    given_by=str(ctx.author)
                )
                await self.send_log(ctx.guild, log)
                return await ctx.reply(f"✅ Given `{target_role.name}` to {member.mention}!")

        # Independent role holders can give that same role
        if perm_key in ('purge', 'lock', 'nick', 'announce', 'audit'):
            if self.has_role_perm(ctx.author, perm_key):
                await member.add_roles(target_role)
                return await ctx.reply(f"✅ Given `{target_role.name}` to {member.mention}!")

        return await ctx.reply(
            f"❌ You don't have permission to give `{target_role.name}`!\n"
            f"You need `role.giver.god` or the same independent role."
        )

    @commands.command(name='takerole')
    async def take_role(self, ctx, member: discord.Member, *, role_name: str):
        """
        Remove a Lucky Bot permission role from a member.
        Usage: !takerole @user warn.exe
        Same permission rules as !giverole
        """
        guild_id = ctx.guild.id
        target_role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not target_role:
            return await ctx.reply(f"❌ Role `{role_name}` not found!")

        lucky_roles = {self.get_role_name(guild_id, p): p for p in self.DEFAULT_ROLES}
        perm_key = lucky_roles.get(target_role.name)
        if not perm_key:
            return await ctx.reply(f"❌ `{role_name}` is not a Lucky Bot role!")

        if not self.is_god_tier(ctx.author) and not self.has_role_perm(ctx.author, 'role_giver'):
            return await ctx.reply("❌ You need `role.giver.god` or god tier to remove roles!")

        await member.remove_roles(target_role)
        log = self.log_embed("🏷️ Role Removed", 0xe74c3c,
            from_user=f"{member} ({member.id})",
            role=target_role.name,
            removed_by=str(ctx.author)
        )
        await self.send_log(ctx.guild, log)
        await ctx.reply(f"✅ Removed `{target_role.name}` from {member.mention}!")

    # ══════════════════════════════════════════
    #   SETUP COMMAND
    # ══════════════════════════════════════════

    @commands.command()
    async def setup(self, ctx):
        """
        Auto-setup everything Lucky Bot needs.
        Creates all roles, channels, and configures permissions.
        Owner or ExtraOwner only.
        """
        if not self.is_god_tier(ctx.author):
            return await ctx.reply("❌ Only the **owner** or **ExtraOwners** can run setup!")

        embed = discord.Embed(
            title="⚙️ Lucky Bot Setup",
            description="Setting everything up... please wait!",
            color=0x3498db
        )
        status_msg = await ctx.send(embed=embed)
        results = []
        guild = ctx.guild

        # ── Create all Lucky Bot roles ─────────
        roles_to_create = [
            # (name, color, description)
            ('ban.exe',        0xc0392b, 'Can ban, kick, mute and warn members'),
            ('mute.exe',       0xe67e22, 'Can mute and warn members'),
            ('warn.exe',       0xf1c40f, 'Can warn members'),
            ('purge.exe',      0x3498db, 'Can purge messages'),
            ('lock.exe',       0x9b59b6, 'Can lock/unlock channels'),
            ('nick.exe',       0x1abc9c, 'Can change nicknames'),
            ('announce.exe',   0x2ecc71, 'Can make announcements'),
            ('audit.viewer',   0x95a5a6, 'Can view mod-logs channel'),
            ('role.giver.god', 0xe91e63, 'Can give Lucky Bot roles to others'),
            ('god.bypass',     0xffd700, 'Bypasses all bot moderation actions'),
        ]

        for role_name, color, desc in roles_to_create:
            existing = discord.utils.get(guild.roles, name=role_name)
            if existing:
                results.append(f"✅ `{role_name}` already exists — skipped")
            else:
                try:
                    await guild.create_role(
                        name=role_name,
                        color=discord.Color(color),
                        reason=f"Lucky Bot setup — {desc}",
                        mentionable=False,
                        hoist=False
                    )
                    results.append(f"✅ Created role `{role_name}`")
                except Exception as e:
                    results.append(f"❌ Failed `{role_name}`: {e}")

        # ── Create mod-logs channel ────────────
        try:
            existing_logs = discord.utils.get(guild.text_channels, name='mod-logs')
            if existing_logs:
                results.append("✅ `#mod-logs` already exists — skipped")
                log_channel = existing_logs
            else:
                # Get audit.viewer role
                audit_role = discord.utils.get(guild.roles, name=self.get_role_name(guild.id, 'audit'))

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
                }
                # Give access to audit.viewer role
                if audit_role:
                    overwrites[audit_role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=False,
                        read_message_history=True
                    )
                # Give access to admin roles
                for role in guild.roles:
                    if role.permissions.administrator:
                        overwrites[role] = discord.PermissionOverwrite(
                            view_channel=True,
                            send_messages=False
                        )

                mod_category = (
                    discord.utils.get(guild.categories, name='Mod') or
                    discord.utils.get(guild.categories, name='Staff') or
                    discord.utils.get(guild.categories, name='Admin')
                )
                log_channel = await guild.create_text_channel(
                    name='mod-logs',
                    overwrites=overwrites,
                    category=mod_category,
                    topic='🔒 Private Lucky Bot mod logs'
                )
                results.append("✅ Created private `#mod-logs` channel")
        except Exception as e:
            results.append(f"❌ Failed `#mod-logs`: {e}")
            log_channel = None

        # ── Create welcome channel ─────────────
        try:
            if not discord.utils.get(guild.text_channels, name='welcome'):
                await guild.create_text_channel(name='welcome', topic='👋 Welcome!')
                results.append("✅ Created `#welcome` channel")
            else:
                results.append("✅ `#welcome` already exists — skipped")
        except Exception as e:
            results.append(f"❌ Failed `#welcome`: {e}")

        # ── Create rules channel ───────────────
        try:
            if not discord.utils.get(guild.text_channels, name='rules'):
                await guild.create_text_channel(name='rules', topic='📋 Server rules')
                results.append("✅ Created `#rules` channel")
            else:
                results.append("✅ `#rules` already exists — skipped")
        except Exception as e:
            results.append(f"❌ Failed `#rules`: {e}")

        # ── Massban off by default ─────────────
        self.massban_enabled[guild.id] = False
        results.append("✅ Massban locked by default")

        # ── Final embed ────────────────────────
        embed = discord.Embed(
            title="✅ Lucky Bot Setup Complete!",
            description="\n".join(results),
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(
            name="📋 Role Hierarchy",
            value=(
                "`ban.exe` → ban + kick + mute + warn\n"
                "`mute.exe` → mute + warn\n"
                "`warn.exe` → warn only"
            ),
            inline=True
        )
        embed.add_field(
            name="🔑 Independent Roles",
            value=(
                "`purge.exe` → purge messages\n"
                "`lock.exe` → lock channels\n"
                "`nick.exe` → nicknames\n"
                "`announce.exe` → announcements\n"
                "`audit.viewer` → see mod-logs"
            ),
            inline=True
        )
        embed.add_field(
            name="👑 Special Roles",
            value=(
                "`role.giver.god` → give/take roles\n"
                "`god.bypass` → immune to bot actions\n"
                "ExtraOwner → bypasses everything"
            ),
            inline=True
        )
        embed.add_field(
            name="⚡ Next Steps",
            value=(
                "1. Give `role.giver.god` to your admins\n"
                "2. Give `ban.exe` to your moderators\n"
                "3. Use `!extraowner add @user` for trusted admins\n"
                "4. Use `!rolebind` to reassign roles if needed"
            ),
            inline=False
        )
        embed.set_footer(text=f"Set up by {ctx.author} • Lucky Bot")
        await status_msg.edit(embed=embed)

        if log_channel:
            await log_channel.send(embed=discord.Embed(
                title="🍀 Lucky Bot is ready!",
                description=(
                    f"Set up by {ctx.author.mention}\n"
                    "All mod actions will be logged here.\n"
                    "Only `audit.viewer` role and admins can see this channel."
                ),
                color=0x2ecc71,
                timestamp=datetime.datetime.utcnow()
            ))

    # ══════════════════════════════════════════
    #   MODERATION COMMANDS
    # ══════════════════════════════════════════

    @commands.command()
    async def warn(self, ctx, member: discord.Member, *, args=""):
        """Warn a member. Usage: !warn @user ?r reason"""
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        if self.has_god_bypass(member) and not self.is_god_tier(ctx.author):
            return await ctx.reply(f"❌ {member.mention} has `god.bypass` — bot cannot take action on them!")

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
            await member.send(
                f"⚠️ Warned in **{ctx.guild.name}**\n"
                f"Reason: {reason}\nTotal: {count} warnings"
            )
        except:
            pass
        if count >= 3:
            await ctx.send(f"🚨 {member.mention} now has **{count} warnings!**")
        log = self.log_embed("⚠️ Member Warned", 0xf39c12,
            user=f"{member} ({member.id})", reason=reason,
            total_warnings=str(count), moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    async def warnings(self, ctx, member: discord.Member):
        """Check warnings. Usage: !warnings @user"""
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        warns = self.warn_db.get(ctx.guild.id, {}).get(member.id, [])
        if not warns:
            return await ctx.reply(f"✅ {member.mention} has no warnings!")
        embed = discord.Embed(
            title=f"⚠️ Warnings for {member.display_name}",
            color=0xf39c12
        )
        for i, w in enumerate(warns, 1):
            embed.add_field(name=f"Warning #{i}", value=w, inline=False)
        embed.set_footer(text=f"Total: {len(warns)} warnings")
        await ctx.send(embed=embed)

    @commands.command()
    async def unwarn(self, ctx, member: discord.Member, number: int = None):
        """Remove a warning. Usage: !unwarn @user  or  !unwarn @user 2"""
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        guild_id = ctx.guild.id
        warns = self.warn_db.get(guild_id, {}).get(member.id, [])
        if not warns:
            return await ctx.reply(f"✅ {member.mention} has no warnings!")
        if number is None:
            removed = warns.pop()
        else:
            if number < 1 or number > len(warns):
                return await ctx.reply(f"❌ Invalid! {member.mention} has {len(warns)} warnings.")
            removed = warns.pop(number - 1)
        self.warn_db[guild_id][member.id] = warns
        embed = discord.Embed(title="✅ Warning Removed", color=0x2ecc71)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Removed", value=removed)
        embed.add_field(name="Remaining", value=str(len(warns)))
        await ctx.send(embed=embed)

    @commands.command()
    async def clearwarn(self, ctx, member: discord.Member):
        """Clear all warnings. Usage: !clearwarn @user"""
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        if ctx.guild.id in self.warn_db and member.id in self.warn_db[ctx.guild.id]:
            self.warn_db[ctx.guild.id][member.id] = []
        await ctx.reply(f"🧹 Cleared all warnings for {member.mention}!")

    @commands.command()
    async def mute(self, ctx, member: discord.Member, *, args=""):
        """
        Mute a member.
        Usage: !mute @user
               !mute @user ?t 10m
               !mute @user ?r reason
               !mute @user ?t 1h ?r reason
        Time: 30s, 10m, 2h, 1d
        """
        if not self.can_do(ctx.author, 'mute'):
            lvl = self.get_hierarchy_level(ctx.author)
            return await ctx.reply(embed=self.perm_error_embed('mute', lvl))
        if self.has_god_bypass(member) and not self.is_god_tier(ctx.author):
            return await ctx.reply(f"❌ {member.mention} has `god.bypass` — bot cannot mute them!")
        if member.id == ctx.guild.owner_id:
            return await ctx.reply("❌ Cannot mute the server owner!")
        if member.id in self.extraowners.get(ctx.guild.id, set()):
            return await ctx.reply("❌ Cannot mute an ExtraOwner!")

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
                return await ctx.reply(
                    "❌ Invalid time format!\n"
                    "Use: `30s`, `10m`, `2h`, `1d`\n"
                    "Example: `!mute @user ?t 30m ?r spamming`"
                )

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
            await member.send(
                f"🔇 Muted in **{ctx.guild.name}** for **{duration_text}**\n"
                f"Reason: {reason}"
            )
        except:
            pass
        log = self.log_embed("🔇 Member Muted", 0x95a5a6,
            user=f"{member} ({member.id})", duration=duration_text,
            reason=reason, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member. Usage: !unmute @user"""
        if not self.can_do(ctx.author, 'mute'):
            return await ctx.reply(embed=self.perm_error_embed('mute'))
        await member.timeout(None)
        embed = discord.Embed(title="🔊 Member Unmuted", color=0x2ecc71)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        log = self.log_embed("🔊 Unmuted", 0x2ecc71,
            user=f"{member} ({member.id})", moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, args=""):
        """Kick a member. Usage: !kick @user ?r reason"""
        if not self.can_do(ctx.author, 'kick'):
            lvl = self.get_hierarchy_level(ctx.author)
            embed = self.perm_error_embed('kick', lvl)
            if lvl > 0:
                embed.add_field(
                    name="💡 Your role can't do this",
                    value=(
                        f"You have `{'mute.exe' if lvl==2 else 'warn.exe'}` — "
                        f"that only allows {'muting' if lvl==2 else 'warning'}.\n"
                        f"You need `ban.exe` to kick members."
                    ),
                    inline=False
                )
            return await ctx.reply(embed=embed)
        if self.has_god_bypass(member) and not self.is_god_tier(ctx.author):
            return await ctx.reply(f"❌ {member.mention} has `god.bypass`!")
        if member.id == ctx.guild.owner_id:
            return await ctx.reply("❌ Cannot kick the server owner!")
        if member.id in self.extraowners.get(ctx.guild.id, set()):
            return await ctx.reply("❌ Cannot kick an ExtraOwner!")

        reason = "No reason provided"
        if "?r" in args:
            reason = args.split("?r", 1)[1].strip()
        await member.kick(reason=reason)
        embed = discord.Embed(title="👢 Member Kicked", color=0xe74c3c)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        try:
            await member.send(f"👢 Kicked from **{ctx.guild.name}**\nReason: {reason}")
        except:
            pass
        log = self.log_embed("👢 Member Kicked", 0xe74c3c,
            user=f"{member} ({member.id})", reason=reason,
            moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, args=""):
        """Ban a member. Usage: !ban @user ?r reason"""
        if not self.can_do(ctx.author, 'ban'):
            lvl = self.get_hierarchy_level(ctx.author)
            embed = self.perm_error_embed('ban', lvl)
            if lvl > 0:
                level_names = {1: 'warn.exe', 2: 'mute.exe'}
                embed.add_field(
                    name="💡 Your role can't do this",
                    value=(
                        f"You have `{level_names.get(lvl, 'unknown')}` — "
                        f"that only allows {'warning' if lvl==1 else 'muting and warning'}.\n"
                        f"You need `ban.exe` to ban members."
                    ),
                    inline=False
                )
            return await ctx.reply(embed=embed)
        if self.has_god_bypass(member) and not self.is_god_tier(ctx.author):
            return await ctx.reply(f"❌ {member.mention} has `god.bypass`!")
        if member.id == ctx.guild.owner_id:
            return await ctx.reply("❌ Cannot ban the server owner!")
        if member.id in self.extraowners.get(ctx.guild.id, set()):
            return await ctx.reply("❌ Cannot ban an ExtraOwner!")

        reason = "No reason provided"
        if "?r" in args:
            reason = args.split("?r", 1)[1].strip()
        await member.ban(reason=reason)
        embed = discord.Embed(title="🔨 Member Banned", color=0xc0392b)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        try:
            await member.send(f"🔨 Banned from **{ctx.guild.name}**\nReason: {reason}")
        except:
            pass
        log = self.log_embed("🔨 Member Banned", 0xc0392b,
            user=f"{member} ({member.id})", reason=reason,
            moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    async def unban(self, ctx, *, username):
        """Unban a user. Usage: !unban username"""
        if not self.can_do(ctx.author, 'ban'):
            return await ctx.reply(embed=self.perm_error_embed('ban'))
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
            log = self.log_embed("✅ Unbanned", 0x2ecc71,
                user=f"{matches[0].user}", moderator=str(ctx.author))
            await self.send_log(ctx.guild, log)
            return
        desc = "\n".join([f"`{i+1}.` {e.user}" for i, e in enumerate(matches[:10])])
        await ctx.send(embed=discord.Embed(
            title="🔍 Multiple matches",
            description=f"{desc}\n\nReply with a number:",
            color=0xe67e22
        ))
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
            index = int(msg.content) - 1
            if 0 <= index < len(matches):
                await ctx.guild.unban(matches[index].user)
                await ctx.reply(f"✅ Unbanned **{matches[index].user}**!")
        except asyncio.TimeoutError:
            await ctx.reply("⏰ Timed out!")

    @commands.command()
    async def tempban(self, ctx, member: discord.Member, time: str, *, args=""):
        """Tempban. Usage: !tempban @user 1h ?r reason"""
        if not self.can_do(ctx.author, 'tempban'):
            lvl = self.get_hierarchy_level(ctx.author)
            return await ctx.reply(embed=self.perm_error_embed('tempban', lvl))
        if self.has_god_bypass(member) and not self.is_god_tier(ctx.author):
            return await ctx.reply(f"❌ {member.mention} has `god.bypass`!")

        reason = "No reason provided"
        if "?r" in args:
            reason = args.split("?r", 1)[1].strip()
        seconds = self.parse_time(time)
        if not seconds:
            return await ctx.reply("❌ Invalid time! Use: `30s`, `10m`, `2h`, `1d`")

        await member.ban(reason=f"[Tempban: {time}] {reason}")
        unban_ts = int((datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)).timestamp())
        embed = discord.Embed(title="⏳ Member Tempbanned", color=0xc0392b)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Duration", value=time)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Unban at", value=f"<t:{unban_ts}:R>")
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        log = self.log_embed("⏳ Tempban", 0xc0392b,
            user=f"{member} ({member.id})", duration=time,
            reason=reason, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)
        await asyncio.sleep(seconds)
        try:
            await ctx.guild.unban(member, reason="Tempban expired")
            await self.send_log(ctx.guild, self.log_embed(
                "✅ Tempban Expired", 0x2ecc71, user=str(member)))
        except:
            pass

    @commands.command()
    async def massban(self, ctx, action: str = None, *members: discord.Member):
        """
        Massban — disabled by default.
        Usage: !massban enable/disable/status
               !massban @u1 @u2 @u3 (when enabled)
        """
        if not self.is_god_tier(ctx.author):
            return await ctx.reply("❌ Only **owner** or **ExtraOwners** can use massban!")
        guild_id = ctx.guild.id
        if action == "enable":
            self.massban_enabled[guild_id] = True
            await ctx.send(embed=discord.Embed(
                title="🔓 Massban ENABLED",
                description="Use `!massban @u1 @u2 ...` to ban multiple members.\nUse `!massban disable` to turn off.",
                color=0xe74c3c
            ))
            return
        if action == "disable":
            self.massban_enabled[guild_id] = False
            return await ctx.reply("🔒 Massban **disabled**!")
        if action == "status":
            status = self.massban_enabled.get(guild_id, False)
            return await ctx.reply(f"Massban is **{'🔓 ENABLED' if status else '🔒 DISABLED'}**")
        if not self.massban_enabled.get(guild_id, False):
            return await ctx.send(embed=discord.Embed(
                title="🔒 Massban is Disabled",
                description="Run `!massban enable` first.\n⚠️ Disable it again after use!",
                color=0xe74c3c
            ))
        if not members and action:
            try:
                first = await commands.MemberConverter().convert(ctx, action)
                members = (first,) + members
            except:
                return await ctx.reply("❌ Mention members to ban!")
        if not members:
            return await ctx.reply("❌ Mention at least one member!")
        await ctx.send(embed=discord.Embed(
            title="⚠️ Confirm Massban",
            description=f"Ban **{len(members)}** members? Reply `yes`.",
            color=0xe74c3c
        ))
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
        try:
            await self.bot.wait_for('message', check=check, timeout=20)
        except asyncio.TimeoutError:
            return await ctx.reply("❌ Cancelled!")
        banned, failed = [], []
        for m in members:
            try:
                await m.ban(reason=f"Massban by {ctx.author}")
                banned.append(str(m))
            except:
                failed.append(str(m))
        embed = discord.Embed(title="🔨 Mass Ban Complete", color=0xc0392b)
        if banned:
            embed.add_field(name=f"✅ Banned ({len(banned)})", value="\n".join(banned))
        if failed:
            embed.add_field(name=f"❌ Failed ({len(failed)})", value="\n".join(failed))
        await ctx.send(embed=embed)
        log = self.log_embed("🔨 Massban", 0xc0392b,
            banned=", ".join(banned) or "None",
            failed=", ".join(failed) or "None",
            moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    async def purge(self, ctx, amount: int, member: discord.Member = None):
        """Delete messages. Usage: !purge 10  or  !purge 10 @user"""
        if not self.can_do(ctx.author, 'purge'):
            return await ctx.reply(embed=self.perm_error_embed('purge'))
        if amount > 100:
            return await ctx.reply("❌ Max 100 at once!")
        if member:
            deleted = await ctx.channel.purge(
                limit=amount * 5,
                check=lambda m: m.author == member
            )
        else:
            deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🗑️ Deleted **{len(deleted)}** messages!")
        await msg.delete(delay=3)
        log = self.log_embed("🗑️ Purge", 0xe74c3c,
            channel=ctx.channel.mention,
            deleted=str(len(deleted)),
            target=str(member) if member else "All",
            moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    async def slowmode(self, ctx, time: str = "0"):
        """Set slowmode. Usage: !slowmode 5m  or  !slowmode 0"""
        if not self.can_do(ctx.author, 'lock'):
            return await ctx.reply(embed=self.perm_error_embed('lock'))
        if time in ("0", "off"):
            await ctx.channel.edit(slowmode_delay=0)
            return await ctx.reply("✅ Slowmode disabled!")
        seconds = self.parse_time(time)
        if not seconds:
            return await ctx.reply("❌ Invalid format! Use: `30s`, `5m`, `1h`")
        if seconds > 21600:
            return await ctx.reply("❌ Max slowmode is 6 hours!")
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.reply(f"✅ Slowmode set to **{time}**!")

    @commands.command()
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Lock a channel. Usage: !lock or !lock #channel"""
        if not self.can_do(ctx.author, 'lock'):
            return await ctx.reply(embed=self.perm_error_embed('lock'))
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(f"🔒 **#{channel.name}** locked!")
        log = self.log_embed("🔒 Channel Locked", 0xe74c3c,
            channel=channel.mention, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock a channel. Usage: !unlock or !unlock #channel"""
        if not self.can_do(ctx.author, 'lock'):
            return await ctx.reply(embed=self.perm_error_embed('lock'))
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(f"🔓 **#{channel.name}** unlocked!")
        log = self.log_embed("🔓 Channel Unlocked", 0x2ecc71,
            channel=channel.mention, moderator=str(ctx.author))
        await self.send_log(ctx.guild, log)

    @commands.command()
    async def nick(self, ctx, member: discord.Member, *, nickname):
        """Change nickname. Usage: !nick @user NewName"""
        if not self.can_do(ctx.author, 'nick'):
            return await ctx.reply(embed=self.perm_error_embed('nick'))
        old = member.display_name
        await member.edit(nick=nickname)
        await ctx.reply(f"✅ Changed **{old}'s** nickname to **{nickname}**!")

    @commands.command()
    async def resetnick(self, ctx, member: discord.Member):
        """Reset nickname. Usage: !resetnick @user"""
        if not self.can_do(ctx.author, 'nick'):
            return await ctx.reply(embed=self.perm_error_embed('nick'))
        await member.edit(nick=None)
        await ctx.reply(f"✅ Reset **{member.name}'s** nickname!")

    @commands.command()
    async def announce(self, ctx, channel: discord.TextChannel, *, args):
        """
        Send announcement.
        Usage: !announce #channel Message
               !announce #channel Title | Message
        """
        if not self.can_do(ctx.author, 'announce'):
            return await ctx.reply(embed=self.perm_error_embed('announce'))
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
    async def poll(self, ctx, *, question):
        """Create a poll. Usage: !poll question"""
        if not self.can_do(ctx.author, 'announce'):
            return await ctx.reply(embed=self.perm_error_embed('announce'))
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
    async def note(self, ctx, member: discord.Member, *, note: str):
        """Add a mod note. Usage: !note @user text"""
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        guild_id = ctx.guild.id
        if guild_id not in self.notes_db:
            self.notes_db[guild_id] = {}
        if member.id not in self.notes_db[guild_id]:
            self.notes_db[guild_id][member.id] = []
        self.notes_db[guild_id][member.id].append({
            'note': note,
            'by': str(ctx.author),
            'time': datetime.datetime.utcnow().strftime("%b %d %Y %H:%M")
        })
        count = len(self.notes_db[guild_id][member.id])
        await ctx.reply(f"📝 Note #{count} added for {member.mention}!")
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.command()
    async def notes(self, ctx, member: discord.Member):
        """View mod notes. Usage: !notes @user"""
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        notes = self.notes_db.get(ctx.guild.id, {}).get(member.id, [])
        if not notes:
            return await ctx.reply(f"📝 No notes for {member.mention}!")
        embed = discord.Embed(
            title=f"📝 Mod Notes — {member.display_name}",
            color=0x9b59b6
        )
        for i, n in enumerate(notes, 1):
            embed.add_field(
                name=f"Note #{i} • {n['by']} • {n['time']}",
                value=n['note'], inline=False
            )
        try:
            await ctx.author.send(embed=embed)
            await ctx.reply("📬 Notes sent to your DMs!")
        except:
            await ctx.send(embed=embed)

    @commands.command()
    async def clearnotes(self, ctx, member: discord.Member):
        """Clear all notes. Usage: !clearnotes @user"""
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        if ctx.guild.id in self.notes_db and member.id in self.notes_db[ctx.guild.id]:
            self.notes_db[ctx.guild.id][member.id] = []
        await ctx.reply(f"🧹 Cleared all notes for {member.mention}!")

    @commands.command()
    async def afk(self, ctx, *, reason="AFK"):
        """Set AFK. Usage: !afk  or  !afk reason"""
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
        embed.set_author(
            name=str(data['author']),
            icon_url=data['author'].display_avatar.url
        )
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
        embed = discord.Embed(
            title="👁️ Edit Sniped",
            color=0x9b59b6,
            timestamp=data['time']
        )
        embed.set_author(
            name=str(data['author']),
            icon_url=data['author'].display_avatar.url
        )
        embed.add_field(name="Before", value=data['before'], inline=False)
        embed.add_field(name="After", value=data['after'], inline=False)
        embed.set_footer(text=f"Sniped by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command()
    async def find(self, ctx, *, query: str):
        """Search for a member. Usage: !find name"""
        results = [
            m for m in ctx.guild.members
            if query.lower() in m.name.lower() or
               query.lower() in m.display_name.lower()
        ][:20]
        if not results:
            return await ctx.reply(f"❌ No members found matching `{query}`")
        embed = discord.Embed(
            title=f"🔍 Search: `{query}`",
            description=f"Found **{len(results)}** member(s)",
            color=0x3498db
        )
        icons = {"online": "🟢", "idle": "🟡", "dnd": "🔴", "offline": "⚫"}
        lines = [
            f"{icons.get(str(m.status), '⚫')} {m.mention} — `{m.id}`"
            for m in results
        ]
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
        god = "👑 ExtraOwner" if member.id in self.extraowners.get(ctx.guild.id, set()) else (
              "👑 Owner" if member.id == ctx.guild.owner_id else (
              "✨ God Bypass" if self.has_god_bypass(member) else "—"))
        embed.add_field(name="Special", value=god)
        lvl = self.get_hierarchy_level(member)
        lvl_name = {0:"None",1:"warn.exe",2:"mute.exe",3:"ban.exe",999:"God Tier"}.get(lvl,"—")
        embed.add_field(name="Mod Level", value=lvl_name)
        if roles:
            embed.add_field(
                name=f"Roles ({len(roles)})",
                value=" ".join(roles[:8]),
                inline=False
            )
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
        embed.add_field(
            name="Channels",
            value=f"💬 {len(g.text_channels)} text\n🔊 {len(g.voice_channels)} voice"
        )
        embed.add_field(name="Roles", value=len(g.roles))
        embed.add_field(name="Created", value=g.created_at.strftime("%b %d, %Y"))
        embed.add_field(
            name="Boost Level",
            value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)"
        )
        eos = len(self.extraowners.get(g.id, set()))
        embed.add_field(name="ExtraOwners", value=str(eos))
        embed.set_footer(text=f"ID: {g.id}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
