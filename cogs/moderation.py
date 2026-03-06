import discord
from discord.ext import commands
from discord import app_commands
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
        self.extraowners = {}
        self.role_bindings = {}

        # ban.exe(4) > kick.exe(3) > mute.exe(2) > warn.exe(1)
        self.DEFAULT_ROLES = {
            'warn':       'warn.exe',
            'mute':       'mute.exe',
            'kick':       'kick.exe',
            'ban':        'ban.exe',
            'purge':      'purge.exe',
            'lock':       'lock.exe',
            'nick':       'nick.exe',
            'announce':   'announce.exe',
            'audit':      'audit.viewer',
            'role_giver': 'role.giver.god',
            'god_bypass': 'god.bypass',
        }

        self.LOG_CHANNELS = [
            'mod-logs',
            'security-logs',
            'ticket-logs',
            'music-logs',
            'economy-logs',
            'leveling-logs',
            'giveaway-logs',
            'server-logs',
        ]

    # ══════════════════════════════════════════
    #   PERMISSION HELPERS
    # ══════════════════════════════════════════

    def get_role_name(self, guild_id, perm):
        return self.role_bindings.get(guild_id, {}).get(perm, self.DEFAULT_ROLES.get(perm))

    def is_god_tier(self, member):
        if member.id == member.guild.owner_id:
            return True
        if member.id in self.extraowners.get(member.guild.id, set()):
            return True
        return False

    def has_role_perm(self, member, perm):
        role_name = self.get_role_name(member.guild.id, perm)
        return discord.utils.get(member.roles, name=role_name) is not None

    def has_god_bypass(self, member):
        role_name = self.get_role_name(member.guild.id, 'god_bypass')
        return discord.utils.get(member.roles, name=role_name) is not None

    def get_hierarchy_level(self, member):
        if self.is_god_tier(member): return 999
        if self.has_role_perm(member, 'ban'):  return 4
        if self.has_role_perm(member, 'kick'): return 3
        if self.has_role_perm(member, 'mute'): return 2
        if self.has_role_perm(member, 'warn'): return 1
        return 0

    def can_do(self, member, action):
        if self.is_god_tier(member): return True
        hierarchy = {'warn': 1, 'mute': 2, 'kick': 3, 'ban': 4, 'tempban': 4}
        independent = {'purge', 'lock', 'nick', 'announce'}
        if action in hierarchy:
            return self.get_hierarchy_level(member) >= hierarchy[action]
        if action in independent:
            return self.has_role_perm(member, action)
        return False

    def perm_error_embed(self, action, member_level=0):
        needed = {
            'warn':     '`warn.exe`, `kick.exe`, `mute.exe`, or `ban.exe`',
            'mute':     '`mute.exe`, `kick.exe`, or `ban.exe`',
            'kick':     '`kick.exe` or `ban.exe`',
            'ban':      '`ban.exe`',
            'tempban':  '`ban.exe`',
            'purge':    '`purge.exe`',
            'lock':     '`lock.exe`',
            'nick':     '`nick.exe`',
            'announce': '`announce.exe`',
        }
        level_names = {1: 'warn.exe', 2: 'mute.exe', 3: 'kick.exe', 4: 'ban.exe'}
        embed = discord.Embed(title="🚫 Missing Role Permission", color=0xe74c3c)
        embed.add_field(name="Required Role", value=needed.get(action, 'required role'), inline=False)
        if member_level > 0:
            embed.add_field(
                name="Your Current Level",
                value=f"`{level_names.get(member_level, 'unknown')}` — not high enough!",
                inline=False
            )
        embed.add_field(
            name="What To Do",
            value="Ask someone with `role.giver.god` or an Owner/ExtraOwner to give you the right role.",
            inline=False
        )
        embed.set_footer(text="Lucky Bot Permission System")
        return embed

    def bypass_error_embed(self, member):
        return discord.Embed(
            title="🛡️ God Bypass Active",
            description=f"{member.mention} has `god.bypass` — the bot cannot act on them!",
            color=0xe74c3c
        )

    def protected_error_embed(self, member):
        return discord.Embed(
            title="❌ Protected User",
            description=f"{member.mention} is an **Owner** or **ExtraOwner** — cannot be moderated!",
            color=0xe74c3c
        )

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
        log_channel = discord.utils.get(guild.text_channels, name='mod-logs')
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
                value=str(value), inline=True
            )
        embed.set_footer(text="Lucky Bot Mod Logs")
        return embed

    # ══════════════════════════════════════════
    #   SHARED LOGIC
    # ══════════════════════════════════════════

    async def _warn(self, guild, author, member, reason):
        if not self.can_do(author, 'warn'):
            return self.perm_error_embed('warn', self.get_hierarchy_level(author)), None
        if self.has_god_bypass(member) and not self.is_god_tier(author):
            return self.bypass_error_embed(member), None
        guild_id = guild.id
        if guild_id not in self.warn_db:
            self.warn_db[guild_id] = {}
        if member.id not in self.warn_db[guild_id]:
            self.warn_db[guild_id][member.id] = []
        self.warn_db[guild_id][member.id].append(reason)
        count = len(self.warn_db[guild_id][member.id])
        embed = discord.Embed(title="⚠️ Member Warned", color=0xf39c12)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Total Warnings", value=f"⚠️ {count}")
        embed.add_field(name="Moderator", value=author.mention)
        embed.set_footer(text="Lucky Bot Moderation")
        try:
            await member.send(embed=discord.Embed(
                title=f"⚠️ You were warned in {guild.name}",
                description=f"**Reason:** {reason}\n**Total warnings:** {count}",
                color=0xf39c12
            ))
        except:
            pass
        await self.send_log(guild, self.log_embed("⚠️ Member Warned", 0xf39c12,
            user=f"{member} ({member.id})", reason=reason,
            total_warnings=str(count), moderator=str(author)))
        extra = None
        if count >= 3:
            extra = discord.Embed(
                title="🚨 Warning Threshold Reached",
                description=f"{member.mention} now has **{count} warnings!**",
                color=0xe74c3c
            )
        return embed, extra

    async def _mute(self, guild, author, member, duration_text, duration_seconds, reason):
        if not self.can_do(author, 'mute'):
            return self.perm_error_embed('mute', self.get_hierarchy_level(author)), None
        if self.has_god_bypass(member) and not self.is_god_tier(author):
            return self.bypass_error_embed(member), None
        if member.id == guild.owner_id:
            return self.protected_error_embed(member), None
        if member.id in self.extraowners.get(guild.id, set()):
            return self.protected_error_embed(member), None
        until = discord.utils.utcnow() + datetime.timedelta(seconds=duration_seconds)
        await member.timeout(until, reason=reason)
        embed = discord.Embed(title="🔇 Member Muted", color=0x95a5a6)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Duration", value=duration_text)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Unmuted", value=f"<t:{int(until.timestamp())}:R>")
        embed.add_field(name="Moderator", value=author.mention)
        embed.set_footer(text="Lucky Bot Moderation")
        try:
            await member.send(embed=discord.Embed(
                title=f"🔇 You were muted in {guild.name}",
                description=f"**Duration:** {duration_text}\n**Reason:** {reason}",
                color=0x95a5a6
            ))
        except:
            pass
        await self.send_log(guild, self.log_embed("🔇 Member Muted", 0x95a5a6,
            user=f"{member} ({member.id})", duration=duration_text,
            reason=reason, moderator=str(author)))
        return embed, None

    async def _kick(self, guild, author, member, reason):
        if not self.can_do(author, 'kick'):
            lvl = self.get_hierarchy_level(author)
            embed = self.perm_error_embed('kick', lvl)
            if lvl in (1, 2):
                embed.add_field(
                    name="💡 Note",
                    value=f"You have `{'warn.exe' if lvl==1 else 'mute.exe'}` — need `kick.exe` or `ban.exe` to kick.",
                    inline=False
                )
            return embed, None
        if self.has_god_bypass(member) and not self.is_god_tier(author):
            return self.bypass_error_embed(member), None
        if member.id == guild.owner_id:
            return self.protected_error_embed(member), None
        if member.id in self.extraowners.get(guild.id, set()):
            return self.protected_error_embed(member), None
        await member.kick(reason=reason)
        embed = discord.Embed(title="👢 Member Kicked", color=0xe74c3c)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=author.mention)
        embed.set_footer(text="Lucky Bot Moderation")
        try:
            await member.send(embed=discord.Embed(
                title=f"👢 You were kicked from {guild.name}",
                description=f"**Reason:** {reason}",
                color=0xe74c3c
            ))
        except:
            pass
        await self.send_log(guild, self.log_embed("👢 Member Kicked", 0xe74c3c,
            user=f"{member} ({member.id})", reason=reason, moderator=str(author)))
        return embed, None

    async def _ban(self, guild, author, member, reason):
        if not self.can_do(author, 'ban'):
            lvl = self.get_hierarchy_level(author)
            embed = self.perm_error_embed('ban', lvl)
            if lvl > 0:
                lvl_names = {1: 'warn.exe', 2: 'mute.exe', 3: 'kick.exe'}
                embed.add_field(
                    name="💡 Note",
                    value=f"You have `{lvl_names.get(lvl,'unknown')}` — need `ban.exe` to ban.",
                    inline=False
                )
            return embed, None
        if self.has_god_bypass(member) and not self.is_god_tier(author):
            return self.bypass_error_embed(member), None
        if member.id == guild.owner_id:
            return self.protected_error_embed(member), None
        if member.id in self.extraowners.get(guild.id, set()):
            return self.protected_error_embed(member), None
        await member.ban(reason=reason)
        embed = discord.Embed(title="🔨 Member Banned", color=0xc0392b)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Moderator", value=author.mention)
        embed.set_footer(text="Lucky Bot Moderation")
        try:
            await member.send(embed=discord.Embed(
                title=f"🔨 You were banned from {guild.name}",
                description=f"**Reason:** {reason}",
                color=0xc0392b
            ))
        except:
            pass
        await self.send_log(guild, self.log_embed("🔨 Member Banned", 0xc0392b,
            user=f"{member} ({member.id})", reason=reason, moderator=str(author)))
        return embed, None

    # ══════════════════════════════════════════
    #   LISTENERS
    # ══════════════════════════════════════════

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        usage = {
            'warn':      '`!warn @user` or `!warn @user ?r reason`',
            'mute':      '`!mute @user` / `!mute @user ?t 10m ?r reason`\nTime: `30s` `10m` `2h` `1d`',
            'unmute':    '`!unmute @user`',
            'kick':      '`!kick @user` or `!kick @user ?r reason`',
            'ban':       '`!ban @user` or `!ban @user ?r reason`',
            'unban':     '`!unban username`',
            'tempban':   '`!tempban @user time ?r reason`',
            'unwarn':    '`!unwarn @user` or `!unwarn @user 2`',
            'warnings':  '`!warnings @user`',
            'clearwarn': '`!clearwarn @user`',
            'purge':     '`!purge 10` or `!purge 10 @user`',
            'slowmode':  '`!slowmode 5m` or `!slowmode 0`',
            'lock':      '`!lock` or `!lock #channel`',
            'unlock':    '`!unlock` or `!unlock #channel`',
            'nick':      '`!nick @user NewName`',
            'resetnick': '`!resetnick @user`',
            'announce':  '`!announce #channel Title | Message`',
            'poll':      '`!poll question`',
            'find':      '`!find name`',
            'afk':       '`!afk` or `!afk reason`',
            'note':      '`!note @user text`',
            'notes':     '`!notes @user`',
            'giverole':  '`!giverole @user warn.exe`',
            'takerole':  '`!takerole @user warn.exe`',
            'clearlogs': '`!clearlogs` / `!clearlogs mod-logs` / `!clearlogs all`',
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
                title=f"❌ Missing Argument in `!{cmd}`", color=0xe74c3c)
            if cmd in usage:
                embed.add_field(name="📖 How to use", value=usage[cmd], inline=False)
            return await ctx.reply(embed=embed)

        if isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                title="❌ Member Not Found",
                description="Couldn't find that member! Make sure you @mention them.",
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
            return await ctx.reply(embed=discord.Embed(
                title="⏰ Slow Down!",
                description=f"Try again in **{error.retry_after:.1f}s**",
                color=0xf39c12
            ))

        print(f'Unhandled error in !{cmd}: {error}')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author.id in self.afk_db:
            del self.afk_db[message.author.id]
            try:
                await message.author.edit(
                    nick=message.author.display_name.replace('[AFK] ', ''))
            except:
                pass
            msg = await message.channel.send(embed=discord.Embed(
                description=f"👋 Welcome back {message.author.mention}! AFK removed.",
                color=0x2ecc71
            ))
            await msg.delete(delay=5)
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
        changes = []
        if before.name != after.name:
            changes.append(f"Server name: `{before.name}` → `{after.name}`")
        if before.icon != after.icon:
            changes.append("Server icon changed")
        if before.description != after.description:
            changes.append("Server description changed")
        if before.banner != after.banner:
            changes.append("Server banner changed")
        if not changes:
            return
        try:
            async for entry in after.audit_logs(
                limit=1, action=discord.AuditLogAction.guild_update):
                user = entry.user
                member = after.get_member(user.id)
                if not member or member.bot:
                    return
                if self.is_god_tier(member):
                    return
                change_text = "\n".join(changes)
                until = discord.utils.utcnow() + datetime.timedelta(minutes=2)
                await member.timeout(until, reason="[Auto-Mod] Unauthorized server profile change")
                embed = discord.Embed(
                    title="🔒 Auto-Mute: Unauthorized Server Change",
                    color=0xff6600,
                    timestamp=datetime.datetime.utcnow()
                )
                embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)")
                embed.add_field(name="Duration", value="2 minutes")
                embed.add_field(name="Changes Made", value=change_text, inline=False)
                embed.add_field(
                    name="Why",
                    value="Only Owner/ExtraOwners can modify the server profile.",
                    inline=False
                )
                embed.set_footer(text="Lucky Bot Auto-Mod")
                await self.send_log(after, embed)
                try:
                    await member.send(embed=discord.Embed(
                        title=f"🔒 Auto-muted in {after.name}",
                        description=f"**Reason:** Unauthorized server profile change\n**Duration:** 2 minutes\n**Changes:** {change_text}",
                        color=0xff6600
                    ))
                except:
                    pass
        except Exception as e:
            print(f"on_guild_update error: {e}")

    # ══════════════════════════════════════════
    #   EXTRAOWNER SYSTEM
    # ══════════════════════════════════════════

    @commands.group(invoke_without_command=True)
    async def extraowner(self, ctx):
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Owner Only",
                description="Only the **server owner** can manage ExtraOwners!",
                color=0xe74c3c
            ))
        eos = self.extraowners.get(ctx.guild.id, set())
        embed = discord.Embed(
            title="👑 ExtraOwners",
            description="\n".join([f"<@{uid}>" for uid in eos]) or "None set",
            color=0xf1c40f
        )
        embed.add_field(
            name="Commands",
            value="`!extraowner add @user`\n`!extraowner remove @user`\n`!extraowner list`",
            inline=False
        )
        await ctx.send(embed=embed)

    @extraowner.command(name='add')
    async def extraowner_add(self, ctx, member: discord.Member):
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Owner Only", color=0xe74c3c,
                description="Only the **server owner** can add ExtraOwners!"
            ))
        guild_id = ctx.guild.id
        if guild_id not in self.extraowners:
            self.extraowners[guild_id] = set()
        self.extraowners[guild_id].add(member.id)
        embed = discord.Embed(
            title="👑 ExtraOwner Added",
            description=f"{member.mention} is now an **ExtraOwner**!",
            color=0xf1c40f
        )
        embed.add_field(
            name="Permissions",
            value="• Use all mod commands\n• Toggle security systems\n• Immune to bot actions",
            inline=False
        )
        await ctx.send(embed=embed)
        await self.send_log(ctx.guild, self.log_embed("👑 ExtraOwner Added", 0xf1c40f,
            user=f"{member} ({member.id})", added_by=str(ctx.author)))

    @extraowner.command(name='remove')
    async def extraowner_remove(self, ctx, member: discord.Member):
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Owner Only", color=0xe74c3c,
                description="Only the **server owner** can remove ExtraOwners!"
            ))
        if ctx.guild.id in self.extraowners:
            self.extraowners[ctx.guild.id].discard(member.id)
        await ctx.reply(embed=discord.Embed(
            title="✅ ExtraOwner Removed",
            description=f"{member.mention} is no longer an ExtraOwner.",
            color=0x2ecc71
        ))

    @extraowner.command(name='list')
    async def extraowner_list(self, ctx):
        eos = self.extraowners.get(ctx.guild.id, set())
        await ctx.send(embed=discord.Embed(
            title="👑 ExtraOwners",
            description="\n".join([f"<@{uid}>" for uid in eos]) or "None set",
            color=0xf1c40f
        ))

    @app_commands.command(name='extraowner', description='Manage ExtraOwners (server owner only)')
    @app_commands.describe(action='add/remove/list', member='Target member')
    async def extraowner_slash(self, interaction: discord.Interaction,
                               action: str, member: discord.Member = None):
        if interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Owner Only", color=0xe74c3c,
                description="Only the **server owner** can manage ExtraOwners!"
            ), ephemeral=True)
        guild_id = interaction.guild.id
        if action == 'add' and member:
            if guild_id not in self.extraowners:
                self.extraowners[guild_id] = set()
            self.extraowners[guild_id].add(member.id)
            await interaction.response.send_message(embed=discord.Embed(
                title="👑 ExtraOwner Added",
                description=f"{member.mention} is now an ExtraOwner!",
                color=0xf1c40f
            ))
        elif action == 'remove' and member:
            if guild_id in self.extraowners:
                self.extraowners[guild_id].discard(member.id)
            await interaction.response.send_message(embed=discord.Embed(
                title="✅ Removed",
                description=f"{member.mention} removed from ExtraOwners.",
                color=0x2ecc71
            ))
        elif action == 'list':
            eos = self.extraowners.get(guild_id, set())
            await interaction.response.send_message(embed=discord.Embed(
                title="👑 ExtraOwners",
                description="\n".join([f"<@{uid}>" for uid in eos]) or "None",
                color=0xf1c40f
            ))
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Usage",
                description="`/extraowner add @user`\n`/extraowner remove @user`\n`/extraowner list`",
                color=0xe74c3c
            ), ephemeral=True)

    # ══════════════════════════════════════════
    #   ROLEBIND
    # ══════════════════════════════════════════

    @commands.command()
    async def rolebind(self, ctx, perm: str = "list", *, role: discord.Role = None):
        if not self.is_god_tier(ctx.author):
            return await ctx.reply(embed=discord.Embed(
                title="❌ No Permission",
                description="Only **Owner** or **ExtraOwners** can rebind roles!",
                color=0xe74c3c
            ))
        if perm == "list":
            bindings = self.role_bindings.get(ctx.guild.id, {})
            embed = discord.Embed(title="🔗 Role Bindings", color=0x3498db)
            for p, default in self.DEFAULT_ROLES.items():
                current = bindings.get(p, default)
                embed.add_field(
                    name=f"{'✏️' if p in bindings else '✅'} {p}",
                    value=f"`{current}`", inline=True
                )
            return await ctx.send(embed=embed)
        valid = list(self.DEFAULT_ROLES.keys())
        perm_map = {v: k for k, v in self.DEFAULT_ROLES.items()}
        if perm in perm_map:
            perm = perm_map[perm]
        if perm not in valid:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Invalid Permission",
                description=f"Valid: `{'`, `'.join(valid)}`",
                color=0xe74c3c
            ))
        guild_id = ctx.guild.id
        if guild_id not in self.role_bindings:
            self.role_bindings[guild_id] = {}
        if role is None:
            self.role_bindings[guild_id].pop(perm, None)
            return await ctx.reply(embed=discord.Embed(
                title="✅ Reset",
                description=f"`{perm}` reset to default: `{self.DEFAULT_ROLES[perm]}`",
                color=0x2ecc71
            ))
        self.role_bindings[guild_id][perm] = role.name
        await ctx.send(embed=discord.Embed(
            title="🔗 Role Binding Updated",
            description=f"`{perm}` is now bound to {role.mention}",
            color=0x2ecc71
        ))

    # ══════════════════════════════════════════
    #   ROLE GIVER/TAKER
    # ══════════════════════════════════════════

    @commands.command(name='giverole')
    async def give_role(self, ctx, member: discord.Member, *, role_name: str):
        guild_id = ctx.guild.id
        target_role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not target_role:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Role Not Found",
                description=f"`{role_name}` doesn't exist in this server!",
                color=0xe74c3c
            ))
        lucky_roles = {self.get_role_name(guild_id, p): p for p in self.DEFAULT_ROLES}
        perm_key = lucky_roles.get(target_role.name)
        if not perm_key:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Not a Lucky Bot Role",
                description=f"`{role_name}` is not a Lucky Bot permission role!",
                color=0xe74c3c
            ))
        if self.is_god_tier(ctx.author):
            await member.add_roles(target_role)
            return await ctx.reply(embed=discord.Embed(
                title="✅ Role Given",
                description=f"Given `{target_role.name}` to {member.mention}!",
                color=0x2ecc71
            ))
        hierarchy_map = {'warn': 1, 'mute': 2, 'kick': 3, 'ban': 4}
        if self.has_role_perm(ctx.author, 'role_giver'):
            author_level = self.get_hierarchy_level(ctx.author)
            target_level = hierarchy_map.get(perm_key, 0)
            if perm_key in hierarchy_map:
                if target_level < author_level:
                    await member.add_roles(target_role)
                    await self.send_log(ctx.guild, self.log_embed("🏷️ Role Given", 0x3498db,
                        to=f"{member} ({member.id})", role=target_role.name,
                        given_by=str(ctx.author)))
                    return await ctx.reply(embed=discord.Embed(
                        title="✅ Role Given",
                        description=f"Given `{target_role.name}` to {member.mention}!",
                        color=0x2ecc71
                    ))
                else:
                    return await ctx.reply(embed=discord.Embed(
                        title="❌ Can't Give That Role",
                        description="You can only give roles **below** your level!",
                        color=0xe74c3c
                    ))
            else:
                await member.add_roles(target_role)
                return await ctx.reply(embed=discord.Embed(
                    title="✅ Role Given",
                    description=f"Given `{target_role.name}` to {member.mention}!",
                    color=0x2ecc71
                ))
        if perm_key in ('purge', 'lock', 'nick', 'announce', 'audit'):
            if self.has_role_perm(ctx.author, perm_key):
                await member.add_roles(target_role)
                return await ctx.reply(embed=discord.Embed(
                    title="✅ Role Given",
                    description=f"Given `{target_role.name}` to {member.mention}!",
                    color=0x2ecc71
                ))
        return await ctx.reply(embed=discord.Embed(
            title="❌ No Permission",
            description="You need `role.giver.god` or the same independent role!",
            color=0xe74c3c
        ))

    @commands.command(name='takerole')
    async def take_role(self, ctx, member: discord.Member, *, role_name: str):
        target_role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not target_role:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Role Not Found", color=0xe74c3c))
        if not self.is_god_tier(ctx.author) and not self.has_role_perm(ctx.author, 'role_giver'):
            return await ctx.reply(embed=discord.Embed(
                title="❌ No Permission",
                description="Need `role.giver.god` or god tier!",
                color=0xe74c3c
            ))
        await member.remove_roles(target_role)
        await self.send_log(ctx.guild, self.log_embed("🏷️ Role Removed", 0xe74c3c,
            from_user=f"{member} ({member.id})", role=target_role.name,
            removed_by=str(ctx.author)))
        await ctx.reply(embed=discord.Embed(
            title="✅ Role Removed",
            description=f"Removed `{target_role.name}` from {member.mention}!",
            color=0x2ecc71
        ))

    # ══════════════════════════════════════════
    #   SETUP
    # ══════════════════════════════════════════

    @commands.command()
    async def setup(self, ctx):
        if not self.is_god_tier(ctx.author):
            return await ctx.reply(embed=discord.Embed(
                title="❌ No Permission",
                description="Only **Owner** or **ExtraOwners** can run setup!",
                color=0xe74c3c
            ))
        status_msg = await ctx.send(embed=discord.Embed(
            title="⚙️ Setting up Lucky Bot...",
            description="Please wait! This may take a moment.",
            color=0x3498db
        ))
        results = []
        guild = ctx.guild

        # ── Create permission roles ────────────
        roles_to_create = [
            ('ban.exe',        0xc0392b, 'Can ban, kick, mute, warn'),
            ('kick.exe',       0xe67e22, 'Can kick, mute, warn'),
            ('mute.exe',       0xf39c12, 'Can mute, warn'),
            ('warn.exe',       0xf1c40f, 'Can warn only'),
            ('purge.exe',      0x3498db, 'Can purge messages'),
            ('lock.exe',       0x9b59b6, 'Can lock/unlock channels'),
            ('nick.exe',       0x1abc9c, 'Can change nicknames'),
            ('announce.exe',   0x2ecc71, 'Can make announcements'),
            ('audit.viewer',   0x95a5a6, 'Can view log channels'),
            ('role.giver.god', 0xe91e63, 'Can give Lucky Bot roles'),
            ('god.bypass',     0xffd700, 'Immune to bot moderation'),
        ]
        for role_name, color, desc in roles_to_create:
            existing = discord.utils.get(guild.roles, name=role_name)
            if existing:
                results.append(f"✅ `{role_name}` already exists")
            else:
                try:
                    await guild.create_role(
                        name=role_name,
                        color=discord.Color(color),
                        reason=f"Lucky Bot setup — {desc}"
                    )
                    results.append(f"✅ Created role `{role_name}`")
                except Exception as e:
                    results.append(f"❌ Failed `{role_name}`: {e}")

        # ── Create Logs category ───────────────
        logs_category = (
            discord.utils.get(guild.categories, name='Logs') or
            discord.utils.get(guild.categories, name='logs')
        )
        if not logs_category:
            try:
                logs_category = await guild.create_category(
                    name='Logs',
                    reason='Lucky Bot setup — log channels'
                )
                results.append("✅ Created `Logs` category")
            except Exception as e:
                results.append(f"❌ Failed `Logs` category: {e}")
                logs_category = None

        # ── Create all log channels ────────────
        audit_role = discord.utils.get(guild.roles, name=self.get_role_name(guild.id, 'audit'))

        log_channels_to_create = [
            ('mod-logs',      '🛡️ Private moderation logs — Lucky Bot'),
            ('security-logs', '🔒 Private security logs — Lucky Bot'),
            ('ticket-logs',   '🎫 Private ticket logs — Lucky Bot'),
            ('music-logs',    '🎵 Music activity logs — Lucky Bot'),
            ('economy-logs',  '💰 Economy logs — Lucky Bot'),
            ('leveling-logs', '⭐ Leveling logs — Lucky Bot'),
            ('giveaway-logs', '🎁 Giveaway logs — Lucky Bot'),
            ('server-logs',   '📋 General server event logs — Lucky Bot'),
        ]

        for ch_name, topic in log_channels_to_create:
            try:
                existing = discord.utils.get(guild.text_channels, name=ch_name)
                if existing:
                    results.append(f"✅ `#{ch_name}` already exists")
                else:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(
                            view_channel=False, send_messages=False),
                        guild.me: discord.PermissionOverwrite(
                            view_channel=True, send_messages=True, embed_links=True),
                    }
                    if audit_role:
                        overwrites[audit_role] = discord.PermissionOverwrite(
                            view_channel=True, send_messages=False, read_message_history=True)
                    for role in guild.roles:
                        if role.permissions.administrator:
                            overwrites[role] = discord.PermissionOverwrite(
                                view_channel=True, send_messages=False)
                    await guild.create_text_channel(
                        name=ch_name,
                        overwrites=overwrites,
                        category=logs_category,
                        topic=topic
                    )
                    results.append(f"✅ Created private `#{ch_name}`")
            except Exception as e:
                results.append(f"❌ Failed `#{ch_name}`: {e}")

        # ── Other channels ─────────────────────
        for ch_name, topic in [('welcome', '👋 Welcome!'), ('rules', '📋 Server rules')]:
            try:
                if not discord.utils.get(guild.text_channels, name=ch_name):
                    await guild.create_text_channel(name=ch_name, topic=topic)
                    results.append(f"✅ Created `#{ch_name}`")
                else:
                    results.append(f"✅ `#{ch_name}` already exists")
            except Exception as e:
                results.append(f"❌ Failed `#{ch_name}`: {e}")

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
            name="📊 Role Hierarchy",
            value=(
                "`ban.exe` → ban + kick + mute + warn\n"
                "`kick.exe` → kick + mute + warn\n"
                "`mute.exe` → mute + warn\n"
                "`warn.exe` → warn only"
            ),
            inline=True
        )
        embed.add_field(
            name="🔑 Independent Roles",
            value=(
                "`purge.exe` `lock.exe` `nick.exe`\n"
                "`announce.exe` `audit.viewer`\n"
                "`role.giver.god` `god.bypass`"
            ),
            inline=True
        )
        embed.add_field(
            name="📋 Log Channels Created",
            value=(
                "`#mod-logs` — moderation actions\n"
                "`#security-logs` — antinuke/raid alerts\n"
                "`#ticket-logs` — ticket activity\n"
                "`#music-logs` — music activity\n"
                "`#economy-logs` — economy events\n"
                "`#leveling-logs` — level ups\n"
                "`#giveaway-logs` — giveaway events\n"
                "`#server-logs` — joins, leaves, edits"
            ),
            inline=False
        )
        embed.add_field(
            name="⚡ Next Steps",
            value=(
                "1. Give `role.giver.god` to your admins\n"
                "2. Give `ban.exe` to your moderators\n"
                "3. Use `!extraowner add @user` for trusted people\n"
                "4. Enable security: `!antinuke on` `!antiraid on`\n"
                "5. Use `!clearlogs` to manage log channels"
            ),
            inline=False
        )
        embed.set_footer(text=f"Set up by {ctx.author} • Lucky Bot")
        await status_msg.edit(embed=embed)

        # Welcome message in mod-logs
        mod_logs = discord.utils.get(guild.text_channels, name='mod-logs')
        if mod_logs:
            await mod_logs.send(embed=discord.Embed(
                title="🍀 Lucky Bot is Ready!",
                description=(
                    f"Set up by {ctx.author.mention}\n"
                    "All moderation actions will be logged here.\n"
                    "Only `audit.viewer` and admins can see this channel."
                ),
                color=0x2ecc71
            ))

    @app_commands.command(name='setup', description='Auto-setup Lucky Bot (Owner/ExtraOwner only)')
    async def setup_slash(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.setup(ctx)

    # ══════════════════════════════════════════
    #   CLEAR LOGS
    # ══════════════════════════════════════════

    @commands.command(name='clearlogs')
    async def clearlogs_prefix(self, ctx, channel_name: str = None):
        """
        Clear log channels.
        Usage: !clearlogs              ← shows menu
               !clearlogs mod-logs     ← clears specific channel
               !clearlogs all          ← clears ALL log channels
        Owner/ExtraOwner only.
        """
        if not self.is_god_tier(ctx.author):
            return await ctx.reply(embed=discord.Embed(
                title="❌ No Permission",
                description="Only **Owner** or **ExtraOwners** can clear logs!",
                color=0xe74c3c
            ))

        # Show menu
        if channel_name is None:
            embed = discord.Embed(
                title="🗑️ Clear Logs — Menu",
                description="Which log channel do you want to clear?",
                color=0xe74c3c
            )
            embed.add_field(
                name="Clear a specific channel",
                value="\n".join([f"`!clearlogs {ch}`" for ch in self.LOG_CHANNELS]),
                inline=True
            )
            embed.add_field(
                name="Clear everything",
                value="`!clearlogs all` — wipes ALL log channels at once",
                inline=True
            )
            embed.set_footer(text="⚠️ This cannot be undone!")
            return await ctx.send(embed=embed)

        # Clear ALL
        if channel_name.lower() == 'all':
            await ctx.send(embed=discord.Embed(
                title="⚠️ Clear ALL Log Channels?",
                description=(
                    "This will wipe **all 8 log channels!**\n\n"
                    + "\n".join([f"• `#{ch}`" for ch in self.LOG_CHANNELS])
                    + "\n\n**Reply `yes` to confirm.**"
                ),
                color=0xe74c3c
            ))
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
            try:
                await self.bot.wait_for('message', check=check, timeout=15)
            except asyncio.TimeoutError:
                return await ctx.send(embed=discord.Embed(
                    title="❌ Cancelled", description="Timed out — nothing cleared.",
                    color=0xe74c3c
                ))
            cleared, failed, skipped = [], [], []
            for ch_name in self.LOG_CHANNELS:
                channel = discord.utils.get(ctx.guild.text_channels, name=ch_name)
                if not channel:
                    skipped.append(ch_name)
                    continue
                try:
                    await channel.purge(limit=None)
                    cleared.append(ch_name)
                    await channel.send(embed=discord.Embed(
                        title="🗑️ Logs Cleared",
                        description=f"Cleared by {ctx.author.mention}",
                        color=0x2ecc71,
                        timestamp=datetime.datetime.utcnow()
                    ))
                except Exception as e:
                    failed.append(f"{ch_name}")
            result = discord.Embed(
                title="🗑️ All Logs Cleared",
                color=0x2ecc71,
                timestamp=datetime.datetime.utcnow()
            )
            if cleared:
                result.add_field(
                    name=f"✅ Cleared ({len(cleared)})",
                    value="\n".join([f"`#{ch}`" for ch in cleared]),
                    inline=False
                )
            if skipped:
                result.add_field(
                    name=f"⏭️ Not found ({len(skipped)})",
                    value="\n".join([f"`#{ch}`" for ch in skipped]),
                    inline=False
                )
            if failed:
                result.add_field(
                    name=f"❌ Failed ({len(failed)})",
                    value="\n".join(failed),
                    inline=False
                )
            result.add_field(name="Cleared by", value=ctx.author.mention)
            return await ctx.send(embed=result)

        # Clear specific channel
        ch_name = channel_name.lstrip('#').lower()
        if ch_name not in self.LOG_CHANNELS:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Invalid Log Channel",
                description=(
                    f"`{channel_name}` is not a Lucky Bot log channel!\n\n"
                    "**Valid channels:**\n"
                    + "\n".join([f"`#{ch}`" for ch in self.LOG_CHANNELS])
                ),
                color=0xe74c3c
            ))
        channel = discord.utils.get(ctx.guild.text_channels, name=ch_name)
        if not channel:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Channel Not Found",
                description=f"`#{ch_name}` doesn't exist! Run `!setup` first.",
                color=0xe74c3c
            ))
        await ctx.send(embed=discord.Embed(
            title=f"⚠️ Clear `#{ch_name}`?",
            description="This deletes **all messages** in that channel.\n**Reply `yes` to confirm.**",
            color=0xe74c3c
        ))
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
        try:
            await self.bot.wait_for('message', check=check, timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send(embed=discord.Embed(
                title="❌ Cancelled", description="Timed out — nothing cleared.",
                color=0xe74c3c
            ))
        await channel.purge(limit=None)
        await channel.send(embed=discord.Embed(
            title="🗑️ Logs Cleared",
            description=f"Cleared by {ctx.author.mention}",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        ))
        await ctx.send(embed=discord.Embed(
            title="✅ Logs Cleared",
            description=f"All messages deleted from `#{ch_name}`!",
            color=0x2ecc71
        ))

    @app_commands.command(name='clearlogs', description='Clear a log channel (Owner/ExtraOwner only)')
    @app_commands.describe(channel='Which log channel to clear')
    @app_commands.choices(channel=[
        app_commands.Choice(name='🗑️ ALL log channels', value='all'),
        app_commands.Choice(name='🛡️ mod-logs', value='mod-logs'),
        app_commands.Choice(name='🔒 security-logs', value='security-logs'),
        app_commands.Choice(name='🎫 ticket-logs', value='ticket-logs'),
        app_commands.Choice(name='🎵 music-logs', value='music-logs'),
        app_commands.Choice(name='💰 economy-logs', value='economy-logs'),
        app_commands.Choice(name='⭐ leveling-logs', value='leveling-logs'),
        app_commands.Choice(name='🎁 giveaway-logs', value='giveaway-logs'),
        app_commands.Choice(name='📋 server-logs', value='server-logs'),
    ])
    async def clearlogs_slash(self, interaction: discord.Interaction, channel: str = None):
        if not self.is_god_tier(interaction.user):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ No Permission",
                description="Only **Owner** or **ExtraOwners** can clear logs!",
                color=0xe74c3c
            ), ephemeral=True)

        if channel is None:
            return await interaction.response.send_message(embed=discord.Embed(
                title="🗑️ Clear Logs",
                description="Pick a channel from the dropdown!\n\n"
                    + "\n".join([f"`#{ch}`" for ch in self.LOG_CHANNELS]),
                color=0x3498db
            ), ephemeral=True)

        await interaction.response.defer()

        if channel == 'all':
            cleared, skipped = [], []
            for ch_name in self.LOG_CHANNELS:
                ch = discord.utils.get(interaction.guild.text_channels, name=ch_name)
                if not ch:
                    skipped.append(ch_name)
                    continue
                try:
                    await ch.purge(limit=None)
                    cleared.append(ch_name)
                    await ch.send(embed=discord.Embed(
                        title="🗑️ Logs Cleared",
                        description=f"Cleared by {interaction.user.mention}",
                        color=0x2ecc71,
                        timestamp=datetime.datetime.utcnow()
                    ))
                except:
                    skipped.append(ch_name)
            embed = discord.Embed(
                title="🗑️ All Logs Cleared", color=0x2ecc71,
                timestamp=datetime.datetime.utcnow())
            if cleared:
                embed.add_field(
                    name=f"✅ Cleared ({len(cleared)})",
                    value="\n".join([f"`#{ch}`" for ch in cleared]), inline=False)
            if skipped:
                embed.add_field(
                    name=f"⏭️ Skipped ({len(skipped)})",
                    value="\n".join([f"`#{ch}`" for ch in skipped]), inline=False)
            return await interaction.followup.send(embed=embed)

        ch = discord.utils.get(interaction.guild.text_channels, name=channel)
        if not ch:
            return await interaction.followup.send(embed=discord.Embed(
                title="❌ Channel Not Found",
                description=f"`#{channel}` doesn't exist! Run `!setup` first.",
                color=0xe74c3c
            ))
        await ch.purge(limit=None)
        await ch.send(embed=discord.Embed(
            title="🗑️ Logs Cleared",
            description=f"Cleared by {interaction.user.mention}",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        ))
        await interaction.followup.send(embed=discord.Embed(
            title="✅ Logs Cleared",
            description=f"All messages deleted from `#{channel}`!",
            color=0x2ecc71
        ))

    # ══════════════════════════════════════════
    #   WARN COMMANDS
    # ══════════════════════════════════════════

    @commands.command()
    async def warn(self, ctx, member: discord.Member, *, args=""):
        reason = args.split("?r", 1)[1].strip() if "?r" in args else "No reason provided"
        embed, extra = await self._warn(ctx.guild, ctx.author, member, reason)
        await ctx.reply(embed=embed)
        if extra:
            await ctx.send(embed=extra)

    @app_commands.command(name='warn', description='Warn a member')
    @app_commands.describe(member='Member to warn', reason='Reason for warning')
    async def warn_slash(self, interaction: discord.Interaction,
                         member: discord.Member, reason: str = "No reason provided"):
        embed, extra = await self._warn(interaction.guild, interaction.user, member, reason)
        await interaction.response.send_message(embed=embed)
        if extra:
            await interaction.followup.send(embed=extra)

    @commands.command()
    async def warnings(self, ctx, member: discord.Member):
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        warns = self.warn_db.get(ctx.guild.id, {}).get(member.id, [])
        if not warns:
            return await ctx.reply(embed=discord.Embed(
                description=f"✅ {member.mention} has no warnings!", color=0x2ecc71))
        embed = discord.Embed(title=f"⚠️ Warnings — {member.display_name}", color=0xf39c12)
        for i, w in enumerate(warns, 1):
            embed.add_field(name=f"Warning #{i}", value=w, inline=False)
        embed.set_footer(text=f"Total: {len(warns)} warnings")
        await ctx.send(embed=embed)

    @app_commands.command(name='warnings', description='Check warnings for a member')
    @app_commands.describe(member='Member to check')
    async def warnings_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not self.can_do(interaction.user, 'warn'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('warn'), ephemeral=True)
        warns = self.warn_db.get(interaction.guild.id, {}).get(member.id, [])
        if not warns:
            return await interaction.response.send_message(embed=discord.Embed(
                description=f"✅ {member.mention} has no warnings!", color=0x2ecc71))
        embed = discord.Embed(title=f"⚠️ Warnings — {member.display_name}", color=0xf39c12)
        for i, w in enumerate(warns, 1):
            embed.add_field(name=f"Warning #{i}", value=w, inline=False)
        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def unwarn(self, ctx, member: discord.Member, number: int = None):
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        warns = self.warn_db.get(ctx.guild.id, {}).get(member.id, [])
        if not warns:
            return await ctx.reply(embed=discord.Embed(
                description=f"✅ {member.mention} has no warnings!", color=0x2ecc71))
        if number is None:
            removed = warns.pop()
        else:
            if number < 1 or number > len(warns):
                return await ctx.reply(embed=discord.Embed(
                    title="❌ Invalid Number",
                    description=f"{member.mention} has {len(warns)} warnings.",
                    color=0xe74c3c))
            removed = warns.pop(number - 1)
        self.warn_db[ctx.guild.id][member.id] = warns
        embed = discord.Embed(title="✅ Warning Removed", color=0x2ecc71)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Removed", value=removed)
        embed.add_field(name="Remaining", value=str(len(warns)))
        await ctx.send(embed=embed)

    @app_commands.command(name='unwarn', description='Remove a warning from a member')
    @app_commands.describe(member='Target member', number='Warning number (empty = latest)')
    async def unwarn_slash(self, interaction: discord.Interaction,
                           member: discord.Member, number: int = None):
        if not self.can_do(interaction.user, 'warn'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('warn'), ephemeral=True)
        warns = self.warn_db.get(interaction.guild.id, {}).get(member.id, [])
        if not warns:
            return await interaction.response.send_message(embed=discord.Embed(
                description=f"✅ {member.mention} has no warnings!", color=0x2ecc71))
        removed = warns.pop() if number is None else warns.pop(number - 1)
        self.warn_db[interaction.guild.id][member.id] = warns
        embed = discord.Embed(title="✅ Warning Removed", color=0x2ecc71)
        embed.add_field(name="Removed", value=removed)
        embed.add_field(name="Remaining", value=str(len(warns)))
        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def clearwarn(self, ctx, member: discord.Member):
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        if ctx.guild.id in self.warn_db and member.id in self.warn_db[ctx.guild.id]:
            self.warn_db[ctx.guild.id][member.id] = []
        await ctx.reply(embed=discord.Embed(
            title="🧹 Warnings Cleared",
            description=f"Cleared all warnings for {member.mention}!",
            color=0x2ecc71
        ))

    @app_commands.command(name='clearwarn', description='Clear all warnings for a member')
    @app_commands.describe(member='Target member')
    async def clearwarn_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not self.can_do(interaction.user, 'warn'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('warn'), ephemeral=True)
        if interaction.guild.id in self.warn_db and member.id in self.warn_db[interaction.guild.id]:
            self.warn_db[interaction.guild.id][member.id] = []
        await interaction.response.send_message(embed=discord.Embed(
            title="🧹 Warnings Cleared",
            description=f"Cleared all warnings for {member.mention}!",
            color=0x2ecc71
        ))

    # ══════════════════════════════════════════
    #   MUTE COMMANDS
    # ══════════════════════════════════════════

    @commands.command()
    async def mute(self, ctx, member: discord.Member, *, args=""):
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
                    return await ctx.reply(embed=discord.Embed(
                        title="❌ Too Long", description="Max mute is 28 days!", color=0xe74c3c))
                duration_seconds = parsed
                duration_text = t_part
            else:
                return await ctx.reply(embed=discord.Embed(
                    title="❌ Invalid Time",
                    description="Use: `30s`, `10m`, `2h`, `1d`",
                    color=0xe74c3c
                ))
        embed, _ = await self._mute(ctx.guild, ctx.author, member,
                                     duration_text, duration_seconds, reason)
        await ctx.reply(embed=embed)

    @app_commands.command(name='mute', description='Mute a member')
    @app_commands.describe(member='Member to mute', duration='e.g. 10m, 1h, 1d', reason='Reason')
    async def mute_slash(self, interaction: discord.Interaction,
                         member: discord.Member,
                         duration: str = "10m",
                         reason: str = "No reason provided"):
        parsed = self.parse_time(duration)
        if not parsed:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Invalid Time", description="Use: `30s`, `10m`, `2h`, `1d`",
                color=0xe74c3c), ephemeral=True)
        embed, _ = await self._mute(interaction.guild, interaction.user,
                                     member, duration, parsed, reason)
        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def unmute(self, ctx, member: discord.Member):
        if not self.can_do(ctx.author, 'mute'):
            return await ctx.reply(embed=self.perm_error_embed('mute'))
        await member.timeout(None)
        embed = discord.Embed(title="🔊 Member Unmuted", color=0x2ecc71)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        await self.send_log(ctx.guild, self.log_embed("🔊 Unmuted", 0x2ecc71,
            user=f"{member} ({member.id})", moderator=str(ctx.author)))

    @app_commands.command(name='unmute', description='Unmute a member')
    @app_commands.describe(member='Member to unmute')
    async def unmute_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not self.can_do(interaction.user, 'mute'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('mute'), ephemeral=True)
        await member.timeout(None)
        await interaction.response.send_message(embed=discord.Embed(
            title="🔊 Member Unmuted",
            description=f"{member.mention} has been unmuted!",
            color=0x2ecc71
        ))

    # ══════════════════════════════════════════
    #   KICK COMMANDS
    # ══════════════════════════════════════════

    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, args=""):
        reason = args.split("?r", 1)[1].strip() if "?r" in args else "No reason provided"
        embed, _ = await self._kick(ctx.guild, ctx.author, member, reason)
        await ctx.reply(embed=embed)

    @app_commands.command(name='kick', description='Kick a member')
    @app_commands.describe(member='Member to kick', reason='Reason')
    async def kick_slash(self, interaction: discord.Interaction,
                         member: discord.Member, reason: str = "No reason provided"):
        embed, _ = await self._kick(interaction.guild, interaction.user, member, reason)
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════
    #   BAN COMMANDS
    # ══════════════════════════════════════════

    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, args=""):
        reason = args.split("?r", 1)[1].strip() if "?r" in args else "No reason provided"
        embed, _ = await self._ban(ctx.guild, ctx.author, member, reason)
        await ctx.reply(embed=embed)

    @app_commands.command(name='ban', description='Ban a member')
    @app_commands.describe(member='Member to ban', reason='Reason')
    async def ban_slash(self, interaction: discord.Interaction,
                        member: discord.Member, reason: str = "No reason provided"):
        embed, _ = await self._ban(interaction.guild, interaction.user, member, reason)
        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def unban(self, ctx, *, username):
        if not self.can_do(ctx.author, 'ban'):
            return await ctx.reply(embed=self.perm_error_embed('ban'))
        banned = [entry async for entry in ctx.guild.bans()]
        matches = [e for e in banned if username.lower() in str(e.user).lower()]
        if not matches:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Not Found",
                description=f"No banned user matching `{username}`",
                color=0xe74c3c
            ))
        if len(matches) == 1:
            await ctx.guild.unban(matches[0].user)
            embed = discord.Embed(title="✅ Member Unbanned", color=0x2ecc71)
            embed.add_field(name="User", value=str(matches[0].user))
            embed.add_field(name="Moderator", value=ctx.author.mention)
            await ctx.send(embed=embed)
            await self.send_log(ctx.guild, self.log_embed("✅ Unbanned", 0x2ecc71,
                user=str(matches[0].user), moderator=str(ctx.author)))
            return
        desc = "\n".join([f"`{i+1}.` {e.user}" for i, e in enumerate(matches[:10])])
        await ctx.send(embed=discord.Embed(
            title="🔍 Multiple Matches",
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
                await ctx.reply(embed=discord.Embed(
                    title="✅ Unbanned",
                    description=f"Unbanned **{matches[index].user}**!",
                    color=0x2ecc71
                ))
        except asyncio.TimeoutError:
            await ctx.reply(embed=discord.Embed(
                title="⏰ Timed Out", description="Unban cancelled.", color=0xe74c3c))

    @app_commands.command(name='unban', description='Unban a user')
    @app_commands.describe(username='Username of the banned user')
    async def unban_slash(self, interaction: discord.Interaction, username: str):
        if not self.can_do(interaction.user, 'ban'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('ban'), ephemeral=True)
        banned = [entry async for entry in interaction.guild.bans()]
        matches = [e for e in banned if username.lower() in str(e.user).lower()]
        if not matches:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Not Found", color=0xe74c3c,
                description=f"No banned user matching `{username}`"))
        await interaction.guild.unban(matches[0].user)
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Unbanned",
            description=f"Unbanned **{matches[0].user}**!",
            color=0x2ecc71
        ))

    @commands.command()
    async def tempban(self, ctx, member: discord.Member, time: str, *, args=""):
        if not self.can_do(ctx.author, 'tempban'):
            return await ctx.reply(embed=self.perm_error_embed(
                'tempban', self.get_hierarchy_level(ctx.author)))
        if self.has_god_bypass(member) and not self.is_god_tier(ctx.author):
            return await ctx.reply(embed=self.bypass_error_embed(member))
        reason = args.split("?r", 1)[1].strip() if "?r" in args else "No reason provided"
        seconds = self.parse_time(time)
        if not seconds:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Invalid Time", description="Use: `30s`, `10m`, `2h`, `1d`",
                color=0xe74c3c))
        await member.ban(reason=f"[Tempban: {time}] {reason}")
        unban_ts = int((datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)).timestamp())
        embed = discord.Embed(title="⏳ Member Tempbanned", color=0xc0392b)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Duration", value=time)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Unban at", value=f"<t:{unban_ts}:R>")
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        await self.send_log(ctx.guild, self.log_embed("⏳ Tempban", 0xc0392b,
            user=f"{member} ({member.id})", duration=time,
            reason=reason, moderator=str(ctx.author)))
        await asyncio.sleep(seconds)
        try:
            await ctx.guild.unban(member, reason="Tempban expired")
            await self.send_log(ctx.guild, self.log_embed(
                "✅ Tempban Expired", 0x2ecc71, user=str(member)))
        except:
            pass

    @app_commands.command(name='tempban', description='Temporarily ban a member')
    @app_commands.describe(member='Member', duration='e.g. 1h, 30m', reason='Reason')
    async def tempban_slash(self, interaction: discord.Interaction,
                            member: discord.Member,
                            duration: str,
                            reason: str = "No reason provided"):
        if not self.can_do(interaction.user, 'tempban'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('tempban'), ephemeral=True)
        seconds = self.parse_time(duration)
        if not seconds:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Invalid Time", color=0xe74c3c,
                description="Use: `30s`, `10m`, `2h`, `1d`"), ephemeral=True)
        await member.ban(reason=f"[Tempban: {duration}] {reason}")
        unban_ts = int((datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)).timestamp())
        embed = discord.Embed(title="⏳ Member Tempbanned", color=0xc0392b)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Duration", value=duration)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Unban at", value=f"<t:{unban_ts}:R>")
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(seconds)
        try:
            await interaction.guild.unban(member, reason="Tempban expired")
        except:
            pass

    # ══════════════════════════════════════════
    #   MASSBAN
    # ══════════════════════════════════════════

    @commands.command()
    async def massban(self, ctx, action: str = None, *members: discord.Member):
        if not self.is_god_tier(ctx.author):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Owner/ExtraOwner Only",
                description="Only god tier users can use massban!",
                color=0xe74c3c
            ))
        guild_id = ctx.guild.id
        if action == "enable":
            self.massban_enabled[guild_id] = True
            return await ctx.send(embed=discord.Embed(
                title="🔓 Massban ENABLED",
                description="Use `!massban @u1 @u2 ...`\nUse `!massban disable` after!",
                color=0xe74c3c))
        if action == "disable":
            self.massban_enabled[guild_id] = False
            return await ctx.reply(embed=discord.Embed(
                title="🔒 Massban Disabled", color=0x2ecc71))
        if action == "status":
            status = self.massban_enabled.get(guild_id, False)
            return await ctx.reply(embed=discord.Embed(
                title="📊 Massban Status",
                description=f"**{'🔓 ENABLED' if status else '🔒 DISABLED'}**",
                color=0xe74c3c if status else 0x2ecc71))
        if not self.massban_enabled.get(guild_id, False):
            return await ctx.send(embed=discord.Embed(
                title="🔒 Massban is Disabled",
                description="Run `!massban enable` first!\n⚠️ Disable after use!",
                color=0xe74c3c))
        if not members and action:
            try:
                first = await commands.MemberConverter().convert(ctx, action)
                members = (first,) + members
            except:
                return await ctx.reply(embed=discord.Embed(
                    title="❌ Usage", description="`!massban @u1 @u2 @u3`", color=0xe74c3c))
        if not members:
            return await ctx.reply(embed=discord.Embed(
                title="❌ No Members", description="Mention at least one member!", color=0xe74c3c))
        await ctx.send(embed=discord.Embed(
            title="⚠️ Confirm Massban",
            description=f"Ban **{len(members)}** members? Reply `yes`.",
            color=0xe74c3c))
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
        try:
            await self.bot.wait_for('message', check=check, timeout=20)
        except asyncio.TimeoutError:
            return await ctx.reply(embed=discord.Embed(title="❌ Cancelled", color=0xe74c3c))
        banned, failed = [], []
        for m in members:
            try:
                await m.ban(reason=f"Massban by {ctx.author}")
                banned.append(str(m))
            except:
                failed.append(str(m))
        embed = discord.Embed(title="🔨 Massban Complete", color=0xc0392b)
        if banned:
            embed.add_field(name=f"✅ Banned ({len(banned)})", value="\n".join(banned))
        if failed:
            embed.add_field(name=f"❌ Failed ({len(failed)})", value="\n".join(failed))
        await ctx.send(embed=embed)
        await self.send_log(ctx.guild, self.log_embed("🔨 Massban", 0xc0392b,
            banned=", ".join(banned) or "None",
            failed=", ".join(failed) or "None",
            moderator=str(ctx.author)))

    # ══════════════════════════════════════════
    #   PURGE
    # ══════════════════════════════════════════

    @commands.command()
    async def purge(self, ctx, amount: int, member: discord.Member = None):
        if not self.can_do(ctx.author, 'purge'):
            return await ctx.reply(embed=self.perm_error_embed('purge'))
        if amount > 100:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Too Many", description="Max 100 at once!", color=0xe74c3c))
        if member:
            deleted = await ctx.channel.purge(
                limit=amount * 5, check=lambda m: m.author == member)
        else:
            deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(embed=discord.Embed(
            description=f"🗑️ Deleted **{len(deleted)}** messages!", color=0x2ecc71))
        await msg.delete(delay=3)
        await self.send_log(ctx.guild, self.log_embed("🗑️ Purge", 0xe74c3c,
            channel=ctx.channel.mention, deleted=str(len(deleted)),
            target=str(member) if member else "All", moderator=str(ctx.author)))

    @app_commands.command(name='purge', description='Delete messages in bulk')
    @app_commands.describe(amount='Number of messages (max 100)', member='Only delete this member\'s messages')
    async def purge_slash(self, interaction: discord.Interaction,
                          amount: int, member: discord.Member = None):
        if not self.can_do(interaction.user, 'purge'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('purge'), ephemeral=True)
        if amount > 100:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Too Many", description="Max 100!", color=0xe74c3c), ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        if member:
            deleted = await interaction.channel.purge(
                limit=amount * 5, check=lambda m: m.author == member)
        else:
            deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(embed=discord.Embed(
            description=f"🗑️ Deleted **{len(deleted)}** messages!", color=0x2ecc71), ephemeral=True)

    # ══════════════════════════════════════════
    #   LOCK / UNLOCK / SLOWMODE
    # ══════════════════════════════════════════

    @commands.command()
    async def slowmode(self, ctx, time: str = "0"):
        if not self.can_do(ctx.author, 'lock'):
            return await ctx.reply(embed=self.perm_error_embed('lock'))
        if time in ("0", "off"):
            await ctx.channel.edit(slowmode_delay=0)
            return await ctx.reply(embed=discord.Embed(
                title="✅ Slowmode Disabled", color=0x2ecc71))
        seconds = self.parse_time(time)
        if not seconds:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Invalid Time", description="Use: `30s`, `5m`, `1h`", color=0xe74c3c))
        if seconds > 21600:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Too Long", description="Max slowmode is 6 hours!", color=0xe74c3c))
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.reply(embed=discord.Embed(
            title="✅ Slowmode Set", description=f"Set to **{time}**!", color=0x2ecc71))

    @app_commands.command(name='slowmode', description='Set channel slowmode')
    @app_commands.describe(duration='e.g. 5m, 30s (use 0 to disable)')
    async def slowmode_slash(self, interaction: discord.Interaction, duration: str = "0"):
        if not self.can_do(interaction.user, 'lock'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('lock'), ephemeral=True)
        if duration in ("0", "off"):
            await interaction.channel.edit(slowmode_delay=0)
            return await interaction.response.send_message(embed=discord.Embed(
                title="✅ Slowmode Disabled", color=0x2ecc71))
        seconds = self.parse_time(duration)
        if not seconds:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Invalid Time", color=0xe74c3c), ephemeral=True)
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Slowmode Set", description=f"Set to **{duration}**!", color=0x2ecc71))

    @commands.command()
    async def lock(self, ctx, channel: discord.TextChannel = None):
        if not self.can_do(ctx.author, 'lock'):
            return await ctx.reply(embed=self.perm_error_embed('lock'))
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(embed=discord.Embed(
            title="🔒 Channel Locked",
            description=f"**#{channel.name}** is now locked!", color=0xe74c3c))
        await self.send_log(ctx.guild, self.log_embed("🔒 Channel Locked", 0xe74c3c,
            channel=channel.mention, moderator=str(ctx.author)))

    @app_commands.command(name='lock', description='Lock a channel')
    @app_commands.describe(channel='Channel to lock (default: current)')
    async def lock_slash(self, interaction: discord.Interaction,
                         channel: discord.TextChannel = None):
        if not self.can_do(interaction.user, 'lock'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('lock'), ephemeral=True)
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(embed=discord.Embed(
            title="🔒 Channel Locked", description=f"**#{channel.name}** locked!", color=0xe74c3c))

    @commands.command()
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        if not self.can_do(ctx.author, 'lock'):
            return await ctx.reply(embed=self.perm_error_embed('lock'))
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(embed=discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"**#{channel.name}** is now unlocked!", color=0x2ecc71))
        await self.send_log(ctx.guild, self.log_embed("🔓 Channel Unlocked", 0x2ecc71,
            channel=channel.mention, moderator=str(ctx.author)))

    @app_commands.command(name='unlock', description='Unlock a channel')
    @app_commands.describe(channel='Channel to unlock (default: current)')
    async def unlock_slash(self, interaction: discord.Interaction,
                           channel: discord.TextChannel = None):
        if not self.can_do(interaction.user, 'lock'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('lock'), ephemeral=True)
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message(embed=discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"**#{channel.name}** unlocked!", color=0x2ecc71))

    # ══════════════════════════════════════════
    #   NICK
    # ══════════════════════════════════════════

    @commands.command()
    async def nick(self, ctx, member: discord.Member, *, nickname):
        if not self.can_do(ctx.author, 'nick'):
            return await ctx.reply(embed=self.perm_error_embed('nick'))
        old = member.display_name
        await member.edit(nick=nickname)
        await ctx.reply(embed=discord.Embed(
            title="✅ Nickname Changed",
            description=f"**{old}** → **{nickname}**", color=0x2ecc71))

    @app_commands.command(name='nick', description='Change a member\'s nickname')
    @app_commands.describe(member='Target member', nickname='New nickname')
    async def nick_slash(self, interaction: discord.Interaction,
                         member: discord.Member, nickname: str):
        if not self.can_do(interaction.user, 'nick'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('nick'), ephemeral=True)
        old = member.display_name
        await member.edit(nick=nickname)
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Nickname Changed",
            description=f"**{old}** → **{nickname}**", color=0x2ecc71))

    @commands.command()
    async def resetnick(self, ctx, member: discord.Member):
        if not self.can_do(ctx.author, 'nick'):
            return await ctx.reply(embed=self.perm_error_embed('nick'))
        await member.edit(nick=None)
        await ctx.reply(embed=discord.Embed(
            title="✅ Nickname Reset",
            description=f"Reset **{member.name}'s** nickname!", color=0x2ecc71))

    @app_commands.command(name='resetnick', description='Reset a member\'s nickname')
    @app_commands.describe(member='Member to reset')
    async def resetnick_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not self.can_do(interaction.user, 'nick'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('nick'), ephemeral=True)
        await member.edit(nick=None)
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Nickname Reset",
            description=f"Reset **{member.name}'s** nickname!", color=0x2ecc71))

    # ══════════════════════════════════════════
    #   ANNOUNCE / POLL
    # ══════════════════════════════════════════

    @commands.command()
    async def announce(self, ctx, channel: discord.TextChannel, *, args):
        if not self.can_do(ctx.author, 'announce'):
            return await ctx.reply(embed=self.perm_error_embed('announce'))
        if "|" in args:
            parts = args.split("|", 1)
            title, content = parts[0].strip(), parts[1].strip()
        else:
            title, content = "📢 Announcement", args.strip()
        embed = discord.Embed(
            title=f"📢 {title}", description=content,
            color=0x3498db, timestamp=datetime.datetime.utcnow())
        embed.set_footer(text=f"By {ctx.author} • {ctx.guild.name}")
        await channel.send(embed=embed)
        await ctx.reply(embed=discord.Embed(
            title="✅ Announcement Sent",
            description=f"Sent to {channel.mention}!", color=0x2ecc71))

    @app_commands.command(name='announce', description='Send an announcement')
    @app_commands.describe(channel='Target channel', message='Message', title='Title')
    async def announce_slash(self, interaction: discord.Interaction,
                             channel: discord.TextChannel,
                             message: str, title: str = "Announcement"):
        if not self.can_do(interaction.user, 'announce'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('announce'), ephemeral=True)
        embed = discord.Embed(
            title=f"📢 {title}", description=message,
            color=0x3498db, timestamp=datetime.datetime.utcnow())
        embed.set_footer(text=f"By {interaction.user} • {interaction.guild.name}")
        await channel.send(embed=embed)
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Sent!", description=f"Announcement sent to {channel.mention}!",
            color=0x2ecc71), ephemeral=True)

    @commands.command()
    async def poll(self, ctx, *, question):
        if not self.can_do(ctx.author, 'announce'):
            return await ctx.reply(embed=self.perm_error_embed('announce'))
        embed = discord.Embed(
            title="📊 Poll", description=question,
            color=0x3498db, timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Vote!", value="✅ Yes  |  ❌ No")
        embed.set_footer(text=f"Poll by {ctx.author}")
        msg = await ctx.send(embed=embed)
        await ctx.message.delete()
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

    @app_commands.command(name='poll', description='Create a yes/no poll')
    @app_commands.describe(question='Poll question')
    async def poll_slash(self, interaction: discord.Interaction, question: str):
        if not self.can_do(interaction.user, 'announce'):
            return await interaction.response.send_message(
                embed=self.perm_error_embed('announce'), ephemeral=True)
        embed = discord.Embed(
            title="📊 Poll", description=question,
            color=0x3498db, timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Vote!", value="✅ Yes  |  ❌ No")
        embed.set_footer(text=f"Poll by {interaction.user}")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

    # ══════════════════════════════════════════
    #   NOTES
    # ══════════════════════════════════════════

    @commands.command()
    async def note(self, ctx, member: discord.Member, *, text: str):
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        guild_id = ctx.guild.id
        if guild_id not in self.notes_db:
            self.notes_db[guild_id] = {}
        if member.id not in self.notes_db[guild_id]:
            self.notes_db[guild_id][member.id] = []
        self.notes_db[guild_id][member.id].append({
            'note': text, 'by': str(ctx.author),
            'time': datetime.datetime.utcnow().strftime("%b %d %Y %H:%M")
        })
        count = len(self.notes_db[guild_id][member.id])
        await ctx.reply(embed=discord.Embed(
            title="📝 Note Added",
            description=f"Note #{count} added for {member.mention}!", color=0x9b59b6))
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.command()
    async def notes(self, ctx, member: discord.Member):
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        notes = self.notes_db.get(ctx.guild.id, {}).get(member.id, [])
        if not notes:
            return await ctx.reply(embed=discord.Embed(
                description=f"📝 No notes for {member.mention}!", color=0x9b59b6))
        embed = discord.Embed(
            title=f"📝 Mod Notes — {member.display_name}", color=0x9b59b6)
        for i, n in enumerate(notes, 1):
            embed.add_field(
                name=f"Note #{i} • {n['by']} • {n['time']}",
                value=n['note'], inline=False)
        try:
            await ctx.author.send(embed=embed)
            await ctx.reply(embed=discord.Embed(
                description="📬 Notes sent to your DMs!", color=0x9b59b6))
        except:
            await ctx.send(embed=embed)

    @commands.command()
    async def clearnotes(self, ctx, member: discord.Member):
        if not self.can_do(ctx.author, 'warn'):
            return await ctx.reply(embed=self.perm_error_embed('warn'))
        if ctx.guild.id in self.notes_db and member.id in self.notes_db[ctx.guild.id]:
            self.notes_db[ctx.guild.id][member.id] = []
        await ctx.reply(embed=discord.Embed(
            title="🧹 Notes Cleared",
            description=f"Cleared all notes for {member.mention}!", color=0x2ecc71))

    # ══════════════════════════════════════════
    #   AFK
    # ══════════════════════════════════════════

    @commands.command()
    async def afk(self, ctx, *, reason="AFK"):
        self.afk_db[ctx.author.id] = {
            'reason': reason,
            'time': int(datetime.datetime.utcnow().timestamp())
        }
        try:
            await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}"[:32])
        except:
            pass
        await ctx.send(embed=discord.Embed(
            title="💤 AFK Set",
            description=f"{ctx.author.mention} is now AFK\nReason: **{reason}**",
            color=0x95a5a6))

    @app_commands.command(name='afk', description='Set yourself as AFK')
    @app_commands.describe(reason='Reason for AFK')
    async def afk_slash(self, interaction: discord.Interaction, reason: str = "AFK"):
        self.afk_db[interaction.user.id] = {
            'reason': reason,
            'time': int(datetime.datetime.utcnow().timestamp())
        }
        try:
            await interaction.user.edit(nick=f"[AFK] {interaction.user.display_name}"[:32])
        except:
            pass
        await interaction.response.send_message(embed=discord.Embed(
            title="💤 AFK Set",
            description=f"{interaction.user.mention} is now AFK\nReason: **{reason}**",
            color=0x95a5a6))

    # ══════════════════════════════════════════
    #   SNIPE / EDITSNIPE
    # ══════════════════════════════════════════

    @commands.command()
    async def snipe(self, ctx):
        data = self.snipe_db.get(ctx.channel.id)
        if not data:
            return await ctx.reply(embed=discord.Embed(
                description="❌ Nothing to snipe here!", color=0xe74c3c))
        embed = discord.Embed(
            title="🕵️ Sniped Message", description=data['content'],
            color=0x3498db, timestamp=data['time'])
        embed.set_author(name=str(data['author']),
                         icon_url=data['author'].display_avatar.url)
        if data['attachments']:
            embed.add_field(name="Attachments", value="\n".join(data['attachments']))
        embed.set_footer(text=f"Sniped by {ctx.author}")
        await ctx.send(embed=embed)

    @app_commands.command(name='snipe', description='Show last deleted message')
    async def snipe_slash(self, interaction: discord.Interaction):
        data = self.snipe_db.get(interaction.channel.id)
        if not data:
            return await interaction.response.send_message(embed=discord.Embed(
                description="❌ Nothing to snipe here!", color=0xe74c3c))
        embed = discord.Embed(
            title="🕵️ Sniped Message", description=data['content'],
            color=0x3498db, timestamp=data['time'])
        embed.set_author(name=str(data['author']),
                         icon_url=data['author'].display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def editsnipe(self, ctx):
        data = self.editsnipe_db.get(ctx.channel.id)
        if not data:
            return await ctx.reply(embed=discord.Embed(
                description="❌ Nothing to editsnipe here!", color=0xe74c3c))
        embed = discord.Embed(
            title="👁️ Edit Sniped", color=0x9b59b6, timestamp=data['time'])
        embed.set_author(name=str(data['author']),
                         icon_url=data['author'].display_avatar.url)
        embed.add_field(name="Before", value=data['before'], inline=False)
        embed.add_field(name="After", value=data['after'], inline=False)
        embed.set_footer(text=f"Sniped by {ctx.author}")
        await ctx.send(embed=embed)

    @app_commands.command(name='editsnipe', description='Show last edited message')
    async def editsnipe_slash(self, interaction: discord.Interaction):
        data = self.editsnipe_db.get(interaction.channel.id)
        if not data:
            return await interaction.response.send_message(embed=discord.Embed(
                description="❌ Nothing to editsnipe here!", color=0xe74c3c))
        embed = discord.Embed(title="👁️ Edit Sniped", color=0x9b59b6)
        embed.add_field(name="Before", value=data['before'], inline=False)
        embed.add_field(name="After", value=data['after'], inline=False)
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════
    #   FIND / USERINFO / SERVERINFO
    # ══════════════════════════════════════════

    @commands.command()
    async def find(self, ctx, *, query: str):
        results = [
            m for m in ctx.guild.members
            if query.lower() in m.name.lower() or
               query.lower() in m.display_name.lower()
        ][:20]
        if not results:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Not Found",
                description=f"No members matching `{query}`", color=0xe74c3c))
        icons = {"online": "🟢", "idle": "🟡", "dnd": "🔴", "offline": "⚫"}
        embed = discord.Embed(
            title=f"🔍 Search: `{query}`",
            description=f"Found **{len(results)}** member(s)", color=0x3498db)
        lines = [f"{icons.get(str(m.status),'⚫')} {m.mention} — `{m.id}`" for m in results]
        embed.add_field(name="Results", value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)

    @app_commands.command(name='find', description='Search for a member by name')
    @app_commands.describe(query='Name to search for')
    async def find_slash(self, interaction: discord.Interaction, query: str):
        results = [
            m for m in interaction.guild.members
            if query.lower() in m.name.lower() or
               query.lower() in m.display_name.lower()
        ][:20]
        if not results:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Not Found", color=0xe74c3c))
        icons = {"online": "🟢", "idle": "🟡", "dnd": "🔴", "offline": "⚫"}
        embed = discord.Embed(
            title=f"🔍 Search: `{query}`",
            description=f"Found **{len(results)}**", color=0x3498db)
        lines = [f"{icons.get(str(m.status),'⚫')} {m.mention}" for m in results]
        embed.add_field(name="Results", value="\n".join(lines), inline=False)
        await interaction.response.send_message(embed=embed)

    @commands.command(aliases=['ui', 'whois'])
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        embed = discord.Embed(
            title=f"👤 {member.display_name}",
            color=member.color if member.color.value else 0x3498db)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member))
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Bot?", value="Yes 🤖" if member.bot else "No 👤")
        embed.add_field(name="Joined", value=member.joined_at.strftime("%b %d, %Y"))
        embed.add_field(name="Created", value=member.created_at.strftime("%b %d, %Y"))
        embed.add_field(name="Top Role", value=member.top_role.mention)
        warns = len(self.warn_db.get(ctx.guild.id, {}).get(member.id, []))
        notes_count = len(self.notes_db.get(ctx.guild.id, {}).get(member.id, []))
        embed.add_field(name="Warnings", value=f"⚠️ {warns}")
        embed.add_field(name="Notes", value=f"📝 {notes_count}")
        embed.add_field(name="AFK", value="💤 Yes" if member.id in self.afk_db else "No")
        if member.id == ctx.guild.owner_id:
            special = "👑 Owner"
        elif member.id in self.extraowners.get(ctx.guild.id, set()):
            special = "👑 ExtraOwner"
        elif self.has_god_bypass(member):
            special = "✨ God Bypass"
        else:
            special = "—"
        embed.add_field(name="Special", value=special)
        lvl = self.get_hierarchy_level(member)
        lvl_name = {0:"None",1:"warn.exe",2:"mute.exe",3:"kick.exe",
                    4:"ban.exe",999:"God Tier"}.get(lvl,"—")
        embed.add_field(name="Mod Level", value=f"`{lvl_name}`")
        if roles:
            embed.add_field(name=f"Roles ({len(roles)})",
                           value=" ".join(roles[:8]), inline=False)
        await ctx.send(embed=embed)

    @app_commands.command(name='userinfo', description='Get info about a member')
    @app_commands.describe(member='Member to check (default: yourself)')
    async def userinfo_slash(self, interaction: discord.Interaction,
                             member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(
            title=f"👤 {member.display_name}",
            color=member.color if member.color.value else 0x3498db)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member))
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Joined", value=member.joined_at.strftime("%b %d, %Y"))
        embed.add_field(name="Created", value=member.created_at.strftime("%b %d, %Y"))
        embed.add_field(name="Top Role", value=member.top_role.mention)
        await interaction.response.send_message(embed=embed)

    @commands.command(aliases=['si', 'server'])
    async def serverinfo(self, ctx):
        g = ctx.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        embed = discord.Embed(title=f"🏠 {g.name}", color=0x3498db)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=g.owner.mention)
        embed.add_field(name="Members", value=f"👤 {humans} humans\n🤖 {bots} bots")
        embed.add_field(name="Channels",
                        value=f"💬 {len(g.text_channels)} text\n🔊 {len(g.voice_channels)} voice")
        embed.add_field(name="Roles", value=len(g.roles))
        embed.add_field(name="Created", value=g.created_at.strftime("%b %d, %Y"))
        embed.add_field(name="Boosts",
                        value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)")
        embed.add_field(name="ExtraOwners",
                        value=str(len(self.extraowners.get(g.id, set()))))
        embed.set_footer(text=f"ID: {g.id}")
        await ctx.send(embed=embed)

    @app_commands.command(name='serverinfo', description='Get server info')
    async def serverinfo_slash(self, interaction: discord.Interaction):
        g = interaction.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        embed = discord.Embed(title=f"🏠 {g.name}", color=0x3498db)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Owner", value=g.owner.mention)
        embed.add_field(name="Members", value=f"👤 {humans} humans\n🤖 {bots} bots")
        embed.add_field(name="Channels", value=f"💬 {len(g.text_channels)} text")
        embed.add_field(name="Roles", value=len(g.roles))
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
