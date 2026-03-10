import os

TOKEN = os.getenv("TOKEN")
NAME = "Lucky"
BotName = "Lucky"
server = os.getenv("SUPPORT_SERVER", "https://discord.gg/q2DdzFxheA")
serverLink = server
ch = os.getenv("SUPPORT_CHANNEL", "https://discord.gg/2DjxEKy3zf")

_owner_ids_raw = os.getenv("OWNER_IDS", "1333571921652088871")
OWNER_IDS = [int(x.strip()) for x in _owner_ids_raw.split(",") if x.strip().isdigit()]

# Lucky Bot — Rewritten
