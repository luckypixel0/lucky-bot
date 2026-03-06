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
        name="📡 General",
        value=(
            f"`{p}ping` — Check bot latency\n"
            f"`{p}botinfo` — Bot stats (servers, members, ping, features)\n"
            f"`{p}serverinfo` — Full server info card\n"
            f"`{p}userinfo [@user]` — Full profile (warnings, notes, mod level)\n"
            f"`{p}find <name>` — Search members by name"
        ),
        inline=False,
    )
    embed.add_field(
        name="💬 AFK",
        value=(
            f"`{p}afk [reason]` — Go AFK (adds `[AFK]` to nickname)\n"
            "↳ Bot auto-detects when you return & notifies anyone who pinged you"
        ),
        inline=False,
    )
    embed.add_field(
        name="🕵️ Snipe",
        value=(
            f"`{p}snipe` — Show last deleted message in this channel\n"
            f"`{p}editsnipe` — Show before/after of last edited message"
        ),
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • All commands also work as slash commands (/)")
    return embed


def build_moderation_page1(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ Moderation Commands — Page 1 / 4",
        description="Warning & Mute systems.",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="⚠️ Warning System",
        value=(
            f"`{p}warn @user [reason]` — Warn a member (DM sent, alert at 3+ warns)\n"
            f"`{p}warnings @user` — View all warnings for a member\n"
            f"`{p}unwarn @user <warn_id>` — Remove a specific warning\n"
            f"`{p}clearwarn @user` — Clear ALL warnings for a member"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔇 Mute System",
        value=(
            f"`{p}mute @user [?t duration] [?r reason]` — Timeout a member\n"
            "↳ Duration examples: `30m`, `2h`, `1d` (max 28 days)\n"
            "↳ Example: `!mute @user ?t 1h ?r spamming`\n"
            f"`{p}unmute @user` — Remove timeout from a member\n"
            "↳ Uses Discord's native timeout — no role needed"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔑 Required Roles",
        value="`mute.exe` or higher (`kick.exe`, `ban.exe`), ExtraOwner, Server Owner",
        inline=False,
    )
    embed.set_footer(text="Page 1/4 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_moderation_page2(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ Moderation Commands — Page 2 / 4",
        description="Kick, Ban & Channel tools.",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="👢 Kick System",
        value=(
            f"`{p}kick @user [reason]` — Kick a member (DM sent)\n"
            "↳ Required: `kick.exe` or higher"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔨 Ban System",
        value=(
            f"`{p}ban @user [reason]` — Permanently ban a member\n"
            f"`{p}unban <user#tag or ID>` — Unban (multi-match picker if needed)\n"
            f"`{p}tempban @user <duration> [reason]` — Temp ban (auto-unbans)\n"
            f"`{p}massban` — Ban multiple users (requires enable toggle for safety)\n"
            "↳ Required: `ban.exe` or higher"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔒 Channel Tools",
        value=(
            f"`{p}purge <amount> [@user]` — Delete up to 100 messages (optional: target user)\n"
            f"`{p}lock [#channel]` — Lock a channel (no one can send)\n"
            f"`{p}unlock [#channel]` — Unlock a channel\n"
            f"`{p}slowmode <seconds>` — Set slowmode (0 to disable)\n"
            "↳ `purge` requires `purge.exe` · `lock/unlock/slowmode` requires `lock.exe`"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 2/4 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_moderation_page3(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ Moderation Commands — Page 3 / 4",
        description="Nicknames, Announcements, Notes & Roles.",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="✏️ Nickname Tools",
        value=(
            f"`{p}nick @user <new_name>` — Change a member's nickname\n"
            f"`{p}resetnick @user` — Reset nickname to account name\n"
            "↳ Required: `nick.exe`"
        ),
        inline=False,
    )
    embed.add_field(
        name="📢 Announcement Tools",
        value=(
            f"`{p}announce [Title |] Message` — Send announcement embed\n"
            "↳ Use `|` to separate title from body: `!announce Event | It's time!`\n"
            f"`{p}poll <question>` — Post a poll (auto-reacts ✅ ❌)\n"
            "↳ Required: `announce.exe`"
        ),
        inline=False,
    )
    embed.add_field(
        name="📝 Note System",
        value=(
            f"`{p}note add @user <note>` — Add private mod note (sent via DM, cmd auto-deleted)\n"
            f"`{p}notes @user` — View all notes for a member\n"
            f"`{p}clearnotes @user` — Clear all notes for a member"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎭 Role Management",
        value=(
            f"`{p}giverole @user <role>` — Give a Lucky Bot permission role\n"
            f"`{p}takerole @user <role>` — Remove a Lucky Bot permission role\n"
            "↳ Required: `role.giver.god` (can only give roles below your own level)"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 3/4 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_moderation_page4(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ Moderation Commands — Page 4 / 4",
        description="ExtraOwner system & Server Protection.",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="👑 ExtraOwner System",
        value=(
            f"`{p}extraowner add @user` — Grant god-tier access (server owner only)\n"
            f"`{p}extraowner remove @user` — Revoke god-tier access\n"
            f"`{p}extraowner list` — List all ExtraOwners\n"
            "↳ ExtraOwners are immune to all bot actions"
        ),
        inline=False,
    )
    embed.add_field(
        name="🛡️ Server Protection (Auto)",
        value=(
            "Lucky Bot **automatically watches** your server:\n"
            "• If anyone not god-tier changes server **name / icon / description / banner**\n"
            "  → They are **auto-muted for 2 minutes** and logged in `#security-logs`\n"
            "↳ No command needed — always active once antinuke is enabled"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔐 Permission Hierarchy",
        value=(
            "`ban.exe` ▸ Level 4 — Ban + kick + mute + warn\n"
            "`kick.exe` ▸ Level 3 — Kick + mute + warn\n"
            "`mute.exe` ▸ Level 2 — Mute + warn\n"
            "`warn.exe` ▸ Level 1 — Warn only\n"
            "━━━━━━━━━━━━\n"
            "`purge.exe` · `lock.exe` · `nick.exe` · `announce.exe`\n"
            "`audit.viewer` · `role.giver.god` · `god.bypass`"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 4/4 — Use ◀ ▶ to navigate • Lucky Bot")
    return embed


def build_settings_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="⚙️ Settings Commands",
        description="Prefix, no-prefix, and role binding settings.",
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="🔤 Prefix Settings",
        value=(
            f"`{p}prefix` — Show current server prefix\n"
            f"`{p}setprefix <new>` — Change server prefix (max 5 chars) — Server Owner only\n"
            f"`{p}setprefix reset` — Reset prefix back to default `!`\n"
            f"`{p}noprefix @user` — Toggle no-prefix access for a user — Bot Owner only\n"
            "↳ No-prefix users can run commands with no prefix at all (e.g. just type `warn @user`)"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔗 Role Binding",
        value=(
            f"`{p}rolebind <permission> <role name>` — Map an existing role to a Lucky Bot permission\n"
            "↳ Example: `!rolebind ban Moderator` — your 'Moderator' role now has ban powers\n"
            f"`{p}rolebind <permission> reset` — Reset that permission back to default Lucky Bot role\n\n"
            "**Available permissions to bind:**\n"
            "`ban` · `kick` · `mute` · `warn` · `purge` · `lock` · `nick` · `announce`\n"
            "`audit` · `rolegiver` · `godbypass`"
        ),
        inline=False,
    )
    embed.add_field(
        name="📋 Logs Management",
        value=(
            f"`{p}clearlogs <channel|all>` — Clear a log channel or all 8 at once\n"
            "↳ Always asks for confirmation before clearing\n"
            "↳ Required: Server Owner or ExtraOwner"
        ),
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • Settings — Server Owner / Bot Owner only")
    return embed


def build_setup_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🔧 Setup Commands",
        description=(
            "Run `!setup` once and Lucky Bot builds **everything** for your server automatically.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.teal(),
    )
    embed.add_field(
        name="🚀 Auto Setup",
        value=(
            f"`{p}setup` — Show the full setup menu\n"
            f"`{p}setup all` — Creates ALL roles, ALL log channels, welcome + rules channels\n"
            f"`{p}setup basic` — Permission roles only\n"
            f"`{p}setup moderation` — Mod roles + `#mod-logs`\n"
            f"`{p}setup security` — `#security-logs` channel + security guide\n"
            f"`{p}setup welcome` · `{p}setup tickets` · `{p}setup economy`\n"
            f"`{p}setup leveling` · `{p}setup giveaway` · `{p}setup music`\n"
            "↳ Server Owner or ExtraOwner only · Safe to re-run — skips existing"
        ),
        inline=False,
    )
    embed.add_field(
        name="📁 Roles Created Automatically",
        value=(
            "**Permission Hierarchy (stackable):**\n"
            "`ban.exe` · `kick.exe` · `mute.exe` · `warn.exe`\n\n"
            "**Independent Permission Roles:**\n"
            "`purge.exe` · `lock.exe` · `nick.exe` · `announce.exe`\n"
            "`audit.viewer` · `role.giver.god` · `god.bypass`"
        ),
        inline=False,
    )
    embed.add_field(
        name="📋 Log Channels Created Automatically",
        value=(
            "All inside a `📋 Logs` category — invisible to normal members:\n"
            "`#mod-logs` · `#security-logs` · `#ticket-logs` · `#music-logs`\n"
            "`#economy-logs` · `#leveling-logs` · `#giveaway-logs` · `#server-logs`"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔄 Want to use your OWN roles instead?",
        value=(
            "After setup, use **rolebind** to link your existing roles:\n"
            f"`{p}rolebind <permission> <your role name>`\n\n"
            f"→ `{p}rolebind ban Moderator` — your 'Moderator' role gets ban powers\n"
            f"→ `{p}rolebind ban reset` — go back to Lucky Bot defaults\n\n"
            "**Want to use your OWN channels instead?**\n"
            f"`{p}channelbind <key> #channel` — point any feature at your own channel\n"
            f"`{p}channelbind list` — see all current channel assignments"
        ),
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • Setup — Server Owner only")
    return embed


def build_botstatus_embed(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🤖 Bot Status Commands",
        description="Control how Lucky Bot appears on Discord. **Bot Owner only.**",
        color=discord.Color.purple(),
    )
    embed.add_field(
        name="🟢 Status",
        value=(
            f"`{p}setstatus <online|idle|dnd|invisible>` — Change bot's online status\n"
            f"`{p}resetstatus` — Reset to default (watching over the server)\n"
            f"`{p}botstatus` — View all current bot appearance settings"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎮 Activity",
        value=(
            f"`{p}setactivity <type> [text]` — Set bot's activity\n"
            "↳ Types: `playing` · `watching` · `listening` · `competing` · `streaming` · `none`\n"
            "↳ Example: `!setactivity watching over 5 servers`\n"
            "⚠️ Note: Discord **blocks custom status for bots** — only above types work"
        ),
        inline=False,
    )
    embed.add_field(
        name="✏️ Name",
        value=(
            f"`{p}setbotname <new name>` — Change the bot's username\n"
            "⚠️ Discord allows max **2 name changes per hour**"
        ),
        inline=False,
    )
    embed.set_footer(text="Lucky Bot • Bot Owner only")
    return embed


# ──────────────────────────────────────────────
#  SECURITY PAGES  (3 pages)
# ──────────────────────────────────────────────

def build_security_page1(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🔐 Security — Page 1 / 3",
        description=(
            "**Lucky Bot has the most advanced security system of any bot.**\n"
            "Antinuke protects against destructive actions by rogue staff or compromised accounts.\n\n"
            "🔑 **Required:** Server Owner, ExtraOwner, or Bot Owner only."
        ),
        color=discord.Color.dark_red(),
    )
    embed.add_field(
        name="🛡️ Overview & Setup",
        value=(
            f"`{p}security` — Full security overview for this server\n"
            f"`{p}antinuke` — Show antinuke status + all module toggles\n"
            f"`{p}antinuke wizard` — 🧙 Interactive 4-step setup wizard\n"
            f"`{p}antinuke setup` — Quick-enable with safe defaults\n"
            f"`{p}antinuke on` / `{p}antinuke off` — Enable / disable antinuke\n"
            f"`{p}antinuke disable` — Disable + clear all config\n"
            f"`{p}antinuke reset` — Reset all settings and stats to defaults\n"
            f"`{p}antinuke settings` — View all thresholds and detailed config"
        ),
        inline=False,
    )
    embed.add_field(
        name="⚙️ Punishment & Whitelist",
        value=(
            f"`{p}antinuke punish <action>` — Set what happens to violators\n"
            "↳ Options: `ban` · `kick` · `mute` · `strip` · `derank`\n"
            f"`{p}antinuke whitelist @user` — Exempt a user from all antinuke\n"
            f"`{p}antinuke unwhitelist @user` — Remove a user's exemption\n"
            f"`{p}antinuke whitelistlist` — Show all whitelisted users\n"
            f"`{p}antinuke threshold <action> <n>` — Set how many actions in 10s triggers protection\n"
            f"`{p}antinuke logchannel #channel` — Set where security alerts are sent"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 1/3 — Use ◀ ▶ to navigate • Lucky Bot Security")
    return embed


def build_security_page2(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🔐 Security — Page 2 / 3",
        description="Individual module toggle commands. Use `on` or `off` after each.",
        color=discord.Color.dark_red(),
    )
    embed.add_field(
        name="🔨 Antinuke Modules — Ban / Kick / Role / Channel",
        value=(
            f"`{p}antinuke antiban <on/off>` — Stop mass bans (threshold: 2 bans/10s)\n"
            f"`{p}antinuke antikick <on/off>` — Stop mass kicks (threshold: 3/10s)\n"
            f"`{p}antinuke antirole <on/off>` — Stop mass role deletion + dangerous perm grants\n"
            "↳ Auto-reverts if admin/dangerous perms are added to a role\n"
            f"`{p}antinuke antichannel <on/off>` — Stop mass channel create/delete\n"
            f"`{p}antinuke antiwebhook <on/off>` — Stop mass webhook creation + auto-deletes them\n"
            f"`{p}antinuke antiprune <on/off>` — Block unauthorized member pruning"
        ),
        inline=False,
    )
    embed.add_field(
        name="📢 Message / Guild / Bot Modules",
        value=(
            f"`{p}antinuke antieveryone <on/off>` — Block mass @everyone/@here pings\n"
            f"`{p}antinuke antiguild <on/off>` — Block unauthorized server name/icon/banner changes\n"
            "↳ Auto-mutes violator for 2 minutes + logs the change\n"
            f"`{p}antinuke antibot <on/off>` — Block unauthorized bot additions\n"
            "↳ Kicks the bot AND punishes the person who added it\n"
            f"`{p}antinuke antimention <on/off>` — Block mass user mention spam\n"
            f"`{p}antinuke antiemoji <on/off>` — Stop mass emoji deletion\n"
            f"`{p}antinuke antisticker <on/off>` — Stop mass sticker deletion\n"
            f"`{p}antinuke antithread <on/off>` — Stop mass thread spam\n"
            f"`{p}antinuke antivc <on/off>` — Stop mass voice channel deletion\n"
            f"`{p}antinuke antiintegration <on/off>` — Block unauthorized integrations/OAuth apps\n\n"
            f"💡 Toggle any single module: `{p}antinuke module <name> on/off`"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 2/3 — Use ◀ ▶ to navigate • Lucky Bot Security")
    return embed


def build_security_page3(p: str) -> discord.Embed:
    embed = discord.Embed(
        title="🔐 Security — Page 3 / 3",
        description="Antiraid, Panic Mode, Recovery & Stats.",
        color=discord.Color.dark_red(),
    )
    embed.add_field(
        name="🚨 Antiraid",
        value=(
            f"`{p}antiraid` — Show antiraid status overview\n"
            f"`{p}antiraid on` / `{p}antiraid off` — Enable / disable raid detection\n"
            f"`{p}antiraid punish <ban|kick|mute>` — Set raid punishment\n"
            f"`{p}antiraid threshold <joins> <seconds>` — Set raid trigger\n"
            "↳ Example: `!antiraid threshold 10 8` = 10 joins in 8 seconds = raid\n"
            f"`{p}antiraid minage <days>` — Block accounts younger than X days (0 = off)\n"
            f"`{p}antiraid noavatar <on/off>` — Block members with no profile picture\n"
            f"`{p}antiraid lockdown <on/off>` — Manually lock server (kicks all new joins)\n"
            f"`{p}antiraid whitelist @user` — Exempt a user from all antiraid checks\n"
            f"`{p}antiraid logchannel #channel` — Set where raid alerts are sent\n"
            f"`{p}antiraid stats` — View raid attempt history"
        ),
        inline=False,
    )
    embed.add_field(
        name="🚨 Panic & Recovery",
        value=(
            f"`{p}antinuke panic` — **EMERGENCY** — instantly blocks ALL new joins + bot adds\n"
            "↳ Run again to deactivate\n"
            f"`{p}antinuke recover` — Restore server from last saved snapshot\n"
            "↳ Snapshots saved automatically every 30 minutes when antinuke is on\n"
            "↳ Also saved when you run `!antinuke on` or `!antinuke setup`\n\n"
            f"`{p}antinuke stats` — View all-time threat statistics\n"
            "↳ Shows every action type and how many times it was triggered"
        ),
        inline=False,
    )
    embed.add_field(
        name="💡 Recommended Quick Start",
        value=(
            f"1️⃣ `{p}setup security` — creates `#security-logs`\n"
            f"2️⃣ `{p}antinuke wizard` — guided setup in 4 steps\n"
            f"3️⃣ `{p}antiraid on` — enable raid detection\n"
            f"4️⃣ `{p}antiraid minage 7` — block accounts under 7 days old\n"
            f"5️⃣ `{p}antinuke whitelist @trusted_admin` — whitelist your team"
        ),
        inline=False,
    )
    embed.set_footer(text="Page 3/3 — Use ◀ ▶ to navigate • Lucky Bot Security")
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
    def __init__(self, p: str):
        self.p = p
        options = [
            discord.SelectOption(label="🏠 Home",         value="home",      description="Main help overview"),
            discord.SelectOption(label="ℹ️ Basic & Info", value="basic",     description="Ping, userinfo, serverinfo, AFK, snipe"),
            discord.SelectOption(label="🛡️ Moderation",  value="mod",       description="Warn, mute, kick, ban, purge & more"),
            discord.SelectOption(label="🔐 Security",     value="security",  description="Antinuke, antiraid, panic & recovery"),
            discord.SelectOption(label="⚙️ Settings",     value="settings",  description="Prefix, rolebind, clearlogs"),
            discord.SelectOption(label="🔧 Setup",         value="setup",     description="Auto-setup roles & channels"),
            discord.SelectOption(label="🤖 Bot Status",   value="botstatus", description="Status, activity, bot name"),
            discord.SelectOption(label="🚫 AutoMod",      value="automod",   description="Auto moderation (coming soon)"),
            discord.SelectOption(label="👋 Welcome",      value="welcome",   description="Welcome messages (coming soon)"),
            discord.SelectOption(label="🎫 Tickets",      value="tickets",   description="Ticket system (coming soon)"),
            discord.SelectOption(label="🎉 Fun",          value="fun",       description="Games & fun commands (coming soon)"),
            discord.SelectOption(label="💰 Economy",      value="economy",   description="Coins & shop (coming soon)"),
            discord.SelectOption(label="📈 Leveling",     value="leveling",  description="XP & rank system (coming soon)"),
            discord.SelectOption(label="🎁 Giveaway",     value="giveaway",  description="Giveaway system (coming soon)"),
            discord.SelectOption(label="🎵 Music",        value="music",     description="Music player (coming soon)"),
        ]
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
        else:
            await interaction.response.edit_message(embed=build_coming_soon_embed(val), view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, p: str):
        super().__init__(timeout=120)
        self.add_item(HelpDropdown(p))

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

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        p = self._prefix(ctx.guild)
        view = HelpView(p)
        await ctx.reply(embed=build_main_embed(p), view=view)

    @app_commands.command(name="help", description="Open the Lucky Bot help menu")
    async def help_slash(self, interaction: discord.Interaction):
        p = self._prefix(interaction.guild)
        view = HelpView(p)
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
