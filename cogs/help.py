import discord
from discord import app_commands
from discord.ext import commands


# ──────────────────────────────────────────────
#  SECTION BUILDERS
# ──────────────────────────────────────────────

def build_main_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🍀 Lucky Bot — Help Center",
        description=(
            "Welcome to **Lucky Bot** — your all-in-one custom Discord bot!\n\n"
            "Use the **dropdown below** to explore every command category.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **Categories Available:**\n"
            "🛡️ Moderation · ⚙️ Settings · 🔧 Setup\n"
            "🤖 Bot Status · ℹ️ Basic / Info · 🔐 Security\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 Your current prefix: `{p}`\n"
            "All commands also work as `/` slash commands."
        ),
        color=discord.Color.green(),
    )
    embed.set_footer(text="Lucky Bot • Made with 🍀 by un.lucky_billi")
    return embed


def build_basic_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="ℹ️ Basic & Info Commands",
        description="General-purpose commands available to everyone.",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="📡 General Information",
        value=(
            f"`{p}ping` — Check bot latency and responsiveness\n"
            f"`{p}botinfo` — View bot stats (servers, members, ping, features)\n"
            f"`{p}serverinfo` — Full server information card\n"
            f"`{p}userinfo [@user]` — Complete member profile (warnings, level, notes, permissions)\n"
            f"`{p}find <n>` — Search members by name in the server"
        ),
        inline=False,
    )
    embed.add_field(
        name="💬 AFK (Away From Keyboard)",
        value=(
            f"`{p}afk [reason]` — Go AFK (auto-adds `[AFK]` to your nickname)\n"
            "↳ Bot auto-detects when you return & notifies who pinged you\n"
            "↳ Usage: `!afk gaming` or just `!afk` for no reason"
        ),
        inline=False,
    )
    embed.add_field(
        name="🕵️ Snipe (Message History)",
        value=(
            f"`{p}snipe` — Show the last deleted message in this channel\n"
            f"`{p}editsnipe` — Show before/after of the last edited message\n"
            "↳ Only works for messages deleted/edited after bot joined"
        ),
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • All commands also work as slash commands (/)")
    return embed


def build_moderation_page1(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ Moderation Commands — Page 1 / 4",
        description="Warning & Mute systems for member discipline.",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="⚠️ Warning System",
        value=(
            f"`{p}warn @user [reason]` — Warn a member (they get a DM, alert at 3+ warns)\n"
            f"`{p}warnings @user` — View all warnings for a member (with reasons)\n"
            f"`{p}unwarn @user <warn_id>` — Remove a specific warning by ID\n"
            f"`{p}clearwarn @user` — Remove ALL warnings for a member\n"
            "↳ Warnings are tracked per guild and help track member behavior"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔇 Mute / Timeout System",
        value=(
            f"`{p}mute @user [?t duration] [?r reason]` — Timeout a member\n"
            "↳ Duration examples: `30m`, `2h`, `1d`, `7d` (max 28 days)\n"
            "↳ Full example: `!mute @user ?t 1h ?r spamming`\n"
            f"`{p}unmute @user` — Remove timeout from a member immediately\n"
            "↳ Uses Discord's native timeout — no special role setup needed"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔑 Required Permissions",
        value="`mute.exe` or higher (`kick.exe`, `ban.exe`), ExtraOwner, or Server Owner",
        inline=False,
    )
    embed.set_footer(text="Page 1/4 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_moderation_page2(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ Moderation Commands — Page 2 / 4",
        description="Kick, Ban & Channel management tools.",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="👢 Kick System",
        value=(
            f"`{p}kick @user [reason]` — Kick a member from server (they get a DM)\n"
            f"`{p}kick @user ?r rule breaking` — Kick with reason\n"
            "↳ Required role: `kick.exe` or higher"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔨 Ban System",
        value=(
            f"`{p}ban @user [reason]` — Permanently ban a member\n"
            f"`{p}unban <user#tag or ID>` — Unban a user (shows picker if multiple matches)\n"
            f"`{p}tempban @user <duration> [reason]` — Temp ban (auto-unbans after time)\n"
            f"`{p}massban` — Ban multiple users (requires enable toggle for safety)\n"
            "↳ Required role: `ban.exe` or higher"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔒 Channel Tools",
        value=(
            f"`{p}purge <amount> [@user]` — Delete up to 100 messages (can target specific user)\n"
            f"`{p}lock [#channel]` — Lock a channel (no one can send messages)\n"
            f"`{p}unlock [#channel]` — Unlock a channel\n"
            f"`{p}slowmode <seconds>` — Set slowmode (0 to disable)\n"
            "↳ `purge` needs `purge.exe` · `lock/unlock/slowmode` need `lock.exe`"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 2/4 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_moderation_page3(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ Moderation Commands — Page 3 / 4",
        description="Member tools, Announcements & Notes.",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="✏️ Nickname Tools",
        value=(
            f"`{p}nick @user <new_name>` — Change a member's nickname\n"
            f"`{p}resetnick @user` — Reset nickname back to account name\n"
            "↳ Required role: `nick.exe`"
        ),
        inline=False,
    )
    embed.add_field(
        name="📢 Announcement Tools",
        value=(
            f"`{p}announce [Title |] Message` — Send announcement embed\n"
            "↳ Use `|` to separate title: `!announce Event | It's time!`\n"
            f"`{p}poll <question>` — Post a poll (auto-reacts ✅ ❌)\n"
            "↳ Required role: `announce.exe`"
        ),
        inline=False,
    )
    embed.add_field(
        name="📝 Private Note System",
        value=(
            f"`{p}note add @user <note>` — Add secret mod note (saved & private)\n"
            f"`{p}notes @user` — View all notes for a member\n"
            f"`{p}clearnotes @user` — Clear all notes for a member\n"
            "↳ Notes are private to staff, sent via DM, command auto-deletes"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎭 Lucky Bot Role Management",
        value=(
            f"`{p}giverole @user <role>` — Give a Lucky Bot permission role\n"
            f"`{p}takerole @user <role>` — Remove a Lucky Bot permission role\n"
            "↳ Required role: `role.giver.god` (can only give roles below your level)"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 3/4 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_moderation_page4(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ Moderation Commands — Page 4 / 4",
        description="ExtraOwner system & Advanced controls.",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="👑 ExtraOwner System (Server Owner Only)",
        value=(
            f"`{p}extraowner add @user` — Grant god-tier access to trusted user\n"
            f"`{p}extraowner remove @user` — Revoke god-tier access\n"
            f"`{p}extraowner list` — View all ExtraOwners\n"
            "↳ ExtraOwners are immune to all bot actions & have full authority"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔓 Permissions Explained",
        value=(
            "**Hierarchy (each includes lower):**\n"
            "`ban.exe` (4) → can ban, kick, mute, warn\n"
            "`kick.exe` (3) → can kick, mute, warn\n"
            "`mute.exe` (2) → can mute & warn\n"
            "`warn.exe` (1) → can warn only\n\n"
            "**Independent Roles (no hierarchy):**\n"
            "`purge.exe`, `lock.exe`, `nick.exe`, `announce.exe`, `role.giver.god`"
        ),
        inline=False,
    )
    embed.add_field(
        name="⚙️ Moderation Settings",
        value=(
            f"`{p}viewperm @user` — See all permissions of a member\n"
            f"`{p}rolebind` — View/manage role permission bindings\n"
            f"`{p}clarlogs [@user]` — Clear mod action logs (admin only)"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 4/4 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_security_page1(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🔐 Security Commands — Page 1 / 3",
        description="Protection against raids, nukes & malicious activity.",
        color=discord.Color.dark_red(),
    )
    embed.add_field(
        name="🛡️ AntiNuke System",
        value=(
            f"`{p}antinuke` — Show AntiNuke settings & status\n"
            f"`{p}antinuke enable` — Enable AntiNuke protection\n"
            f"`{p}antinuke disable` — Disable AntiNuke protection\n"
            "↳ Prevents: bans, kicks, channel/role/webhook deletion, @everyone, emoji/sticker damage"
        ),
        inline=False,
    )
    embed.add_field(
        name="🚨 AntiRaid System",
        value=(
            f"`{p}antiraid` — Show AntiRaid settings\n"
            f"`{p}antiraid enable` — Enable AntiRaid (blocks mass-joins)\n"
            f"`{p}antiraid disable` — Disable AntiRaid\n"
            "↳ Prevents: sudden mass-joins, brand new accounts, accounts without avatars"
        ),
        inline=False,
    )
    embed.add_field(
        name="⚡ Quick Actions",
        value=(
            f"`{p}panic` — EMERGENCY: locks server, enables all protections\n"
            f"`{p}recover` — Exit panic mode, return to normal\n"
            "↳ Use during active raid/attack (Server Owner only)"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 1/3 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_security_page2(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🔐 Security Commands — Page 2 / 3",
        description="Fine-tuning AntiNuke & AntiRaid protection.",
        color=discord.Color.dark_red(),
    )
    embed.add_field(
        name="🔧 AntiNuke Configuration",
        value=(
            f"`{p}antinuke setlog #channel` — Set where AntiNuke alerts go\n"
            f"`{p}antinuke setpunish <ban|kick|mute>` — Choose punishment type\n"
            f"`{p}antinuke whitelist add @user` — Exempt user from AntiNuke\n"
            f"`{p}antinuke whitelist remove @user` — Remove whitelist exemption\n"
            f"`{p}antinuke toggles` — Enable/disable specific protections"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔧 AntiRaid Configuration",
        value=(
            f"`{p}antiraid setlog #channel` — Set where AntiRaid alerts go\n"
            f"`{p}antiraid setpunish <ban|kick|mute>` — Choose punishment\n"
            f"`{p}antiraid joinspeed <number> <seconds>` — Set join threshold\n"
            f"`{p}antiraid minage <days>` — Require minimum account age\n"
            f"`{p}antiraid whitelist add @user` — Exempt from AntiRaid"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 2/3 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_security_page3(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🔐 Security Commands — Page 3 / 3",
        description="Monitoring & Advanced security features.",
        color=discord.Color.dark_red(),
    )
    embed.add_field(
        name="📊 Security Status & Logs",
        value=(
            f"`{p}secstatus` — Show all security features & their status\n"
            f"`{p}seclogs` — View recent security actions\n"
            f"`{p}secstats` — Show statistics (blocks, punishments, threats)"
        ),
        inline=False,
    )
    embed.add_field(
        name="⚠️ What Gets Protected",
        value=(
            "**AntiNuke stops:**\n"
            "• Mass bans/kicks • Channel deletion • Role deletion • Webhook spam\n"
            "• @everyone mentions • Emoji/sticker removal • Bot adds\n\n"
            "**AntiRaid stops:**\n"
            "• 10+ joins in 10 seconds • Brand new accounts • No-avatar accounts\n"
            "• Suspicious bot accounts • Auto-locks during raids"
        ),
        inline=False,
    )
    embed.add_field(
        name="📝 Note",
        value="Security features require setup — run `/setup` for guided auto-configuration.",
        inline=False,
    )
    embed.set_footer(text="Page 3/3 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_settings_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="⚙️ Settings & Configuration",
        description="Control how Lucky Bot behaves in your server.",
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="🔤 Prefix Settings (Server Owner Only)",
        value=(
            f"`{p}setprefix <symbol>` — Change command prefix (e.g., `?`, `$`, `!!`)\n"
            f"`{p}setprefix reset` — Reset to default prefix `!`\n"
            f"`{p}prefix` — View current server prefix"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎯 Role Binding (Advanced)",
        value=(
            f"`{p}rolebind` — View current role permission mappings\n"
            f"`{p}rolebind <permission> <@role>` — Map custom role to permission\n"
            "↳ Customize which Discord roles unlock Lucky Bot permissions"
        ),
        inline=False,
    )
    embed.add_field(
        name="📋 Logging & Audit",
        value=(
            f"`{p}clearlogs [@user]` — Clear mod action logs\n"
            f"`{p}viewlogs [@user]` — View moderation history\n"
            "↳ Logs track all warnings, mutes, kicks, bans, and role changes"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎭 Note",
        value="Most settings are managed by **Server Owner** only for security.",
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • All commands also work as slash commands (/)")
    return embed


def build_setup_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🔧 Setup & Installation",
        description="Auto-create roles, channels, and initial configuration.",
        color=discord.Color.teal(),
    )
    embed.add_field(
        name="⚡ Quick Setup (Server Owner Only)",
        value=(
            f"`{p}setup` — Show setup menu\n"
            f"`{p}setup all` — Create EVERYTHING (roles + all log channels)\n"
            f"`{p}setup basic` — Create only permission roles\n"
            f"`{p}setup moderation` — Create mod roles + mod-logs\n"
            f"`{p}setup security` — Create security logs + antinuke/raid info"
        ),
        inline=False,
    )
    embed.add_field(
        name="📂 Channel Setup Options",
        value=(
            f"`{p}setup tickets` — Create ticket system channels\n"
            f"`{p}setup welcome` — Create welcome/goodbye channels\n"
            f"`{p}setup economy` — Create economy logs\n"
            f"`{p}setup leveling` — Create leveling logs\n"
            f"`{p}setup giveaway` — Create giveaway logs\n"
            f"`{p}setup music` — Create music logs"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔗 Channel Binding (Advanced)",
        value=(
            f"`{p}channelbind` — Show all channel bindings\n"
            f"`{p}channelbind <key> #channel` — Move a log/feature to different channel\n"
            f"`{p}channelbind reset <key>` — Reset one channel to default\n"
            f"`{p}channelbind reset all` — Reset all channels\n"
            "↳ Examples: `!channelbind mod-logs #logs` or `!channelbind welcome #introductions`"
        ),
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • Setup creates organized role & channel structure")
    return embed


def build_botstatus_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🤖 Bot Status & Presence",
        description="Control how Lucky Bot appears in your server.",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="📊 Bot Status (Bot Owner Only)",
        value=(
            f"`{p}setstatus <online|idle|dnd|invisible>` — Change bot status\n"
            "↳ `online` = active, `idle` = away, `dnd` = do not disturb, `invisible` = hidden"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎭 Bot Activity (Bot Owner Only)",
        value=(
            f"`{p}setactivity <type> <text>` — Set what bot is doing\n"
            "↳ Types: `playing`, `watching`, `listening`, `competing`, `none`\n"
            f"↳ Examples: `!setactivity playing with 🍀` or `!setactivity watching the server`"
        ),
        inline=False,
    )
    embed.add_field(
        name="📋 Bot Information",
        value=(
            f"`{p}botstatus` — View current bot status and activity\n"
            f"`{p}botinfo` — View bot statistics and features"
        ),
        inline=False,
    )
    embed.add_field(
        name="📝 Note",
        value="Only the **Bot Owner** can change bot status & activity to prevent misuse.",
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • Made with 🍀 by un.lucky_billi")
    return embed


def build_serverowner_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="👑 Server Owner Commands",
        description="Commands exclusively for the Server Owner — full server control.",
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="🔐 Server Owner Exclusive Access",
        value=(
            "**You have exclusive access to these commands:**\n\n"
            f"`{p}setprefix <symbol>` — Change command prefix globally\n"
            f"`{p}extraowner add @user` — Grant god-tier access to trusted member\n"
            f"`{p}extraowner remove @user` — Remove god-tier access\n"
            f"`{p}extraowner list` — View all ExtraOwners\n"
            f"`{p}setup <type>` — Auto-create roles, channels, log system\n"
            f"`{p}channelbind <key> #channel` — Reassign log/feature channels\n"
            f"`{p}panic` — EMERGENCY: Lock server + enable all protections\n"
            f"`{p}recover` — Exit emergency mode"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎯 Why These Are Server Owner Only",
        value=(
            "Server Owner has ultimate authority to:\n"
            "• Change how bot works in your server\n"
            "• Delegate authority to ExtraOwners\n"
            "• Create organized role & channel structure\n"
            "• Respond to emergencies quickly\n\n"
            "This ensures bad actors can't hijack your bot."
        ),
        inline=False,
    )
    embed.add_field(
        name="💡 Pro Tip",
        value=(
            f"Start with `{p}setup all` to auto-create everything.\n"
            "Then use `{p}extraowner add @trusted` to delegate management."
        ),
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • You have ultimate authority in this server")
    return embed


def build_botowner_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🔑 Bot Owner Commands",
        description="Commands exclusively for the Bot Creator — global bot control.",
        color=discord.Color.dark_gold(),
    )
    embed.add_field(
        name="🤖 Bot Owner Exclusive Access",
        value=(
            "**Only the Bot Owner can use these:**\n\n"
            f"`{p}setstatus <online|idle|dnd|invisible>` — Global bot status\n"
            f"`{p}setactivity <type> <text>` — Global bot activity/presence\n"
            f"`{p}noprefix add @user` — Allow user to run commands without prefix\n"
            f"`{p}noprefix remove @user` — Revoke no-prefix access\n"
            "↳ These prevent misuse by keeping control at bot creator level"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔑 Why Bot Owner Only",
        value=(
            "Bot Owner has global authority to:\n"
            "• Control bot presence across all servers\n"
            "• Grant special no-prefix access (experimental)\n"
            "• Prevent servers from changing core behavior\n"
            "• Manage bot-wide security policies\n\n"
            "This protects your bot from being hijacked by other servers."
        ),
        inline=False,
    )
    embed.add_field(
        name="📝 Note",
        value="This section is **only visible to the Bot Owner**. Other users cannot see these commands.",
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • You have ultimate global authority")
    return embed


def build_coming_soon_embed(section: str) -> discord.Embed:
    icons = {
        "automod": "🤖",
        "welcome": "👋",
        "tickets": "🎫",
        "fun":     "🎉",
        "economy": "💰",
        "leveling":"📈",
        "giveaway":"🎁",
        "music":   "🎵",
    }
    icon = icons.get(section, "🚧")
    embed = discord.Embed(
        title=f"{icon} {section.title()} — Coming Soon",
        description=(
            f"The **{section.title()}** module is currently under construction.\n\n"
            "🍀 Lucky Bot is actively being developed — check back soon!\n\n"
            "Planned features for this module will appear here once built."
        ),
        color=discord.Color.orange(),
    )
    embed.set_footer(text="Lucky Bot • Made with 🍀 by un.lucky_billi")
    return embed


# ──────────────────────────────────────────────
#  PAGE LISTS
# ──────────────────────────────────────────────

MOD_PAGES = [
    build_moderation_page1,
    build_moderation_page2,
    build_moderation_page3,
    build_moderation_page4,
]

SECURITY_PAGES = [
    build_security_page1,
    build_security_page2,
    build_security_page3,
]


# ──────────────────────────────────────────────
#  VIEWS — DROPDOWN + PAGINATION
# ──────────────────────────────────────────────

class HelpDropdown(discord.ui.Select):
    def __init__(self, p: str, is_bot_owner: bool = False):
        self.p = p
        self.is_bot_owner = is_bot_owner
        
        options = [
            discord.SelectOption(label="🏠 Home",         value="home",       description="Main help overview"),
            discord.SelectOption(label="ℹ️ Basic & Info", value="basic",      description="Ping, userinfo, serverinfo, AFK, snipe"),
            discord.SelectOption(label="🛡️ Moderation",  value="mod",        description="Warn, mute, kick, ban, purge & more"),
            discord.SelectOption(label="🔐 Security",     value="security",   description="Antinuke, antiraid, panic & recovery"),
            discord.SelectOption(label="⚙️ Settings",     value="settings",   description="Prefix, rolebind, clearlogs"),
            discord.SelectOption(label="🔧 Setup",        value="setup",      description="Auto-setup roles & channels"),
            discord.SelectOption(label="🤖 Bot Status",   value="botstatus",  description="Status, activity, bot name"),
            discord.SelectOption(label="👑 Server Owner", value="serverowner", description="Server Owner exclusive commands"),
        ]
        
        # Only show Bot Owner section if user is bot owner
        if is_bot_owner:
            options.append(
                discord.SelectOption(label="🔑 Bot Owner Only", value="botowner", description="Bot Creator exclusive commands")
            )
        
        # Add coming soon sections
        options.extend([
            discord.SelectOption(label="🚫 AutoMod",      value="automod",   description="Auto moderation (coming soon)"),
            discord.SelectOption(label="👋 Welcome",      value="welcome",   description="Welcome messages (coming soon)"),
            discord.SelectOption(label="🎫 Tickets",      value="tickets",   description="Ticket system (coming soon)"),
            discord.SelectOption(label="🎉 Fun",          value="fun",       description="Games & fun commands (coming soon)"),
            discord.SelectOption(label="💰 Economy",      value="economy",   description="Coins & shop (coming soon)"),
            discord.SelectOption(label="📈 Leveling",     value="leveling",  description="XP & rank system (coming soon)"),
            discord.SelectOption(label="🎁 Giveaway",     value="giveaway",  description="Giveaway system (coming soon)"),
            discord.SelectOption(label="🎵 Music",        value="music",     description="Music player (coming soon)"),
        ])
        
        super().__init__(placeholder="📂 Select a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "home":
            await interaction.response.edit_message(embed=build_main_embed(self.p), view=self.view)
        elif val == "basic":
            await interaction.response.edit_message(embed=build_basic_embed(self.p), view=self.view)
        elif val == "mod":
            view = ModPaginatedView(self.p)
            await interaction.response.edit_message(embed=build_moderation_page1(self.p), view=view)
        elif val == "security":
            view = SecurityPaginatedView(self.p)
            await interaction.response.edit_message(embed=build_security_page1(self.p), view=view)
        elif val == "settings":
            await interaction.response.edit_message(embed=build_settings_embed(self.p), view=self.view)
        elif val == "setup":
            await interaction.response.edit_message(embed=build_setup_embed(self.p), view=self.view)
        elif val == "botstatus":
            await interaction.response.edit_message(embed=build_botstatus_embed(self.p), view=self.view)
        elif val == "serverowner":
            await interaction.response.edit_message(embed=build_serverowner_embed(self.p), view=self.view)
        elif val == "botowner":
            # Double-check bot owner before showing
            if self.is_bot_owner:
                await interaction.response.edit_message(embed=build_botowner_embed(self.p), view=self.view)
            else:
                await interaction.response.send_message(
                    embed=discord.Embed(title="❌ Unauthorized", description="Only the Bot Owner can view this.", color=discord.Color.red()),
                    ephemeral=True
                )
        else:
            await interaction.response.edit_message(embed=build_coming_soon_embed(val), view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, p: str, is_bot_owner: bool = False):
        super().__init__(timeout=120)
        self.add_item(HelpDropdown(p, is_bot_owner))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ──────────────────────────────────────────────
#  SHARED PAGINATOR BASE
# ──────────────────────────────────────────────

class PaginatedView(discord.ui.View):
    """Generic paginator — subclass and set self.pages."""

    def __init__(self, p: str, pages: list, page: int = 0):
        super().__init__(timeout=120)
        self.p = p
        self.pages = pages
        self.page = page
        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page == len(self.pages) - 1
        self.page_label.label = f"Page {self.page + 1} / {len(self.pages)}"

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page](self.p), view=self)

    @discord.ui.button(label="Page 1 / ?", style=discord.ButtonStyle.primary, disabled=True)
    async def page_label(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page](self.p), view=self)

    @discord.ui.button(label="🏠 Back to Menu", style=discord.ButtonStyle.success)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = HelpView(self.p)
        await interaction.response.edit_message(embed=build_main_embed(self.p), view=view)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class ModPaginatedView(PaginatedView):
    def __init__(self, p: str, page: int = 0):
        super().__init__(p, MOD_PAGES, page)


class SecurityPaginatedView(PaginatedView):
    def __init__(self, p: str, page: int = 0):
        super().__init__(p, SECURITY_PAGES, page)


# ──────────────────────────────────────────────
#  COG
# ──────────────────────────────────────────────

class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _prefix(self, guild: discord.Guild | None) -> str:
        if guild is None:
            return self.bot.DEFAULT_PREFIX
        return self.bot.custom_prefixes.get(guild.id, self.bot.DEFAULT_PREFIX)

    def _is_bot_owner(self, user_id: int) -> bool:
        return user_id == self.bot.BOT_OWNER_ID

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        p = self._prefix(ctx.guild)
        is_bot_owner = self._is_bot_owner(ctx.author.id)
        view = HelpView(p, is_bot_owner)
        await ctx.reply(embed=build_main_embed(p), view=view)

    @app_commands.command(name="help", description="Open the Lucky Bot help menu")
    async def help_slash(self, interaction: discord.Interaction):
        p = self._prefix(interaction.guild)
        is_bot_owner = self._is_bot_owner(interaction.user.id)
        view = HelpView(p, is_bot_owner)
        await interaction.response.send_message(embed=build_main_embed(p), view=view)

    @commands.command(name="ping")
    async def ping_prefix(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: `{round(self.bot.latency * 1000)}ms`",
            color=discord.Color.green(),
        )
        await ctx.reply(embed=embed)

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: `{round(self.bot.latency * 1000)}ms`",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
