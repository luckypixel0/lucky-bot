"""
Lucky Bot Music Cog - Complete All-In-One Music System
Features: Play, Queue, Download, Playlists, Favorites, Lyrics, Filters, Stats
All responses in embed format | 15-minute temp file storage | Per-guild voice client
"""

import discord
from discord.ext import commands, tasks
import yt_dlp
import subprocess
import os
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import random
import math
from typing import Optional, Dict, List
import aiohttp

# Configuration
TEMP_DIR = "/tmp/lucky_bot_music"
TEMP_EXPIRY = 900  # 15 minutes in seconds
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
DISCORD_MAX_FILE = 10 * 1024 * 1024  # Discord's actual limit

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)

# Color scheme for embeds
COLOR_SUCCESS = 0x2ECC71
COLOR_INFO = 0x3498DB
COLOR_WARNING = 0xF39C12
COLOR_ERROR = 0xE74C3C
COLOR_MUSIC = 0x9B59B6


class MusicQueue:
    """Per-guild music queue management"""
    
    def __init__(self):
        self.current = None
        self.queue = []
        self.history = []
        self.loop_mode = 0  # 0=off, 1=song, 2=queue
        self.is_playing = False
        self.is_paused = False
    
    def add(self, track):
        self.queue.append(track)
    
    def add_next(self, track):
        self.queue.insert(0, track)
    
    def skip(self):
        if self.queue:
            return self.queue.pop(0)
        return None
    
    def remove(self, index):
        if 0 <= index < len(self.queue):
            return self.queue.pop(index)
        return None
    
    def shuffle(self):
        random.shuffle(self.queue)
    
    def clear(self):
        self.queue.clear()
    
    def get_queue_display(self, page=1, per_page=5):
        total_pages = math.ceil(len(self.queue) / per_page) or 1
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        display = self.queue[start_idx:end_idx]
        return display, page, total_pages, len(self.queue)


