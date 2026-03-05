import discord
from discord.ext import commands
from discord import app_commands
import datetime

# ══════════════════════════════════════════════
#   HELP DATA — Edit this to update help pages
# ══════════════════════════════════════════════

SECTIONS = {
    'mod': {
        'emoji': '🛡️',
        'name': 'Moderation',
        'description': 'Commands for moderating members and channels',
        'color': 0xe74c3c,
    },
    'security': {
        'emoji': '🔒',
        'name': 'Security',
        'description': 'Anti-nuke, anti-raid, anti-spam and anti-bot systems',
        'color': 0x9b59b6,
    },
    'tickets': {
        'emoji': '🎫',
        'name': 'Tickets',
        'description': 'Support ticket system',
        'color': 0x3498db,
    },
    'music': {
        'emoji': '🎵',
        'name': 'Music',
        'description': 'Play music in voice channels',
        'color': 0x1abc9c,
    },
    'fun': {
        'emoji': '😂',
        'name': 'Fun',
        'description': 'Fun commands and games',
        'color': 0xf39c12,
    },
    'economy': {
        'emoji': '💰',
        'name': 'Economy',
        'description': 'Coins, shop, and daily rewards',
        'color': 0xf1c40f,
    },
    'leveling': {
        'emoji': '⭐',
        'name': 'Leveling',
        'description': 'XP, ranks, and level cards',
        'color': 0xe91e63,
    },
    'giveaway': {
        'emoji': '🎁',
        'name': 'Giveaway',
        'description': 'Create and manage giveaways',
        'color': 0xff6600,
    },
    'settings': {
        'emoji': '⚙️',
        'name': 'Settings',
        'description': 'Bot configuration and permission system',
        'color': 0x95a5a6,
    },
}

