import discord
from discord.ext import commands
from discord import app_commands
import datetime

class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_prefix(self, guild_id):
        return self.bot.custom_prefixes.get(guild_id, '!')

    def is_bot_owner(self, user_id):
        return user_id == self.bot.BOT_OWNER_ID

    # ══════════════════════════════════════════
    #   SET PREFIX
    # ══════════════════════════════════════════

    @commands.command(name='setprefix')
    async def setprefix_prefix(self, ctx, new_prefix: str):
        """
        Change the bot prefix for this server.
        Usage: !setprefix &
        Server owner only.
        """
        if ctx.author.id != ctx.guild.owner_id and not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ No Permission",
                description="Only the **server owner** can change the prefix!",
                color=0xe74c3c
            ))
        if len(new_prefix) > 5:
            return await ctx.reply(embed=discord.Embed(
                title="❌ Too Long",
                description="Prefix must be **5 characters or less**!",
                color=0xe74c3c
            ))
        if new_prefix.lower() == 'reset':
            self.bot.custom_prefixes.pop(ctx.guild.id, None)
            return await ctx.reply(embed=discord.Embed(
                title="✅ Prefix Reset",
                description="Prefix reset back to default: `!`",
                color=0x2ecc71
            ))
        self.bot.custom_prefixes[ctx.guild.id] = new_prefix
        embed = discord.Embed(
            title="✅ Prefix Updated",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="New Prefix", value=f"`{new_prefix}`")
        embed.add_field(name="Example", value=f"`{new_prefix}ping`")
        embed.add_field(
            name="💡 Tip",
            value="If you forget your prefix, use `/prefix` to check it!",
            inline=False
        )
        embed.set_footer(text="Lucky Bot Prefix System")
        await ctx.reply(embed=embed)

    @app_commands.command(name='setprefix', description='Change the bot prefix for this server')
    @app_commands.describe(new_prefix='New prefix (max 5 characters, type "reset" to reset to !)')
    async def setprefix_slash(self, interaction: discord.Interaction, new_prefix: str):
        if interaction.user.id != interaction.guild.owner_id and \
           not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ No Permission",
                description="Only the **server owner** can change the prefix!",
                color=0xe74c3c
            ), ephemeral=True)
        if len(new_prefix) > 5:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Too Long",
                description="Prefix must be **5 characters or less**!",
                color=0xe74c3c
            ), ephemeral=True)
        if new_prefix.lower() == 'reset':
            self.bot.custom_prefixes.pop(interaction.guild.id, None)
            return await interaction.response.send_message(embed=discord.Embed(
                title="✅ Prefix Reset",
                description="Prefix reset back to default: `!`",
                color=0x2ecc71
            ))
        self.bot.custom_prefixes[interaction.guild.id] = new_prefix
        embed = discord.Embed(
            title="✅ Prefix Updated",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="New Prefix", value=f"`{new_prefix}`")
        embed.add_field(name="Example", value=f"`{new_prefix}ping`")
        embed.set_footer(text="Lucky Bot Prefix System")
        await interaction.response.send_message(embed=embed)

    # ══════════════════════════════════════════
    #   CHECK PREFIX
    # ══════════════════════════════════════════

    @commands.command(name='prefix')
    async def prefix_cmd(self, ctx):
        """Show current prefix. Usage: !prefix"""
        current = self.get_prefix(ctx.guild.id if ctx.guild else None)
        embed = discord.Embed(
            title="⚙️ Server Prefix",
            color=0x3498db,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Current Prefix", value=f"`{current}`")
        embed.add_field(name="Example", value=f"`{current}help`")
        embed.add_field(
            name="Change it",
            value=f"`{current}setprefix <new>` — server owner only\n`{current}setprefix reset` — reset to `!`",
            inline=False
        )
        embed.add_field(
            name="💡 Always works",
            value="Slash commands like `/help` always work regardless of prefix!",
            inline=False
        )
        embed.set_footer(text="Lucky Bot Prefix System")
        await ctx.reply(embed=embed)

    @app_commands.command(name='prefix', description='Show the current bot prefix for this server')
    async def prefix_slash(self, interaction: discord.Interaction):
        current = self.get_prefix(interaction.guild.id if interaction.guild else None)
        embed = discord.Embed(
            title="⚙️ Server Prefix",
            color=0x3498db,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Current Prefix", value=f"`{current}`")
        embed.add_field(name="Example", value=f"`{current}help`")
        embed.add_field(
            name="Change it",
            value=f"`/setprefix` — server owner only",
            inline=False
        )
        embed.set_footer(text="Lucky Bot Prefix System")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ══════════════════════════════════════════
    #   NO PREFIX SYSTEM
    #   Bot owner only — grants prefix-free usage
    # ══════════════════════════════════════════

    @commands.group(name='noprefix', invoke_without_command=True)
    async def noprefix_group(self, ctx):
        """No-prefix management. Bot owner only."""
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only",
                description="Only the **bot creator** can manage no-prefix access!",
                color=0xe74c3c
            ))
        users = self.bot.no_prefix_users
        embed = discord.Embed(
            title="🔇 No-Prefix Users",
            description="\n".join([f"<@{uid}>" for uid in users]) or "None set",
            color=0x3498db,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(
            name="Commands",
            value=(
                "`!noprefix add @user` — grant no-prefix\n"
                "`!noprefix remove @user` — revoke no-prefix\n"
                "`!noprefix list` — see all users\n"
                "`!noprefix clear` — remove everyone"
            ),
            inline=False
        )
        embed.add_field(
            name="What is no-prefix?",
            value="Users with this can type `warn @user` instead of `!warn @user`",
            inline=False
        )
        embed.set_footer(text="Lucky Bot • Bot Owner Only")
        await ctx.send(embed=embed)

    @noprefix_group.command(name='add')
    async def noprefix_add(self, ctx, member: discord.Member):
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))
        self.bot.no_prefix_users.add(member.id)
        embed = discord.Embed(
            title="✅ No-Prefix Granted",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="User", value=member.mention)
        embed.add_field(
            name="What changed",
            value=f"{member.mention} can now use all commands **without any prefix**!"
        )
        embed.set_footer(text="Lucky Bot • Bot Owner Only")
        await ctx.reply(embed=embed)

    @noprefix_group.command(name='remove')
    async def noprefix_remove(self, ctx, member: discord.Member):
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))
        self.bot.no_prefix_users.discard(member.id)
        await ctx.reply(embed=discord.Embed(
            title="✅ No-Prefix Revoked",
            description=f"{member.mention} now needs to use the prefix again.",
            color=0x2ecc71
        ))

    @noprefix_group.command(name='list')
    async def noprefix_list(self, ctx):
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))
        users = self.bot.no_prefix_users
        await ctx.send(embed=discord.Embed(
            title="🔇 No-Prefix Users",
            description="\n".join([f"<@{uid}>" for uid in users]) or "None set",
            color=0x3498db
        ))

    @noprefix_group.command(name='clear')
    async def noprefix_clear(self, ctx):
        if not self.is_bot_owner(ctx.author.id):
            return await ctx.reply(embed=discord.Embed(
                title="❌ Bot Owner Only", color=0xe74c3c))
        count = len(self.bot.no_prefix_users)
        self.bot.no_prefix_users.clear()
        await ctx.reply(embed=discord.Embed(
            title="🧹 No-Prefix Cleared",
            description=f"Removed no-prefix access from **{count}** user(s).",
            color=0x2ecc71
        ))

    # Slash version
    @app_commands.command(name='noprefix', description='Manage no-prefix access (bot owner only)')
    @app_commands.describe(action='add/remove/list/clear', member='Target member')
    @app_commands.choices(action=[
        app_commands.Choice(name='add — grant no-prefix', value='add'),
        app_commands.Choice(name='remove — revoke no-prefix', value='remove'),
        app_commands.Choice(name='list — see all users', value='list'),
        app_commands.Choice(name='clear — remove everyone', value='clear'),
    ])
    async def noprefix_slash(self, interaction: discord.Interaction,
                             action: str, member: discord.Member = None):
        if not self.is_bot_owner(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Bot Owner Only",
                description="Only the **bot creator** can manage no-prefix access!",
                color=0xe74c3c
            ), ephemeral=True)
        if action == 'add' and member:
            self.bot.no_prefix_users.add(member.id)
            await interaction.response.send_message(embed=discord.Embed(
                title="✅ No-Prefix Granted",
                description=f"{member.mention} can now use commands without prefix!",
                color=0x2ecc71
            ))
        elif action == 'remove' and member:
            self.bot.no_prefix_users.discard(member.id)
            await interaction.response.send_message(embed=discord.Embed(
                title="✅ Revoked",
                description=f"{member.mention} needs prefix again.",
                color=0x2ecc71
            ))
        elif action == 'list':
            users = self.bot.no_prefix_users
            await interaction.response.send_message(embed=discord.Embed(
                title="🔇 No-Prefix Users",
                description="\n".join([f"<@{uid}>" for uid in users]) or "None",
                color=0x3498db
            ), ephemeral=True)
        elif action == 'clear':
            count = len(self.bot.no_prefix_users)
            self.bot.no_prefix_users.clear()
            await interaction.response.send_message(embed=discord.Embed(
                title="🧹 Cleared",
                description=f"Removed no-prefix from **{count}** user(s).",
                color=0x2ecc71
            ))
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Missing Member",
                description="Please mention a member for add/remove!",
                color=0xe74c3c
            ), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Prefix(bot))
