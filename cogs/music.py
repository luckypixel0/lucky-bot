"""
Lucky Bot Music Cog - SIMPLIFIED VERSION
Direct YouTube streaming - No conversion, no complex setup
"""

import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random
from datetime import datetime

# Colors for embeds
COLOR_SUCCESS = 0x2ECC71
COLOR_INFO = 0x3498DB
COLOR_WARNING = 0xF39C12
COLOR_ERROR = 0xE74C3C
COLOR_MUSIC = 0x9B59B6


class Music(commands.Cog):
    """Lucky Bot Music - Simple YouTube Player"""
    
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # {guild_id: [tracks]}
        self.now_playing = {}  # {guild_id: current_track}
    
    def format_duration(self, seconds):
        """Convert seconds to MM:SS"""
        if not seconds:
            return "00:00"
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"
    
    def get_queue(self, guild_id):
        """Get or create queue for guild"""
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]
    
    async def get_youtube_url(self, query):
        """Search YouTube and get first result URL"""
        try:
            ydl_opts = {
                'format': 'bestaudio',
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch',
                'socket_timeout': 30,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                'noplaylist': True,
                'skip_unavailable_fragments': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"[Music] Searching for: {query}")
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: ydl.extract_info(query, download=False)
                )
            
            if not result:
                print("[Music] No result from yt-dlp")
                return None
            
            # Get URL - try different methods
            url = result.get('url')
            
            # If no direct URL, try formats
            if not url and result.get('formats'):
                print("[Music] Trying to get URL from formats")
                for fmt in result.get('formats', []):
                    if fmt.get('url'):
                        url = fmt['url']
                        break
            
            # If still no URL, try webpage_url
            if not url:
                url = result.get('webpage_url')
                print(f"[Music] Using webpage_url: {url}")
            
            if not url:
                print("[Music] ERROR: Could not find URL in result")
                print(f"[Music] Result keys: {result.keys()}")
                return None
            
            print(f"[Music] Got URL successfully")
            
            title = result.get('title', 'Unknown')
            duration = result.get('duration', 0)
            uploader = result.get('uploader', 'Unknown')
            thumbnail = result.get('thumbnail', '')
            
            return {
                'url': url,
                'title': title,
                'duration': duration,
                'uploader': uploader,
                'thumbnail': thumbnail
            }
        except Exception as e:
            print(f"[Music] YouTube error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @commands.hybrid_command(name="play", aliases=["p"])
    async def play(self, ctx, *, query):
        """Play a song from YouTube"""
        
        # Check if user in voice
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Not in Voice",
                description="You must be in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed)
            return
        
        # Loading message
        loading = discord.Embed(
            title="🔄 Searching YouTube...",
            description=f"Query: **{query}**",
            color=COLOR_INFO
        )
        msg = await ctx.send(embed=loading)
        
        # Get YouTube URL
        track_info = await self.get_youtube_url(query)
        
        if not track_info or not track_info.get('url'):
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"Could not find or load: **{query}**\n\nTry a different song name",
                color=COLOR_ERROR
            )
            await msg.edit(embed=embed)
            return
        
        # Join voice channel
        vc = ctx.voice_client
        if vc is None:
            try:
                vc = await ctx.author.voice.channel.connect()
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Connection Failed",
                    description=f"Could not join: {str(e)[:50]}",
                    color=COLOR_ERROR
                )
                await msg.edit(embed=embed)
                return
        
        # Try to play
        try:
            if not track_info['url']:
                embed = discord.Embed(
                    title="❌ No Audio URL",
                    description="Could not extract audio from video",
                    color=COLOR_ERROR
                )
                await msg.edit(embed=embed)
                return
            
            print(f"[Music] Creating FFmpeg audio from URL: {track_info['url'][:50]}...")
            
            audio = discord.FFmpegPCMAudio(
                track_info['url'],
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                options='-vn'
            )
            
            def after_finish(error):
                if error:
                    print(f"[Music] Playback error: {error}")
                # Play next song if queue exists
                queue = self.get_queue(ctx.guild.id)
                if queue:
                    asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
            
            vc.play(audio, after=after_finish)
            self.now_playing[ctx.guild.id] = track_info
            
            # Show now playing
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**{track_info['title']}**",
                color=COLOR_MUSIC
            )
            embed.add_field(name="Artist", value=track_info['uploader'], inline=True)
            embed.add_field(name="Duration", value=self.format_duration(track_info['duration']), inline=True)
            embed.add_field(name="Requested by", value=ctx.author.mention, inline=True)
            if track_info['thumbnail']:
                embed.set_thumbnail(url=track_info['thumbnail'])
            
            await msg.edit(embed=embed)
            print("[Music] Now playing!")
            
        except Exception as e:
            print(f"[Music] Play error: {e}")
            import traceback
            traceback.print_exc()
            embed = discord.Embed(
                title="❌ Playback Failed",
                description=f"Error: {str(e)[:100]}",
                color=COLOR_ERROR
            )
            await msg.edit(embed=embed)
    
    async def play_next(self, ctx):
        """Play next song in queue"""
        queue = self.get_queue(ctx.guild.id)
        if queue and ctx.voice_client:
            next_track = queue.pop(0)
            try:
                audio = discord.FFmpegPCMAudio(
                    next_track['url'],
                    before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    options='-vn'
                )
                ctx.voice_client.play(audio, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
                self.now_playing[ctx.guild.id] = next_track
            except Exception as e:
                print(f"[Music] Queue play error: {e}")
    
    @commands.hybrid_command(name="pause")
    async def pause(self, ctx):
        """Pause music"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            embed = discord.Embed(
                title="⏸️ Paused",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed, delete_after=10)
        else:
            embed = discord.Embed(
                title="❌ Nothing Playing",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
    
    @commands.hybrid_command(name="resume", aliases=["unpause"])
    async def resume(self, ctx):
        """Resume music"""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            embed = discord.Embed(
                title="▶️ Resumed",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed, delete_after=10)
        else:
            embed = discord.Embed(
                title="❌ Not Paused",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=5)
    
    @commands.hybrid_command(name="stop")
    async def stop(self, ctx):
        """Stop music and leave voice"""
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            self.queues[ctx.guild.id] = []
            self.now_playing.pop(ctx.guild.id, None)
            
            embed = discord.Embed(
                title="⏹️ Stopped",
                description="Bot disconnected",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="join")
    async def join(self, ctx):
        """Join voice channel"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Not in Voice",
                description="You must be in a voice channel",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed)
            return
        
        try:
            await ctx.author.voice.channel.connect()
            embed = discord.Embed(
                title="✅ Joined",
                description=f"Connected to **{ctx.author.voice.channel.name}**",
                color=COLOR_SUCCESS
            )
            await ctx.send(embed=embed, delete_after=10)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed",
                description=str(e)[:100],
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="leave")
    async def leave(self, ctx):
        """Leave voice channel"""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            embed = discord.Embed(
                title="👋 Left",
                description="Disconnected from voice",
                color=COLOR_INFO
            )
            await ctx.send(embed=embed, delete_after=10)
    
    @commands.hybrid_command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        """Show currently playing song"""
        track = self.now_playing.get(ctx.guild.id)
        
        if not track:
            embed = discord.Embed(
                title="❌ Nothing Playing",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{track['title']}**",
            color=COLOR_MUSIC
        )
        embed.add_field(name="Artist", value=track['uploader'], inline=True)
        embed.add_field(name="Duration", value=self.format_duration(track['duration']), inline=True)
        if track['thumbnail']:
            embed.set_thumbnail(url=track['thumbnail'])
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="search")
    async def search(self, ctx, *, query):
        """Search for songs"""
        loading = discord.Embed(
            title="🔄 Searching...",
            description=f"Query: **{query}**",
            color=COLOR_INFO
        )
        msg = await ctx.send(embed=loading)
        
        track = await self.get_youtube_url(query)
        
        if not track:
            embed = discord.Embed(
                title="❌ Not Found",
                color=COLOR_ERROR
            )
            await msg.edit(embed=embed)
            return
        
        embed = discord.Embed(
            title="🔍 Found",
            description=f"**{track['title']}**",
            color=COLOR_SUCCESS
        )
        embed.add_field(name="Artist", value=track['uploader'], inline=True)
        embed.add_field(name="Duration", value=self.format_duration(track['duration']), inline=True)
        if track['thumbnail']:
            embed.set_thumbnail(url=track['thumbnail'])
        
        await msg.edit(embed=embed)
    
    @commands.hybrid_command(name="musichelp")
    async def musichelp(self, ctx):
        """Show music commands"""
        embed = discord.Embed(
            title="🎵 Music Commands",
            color=COLOR_MUSIC
        )
        embed.add_field(name="▶️ Playback", value="`play`, `pause`, `resume`, `stop`", inline=False)
        embed.add_field(name="🎤 Voice", value="`join`, `leave`", inline=False)
        embed.add_field(name="🔍 Info", value="`search`, `nowplaying`", inline=False)
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Load music cog"""
    await bot.add_cog(Music(bot))
