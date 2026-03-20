# Lucky Bot — cogs/__init__.py
import os
from discord.ext import commands

async def setup(bot: commands.Bot):
    """Dynamically load all cog submodules from every subfolder."""
    cog_dirs = [
        ("cogs/commands",  "cogs.commands"),
        ("cogs/moderation","cogs.moderation"),
        ("cogs/events",    "cogs.events"),
        ("cogs/automod",   "cogs.automod"),
        ("cogs/antinuke",  "cogs.antinuke"),
    ]
    for dir_path, module_prefix in cog_dirs:
        if not os.path.isdir(dir_path):
            continue
        for filename in sorted(os.listdir(dir_path)):
            if filename.endswith(".py") and not filename.startswith("_"):
                module = f"{module_prefix}.{filename[:-3]}"
                try:
                    await bot.load_extension(module)
                except Exception as e:
                    print(f"[Lucky] Failed to load {module}: {e}")

# Lucky Bot — Rewritten