# ── All moderation commands ────────────────────
MOD_COMMANDS = [
    # (name, usage, description, required_role, aliases)
    (
        'warn',
        '`!warn @user` or `!warn @user ?r reason`',
        'Warn a member. Sends them a DM and logs it. Alerts when they reach 3+ warnings.',
        '`warn.exe` or higher',
        '`/warn`'
    ),
    (
        'warnings',
        '`!warnings @user`',
        'View all warnings for a member. Shows each warning with its reason and number.',
        '`warn.exe` or higher',
        '`/warnings`'
    ),
    (
        'unwarn',
        '`!unwarn @user` or `!unwarn @user 2`',
        'Remove a warning. Leave the number empty to remove the latest one, or specify a number.',
        '`warn.exe` or higher',
        '`/unwarn`'
    ),
    (
        'clearwarn',
        '`!clearwarn @user`',
        'Wipe ALL warnings from a member at once.',
        '`warn.exe` or higher',
        '`/clearwarn`'
    ),
    (
        'mute',
        (
            '`!mute @user`\n'
            '`!mute @user ?t 10m`\n'
            '`!mute @user ?r reason`\n'
            '`!mute @user ?t 1h ?r reason`'
        ),
        'Timeout a member. Default duration is 10 minutes if no `?t` is given. Max is 28 days.\n**Time formats:** `30s` `10m` `2h` `1d`',
        '`mute.exe` or higher',
        '`/mute`'
    ),
    (
        'unmute',
        '`!unmute @user`',
        'Remove a timeout from a member immediately.',
        '`mute.exe` or higher',
        '`/unmute`'
    ),
    (
        'kick',
        '`!kick @user` or `!kick @user ?r reason`',
        'Kick a member from the server. They can rejoin with an invite.',
        '`kick.exe` or higher',
        '`/kick`'
    ),
    (
        'ban',
        '`!ban @user` or `!ban @user ?r reason`',
        'Permanently ban a member. They cannot rejoin unless unbanned.',
        '`ban.exe`',
        '`/ban`'
    ),
    (
        'unban',
        '`!unban username`',
        'Unban a user by their username. If multiple matches found, you pick the right one.',
        '`ban.exe`',
        '`/unban`'
    ),
    (
        'tempban',
        '`!tempban @user 1h` or `!tempban @user 30m ?r reason`',
        'Ban a member for a set time, then automatically unban them.\n**Time formats:** `30s` `10m` `2h` `1d`',
        '`ban.exe`',
        '`/tempban`'
    ),
    (
        'massban',
        (
            '`!massban enable` — turn on massban\n'
            '`!massban disable` — turn off\n'
            '`!massban status` — check if on\n'
            '`!massban @u1 @u2 @u3` — ban multiple (when enabled)'
        ),
        'Ban multiple members at once. **Disabled by default for safety.** Must be enabled first. Asks for confirmation before banning.',
        '**Owner / ExtraOwner only**',
        'No slash version'
    ),
    (
        'purge',
        '`!purge 10` or `!purge 10 @user`',
        'Delete messages in bulk. Max 100 at once. Add a @user to only delete their messages.',
        '`purge.exe`',
        '`/purge`'
    ),
    (
        'lock',
        '`!lock` or `!lock #channel`',
        'Lock a channel so normal members cannot send messages. Defaults to current channel.',
        '`lock.exe`',
        '`/lock`'
    ),
    (
        'unlock',
        '`!unlock` or `!unlock #channel`',
        'Unlock a previously locked channel.',
        '`lock.exe`',
        '`/unlock`'
    ),
    (
        'slowmode',
        '`!slowmode 5m` or `!slowmode 0` to disable',
        'Set slowmode on a channel. Users must wait between messages.\n**Time formats:** `30s` `5m` `1h` (max 6h)',
        '`lock.exe`',
        '`/slowmode`'
    ),
    (
        'nick',
        '`!nick @user NewNickname`',
        'Change a member\'s nickname to anything you want.',
        '`nick.exe`',
        '`/nick`'
    ),
    (
        'resetnick',
        '`!resetnick @user`',
        'Reset a member\'s nickname back to their original username.',
        '`nick.exe`',
        '`/resetnick`'
    ),
    (
        'announce',
        (
            '`!announce #channel Message`\n'
            '`!announce #channel Title | Message`'
        ),
        'Send a formatted announcement embed to any channel. Use `|` to separate title and message.',
        '`announce.exe`',
        '`/announce`'
    ),
    (
        'poll',
        '`!poll Should we add a gaming channel?`',
        'Create a Yes/No poll with ✅ and ❌ reactions. The command message is deleted automatically.',
        '`announce.exe`',
        '`/poll`'
    ),
    (
        'note',
        '`!note @user they were verbally warned`',
        'Add a private moderator note on a user. Notes are hidden — the command message is deleted. Only mods can see them.',
        '`warn.exe` or higher',
        'No slash version'
    ),
    (
        'notes',
        '`!notes @user`',
        'View all mod notes for a user. Sent to your DMs to keep it private.',
        '`warn.exe` or higher',
        'No slash version'
    ),
    (
        'clearnotes',
        '`!clearnotes @user`',
        'Delete all mod notes for a user.',
        '`warn.exe` or higher',
        'No slash version'
    ),
    (
        'snipe',
        '`!snipe`',
        'Show the last deleted message in the current channel. Only works for messages deleted after the bot started.',
        'Everyone',
        '`/snipe`'
    ),
    (
        'editsnipe',
        '`!editsnipe`',
        'Show the last edited message in the current channel — shows both before and after.',
        'Everyone',
        '`/editsnipe`'
    ),
    (
        'find',
        '`!find john`',
        'Search for members by name or nickname. Shows up to 20 results with online status.',
        'Everyone',
        '`/find`'
    ),
    (
        'afk',
        '`!afk` or `!afk doing homework`',
        'Set yourself as AFK. Your nickname gets `[AFK]` prefix. If anyone pings you, they get notified. Removed when you next send a message.',
        'Everyone',
        '`/afk`'
    ),
    (
        'userinfo',
        '`!userinfo` or `!userinfo @user`',
        'View detailed info about a member — join date, roles, warnings, mod level, special status and more.',
        'Everyone',
        '`/userinfo` • Aliases: `!ui` `!whois`'
    ),
    (
        'serverinfo',
        '`!serverinfo`',
        'View server stats — member count, channels, roles, boost level, and ExtraOwner count.',
        'Everyone',
        '`/serverinfo` • Aliases: `!si` `!server`'
    ),
]

