import discord
import os
import random
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv('token.env')
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command('help')

music_state = {
    'queue': [],
    'current_folder': "",
    'current_song': None,
    'volume': 0.5,
    'idle_minutes': 0 
}
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    check_inactivity.start() 

@tasks.loop(minutes=1.0)
async def check_inactivity():
    for vc in bot.voice_clients:
        is_alone = len([m for m in vc.channel.members if not m.bot]) == 0
        is_idle = not vc.is_playing()

        if is_alone or is_idle:
            music_state['idle_minutes'] += 1
            if music_state['idle_minutes'] >= 5:
                await vc.disconnect()
                music_state['idle_minutes'] = 0
                music_state['queue'].clear()
                music_state['current_song'] = None
                print("Disconnected from voice due to 5 minutes of inactivity.")
        else:
            music_state['idle_minutes'] = 0

async def start_playing(ctx, folder_path):
    music_state['current_folder'] = folder_path

    if not ctx.author.voice:
        return await ctx.send("You need to be in a voice channel")
    
    if not ctx.voice_client:
        try:
            vc = await ctx.author.voice.channel.connect(timeout=20.0, reconnect=True)
        except Exception as e:
            return await ctx.send(f"Failed to connect: {e}")
    else:
        vc = ctx.voice_client

    if vc.is_playing():
        vc.stop()
    
    music_state['queue'].clear() 

    if not os.path.exists(music_state['current_folder']):
        return await ctx.send(f"The folder `{music_state['current_folder'].strip('./')}` does not exist. Did you create it?")

    music_state['queue'] = [f for f in os.listdir(music_state['current_folder']) if f.endswith('.mp3')]
    
    if not music_state['queue']:
        return await ctx.send(f"The folder `{music_state['current_folder'].strip('./')}` is empty")

    random.shuffle(music_state['queue'])

    def play_next(error):
        if music_state['queue'] and vc.is_connected():
            next_song = music_state['queue'].pop(0)
            music_state['current_song'] = next_song
            path = os.path.join(music_state['current_folder'], next_song)
            
            audio = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(path, executable="./ffmpeg.exe"), volume=music_state['volume'])
            vc.play(audio, after=play_next)
        else:
            music_state['current_song'] = None 

    first_song = music_state['queue'].pop(0)
    music_state['current_song'] = first_song
    path = os.path.join(music_state['current_folder'], first_song)
    
    await ctx.send(f"**Loaded the `{music_state['current_folder'].strip('./')}` playlist (Shuffled automatically)**\nNow playing: **{first_song}**")
    
    audio = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(path, executable="./ffmpeg.exe"), volume=music_state['volume'])
    vc.play(audio, after=play_next)


@bot.command()
async def aura(ctx):
    await start_playing(ctx, "./aura")

@bot.command()
async def mommy(ctx):
    await start_playing(ctx, "./mommy")


@bot.command()
async def nowplaying(ctx):
    if music_state['current_song']:
        await ctx.send(f"**Currently playing:** {music_state['current_song']}")
    else:
        await ctx.send("Nothing is playing right now")

@bot.command()
async def volume(ctx, vol: int):
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel")
    
    if 0 <= vol <= 100:
        music_state['volume'] = vol / 100
        if ctx.voice_client.source:
            ctx.voice_client.source.volume = music_state['volume']
        await ctx.send(f"Volume set to **{vol}%**")
    else:
        await ctx.send("Please pick a volume between 0 and 100")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop() 
        await ctx.send("**Skipped**")
    else:
        await ctx.send("I'm not playing anything right now")

@bot.command(name="queue")
async def show_queue(ctx):
    if not music_state['queue']:
        return await ctx.send("The queue is currently empty")
    
    upcoming = music_state['queue'][:10]
    queue_text = "**upcoming songs:**\n"
    for i, song in enumerate(upcoming, 1):
        queue_text += f"{i}. {song}\n"
    
    if len(music_state['queue']) > 10:
        queue_text += f"\n*...and {len(music_state['queue']) - 10} more songs*"
        
    await ctx.send(queue_text)

@bot.command()
async def stop(ctx):
    music_state['queue'].clear()
    music_state['current_song'] = None
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Stopped the music and cleared the queue")
    else:
        await ctx.send("I'm not in a voice channel")

@bot.command()
async def shuffle(ctx):
    if len(music_state['queue']) > 1:
        random.shuffle(music_state['queue'])
        await ctx.send("**The remaining songs have been re-shuffled**")
    else:
        await ctx.send("Not enough songs to shuffle")

@bot.command()
async def unshuffle(ctx):
    if len(music_state['queue']) > 1:
        music_state['queue'].sort() 
        await ctx.send("**The remaining songs have been unshuffled (back to alphabetical order)**")
    else:
        await ctx.send("Not enough songs in the queue to unshuffle")

@bot.command()
async def help(ctx):
    help_text = """
    **Music Commands:**
    `!aura` - Loads, auto-shuffles, and plays the 'aura' playlist
    `!mommy` - Loads, auto-shuffles, and plays the 'mommy' playlist
    
    **Controls:**
    `!nowplaying` - Shows what is currently playing
    `!volume [0-100]` - Changes the bot's volume
    `!skip` - Skips the current song
    `!queue` - Shows the upcoming songs
    `!stop` - Stops music and leaves
    `!shuffle` - Randomizes the remaining queue
    `!unshuffle` - Restores the remaining queue to original alphabetical order
    `!help` - Shows this message
    """
    await ctx.send(help_text)

bot.run(TOKEN)