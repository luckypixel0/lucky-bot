import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _prefix(self, guild: discord.Guild | None) -> str:
        if guild is None:
            return self.bot.DEFAULT_PREFIX
        return self.bot.custom_prefixes.get(guild.id, self.bot.DEFAULT_PREFIX)

    def _build_help_embed(self, guild: discord.Guild | None) -> discord.Embed:
        p = self._prefix(guild)
        embed = discord.Embed(
            title="🍀 Lucky Bot — Help (Phase 1)",
            description="Core commands rebuilt cleanly for Phase 1.",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Prefix Commands",
            value=(
                f"`{p}prefix` — Show current prefix\n"
                f"`{p}setprefix <new>` — Change server prefix (owner only)\n"
                f"`{p}setprefix reset` — Reset to default `!`\n"
                f"`{p}noprefix @user` — Toggle no-prefix access (bot owner only)\n"
                f"`{p}ping` — Check bot latency"
            ),
            inline=False,
        )
        embed.add_field(
            name="Bot Status Commands (Owner)",
            value=(
                f"`{p}setstatus <online|idle|dnd|invisible>`\n"
                f"`{p}setactivity <playing|watching|listening|competing|none> [text]`\n"
                f"`{p}botstatus`"
            ),
            inline=False,
        )
        embed.add_field(name="Slash Commands", value="All above commands also work as `/` slash commands.", inline=False)
        embed.set_footer(text=f"Default prefix: {self.bot.DEFAULT_PREFIX}")
        return embed

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        await ctx.reply(embed=self._build_help_embed(ctx.guild))

    @app_commands.command(name="help", description="Show Lucky Bot help")
    async def help_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._build_help_embed(interaction.guild))


    @commands.command(name="ping")
    async def ping_prefix(self, ctx: commands.Context):
        await ctx.reply(f"🏓 Pong! `{round(self.bot.latency * 1000)}ms`")

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🏓 Pong! `{round(self.bot.latency * 1000)}ms`"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
