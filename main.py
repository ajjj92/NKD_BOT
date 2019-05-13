#attejantunen
import logging
import discord
import asyncio
from discord.ext import commands
from discord.utils import get
import youtube_dl
from functools import partial

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

logging.basicConfig(level=logging.INFO)

prefix = '.'
bot = commands.Bot(command_prefix = prefix)



@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.event
async def on_member_join(member):
    for channel in member.server.channels:
        if str(channel) == "lobby": # We check to make sure we are sending the message in the general channel
            await bot.send_message(f"""Welcome to the NKD server {member.mention}""")

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlist = []
        self.titlelist = []
        self.empty = False
        self.beforeArgs = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5" 
        
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

    @commands.command()
    async def showhelp(self, ctx):
        await ctx.send('Command prefix "."\nshowhelp\necho\nqueue\nremove\nshowq\nempty\njoin\nplaylist\nstream\nvolume\nstop\n ')

    @commands.command()
    async def queue(self, ctx, url):
        self.playlist.append(str(url))
        self.titlelist.append(ytdl.extract_info("{}".format(url)).get("title", None))
        await ctx.send(f"""Added link to queue.""", delete_after=15)
        

    @commands.command()
    async def remove(self, ctx, *, number):
        self.playlist.pop(int(number)-1)
        self.titlelist.pop(int(number)-1)
        await ctx.send('{} removed.'.format(number),delete_after=15)

    @commands.command()
    async def showq(self, ctx):
        for i in range(len(self.titlelist)):
            await ctx.send('{}: {}'.format(i+1, self.titlelist[i]))

    @commands.command()
    async def empty(self, ctx):
        self.playlist.clear()
        await ctx.send('Queue cleared.',delete_after=15)

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel=None):
        """Joins a voice channel"""

        if not channel:
            try:
                channel = ctx.author.voice.channel
                await channel.connect()
            except AttributeError:
                raise commands.CommandError('No channel to join. Please either specify a valid channel or join one.')

        vc = ctx.voice_client
        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise commands.CommandError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise commands.CommandError(f'Connecting to channel: <{channel}> timed out.')
                
    @commands.command()
    async def play(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(query))

    @commands.command()
    async def yt(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))
            
    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))
    
    async def playsong(self, ctx):
        async with ctx.typing():
            
            player = await YTDLSource.from_url(self.playlist[0], loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        await ctx.send('Now playing: {}'.format(player.title))    
            
    @commands.command()
    async def playlist(self,ctx):
        vc = ctx.voice_client
        while self.empty == False: 
            if vc.is_playing():
                await asyncio.sleep(1)
            if vc.is_playing() == False:
                    self.stream(self.playlist[0])
                    self.playlist.pop(0)
                    self.titlelist.pop(0)
            if len(self.playlist) == 0:
                self.empty = True
          
    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume),delete_after=15)

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()
'''
    @play.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()
'''

@bot.command()
async def echo(ctx, message):
    await ctx.send(message)

bot.add_cog(Music(bot))


bot.run('NTc1NzIzOTgzMzkyMjEwOTUy.XNMH3A.BOzTVp3EyxU71GAlP4fRysv9YEc')