class YTDLSource(discord.PCMVolumeTransformer):
    """Audio source wrapper for discord.py"""
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration', 0)
        self.uploader = data.get('uploader', 'Unknown')
        self.thumbnail = data.get('thumbnail')
    
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        """Create audio source from YouTube URL"""
        loop = loop or asyncio.get_event_loop()
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'default_search': 'ytsearch',
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            
            if data is None:
                return None
            
            filename = data['url'] if not stream else None
            return cls(discord.FFmpegPCMAudio(data['url'], **{'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}), data=data)
        except Exception as e:
            print(f"[Music] Error loading audio: {e}")
            return None
    
    @staticmethod
    async def search(query, loop=None):
        """Search for songs on YouTube"""
        loop = loop or asyncio.get_event_loop()
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                results = await loop.run_in_executor(
                    None, 
                    lambda: ydl.extract_info(f'ytsearch5:{query}', download=False)
                )
            
            return results.get('entries', [])
        except Exception as e:
            print(f"[Music] Search error: {e}")
            return []


class Music(commands.Cog):
    """Lucky Bot Music System - All-In-One Player"""
    
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # Per-guild queues
        self.playlists = {}  # Per-user playlists
        self.favorites = {}  # Per-user favorites
        self.history = {}  # Per-guild play history
        self.user_stats = {}  # Per-user statistics
        self.guild_stats = {}  # Per-guild statistics
        self.playing_embeds = {}  # Track playing embed messages
        self.temp_files = {}  # Track temp files for cleanup
        self.skip_votes = {}  # Track skip votes per guild
        self.banned_users = {}  # Per-guild banned users
        self.music_channels = {}  # Per-guild music-only channels
        self.dj_roles = {}  # Per-guild DJ role
        
        # Start cleanup task
        self.cleanup_temp_files.start()
    
    def get_queue(self, guild_id):
        """Get or create queue for guild"""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]
    
    def has_permission(self, ctx, permission_type="play"):
        """Check if user has music permission"""
        # Bot owner has all permissions
        if ctx.author.id == self.bot.owner_id:
            return True
        
        # Guild owner has all permissions
        if ctx.author == ctx.guild.owner:
            return True
        
        # Check for dj.exe role or admin
        dj_role_name = self.dj_roles.get(ctx.guild.id, "dj.exe")
        has_dj = any(role.name == dj_role_name for role in ctx.author.roles)
        has_admin = ctx.author.guild_permissions.administrator
        
        if permission_type in ["forceskip", "forceremove", "stop"]:
            return has_dj or has_admin
        
        return True  # Everyone can play
    
    def format_duration(self, seconds):
        """Convert seconds to MM:SS format"""
        if not seconds:
            return "00:00"
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"
    
    @tasks.loop(minutes=1)
    async def cleanup_temp_files(self):
        """Clean up temp files older than 15 minutes"""
        try:
            current_time = datetime.now()
            expired = []
            
            for file_path, created_time in list(self.temp_files.items()):
                if (current_time - created_time).total_seconds() > TEMP_EXPIRY:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        expired.append(file_path)
                    except:
                        pass
            
            for file_path in expired:
                del self.temp_files[file_path]
        except Exception as e:
            print(f"[Music] Cleanup error: {e}")
    
    # ==================== PLAYBACK COMMANDS ====================
    
    @commands.hybrid_command(name="play", aliases=["p"])
    async def play(self, ctx, *, query):
        """Play a song from YouTube by URL or search query"""
        
        # Check music channel restriction
        if ctx.guild.id in self.music_channels:
            restricted_channel_id = self.music_channels[ctx.guild.id]
            if ctx.channel.id != restricted_channel_id:
                embed = discord.Embed(
                    title="❌ Wrong Channel",
                    description=f"Music commands only work in <#{restricted_channel_id}>",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
        
        # Check if user is banned
        if ctx.guild.id in self.banned_users and ctx.author.id in self.banned_users[ctx.guild.id]:
            embed = discord.Embed(
                title="❌ Banned",
                description="You are banned from using music commands",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        # Check if user in voice channel
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Not in Voice",
                description="You must be in a voice channel to play music",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed)
            return
        
        loading_embed = discord.Embed(
            title="🔄 Searching...",
            description=f"Looking for: **{query}**",
            color=COLOR_INFO
        )
        msg = await ctx.send(embed=loading_embed)
        
        try:
            # Search for the track
            results = await YTDLSource.search(query)
            
            if not results:
                embed = discord.Embed(
                    title="❌ No Results",
                    description=f"No songs found for: **{query}**",
                    color=COLOR_ERROR
                )
                await msg.edit(embed=embed)
                return
            
            # Use first result
            track_data = results[0]
            url = f"https://www.youtube.com/watch?v={track_data['id']}"
            
            # Get audio source
            source = await YTDLSource.from_url(url, loop=self.bot.loop)
            if not source:
                embed = discord.Embed(
                    title="❌ Load Failed",
                    description="Could not load audio stream",
                    color=COLOR_ERROR
                )
                await msg.edit(embed=embed)
                return
            
            # Create track dict
            track = {
                'title': source.title,
                'url': source.url,
                'duration': source.duration,
                'uploader': source.uploader,
                'thumbnail': source.thumbnail,
                'requester': ctx.author,
                'source': source
            }
            
            # Join voice channel
            queue = self.get_queue(ctx.guild.id)
            vc = ctx.author.voice.channel
            
            if ctx.voice_client is None:
                try:
                    await vc.connect()
                except Exception as e:
                    embed = discord.Embed(
                        title="❌ Connection Failed",
                        description=f"Could not connect to voice: {str(e)}",
                        color=COLOR_ERROR
                    )
                    await msg.edit(embed=embed)
                    return
            
            # Check if already playing
            if ctx.voice_client.is_playing():
                queue.add(track)
                
                embed = discord.Embed(
                    title="✅ Added to Queue",
                    description=f"**{source.title}**",
                    color=COLOR_SUCCESS
                )
                embed.add_field(name="Artist", value=source.uploader, inline=True)
                embed.add_field(name="Duration", value=self.format_duration(source.duration), inline=True)
                embed.add_field(name="Position", value=f"#{len(queue.queue)}", inline=True)
                embed.add_field(name="Requested by", value=ctx.author.mention, inline=False)
                embed.set_thumbnail(url=source.thumbnail)
                
                await msg.edit(embed=embed)
            else:
                queue.current = track
                queue.is_playing = True
                ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.after_playing(ctx), self.bot.loop).result())
                
                embed = discord.Embed(
                    title="🎵 Now Playing",
                    description=f"**{source.title}**",
                    color=COLOR_MUSIC
                )
                embed.add_field(name="Artist", value=source.uploader, inline=True)
                embed.add_field(name="Duration", value=self.format_duration(source.duration), inline=True)
                embed.add_field(name="Requested by", value=ctx.author.mention, inline=True)
                embed.set_thumbnail(url=source.thumbnail)
                
                await msg.edit(embed=embed)
            
            # Track stats
            if ctx.guild.id not in self.guild_stats:
                self.guild_stats[ctx.guild.id] = {'plays': 0, 'skips': 0}
            if ctx.author.id not in self.user_stats:
                self.user_stats[ctx.author.id] = {'requested': 0}
            
            self.user_stats[ctx.author.id]['requested'] += 1
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Error loading track: {str(e)[:100]}",
                color=COLOR_ERROR
            )
            await msg.edit(embed=embed)
    
    @commands.hybrid_command(name="pause")
    async def pause(self, ctx):
        """Pause the current song"""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            embed = discord.Embed(
                title="❌ Nothing Playing",
                description="There's no music playing",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        ctx.voice_client.pause()
        queue = self.get_queue(ctx.guild.id)
        queue.is_paused = True
        
        embed = discord.Embed(
            title="⏸️ Paused",
            description=f"**{queue.current['title']}**",
            color=COLOR_INFO
        )
        embed.set_thumbnail(url=queue.current['thumbnail'])
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="resume", aliases=["unpause"])
    async def resume(self, ctx):
        """Resume the paused song"""
        if not ctx.voice_client:
            embed = discord.Embed(
                title="❌ Not Connected",
                description="Bot is not in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            queue = self.get_queue(ctx.guild.id)
            queue.is_paused = False
            
            embed = discord.Embed(
                title="▶️ Resumed",
                description=f"**{queue.current['title']}**",
                color=COLOR_INFO
            )
            embed.set_thumbnail(url=queue.current['thumbnail'])
            await ctx.send(embed=embed, delete_after=10)
        else:
            embed = discord.Embed(
                title="❌ Not Paused",
                description="Music is already playing",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
    
    @commands.hybrid_command(name="skip", aliases=["next"])
    async def skip(self, ctx):
        """Skip to next song (DJ/Admin can force)"""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            embed = discord.Embed(
                title="❌ Nothing Playing",
                description="There's no music playing to skip",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        is_dj = self.has_permission(ctx, "forceskip")
        queue = self.get_queue(ctx.guild.id)
        
        if is_dj:
            # DJ can forceskip
            ctx.voice_client.stop()
            
            embed = discord.Embed(
                title="⏭️ Skipped",
                description="DJ skipped the song",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed, delete_after=10)
        else:
            # Regular user voting
            if ctx.guild.id not in self.skip_votes:
                self.skip_votes[ctx.guild.id] = set()
            
            if ctx.author.id in self.skip_votes[ctx.guild.id]:
                embed = discord.Embed(
                    title="⚠️ Already Voted",
                    description="You already voted to skip",
                    color=COLOR_WARNING
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            self.skip_votes[ctx.guild.id].add(ctx.author.id)
            
            # Count members in voice
            vc = ctx.guild.voice_client
            member_count = len([m for m in vc.channel.members if not m.bot])
            votes_needed = max(2, member_count // 2)
            current_votes = len(self.skip_votes[ctx.guild.id])
            
            if current_votes >= votes_needed:
                ctx.voice_client.stop()
                self.skip_votes[ctx.guild.id].clear()
                
                embed = discord.Embed(
                    title="⏭️ Skipped",
                    description=f"Skip vote passed ({current_votes}/{votes_needed})",
                    color=COLOR_INFO
                )
                await ctx.send(embed=embed, delete_after=10)
            else:
                embed = discord.Embed(
                    title="🗳️ Skip Vote",
                    description=f"{current_votes}/{votes_needed} votes needed",
                    color=COLOR_INFO
                )
                embed.add_field(name="Voted by", value=ctx.author.mention, inline=False)
                await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="stop")
    async def stop(self, ctx):
        """Stop music and leave voice channel"""
        if not self.has_permission(ctx, "stop"):
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only DJ or Admin can stop music",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if not ctx.voice_client:
            embed = discord.Embed(
                title="❌ Not Connected",
                description="Bot is not in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        queue = self.get_queue(ctx.guild.id)
        queue.clear()
        queue.current = None
        queue.is_playing = False
        
        await ctx.voice_client.disconnect()
        
        embed = discord.Embed(
            title="⏹️ Stopped",
            description="Music stopped and bot disconnected",
            color=COLOR_INFO
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="queue", aliases=["q"])
    async def queue(self, ctx, page: int = 1):
        """Display current queue with pagination"""
        queue = self.get_queue(ctx.guild.id)
        
        if not queue.current and not queue.queue:
            embed = discord.Embed(
                title="📭 Empty Queue",
                description="Nothing is playing right now",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed)
            return
        
        display, current_page, total_pages, total_tracks = queue.get_queue_display(page)
        
        embed = discord.Embed(
            title="🎵 Queue",
            color=COLOR_MUSIC
        )
        
        if queue.current:
            embed.add_field(
                name="▶️ Now Playing",
                value=f"**{queue.current['title']}** ({self.format_duration(queue.current['duration'])})\n*by {queue.current['requester'].mention}*",
                inline=False
            )
        
        if display:
            queue_text = ""
            for idx, track in enumerate(display, start=(page - 1) * 5 + 1):
                queue_text += f"`{idx}.` **{track['title']}** ({self.format_duration(track['duration'])})\n"
            embed.add_field(name="⏰ Upcoming", value=queue_text, inline=False)
        else:
            embed.add_field(name="⏰ Upcoming", value="No songs in queue", inline=False)
        
        embed.set_footer(text=f"Page {current_page}/{total_pages} | Total: {total_tracks} songs")
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        """Show currently playing song with duration bar"""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            embed = discord.Embed(
                title="❌ Nothing Playing",
                description="No music is currently playing",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed)
            return
        
        queue = self.get_queue(ctx.guild.id)
        track = queue.current
        
        # Calculate duration bar
        if track['duration']:
            current_pos = getattr(ctx.voice_client, 'position', 0) or 0
            bar_length = 20
            filled = int((current_pos / track['duration']) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            duration_str = f"{self.format_duration(current_pos)} {bar} {self.format_duration(track['duration'])}"
        else:
            duration_str = "🔴 Live Stream"
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{track['title']}**",
            color=COLOR_MUSIC
        )
        embed.add_field(name="Artist", value=track['uploader'], inline=True)
        embed.add_field(name="Duration", value=duration_str, inline=False)
        embed.add_field(name="Requested by", value=track['requester'].mention, inline=True)
        
        loop_modes = ["🔁 Off", "🔂 Song", "🔁 Queue"]
        embed.add_field(name="Loop Mode", value=loop_modes[queue.loop_mode], inline=True)
        
        embed.set_thumbnail(url=track['thumbnail'])
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="loop", aliases=["repeat"])
    async def loop(self, ctx):
        """Cycle through loop modes (off → song → queue)"""
        queue = self.get_queue(ctx.guild.id)
        queue.loop_mode = (queue.loop_mode + 1) % 3
        
        loop_names = ["Off", "Song", "Queue"]
        loop_icons = ["🔁", "🔂", "🔁"]
        
        embed = discord.Embed(
            title="🔁 Loop Mode Changed",
            description=f"{loop_icons[queue.loop_mode]} **{loop_names[queue.loop_mode]}**",
            color=COLOR_INFO
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="shuffle", aliases=["mix"])
    async def shuffle(self, ctx):
        """Shuffle current queue"""
        queue = self.get_queue(ctx.guild.id)
        
        if not queue.queue:
            embed = discord.Embed(
                title="❌ Empty Queue",
                description="Nothing to shuffle",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        queue.shuffle()
        
        embed = discord.Embed(
            title="🔀 Queue Shuffled",
            description=f"Shuffled {len(queue.queue)} songs",
            color=COLOR_INFO
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="volume")
    async def volume(self, ctx, level: int = None):
        """Set or show current volume (0-100)"""
        if not ctx.voice_client:
            embed = discord.Embed(
                title="❌ Not Connected",
                description="Bot is not in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if level is None:
            current_vol = int(ctx.voice_client.source.volume * 100) if ctx.voice_client.source else 50
            embed = discord.Embed(
                title="🔊 Current Volume",
                description=f"**{current_vol}%**",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed, delete_after=10)
            return
        
        if not 0 <= level <= 100:
            embed = discord.Embed(
                title="❌ Invalid Volume",
                description="Volume must be between 0 and 100",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if ctx.voice_client.source:
            ctx.voice_client.source.volume = level / 100
        
        # Volume bar visualization
        bar_filled = int(level / 5)
        bar = "🟩" * bar_filled + "🟥" * (20 - bar_filled)
        
        embed = discord.Embed(
            title="🔊 Volume Set",
            description=f"{bar}\n**{level}%**",
            color=COLOR_INFO
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="remove")
    async def remove(self, ctx, position: int):
        """Remove song from queue by position"""
        queue = self.get_queue(ctx.guild.id)
        
        if not queue.queue:
            embed = discord.Embed(
                title="❌ Empty Queue",
                description="There are no songs to remove",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if not 1 <= position <= len(queue.queue):
            embed = discord.Embed(
                title="❌ Invalid Position",
                description=f"Position must be 1-{len(queue.queue)}",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        removed = queue.remove(position - 1)
        
        embed = discord.Embed(
            title="❌ Removed from Queue",
            description=f"**{removed['title']}**",
            color=COLOR_INFO
        )
        embed.add_field(name="Duration", value=self.format_duration(removed['duration']), inline=True)
        embed.set_thumbnail(url=removed['thumbnail'])
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="clear", aliases=["clearqueue"])
    async def clear(self, ctx):
        """Clear the entire queue"""
        if not self.has_permission(ctx, "stop"):
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only DJ or Admin can clear queue",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        queue = self.get_queue(ctx.guild.id)
        queue.clear()
        
        embed = discord.Embed(
            title="🗑️ Queue Cleared",
            description="All songs have been removed from queue",
            color=COLOR_INFO
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="skipto")
    async def skipto(self, ctx, position: int):
        """Jump to specific song in queue"""
        if not self.has_permission(ctx, "forceskip"):
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only DJ or Admin can skip to position",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        queue = self.get_queue(ctx.guild.id)
        
        if not 1 <= position <= len(queue.queue):
            embed = discord.Embed(
                title="❌ Invalid Position",
                description=f"Position must be 1-{len(queue.queue)}",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        # Remove songs before position
        for _ in range(position - 1):
            queue.queue.pop(0)
        
        ctx.voice_client.stop()
        
        embed = discord.Embed(
            title="⏭️ Jumped to Position",
            description=f"**Position #{position}**",
            color=COLOR_INFO
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="playtop", aliases=["playnext"])
    async def playtop(self, ctx, *, query):
        """Add song to top of queue (next to play)"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Not in Voice",
                description="You must be in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed)
            return
        
        loading_embed = discord.Embed(
            title="🔄 Searching...",
            description=f"Looking for: **{query}**",
            color=COLOR_INFO
        )
        msg = await ctx.send(embed=loading_embed)
        
        try:
            results = await YTDLSource.search(query)
            
            if not results:
                embed = discord.Embed(
                    title="❌ No Results",
                    description=f"No songs found for: **{query}**",
                    color=COLOR_ERROR
                )
                await msg.edit(embed=embed)
                return
            
            track_data = results[0]
            url = f"https://www.youtube.com/watch?v={track_data['id']}"
            source = await YTDLSource.from_url(url, loop=self.bot.loop)
            
            if not source:
                embed = discord.Embed(
                    title="❌ Load Failed",
                    description="Could not load audio stream",
                    color=COLOR_ERROR
                )
                await msg.edit(embed=embed)
                return
            
            queue = self.get_queue(ctx.guild.id)
            
            track = {
                'title': source.title,
                'url': source.url,
                'duration': source.duration,
                'uploader': source.uploader,
                'thumbnail': source.thumbnail,
                'requester': ctx.author,
                'source': source
            }
            
            queue.add_next(track)
            
            embed = discord.Embed(
                title="⬆️ Added to Top of Queue",
                description=f"**{source.title}**",
                color=COLOR_SUCCESS
            )
            embed.add_field(name="Will play next", value="after current song", inline=False)
            embed.set_thumbnail(url=source.thumbnail)
            
            await msg.edit(embed=embed)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Error loading track: {str(e)[:100]}",
                color=COLOR_ERROR
            )
            await msg.edit(embed=embed)
    
    # ==================== SEARCH COMMANDS ====================
    
    @commands.hybrid_command(name="search")
    async def search(self, ctx, *, query):
        """Search for songs and select from results"""
        loading_embed = discord.Embed(
            title="🔄 Searching...",
            description=f"Looking for: **{query}**",
            color=COLOR_INFO
        )
        msg = await ctx.send(embed=loading_embed)
        
        try:
            results = await YTDLSource.search(query)
            
            if not results:
                embed = discord.Embed(
                    title="❌ No Results",
                    description=f"No songs found for: **{query}**",
                    color=COLOR_ERROR
                )
                await msg.edit(embed=embed)
                return
            
            # Show top 5 results
            embed = discord.Embed(
                title="🔍 Search Results",
                description=f"Found {len(results)} results for: **{query}**\n\nReact to select or type number (1-5)",
                color=COLOR_INFO
            )
            
            for idx, result in enumerate(results[:5], 1):
                title = result.get('title', 'Unknown')
                duration = result.get('duration', 0)
                embed.add_field(
                    name=f"{idx}️⃣ {title[:60]}",
                    value=f"⏱️ {self.format_duration(duration)}",
                    inline=False
                )
            
            await msg.edit(embed=embed)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Search error: {str(e)[:100]}",
                color=COLOR_ERROR
            )
            await msg.edit(embed=embed)
    
    @commands.hybrid_command(name="lyrics")
    async def lyrics(self, ctx, *, song_name: str = None):
        """Fetch song lyrics"""
        if song_name is None:
            queue = self.get_queue(ctx.guild.id)
            if not queue.current:
                embed = discord.Embed(
                    title="❌ No Song",
                    description="No song currently playing. Specify song name.",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed)
                return
            song_name = queue.current['title']
        
        loading_embed = discord.Embed(
            title="🔄 Fetching lyrics...",
            description=f"Looking for: **{song_name}**",
            color=COLOR_INFO
        )
        msg = await ctx.send(embed=loading_embed)
        
        try:
            # Using a simple lyrics API
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.genius.com/search?q={song_name}") as resp:
                    if resp.status != 200:
                        embed = discord.Embed(
                            title="❌ Lyrics Not Found",
                            description=f"Could not find lyrics for: **{song_name}**",
                            color=COLOR_ERROR
                        )
                        await msg.edit(embed=embed)
                        return
                    
                    data = await resp.json()
                    hits = data.get('response', {}).get('hits', [])
                    
                    if not hits:
                        embed = discord.Embed(
                            title="❌ No Lyrics Found",
                            description=f"Could not find lyrics for: **{song_name}**",
                            color=COLOR_ERROR
                        )
                        await msg.edit(embed=embed)
                        return
                    
                    result = hits[0]['result']
                    embed = discord.Embed(
                        title="📝 Lyrics Found",
                        description=f"**{result['title']}** by {result['primary_artist']['name']}",
                        color=COLOR_INFO
                    )
                    embed.add_field(
                        name="View Full Lyrics",
                        value=f"[Click here]({result['url']})",
                        inline=False
                    )
                    
                    if result.get('song_art_image_url'):
                        embed.set_thumbnail(url=result['song_art_image_url'])
                    
                    await msg.edit(embed=embed)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Lyrics fetch error: {str(e)[:100]}",
                color=COLOR_ERROR
            )
            await msg.edit(embed=embed)
    
    # ==================== PLAYLIST COMMANDS ====================
    
    @commands.hybrid_command(name="playlist")
    async def playlist(self, ctx, action: str = None, *, name: str = None):
        """Manage playlists: create/add/remove/delete/list/load"""
        
        if action is None:
            embed = discord.Embed(
                title="📋 Playlist Commands",
                description="Usage: `!playlist [action] [name]`",
                color=COLOR_INFO
            )
            embed.add_field(name="create [name]", value="Create new playlist", inline=False)
            embed.add_field(name="add [name]", value="Add current song to playlist", inline=False)
            embed.add_field(name="remove [name] [position]", value="Remove song from playlist", inline=False)
            embed.add_field(name="delete [name]", value="Delete entire playlist", inline=False)
            embed.add_field(name="list", value="Show all playlists", inline=False)
            embed.add_field(name="load [name]", value="Load playlist into queue", inline=False)
            embed.add_field(name="info [name]", value="Show playlist details", inline=False)
            await ctx.send(embed=embed)
            return
        
        user_id = ctx.author.id
        if user_id not in self.playlists:
            self.playlists[user_id] = {}
        
        action = action.lower()
        
        if action == "create":
            if not name:
                embed = discord.Embed(
                    title="❌ No Name",
                    description="Please provide a playlist name",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            if name in self.playlists[user_id]:
                embed = discord.Embed(
                    title="❌ Exists",
                    description=f"Playlist **{name}** already exists",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            self.playlists[user_id][name] = []
            
            embed = discord.Embed(
                title="✅ Playlist Created",
                description=f"**{name}** created successfully",
                color=COLOR_SUCCESS
            )
            await ctx.send(embed=embed, delete_after=10)
        
        elif action == "add":
            queue = self.get_queue(ctx.guild.id)
            if not queue.current:
                embed = discord.Embed(
                    title="❌ No Song",
                    description="No song currently playing",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            if not name:
                embed = discord.Embed(
                    title="❌ No Playlist",
                    description="Please provide a playlist name",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            if name not in self.playlists[user_id]:
                embed = discord.Embed(
                    title="❌ Not Found",
                    description=f"Playlist **{name}** not found",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            self.playlists[user_id][name].append(queue.current)
            
            embed = discord.Embed(
                title="✅ Added to Playlist",
                description=f"**{queue.current['title']}** added to **{name}**",
                color=COLOR_SUCCESS
            )
            embed.set_thumbnail(url=queue.current['thumbnail'])
            await ctx.send(embed=embed, delete_after=10)
        
        elif action == "list":
            if not self.playlists[user_id]:
                embed = discord.Embed(
                    title="📭 No Playlists",
                    description="You don't have any playlists",
                    color=COLOR_INFO
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="📋 Your Playlists",
                color=COLOR_MUSIC
            )
            
            for pl_name, tracks in self.playlists[user_id].items():
                embed.add_field(
                    name=f"📁 {pl_name}",
                    value=f"**{len(tracks)}** songs",
                    inline=True
                )
            
            await ctx.send(embed=embed)
        
        elif action == "info":
            if not name:
                embed = discord.Embed(
                    title="❌ No Playlist",
                    description="Please provide a playlist name",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            if name not in self.playlists[user_id]:
                embed = discord.Embed(
                    title="❌ Not Found",
                    description=f"Playlist **{name}** not found",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            tracks = self.playlists[user_id][name]
            
            embed = discord.Embed(
                title=f"📋 {name}",
                description=f"**{len(tracks)}** songs",
                color=COLOR_MUSIC
            )
            
            for idx, track in enumerate(tracks[:5], 1):
                embed.add_field(
                    name=f"{idx}. {track['title']}",
                    value=f"⏱️ {self.format_duration(track['duration'])}",
                    inline=False
                )
            
            if len(tracks) > 5:
                embed.add_field(
                    name="...",
                    value=f"and {len(tracks) - 5} more songs",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        elif action == "load":
            if not name:
                embed = discord.Embed(
                    title="❌ No Playlist",
                    description="Please provide a playlist name",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            if name not in self.playlists[user_id]:
                embed = discord.Embed(
                    title="❌ Not Found",
                    description=f"Playlist **{name}** not found",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            queue = self.get_queue(ctx.guild.id)
            tracks = self.playlists[user_id][name]
            
            for track in tracks:
                queue.add(track)
            
            embed = discord.Embed(
                title="✅ Playlist Loaded",
                description=f"**{len(tracks)}** songs added to queue from **{name}**",
                color=COLOR_SUCCESS
            )
            await ctx.send(embed=embed, delete_after=10)
        
        elif action == "delete":
            if not name:
                embed = discord.Embed(
                    title="❌ No Playlist",
                    description="Please provide a playlist name",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            if name not in self.playlists[user_id]:
                embed = discord.Embed(
                    title="❌ Not Found",
                    description=f"Playlist **{name}** not found",
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            
            del self.playlists[user_id][name]
            
            embed = discord.Embed(
                title="✅ Playlist Deleted",
                description=f"**{name}** has been deleted",
                color=COLOR_SUCCESS
            )
            await ctx.send(embed=embed, delete_after=10)
    
    # ==================== FAVORITES COMMANDS ====================
    
    @commands.hybrid_command(name="favorite", aliases=["like"])
    async def favorite(self, ctx):
        """Add current song to favorites"""
        queue = self.get_queue(ctx.guild.id)
        
        if not queue.current:
            embed = discord.Embed(
                title="❌ No Song",
                description="No song currently playing",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        user_id = ctx.author.id
        if user_id not in self.favorites:
            self.favorites[user_id] = []
        
        track = queue.current
        
        # Check if already favorited
        if any(t['url'] == track['url'] for t in self.favorites[user_id]):
            embed = discord.Embed(
                title="⚠️ Already Favorited",
                description="This song is already in your favorites",
                color=COLOR_WARNING
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        self.favorites[user_id].append(track)
        
        embed = discord.Embed(
            title="❤️ Added to Favorites",
            description=f"**{track['title']}**",
            color=COLOR_SUCCESS
        )
        embed.set_thumbnail(url=track['thumbnail'])
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="myfavorites")
    async def myfavorites(self, ctx, page: int = 1):
        """Show your favorite songs"""
        user_id = ctx.author.id
        
        if user_id not in self.favorites or not self.favorites[user_id]:
            embed = discord.Embed(
                title="📭 No Favorites",
                description="You don't have any favorite songs yet",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed)
            return
        
        favorites = self.favorites[user_id]
        per_page = 5
        total_pages = math.ceil(len(favorites) / per_page)
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        display = favorites[start_idx:end_idx]
        
        embed = discord.Embed(
            title="❤️ Your Favorites",
            color=COLOR_MUSIC
        )
        
        for idx, track in enumerate(display, start=start_idx + 1):
            embed.add_field(
                name=f"{idx}. {track['title']}",
                value=f"⏱️ {self.format_duration(track['duration'])} • *by {track['uploader']}*",
                inline=False
            )
        
        embed.set_footer(text=f"Page {page}/{total_pages} | Total: {len(favorites)} favorites")
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="unfavorite")
    async def unfavorite(self, ctx, position: int):
        """Remove song from favorites by position"""
        user_id = ctx.author.id
        
        if user_id not in self.favorites or not self.favorites[user_id]:
            embed = discord.Embed(
                title="📭 No Favorites",
                description="You don't have any favorite songs",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if not 1 <= position <= len(self.favorites[user_id]):
            embed = discord.Embed(
                title="❌ Invalid Position",
                description=f"Position must be 1-{len(self.favorites[user_id])}",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        removed = self.favorites[user_id].pop(position - 1)
        
        embed = discord.Embed(
            title="💔 Removed from Favorites",
            description=f"**{removed['title']}**",
            color=COLOR_INFO
        )
        embed.set_thumbnail(url=removed['thumbnail'])
        await ctx.send(embed=embed, delete_after=10)
    
    # ==================== HISTORY & STATS ====================
    
    @commands.hybrid_command(name="history")
    async def history(self, ctx, page: int = 1):
        """Show recently played songs this session"""
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        
        if not queue.history:
            embed = discord.Embed(
                title="📭 No History",
                description="No songs have been played yet",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed)
            return
        
        per_page = 5
        total_pages = math.ceil(len(queue.history) / per_page)
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        display = queue.history[start_idx:end_idx]
        
        embed = discord.Embed(
            title="📜 Recently Played",
            color=COLOR_MUSIC
        )
        
        for idx, track in enumerate(display, start=start_idx + 1):
            embed.add_field(
                name=f"{idx}. {track['title']}",
                value=f"⏱️ {self.format_duration(track['duration'])}",
                inline=False
            )
        
        embed.set_footer(text=f"Page {page}/{total_pages} | Total: {len(queue.history)} played")
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="musicstats")
    async def musicstats(self, ctx):
        """Show music statistics for this server"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.guild_stats:
            embed = discord.Embed(
                title="📊 Music Stats",
                description="No statistics yet",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed)
            return
        
        stats = self.guild_stats[guild_id]
        
        embed = discord.Embed(
            title="📊 Server Music Stats",
            color=COLOR_MUSIC
        )
        embed.add_field(name="🎵 Total Plays", value=stats.get('plays', 0), inline=True)
        embed.add_field(name="⏭️ Total Skips", value=stats.get('skips', 0), inline=True)
        embed.add_field(name="👥 Server", value=ctx.guild.name, inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="userstats")
    async def userstats(self, ctx):
        """Show your music statistics"""
        user_id = ctx.author.id
        
        if user_id not in self.user_stats:
            embed = discord.Embed(
                title="📊 Your Music Stats",
                description="No statistics yet",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed)
            return
        
        stats = self.user_stats[user_id]
        
        embed = discord.Embed(
            title="📊 Your Music Stats",
            color=COLOR_MUSIC
        )
        embed.add_field(name="🎵 Songs Requested", value=stats.get('requested', 0), inline=True)
        embed.add_field(name="❤️ Favorites", value=len(self.favorites.get(user_id, [])), inline=True)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else "")
        
        await ctx.send(embed=embed)
    
    # ==================== DOWNLOAD COMMAND ====================
    
    @commands.hybrid_command(name="download")
    async def download(self, ctx, *, query: str, format: str = "mp3"):
        """Download music in any format (mp3/wav/m4a/flac/opus)
        
        ⏱️ Files stored for 15 minutes only
        📦 Files over 20MB sent as link only
        """
        
        # Check permissions
        if not self.has_permission(ctx, "play"):
            embed = discord.Embed(
                title="❌ No Permission",
                description="You cannot use music commands",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        # Validate format
        valid_formats = ["mp3", "wav", "m4a", "flac", "opus"]
        format = format.lower()
        
        if format not in valid_formats:
            embed = discord.Embed(
                title="❌ Invalid Format",
                description=f"Supported formats: {', '.join(valid_formats)}",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        loading_embed = discord.Embed(
            title="🔄 Processing...",
            description=f"Downloading and converting to **{format.upper()}**...\nThis may take 30-60 seconds",
            color=COLOR_INFO
        )
        msg = await ctx.send(embed=loading_embed)
        
        try:
            # Parse format from query if provided
            query_parts = query.rsplit(None, 1)
            if len(query_parts) == 2 and query_parts[1].lower() in valid_formats:
                song_query = query_parts[0]
                format = query_parts[1].lower()
            else:
                song_query = query
            
            # Search for song
            results = await YTDLSource.search(song_query)
            
            if not results:
                embed = discord.Embed(
                    title="❌ Not Found",
                    description=f"No songs found for: **{song_query}**",
                    color=COLOR_ERROR
                )
                await msg.edit(embed=embed)
                return
            
            # Use first result
            track_data = results[0]
            url = f"https://www.youtube.com/watch?v={track_data['id']}"
            
            # Download and convert
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': False,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                title = info.get('title', 'unknown')
                duration = info.get('duration', 0)
                uploader = info.get('uploader', 'Unknown')
            
            # Convert to desired format
            output_path = os.path.join(TEMP_DIR, f"{title[:50]}_{ctx.author.id}.{format}")
            
            # FFmpeg conversion
            ffmpeg_cmd = self.get_ffmpeg_command(audio_url, output_path, format)
            
            process = await asyncio.create_subprocess_shell(
                ffmpeg_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            await process.wait()
            
            if not os.path.exists(output_path):
                embed = discord.Embed(
                    title="❌ Conversion Failed",
                    description="Could not convert audio file",
                    color=COLOR_ERROR
                )
                await msg.edit(embed=embed)
                return
            
            # Check file size
            file_size = os.path.getsize(output_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # Track temp file
            self.temp_files[output_path] = datetime.now()
            
            # Create embed response
            embed = discord.Embed(
                title="✅ Download Ready",
                description=f"**{title}**",
                color=COLOR_SUCCESS
            )
            embed.add_field(name="Artist", value=uploader, inline=True)
            embed.add_field(name="Format", value=format.upper(), inline=True)
            embed.add_field(name="Size", value=f"{file_size_mb:.1f} MB", inline=True)
            embed.add_field(name="Duration", value=self.format_duration(duration), inline=True)
            embed.add_field(name="⏱️ Expires in", value="15 minutes", inline=True)
            
            # Send file or link based on size
            if file_size > MAX_FILE_SIZE:
                # File too large - send link only
                download_link = f"[Download Link]({url})"
                embed.set_field_at(
                    0,
                    name="✅ Download Ready",
                    value=f"**{title}**\n\n⚠️ File exceeds 20MB limit\nFile cannot be uploaded directly",
                    inline=False
                )
                embed.add_field(
                    name="🔗 Download",
                    value=download_link,
                    inline=False
                )
                embed.add_field(
                    name="📌 Note",
                    value="Download link valid for 24 hours",
                    inline=False
                )
                embed.color = COLOR_WARNING
                
                await msg.edit(embed=embed)
            else:
                # File small enough - send file AND link
                embed.add_field(
                    name="📥 File",
                    value="Check attachment below",
                    inline=False
                )
                embed.add_field(
                    name="🔗 Alternative Link",
                    value=f"[Download from YouTube]({url})",
                    inline=False
                )
                
                try:
                    await msg.edit(embed=embed)
                    await ctx.send(file=discord.File(output_path, filename=f"{title[:50]}.{format}"))
                except discord.errors.HTTPException as e:
                    if "payload too large" in str(e).lower():
                        embed.color = COLOR_WARNING
                        embed.set_field_at(
                            -1,
                            name="⚠️ File Too Large for Upload",
                            value=f"[Download from YouTube]({url})",
                            inline=False
                        )
                        await msg.edit(embed=embed)
                    else:
                        raise
        
        except Exception as e:
            print(f"[Music Download] Error: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Download error: {str(e)[:100]}",
                color=COLOR_ERROR
            )
            await msg.edit(embed=embed)
    
    def get_ffmpeg_command(self, input_url, output_path, format):
        """Build FFmpeg command for format conversion"""
        
        format_options = {
            "mp3": "-codec:a libmp3lame -q:a 4",  # Good quality
            "wav": "-codec:a pcm_s16le",  # Lossless
            "m4a": "-codec:a aac -b:a 192k",  # Balanced
            "flac": "-codec:a flac",  # Lossless
            "opus": "-codec:a libopus -b:a 128k"  # Efficient
        }
        
        opts = format_options.get(format, "-codec:a libmp3lame -q:a 4")
        
        cmd = f'ffmpeg -i "{input_url}" {opts} "{output_path}" -y'
        return cmd
    
    # ==================== VOICE MANAGEMENT ====================
    
    @commands.hybrid_command(name="join", aliases=["connect"])
    async def join(self, ctx):
        """Join your voice channel"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Not in Voice",
                description="You must be in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed)
            return
        
        if ctx.voice_client:
            if ctx.voice_client.channel == ctx.author.voice.channel:
                embed = discord.Embed(
                    title="✅ Already Connected",
                    description=f"Already in **{ctx.author.voice.channel.name}**",
                    color=COLOR_INFO
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            else:
                await ctx.voice_client.move_to(ctx.author.voice.channel)
        else:
            await ctx.author.voice.channel.connect()
        
        embed = discord.Embed(
            title="✅ Joined",
            description=f"Connected to **{ctx.author.voice.channel.name}**",
            color=COLOR_SUCCESS
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="leave")
    async def leave(self, ctx):
        """Leave voice channel"""
        if not ctx.voice_client:
            embed = discord.Embed(
                title="❌ Not Connected",
                description="Bot is not in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        queue = self.get_queue(ctx.guild.id)
        queue.clear()
        queue.current = None
        
        await ctx.voice_client.disconnect()
        
        embed = discord.Embed(
            title="👋 Disconnected",
            description="Left voice channel",
            color=COLOR_INFO
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="move")
    async def move(self, ctx, *, channel: discord.VoiceChannel):
        """Move bot to different voice channel"""
        if not ctx.voice_client:
            embed = discord.Embed(
                title="❌ Not Connected",
                description="Bot is not in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        await ctx.voice_client.move_to(channel)
        
        embed = discord.Embed(
            title="✅ Moved",
            description=f"Moved to **{channel.name}**",
            color=COLOR_SUCCESS
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="status")
    async def status(self, ctx):
        """Show bot voice channel status"""
        if not ctx.voice_client:
            embed = discord.Embed(
                title="❌ Not Connected",
                description="Bot is not in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed)
            return
        
        queue = self.get_queue(ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Bot Status",
            color=COLOR_MUSIC
        )
        embed.add_field(name="🎤 Channel", value=ctx.voice_client.channel.name, inline=True)
        embed.add_field(name="👥 Users", value=len([m for m in ctx.voice_client.channel.members if not m.bot]), inline=True)
        embed.add_field(name="▶️ Playing", value="Yes" if ctx.voice_client.is_playing() else "No", inline=True)
        embed.add_field(name="⏸️ Paused", value="Yes" if ctx.voice_client.is_paused() else "No", inline=True)
        embed.add_field(name="🎵 Queue Length", value=len(queue.queue), inline=True)
        embed.add_field(name="🔊 Volume", value=f"{int(ctx.voice_client.source.volume * 100)}%", inline=True)
        
        if queue.current:
            embed.add_field(name="Now Playing", value=f"**{queue.current['title']}**", inline=False)
        
        await ctx.send(embed=embed)
    
    # ==================== DJ PERMISSIONS ====================
    
    @commands.hybrid_command(name="djrole")
    async def djrole(self, ctx, action: str = None, *, role: discord.Role = None):
        """Set or check DJ role for this server"""
        if not ctx.author.guild_permissions.administrator and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only admin or owner can manage DJ role",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if action is None:
            current_role = self.dj_roles.get(ctx.guild.id, "dj.exe")
            embed = discord.Embed(
                title="🎵 DJ Role",
                description=f"Current DJ role: **{current_role}**",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed)
            return
        
        action = action.lower()
        
        if action == "set" and role:
            self.dj_roles[ctx.guild.id] = role.name
            
            embed = discord.Embed(
                title="✅ DJ Role Set",
                description=f"DJ role set to **{role.name}**",
                color=COLOR_SUCCESS
            )
            await ctx.send(embed=embed, delete_after=10)
        elif action == "reset":
            self.dj_roles[ctx.guild.id] = "dj.exe"
            
            embed = discord.Embed(
                title="✅ DJ Role Reset",
                description="DJ role reset to **dj.exe**",
                color=COLOR_SUCCESS
            )
            await ctx.send(embed=embed, delete_after=10)
        else:
            embed = discord.Embed(
                title="❌ Invalid Action",
                description="Usage: `!djrole set [role]` or `!djrole reset`",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
    
    # ==================== MODERATION ====================
    
    @commands.hybrid_command(name="musicchannel")
    async def musicchannel(self, ctx, action: str = None, *, channel: discord.TextChannel = None):
        """Set music-only text channel"""
        if not ctx.author.guild_permissions.administrator and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only admin or owner can set music channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if action is None:
            if ctx.guild.id in self.music_channels:
                channel_id = self.music_channels[ctx.guild.id]
                embed = discord.Embed(
                    title="🎵 Music Channel",
                    description=f"Music commands restricted to <#{channel_id}>",
                    color=COLOR_INFO
                )
            else:
                embed = discord.Embed(
                    title="🎵 Music Channel",
                    description="No restriction (music works in all channels)",
                    color=COLOR_INFO
                )
            await ctx.send(embed=embed)
            return
        
        action = action.lower()
        
        if action == "set" and channel:
            self.music_channels[ctx.guild.id] = channel.id
            
            embed = discord.Embed(
                title="✅ Music Channel Set",
                description=f"Music commands now restricted to <#{channel.id}>",
                color=COLOR_SUCCESS
            )
            await ctx.send(embed=embed, delete_after=10)
        elif action == "reset":
            if ctx.guild.id in self.music_channels:
                del self.music_channels[ctx.guild.id]
            
            embed = discord.Embed(
                title="✅ Music Channel Reset",
                description="Music works in all channels",
                color=COLOR_SUCCESS
            )
            await ctx.send(embed=embed, delete_after=10)
        else:
            embed = discord.Embed(
                title="❌ Invalid Action",
                description="Usage: `!musicchannel set [channel]` or `!musicchannel reset`",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
    
    @commands.hybrid_command(name="banuser")
    async def banuser(self, ctx, user: discord.User):
        """Ban user from music commands"""
        if not self.has_permission(ctx, "stop"):
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only DJ or Admin can ban users",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if ctx.guild.id not in self.banned_users:
            self.banned_users[ctx.guild.id] = set()
        
        self.banned_users[ctx.guild.id].add(user.id)
        
        embed = discord.Embed(
            title="🚫 User Banned",
            description=f"**{user}** banned from music commands",
            color=COLOR_WARNING
        )
        await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="unbanuser")
    async def unbanuser(self, ctx, user: discord.User):
        """Unban user from music commands"""
        if not self.has_permission(ctx, "stop"):
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only DJ or Admin can unban users",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        
        if ctx.guild.id in self.banned_users and user.id in self.banned_users[ctx.guild.id]:
            self.banned_users[ctx.guild.id].remove(user.id)
            
            embed = discord.Embed(
                title="✅ User Unbanned",
                description=f"**{user}** unbanned from music commands",
                color=COLOR_SUCCESS
            )
            await ctx.send(embed=embed, delete_after=10)
        else:
            embed = discord.Embed(
                title="❌ Not Banned",
                description=f"**{user}** is not banned",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
    
    # ==================== HELP & INFO ====================
    
    @commands.hybrid_command(name="musichelp")
    async def musichelp(self, ctx):
        """Show all music commands"""
        embed = discord.Embed(
            title="🎵 Music Commands",
            description="Complete command list",
            color=COLOR_MUSIC
        )
        
        embed.add_field(
            name="▶️ Playback",
            value="`play/p`, `pause`, `resume`, `skip`, `stop`, `volume`, `loop`, `shuffle`",
            inline=False
        )
        embed.add_field(
            name="📋 Queue",
            value="`queue/q`, `nowplaying/np`, `remove`, `clear`, `skipto`, `playtop`",
            inline=False
        )
        embed.add_field(
            name="🔍 Search",
            value="`search`, `lyrics`",
            inline=False
        )
        embed.add_field(
            name="📁 Playlists",
            value="`playlist create/add/list/load/info/delete`",
            inline=False
        )
        embed.add_field(
            name="❤️ Favorites",
            value="`favorite/like`, `myfavorites`, `unfavorite`",
            inline=False
        )
        embed.add_field(
            name="📊 Stats & History",
            value="`history`, `musicstats`, `userstats`",
            inline=False
        )
        embed.add_field(
            name="📥 Download",
            value="`download [song] [format]` - mp3/wav/m4a/flac/opus (15min storage)",
            inline=False
        )
        embed.add_field(
            name="🎤 Voice",
            value="`join`, `leave`, `move`, `status`",
            inline=False
        )
        embed.add_field(
            name="🎵 Settings",
            value="`djrole`, `musicchannel`, `banuser`, `unbanuser`",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="musicinfo")
    async def musicinfo(self, ctx):
        """Show music bot information"""
        embed = discord.Embed(
            title="🎵 Lucky Bot Music",
            description="All-in-One Music System",
            color=COLOR_MUSIC
        )
        embed.add_field(
            name="Features",
            value="Play, Queue, Playlists, Favorites, Lyrics, Download, Stats",
            inline=False
        )
        embed.add_field(
            name="Sources",
            value="YouTube",
            inline=True
        )
        embed.add_field(
            name="Download Formats",
            value="MP3, WAV, M4A, FLAC, OPUS",
            inline=True
        )
        embed.add_field(
            name="Storage",
            value="15 minutes for temp files",
            inline=True
        )
        embed.add_field(
            name="Prefix + Slash",
            value="All commands available in both",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # ==================== AFTER PLAYING ====================
    
    async def after_playing(self, ctx):
        """Called when a song finishes"""
        queue = self.get_queue(ctx.guild.id)
        
        # Add to history
        if queue.current:
            if ctx.guild.id not in self.history:
                self.history[ctx.guild.id] = []
            self.history[ctx.guild.id].append(queue.current)
            queue.history.append(queue.current)
        
        # Handle loop modes
        if queue.loop_mode == 1:  # Loop song
            queue.add_next(queue.current)
        elif queue.loop_mode == 2:  # Loop queue
            queue.add(queue.current)
        
        # Get next song
        if queue.queue:
            next_track = queue.skip()
            queue.current = next_track
            
            source = next_track['source']
            ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.after_playing(ctx), self.bot.loop).result())
        else:
            queue.is_playing = False
            queue.current = None


async def setup(bot):
    """Load music cog"""
    await bot.add_cog(Music(bot))
