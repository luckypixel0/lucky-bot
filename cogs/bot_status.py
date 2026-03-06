import discord
from discord import app_commands
from discord.ext import commands


STATUS_MAP = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
    "invisible": discord.Status.invisible,
}

ACTIVITY_TYPE_MAP = {
    "playing": discord.ActivityType.playing,
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "competing": discord.ActivityType.competing,
}


class BotStatus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.current_status = "online"
        self.current_activity_type = "watching"
        self.current_activity_text = "over the server"

    def _is_bot_owner(self, user_id: int) -> bool:
        return user_id == self.bot.BOT_OWNER_ID

    def _build_activity(self):
        if self.current_activity_type == "none":
            return None
        return discord.Activity(
            type=ACTIVITY_TYPE_MAP[self.current_activity_type],
            name=self.current_activity_text,
        )

    async def _apply_presence(self):
        await self.bot.change_presence(
            status=STATUS_MAP[self.current_status],
            activity=self._build_activity(),
        )

    @commands.command(name="setstatus")
    async def setstatus_prefix(self, ctx: commands.Context, status: str):
        if not self._is_bot_owner(ctx.author.id):
            await ctx.reply(embed=discord.Embed(title="❌ Bot Owner Only", color=discord.Color.red()))
            return

        status = status.lower().strip()
        if status not in STATUS_MAP:
            await ctx.reply(
                embed=discord.Embed(
                    title="❌ Invalid Status",
                    description="Use: `online`, `idle`, `dnd`, or `invisible`.",
                    color=discord.Color.red(),
                )
            )
            return

        self.current_status = status
        await self._apply_presence()
        await ctx.reply(embed=discord.Embed(title="✅ Status Updated", description=f"Now `{status}`", color=discord.Color.green()))

    @app_commands.command(name="setstatus", description="Set bot status (bot owner only)")
    @app_commands.describe(status="online, idle, dnd, invisible")
    async def setstatus_slash(self, interaction: discord.Interaction, status: str):
        if not self._is_bot_owner(interaction.user.id):
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Bot Owner Only", color=discord.Color.red()), ephemeral=True
            )
            return

        status = status.lower().strip()
        if status not in STATUS_MAP:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Invalid Status",
                    description="Use: `online`, `idle`, `dnd`, or `invisible`.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        self.current_status = status
        await self._apply_presence()
        await interaction.response.send_message(
            embed=discord.Embed(title="✅ Status Updated", description=f"Now `{status}`", color=discord.Color.green())
        )

    @commands.command(name="setactivity")
    async def setactivity_prefix(self, ctx: commands.Context, activity_type: str, *, text: str = ""):
        if not self._is_bot_owner(ctx.author.id):
            await ctx.reply(embed=discord.Embed(title="❌ Bot Owner Only", color=discord.Color.red()))
            return

        activity_type = activity_type.lower().strip()
        if activity_type not in {*ACTIVITY_TYPE_MAP.keys(), "none"}:
            await ctx.reply(
                embed=discord.Embed(
                    title="❌ Invalid Activity",
                    description="Use: playing, watching, listening, competing, none",
                    color=discord.Color.red(),
                )
            )
            return

        if activity_type != "none" and not text.strip():
            await ctx.reply(
                embed=discord.Embed(
                    title="⚠️ Missing Text",
                    description="Please provide activity text. Example: `!setactivity watching over the server`",
                    color=discord.Color.orange(),
                )
            )
            return

        self.current_activity_type = activity_type
        self.current_activity_text = text.strip() if text.strip() else ""
        await self._apply_presence()
        await ctx.reply(embed=discord.Embed(title="✅ Activity Updated", color=discord.Color.green()))

    @app_commands.command(name="setactivity", description="Set bot activity (bot owner only)")
    async def setactivity_slash(self, interaction: discord.Interaction, activity_type: str, text: str = ""):
        if not self._is_bot_owner(interaction.user.id):
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Bot Owner Only", color=discord.Color.red()), ephemeral=True
            )
            return

        activity_type = activity_type.lower().strip()
        if activity_type not in {*ACTIVITY_TYPE_MAP.keys(), "none"}:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Invalid Activity",
                    description="Use: playing, watching, listening, competing, none",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        if activity_type != "none" and not text.strip():
            await interaction.response.send_message(
                embed=discord.Embed(title="⚠️ Missing Text", description="Please provide activity text.", color=discord.Color.orange()),
                ephemeral=True,
            )
            return

        self.current_activity_type = activity_type
        self.current_activity_text = text.strip() if text.strip() else ""
        await self._apply_presence()
        await interaction.response.send_message(
            embed=discord.Embed(title="✅ Activity Updated", color=discord.Color.green())
        )

    @commands.command(name="botstatus")
    async def botstatus_prefix(self, ctx: commands.Context):
        activity_text = "None" if self.current_activity_type == "none" else f"{self.current_activity_type} {self.current_activity_text}"
        embed = discord.Embed(title="🤖 Lucky Bot Status", color=discord.Color.blurple())
        embed.add_field(name="Status", value=self.current_status)
        embed.add_field(name="Activity", value=activity_text, inline=False)
        await ctx.reply(embed=embed)

    @app_commands.command(name="botstatus", description="Show current bot status/activity")
    async def botstatus_slash(self, interaction: discord.Interaction):
        activity_text = "None" if self.current_activity_type == "none" else f"{self.current_activity_type} {self.current_activity_text}"
        embed = discord.Embed(title="🤖 Lucky Bot Status", color=discord.Color.blurple())
        embed.add_field(name="Status", value=self.current_status)
        embed.add_field(name="Activity", value=activity_text, inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(BotStatus(bot))