# ── Settings commands ──────────────────────────
SETTINGS_COMMANDS = [
    (
        'setup',
        '`!setup`',
        'Auto-setup everything Lucky Bot needs. Creates all permission roles, `#mod-logs` channel, `#welcome`, `#rules`. Run this first!',
        '**Owner / ExtraOwner only**',
        '`/setup`'
    ),
    (
        'setprefix',
        '`!setprefix &` or `!setprefix !`',
        'Change the bot prefix for this server. Max 5 characters. Use `/setprefix` if you forget your prefix.',
        '**Server owner only**',
        '`/setprefix`'
    ),
    (
        'prefix',
        '`!prefix`',
        'Check the current prefix for this server.',
        'Everyone',
        '`/prefix`'
    ),
    (
        'noprefix',
        (
            '`!noprefix add @user`\n'
            '`!noprefix remove @user`\n'
            '`!noprefix list`'
        ),
        'Grant a user the ability to use commands without any prefix at all. They can type `warn @user` instead of `!warn @user`.',
        '**Bot owner only**',
        '`/noprefix`'
    ),
    (
        'extraowner',
        (
            '`!extraowner add @user`\n'
            '`!extraowner remove @user`\n'
            '`!extraowner list`'
        ),
        'Add or remove ExtraOwners. ExtraOwners bypass all permission checks and can use every command.',
        '**Server owner only**',
        '`/extraowner`'
    ),
    (
        'giverole',
        '`!giverole @user warn.exe`',
        'Give a Lucky Bot permission role to a member. Follows hierarchy rules — you can only give roles below your own level.',
        '`role.giver.god` or higher',
        '`/giverole`'
    ),
    (
        'takerole',
        '`!takerole @user warn.exe`',
        'Remove a Lucky Bot permission role from a member.',
        '`role.giver.god` or higher',
        'No slash version'
    ),
    (
        'rolebind',
        (
            '`!rolebind list`\n'
            '`!rolebind warn.exe @role`\n'
            '`!rolebind warn reset`'
        ),
        'Reassign which Discord role has a Lucky Bot permission. Useful if you want your existing `Moderator` role to have `ban.exe` powers instead of a new role.',
        '**Owner / ExtraOwner only**',
        'No slash version'
    ),
]

# ══════════════════════════════════════════════
#   VIEWS — Dropdown navigation
# ══════════════════════════════════════════════

