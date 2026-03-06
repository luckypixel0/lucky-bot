import discord
from discord import app_commands
from discord.ext import commands


class Prefix(commands.Cog):
    """Prefix + no-prefix management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_bot_owner(self, user_id: int) -> bool:
        return user_id == self.bot.BOT_OWNER_ID

    def _is_server_owner(self, guild: discord.Guild, user_id: int) -> bool:
        return guild and guild.owner_id == user_id

    def _current_prefix(self, guild: discord.Guild | None) -> str:
        if guild is None:
            return self.bot.DEFAULT_PREFIX
        return self.bot.custom_prefixes.get(guild.id, self.bot.DEFAULT_PREFIX)

    async def _set_prefix_logic(self, guild: discord.Guild, actor_id: int, new_prefix: str):
        if not (self._is_server_owner(guild, actor_id) or self._is_bot_owner(actor_id)):
            return False, "Only the **server owner** (or bot owner) can change prefix."

        if new_prefix.lower() == "reset":
            self.bot.custom_prefixes.pop(guild.id, None)
            return True, f"Prefix reset to default: `{self.bot.DEFAULT_PREFIX}`"

        if len(new_prefix) > 5:
            return False, "Prefix must be at most **5 characters**."

        self.bot.custom_prefixes[guild.id] = new_prefix
        return True, f"Prefix updated to: `{new_prefix}`"

    @commands.command(name="setprefix")
    @commands.guild_only()
    async def setprefix_prefix(self, ctx: commands.Context, *, new_prefix: str):
        """Set custom prefix. Example: !setprefix ?"""
        ok, message = await self._set_prefix_logic(ctx.guild, ctx.author.id, new_prefix.strip())
        color = discord.Color.green() if ok else discord.Color.red()
        await ctx.reply(embed=discord.Embed(title="Prefix Settings", description=message, color=color))

    @app_commands.command(name="setprefix", description="Set this server prefix (owner or bot owner only)")
    @app_commands.describe(new_prefix="Example: ?, $, !! or reset")
    async def setprefix_slash(self, interaction: discord.Interaction, new_prefix: str):
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Server Only",
                    description="Use this inside a server.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        ok, message = await self._set_prefix_logic(interaction.guild, interaction.user.id, new_prefix.strip())
        color = discord.Color.green() if ok else discord.Color.red()
        await interaction.response.send_message(
            embed=discord.Embed(title="Prefix Settings", description=message, color=color),
            ephemeral=not ok,
        )

    @commands.command(name="prefix")
    async def prefix_prefix(self, ctx: commands.Context):
        prefix = self._current_prefix(ctx.guild)
        embed = discord.Embed(
            title="Current Prefix",
            description=f"This server prefix is `{prefix}`\nDefault prefix is `{self.bot.DEFAULT_PREFIX}`.",
            color=discord.Color.blurple(),
        )
        await ctx.reply(embed=embed)

    @app_commands.command(name="prefix", description="Show this server's current prefix")
    async def prefix_slash(self, interaction: discord.Interaction):
        prefix = self._current_prefix(interaction.guild)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Current Prefix",
                description=f"This server prefix is `{prefix}`\nDefault prefix is `{self.bot.DEFAULT_PREFIX}`.",
                color=discord.Color.blurple(),
            )
        )

    @commands.command(name="noprefix")
    async def noprefix_prefix(self, ctx: commands.Context, member: discord.Member):
        if not self._is_bot_owner(ctx.author.id):
            await ctx.reply(
                embed=discord.Embed(
                    title="❌ Bot Owner Only",
                    description="Only the bot owner can grant/revoke no-prefix access.",
                    color=discord.Color.red(),
                )
            )
            return

        granted = member.id not in self.bot.no_prefix_users
        if granted:
            self.bot.no_prefix_users.add(member.id)
            message = f"✅ {member.mention} can now use commands with **no prefix**."
        else:
            self.bot.no_prefix_users.remove(member.id)
            message = f"✅ Removed no-prefix access from {member.mention}."

        await ctx.reply(embed=discord.Embed(title="No Prefix", description=message, color=discord.Color.green()))

    @app_commands.command(name="noprefix", description="Grant or revoke no-prefix access (bot owner only)")
    async def noprefix_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not self._is_bot_owner(interaction.user.id):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Bot Owner Only",
                    description="Only the bot owner can grant/revoke no-prefix access.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        granted = member.id not in self.bot.no_prefix_users
        if granted:
            self.bot.no_prefix_users.add(member.id)
            message = f"✅ {member.mention} can now use commands with **no prefix**."
        else:
            self.bot.no_prefix_users.remove(member.id)
            message = f"✅ Removed no-prefix access from {member.mention}."

        await interaction.response.send_message(
            embed=discord.Embed(title="No Prefix", description=message, color=discord.Color.green())
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Prefix(bot))