class HelpDropdown(discord.ui.Select):
    def __init__(self, bot, prefix):
        self.bot = bot
        self.prefix = prefix
        options = [
            discord.SelectOption(
                label='🏠 Main Menu',
                value='main',
                description='Back to the main help page'
            ),
            discord.SelectOption(
                label='🛡️ Moderation',
                value='mod',
                description='warn, mute, ban, kick, purge and more'
            ),
            discord.SelectOption(
                label='🔒 Security',
                value='security',
                description='Anti-nuke, anti-raid, anti-spam, anti-bot'
            ),
            discord.SelectOption(
                label='⚙️ Settings',
                value='settings',
                description='Prefix, roles, extraowner, setup'
            ),
            discord.SelectOption(
                label='🎫 Tickets',
                value='tickets',
                description='Coming soon!'
            ),
            discord.SelectOption(
                label='🎵 Music',
                value='music',
                description='Coming soon!'
            ),
            discord.SelectOption(
                label='😂 Fun',
                value='fun',
                description='Coming soon!'
            ),
            discord.SelectOption(
                label='💰 Economy',
                value='economy',
                description='Coming soon!'
            ),
            discord.SelectOption(
                label='⭐ Leveling',
                value='leveling',
                description='Coming soon!'
            ),
            discord.SelectOption(
                label='🎁 Giveaway',
                value='giveaway',
                description='Coming soon!'
            ),
        ]
        super().__init__(
            placeholder='📖 Select a category...',
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value == 'main':
            embed = build_main_embed(self.bot, self.prefix)
        elif value == 'mod':
            embed = build_mod_embed(self.prefix, page=1)
        elif value == 'settings':
            embed = build_settings_embed(self.prefix)
        elif value == 'security':
            embed = build_coming_soon('🔒 Security', 'antinuke, antiraid, antispam, antibot')
        else:
            section = SECTIONS.get(value, {})
            embed = build_coming_soon(
                f"{section.get('emoji','📦')} {section.get('name', value.title())}",
                section.get('description', '')
            )
        await interaction.response.edit_message(embed=embed, view=self.view)


class ModPageButtons(discord.ui.View):
    def __init__(self, bot, prefix, page, total_pages):
        super().__init__(timeout=120)
        self.bot = bot
        self.prefix = prefix
        self.page = page
        self.total_pages = total_pages

        # Add dropdown
        self.add_item(HelpDropdown(bot, prefix))

        # Previous button
        prev = discord.ui.Button(
            label='◀ Previous',
            style=discord.ButtonStyle.secondary,
            disabled=(page <= 1)
        )
        prev.callback = self.prev_callback
        self.add_item(prev)

        # Page counter
        counter = discord.ui.Button(
            label=f'Page {page}/{total_pages}',
            style=discord.ButtonStyle.primary,
            disabled=True
        )
        self.add_item(counter)

        # Next button
        nxt = discord.ui.Button(
            label='Next ▶',
            style=discord.ButtonStyle.secondary,
            disabled=(page >= total_pages)
        )
        nxt.callback = self.next_callback
        self.add_item(nxt)

    async def prev_callback(self, interaction: discord.Interaction):
        new_page = self.page - 1
        embed = build_mod_embed(self.prefix, new_page)
        view = ModPageButtons(self.bot, self.prefix, new_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=view)

    async def next_callback(self, interaction: discord.Interaction):
        new_page = self.page + 1
        embed = build_mod_embed(self.prefix, new_page)
        view = ModPageButtons(self.bot, self.prefix, new_page, self.total_pages)
        await interaction.response.edit_message(embed=embed, view=view)


class MainHelpView(discord.ui.View):
    def __init__(self, bot, prefix):
        super().__init__(timeout=120)
        self.add_item(HelpDropdown(bot, prefix))


# ══════════════════════════════════════════════
#   EMBED BUILDERS
# ══════════════════════════════════════════════

COMMANDS_PER_PAGE = 6

def build_main_embed(bot, prefix):
    embed = discord.Embed(
        title="🍀 Lucky Bot — Help Menu",
        description=(
            f"**Prefix:** `{prefix}` — also works with `/`\n\n"
            "Use the dropdown below to explore each section!\n"
            "Every command has both a prefix version and a `/` slash version."
        ),
        color=0x2ecc71,
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(
        name="🛡️ Moderation",
        value="warn, mute, ban, kick, purge, lock, snipe...",
        inline=True
    )
    embed.add_field(
        name="🔒 Security",
        value="antinuke, antiraid, antispam, antibot...",
        inline=True
    )
    embed.add_field(
        name="⚙️ Settings",
        value="setup, prefix, roles, extraowner...",
        inline=True
    )
    embed.add_field(
        name="🎫 Tickets",
        value="Coming soon!",
        inline=True
    )
    embed.add_field(
        name="🎵 Music",
        value="Coming soon!",
        inline=True
    )
    embed.add_field(
        name="😂 Fun",
        value="Coming soon!",
        inline=True
    )
    embed.add_field(
        name="💰 Economy",
        value="Coming soon!",
        inline=True
    )
    embed.add_field(
        name="⭐ Leveling",
        value="Coming soon!",
        inline=True
    )
    embed.add_field(
        name="🎁 Giveaway",
        value="Coming soon!",
        inline=True
    )
    embed.add_field(
        name="📊 Role Hierarchy",
        value=(
            "`ban.exe` → ban + kick + mute + warn\n"
            "`kick.exe` → kick + mute + warn\n"
            "`mute.exe` → mute + warn\n"
            "`warn.exe` → warn only"
        ),
        inline=False
    )
    embed.add_field(
        name="👑 Special",
        value=(
            "`god.bypass` → immune to all bot actions\n"
            "`role.giver.god` → can give/take Lucky Bot roles\n"
            "**ExtraOwner** → bypasses everything\n"
            "**Owner** → god tier"
        ),
        inline=False
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text="Lucky Bot • lucky.unaux.com • Use the dropdown to navigate")
    return embed


def build_mod_embed(prefix, page=1):
    total_pages = -(-len(MOD_COMMANDS) // COMMANDS_PER_PAGE)  # ceiling division
    start = (page - 1) * COMMANDS_PER_PAGE
    end = start + COMMANDS_PER_PAGE
    page_commands = MOD_COMMANDS[start:end]

    embed = discord.Embed(
        title=f"🛡️ Moderation Commands — Page {page}/{total_pages}",
        description=(
            f"All commands work with `{prefix}` prefix **and** `/` slash.\n"
            "Permissions shown are Lucky Bot roles, not Discord permissions."
        ),
        color=0xe74c3c,
        timestamp=datetime.datetime.utcnow()
    )

    for name, usage, desc, required, slash in page_commands:
        embed.add_field(
            name=f"• `{prefix}{name}`",
            value=(
                f"**Usage:** {usage}\n"
                f"**What it does:** {desc}\n"
                f"**Required role:** {required}\n"
                f"**Slash:** {slash}"
            ),
            inline=False
        )

    embed.set_footer(
        text=f"Page {page}/{total_pages} • {len(MOD_COMMANDS)} total commands • Use buttons to navigate"
    )
    return embed


def build_settings_embed(prefix):
    embed = discord.Embed(
        title="⚙️ Settings & Configuration",
        description=(
            f"All settings commands use `{prefix}` prefix or `/`.\n"
            "Most settings commands require special permissions."
        ),
        color=0x95a5a6,
        timestamp=datetime.datetime.utcnow()
    )
    for name, usage, desc, required, slash in SETTINGS_COMMANDS:
        embed.add_field(
            name=f"• `{prefix}{name}`",
            value=(
                f"**Usage:** {usage}\n"
                f"**What it does:** {desc}\n"
                f"**Required:** {required}\n"
                f"**Slash:** {slash}"
            ),
            inline=False
        )
    embed.set_footer(text="Lucky Bot Settings • Use the dropdown to navigate")
    return embed


def build_coming_soon(title, description):
    embed = discord.Embed(
        title=f"{title} — Coming Soon!",
        description=(
            f"{description}\n\n"
            "⚒️ This section is currently being built!\n"
            "Check back after the next update."
        ),
        color=0x95a5a6
    )
    embed.set_footer(text="Lucky Bot • Use the dropdown to navigate")
    return embed


# ══════════════════════════════════════════════
#   COG
# ══════════════════════════════════════════════

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_prefix(self, guild_id):
        return self.bot.custom_prefixes.get(guild_id, '!')

    # ── Prefix command ─────────────────────────
    @commands.command(name='help')
    async def help_prefix(self, ctx, section: str = None):
        """
        Lucky Bot help menu.
        Usage: !help
               !help mod
               !help settings
               !help security
        """
        prefix = self.get_prefix(ctx.guild.id if ctx.guild else None)

        if section is None:
            embed = build_main_embed(self.bot, prefix)
            view = MainHelpView(self.bot, prefix)
            await ctx.send(embed=embed, view=view)
            return

        section = section.lower()

        if section in ('mod', 'moderation'):
            embed = build_mod_embed(prefix, page=1)
            total_pages = -(-len(MOD_COMMANDS) // COMMANDS_PER_PAGE)
            view = ModPageButtons(self.bot, prefix, 1, total_pages)
            await ctx.send(embed=embed, view=view)

        elif section in ('settings', 'setting', 'config'):
            embed = build_settings_embed(prefix)
            view = MainHelpView(self.bot, prefix)
            await ctx.send(embed=embed, view=view)

        elif section in ('security', 'sec'):
            embed = build_coming_soon('🔒 Security', 'antinuke, antiraid, antispam, antibot')
            view = MainHelpView(self.bot, prefix)
            await ctx.send(embed=embed, view=view)

        else:
            section_data = SECTIONS.get(section, {})
            if section_data:
                embed = build_coming_soon(
                    f"{section_data['emoji']} {section_data['name']}",
                    section_data['description']
                )
            else:
                embed = discord.Embed(
                    title="❌ Unknown Section",
                    description=(
                        f"Section `{section}` not found!\n\n"
                        f"Available: `mod`, `security`, `settings`, "
                        f"`tickets`, `music`, `fun`, `economy`, `leveling`, `giveaway`"
                    ),
                    color=0xe74c3c
                )
            view = MainHelpView(self.bot, prefix)
            await ctx.send(embed=embed, view=view)

    # ── Slash command ──────────────────────────
    @app_commands.command(name='help', description='Show Lucky Bot help menu')
    @app_commands.describe(section='Category to view (leave empty for main menu)')
    @app_commands.choices(section=[
        app_commands.Choice(name='🛡️ Moderation', value='mod'),
        app_commands.Choice(name='🔒 Security', value='security'),
        app_commands.Choice(name='⚙️ Settings', value='settings'),
        app_commands.Choice(name='🎫 Tickets', value='tickets'),
        app_commands.Choice(name='🎵 Music', value='music'),
        app_commands.Choice(name='😂 Fun', value='fun'),
        app_commands.Choice(name='💰 Economy', value='economy'),
        app_commands.Choice(name='⭐ Leveling', value='leveling'),
        app_commands.Choice(name='🎁 Giveaway', value='giveaway'),
        app_commands.Choice(name='⚙️ Settings', value='settings'),
    ])
    async def help_slash(
        self,
        interaction: discord.Interaction,
        section: str = None
    ):
        prefix = self.get_prefix(interaction.guild.id if interaction.guild else None)

        if section is None:
            embed = build_main_embed(self.bot, prefix)
            view = MainHelpView(self.bot, prefix)
            await interaction.response.send_message(embed=embed, view=view)
            return

        if section == 'mod':
            embed = build_mod_embed(prefix, page=1)
            total_pages = -(-len(MOD_COMMANDS) // COMMANDS_PER_PAGE)
            view = ModPageButtons(self.bot, prefix, 1, total_pages)
            await interaction.response.send_message(embed=embed, view=view)

        elif section == 'settings':
            embed = build_settings_embed(prefix)
            view = MainHelpView(self.bot, prefix)
            await interaction.response.send_message(embed=embed, view=view)

        else:
            section_data = SECTIONS.get(section, {})
            embed = build_coming_soon(
                f"{section_data.get('emoji','📦')} {section_data.get('name', section.title())}",
                section_data.get('description', '')
            )
            view = MainHelpView(self.bot, prefix)
            await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Help(bot))
