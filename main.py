#python3 -m pip install -U "discord.py[voice]"

import discord
import os 
import pafy
import urllib.request
import re
import random
import youtube_dl
import lyricsgenius as lg
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands,tasks
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
TOKEN = os.environ['TOKEN']
bot = commands.Bot(command_prefix = '-')
#, help_command = None)

GENIUS_ACCESS = os.environ['GENIUS_ACCESS']
genius = lg.Genius(GENIUS_ACCESS, skip_non_songs=True, excluded_terms=["(Remix)", "(Live)"], remove_section_headers=True)

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}

briefs = {'Player':{ 
            'play':'Plays song to connected channel',
            'pause':'Pauses the song currently playing',
            'resume':'Resumes the previously paused song',
            'stop':'Stops the song'},
          'Queue':{
            'clear':'Clears the queue',
            'list':'Shows the current queue',
            'next':'Plays next song in queue'},
          'Basic':{
            'join':'Adds bot to current channel',
            'exit':'Disconnects bot from user channel'},
          'Volume':{
            'volume':'Changes bot volume',
            'mute':'Mutes the bot, sets volume to 0',
            'unmute':'Unmutes the bot, sets volume to 1'},
          'Miscellaneous':{
            'playlist':'Work in progress...',
            'lyrics':'Shows lyrics for first song in queue',
            'mask':'Clones a user',
            'default':'Sets name and avatar to default',
            'xingue':'Mystery'}
          
          }

msgs = ['nao to tocando nada agora','nao to conectado...','to num outro canal bobao, nao da pra voce me manda comando nao']

queue = {}

random.seed()

def is_connected(ctx):
  voice_client = ctx.voice_client
  # if voice_client is not null check if is connected
  if voice_client:
    return voice_client.is_connected()

  return False

def sameChannel(ctx):
  # gets user's and bot's channel
  bot_channel = ctx.voice_client.channel
  user_channel = ctx.message.author.voice.channel

  return bot_channel == user_channel

def add_queue(song, url, server):
  # gets best audio source
  audio = song.getbestaudio() 
  # converts yt source to discord format
  source = FFmpegPCMAudio(audio.url, **FFMPEG_OPTIONS)

  queue[server] = queue.get(server, [])
  queue[server].append({'source':source, 'url':url})

  return

def play_next(ctx):
    if len(queue[ctx.guild.id]) > 1:
      del queue[ctx.guild.id][0]
      ctx.voice_client.play(queue[ctx.guild.id][0]['source'],after=lambda e: play_next(ctx))
      ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source, 1.0)
      ctx.voice_client.is_playing()

def get_song_info(url):
  ydl = youtube_dl.YoutubeDL({})
  with ydl:
      video = ydl.extract_info(url, download=False)

  name = video.get('track', None)
  artist = video.get('artist', None)

  if artist:
    artist = artist.split(',')[0]

  return {'name':name,'artist':artist}

def get_video_title(url):
  ydl = youtube_dl.YoutubeDL({})
  with ydl:
      video = ydl.extract_info(url, download=False)

  return video['title']

@bot.command(brief = briefs['Basic']['join'])
async def join(ctx):
  if ctx.message.author.voice and not is_connected(ctx):
    channel = ctx.message.author.voice.channel
    
  elif is_connected(ctx):
    await ctx.channel.send('ja to conectado porra')
    return

  await channel.connect()

@bot.command(name = 'p', aliases = ['play'], brief = briefs['Player']['play'])
async def connect_and_play(ctx, *arg):
   # checks if whoever issued the command is in voice
   # and connects in case it isnt already
  if ctx.message.author.voice and not is_connected(ctx):
    channel = ctx.message.author.voice.channel
    await channel.connect()
  elif is_connected(ctx):
    pass
  else:
    await ctx.channel.send('{}, se tem q ta conectado num canal pra eu entrar. Mas ja digo q se entrar num canal eh viado'.format(ctx.message.author.name))
    return

  # play requested song from arg
  if is_connected(ctx) and sameChannel(ctx):
    if arg[0].lower().startswith(('http://', 'https://')):
      url = arg[0]
    else:
      # url search format
      search = "+".join(arg)

      html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + search)

      video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())  

      url = "https://www.youtube.com/watch?v=" + video_ids[0]

    if 'list=' in url:
      await ctx.send(embed=discord.Embed(description="Please use **-playlist** to play a playlist seu merda"))
      return
    # initializes pafy object
    try:
      song = pafy.new(url)
    except:
      await ctx.send(embed=discord.Embed(description="Error has occured, please try again"))
      return

    add_queue(song, url, ctx.guild.id)

    n = random.randint(1,11)

    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
      # it's a song
      if get_song_info(queue[ctx.guild.id][0]['url'])['name']:
        note = ':musical_note:'
      else:
        note = '🎬'

      await ctx.send(embed=discord.Embed(description="{} {} pediu pra tocar:\n".format("O/A ", ctx.message.author.mention) + "[" + "**" + get_video_title(url) + "**" + "]" + "(" + url + ") " + note))

      ctx.voice_client.play(queue[ctx.guild.id][0]['source'],after=lambda e: play_next(ctx))
      ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source, 1.0)
      ctx.voice_client.is_playing()

    else:
      if ctx.voice_client.is_paused():
        await ctx.send(embed=discord.Embed(description="to pausado, **-resume** pra eu pode tocar o resto das musicas"))

      await ctx.send(embed=discord.Embed(description="Queued " + "[" + "**" + get_video_title(url) + "**" + "]" + "(" + url + ")" + " [{}]".format(ctx.message.author.mention)))

  elif is_connected(ctx):
    await ctx.channel.send('to num outro canal bobao')

@bot.command(aliases = ['skip'], brief = briefs['Queue']['next'])
async def next(ctx):
  if is_connected(ctx) and sameChannel(ctx):
    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
      if len(queue[ctx.guild.id]) == 1:
        # only one on the queue, can't skip
        await ctx.send(embed=discord.Embed(description="Can't skip, only one song in queue"))
        return

      ctx.voice_client.pause()
      await ctx.message.add_reaction('⏭️')
      play_next(ctx)

      n = random.randint(1,11)

      # it's a song
      if get_song_info(queue[ctx.guild.id][0]['url'])['name']:
        note = ':musical_note:'
      else:
        note = '🎬'

      await ctx.send(embed=discord.Embed(description="{} {} pediu pra skipa, agora tocando:\n".format("O/A ", ctx.message.author.mention) + "[" + "**" + get_video_title(queue[ctx.guild.id][0]['url']) + "**" + "]" + "(" + queue[ctx.guild.id][0]['url'] + ") " + note))
    else:
      await ctx.send(msgs[0])

  elif not is_connected(ctx):
    await ctx.channel.send(msgs[1])
    
  else:
    # user on different channel than bot
    await ctx.channel.send(msgs[2])

@bot.command(brief = briefs['Queue']['clear'])
async def clear(ctx):
  if is_connected(ctx) and sameChannel(ctx):
    if len(queue[ctx.guild.id]) > 0:
      ctx.voice_client.pause()
      queue[ctx.guild.id].clear()
      ctx.voice_client.resume()

      await ctx.send(embed=discord.Embed(description="Queue has gone to the abyss"))
    else:
      await ctx.send('nao tem nenhuma musica na queue')
  elif not is_connected(ctx):
    await ctx.channel.send(msgs[1])
  else:
    # user on different channel than bot
    await ctx.channel.send(msgs[2])

@bot.command(brief = briefs['Player']['pause'])
async def pause(ctx):
  if is_connected(ctx) and sameChannel(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
      voice_client.pause()
      await ctx.message.add_reaction('⏸️')
    else:
      await ctx.send(msgs[0])
  elif not is_connected(ctx):
    await ctx.channel.send('nao da pra pausar oq nao ta tocando')
  else:
    # user on different channel than bot
    await ctx.channel.send(msgs[2])

@bot.command(aliases = ['continue'], brief = briefs['Player']['resume'])
async def resume(ctx):
  if is_connected(ctx) and sameChannel(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
      voice_client.resume()
      await ctx.message.add_reaction('⏯️')
    else:
      await ctx.send('nao to pausado besta')
  elif not is_connected(ctx):
    await ctx.channel.send('nao da pra continua oq nunca existiu')
  else:
    # user on different channel than bot
    await ctx.channel.send(msgs[2])

@bot.command(brief = briefs['Player']['stop'])
async def stop(ctx):
  if is_connected(ctx) and sameChannel(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
      voice_client.stop()
      queue[ctx.guild.id].clear()
      await ctx.message.add_reaction('🛑')
    else:
      await ctx.send('nao to tocando nada agora besta')
  elif not is_connected(ctx):
    await ctx.channel.send('nao da pra parar se nao ta conectado')
  else:
    # user on different channel than bot
    await ctx.channel.send(msgs[2])
  
@bot.command(aliases = ['leave', 'remove'], brief = briefs['Basic']['exit'])
async def exit(ctx):
  if is_connected(ctx) and sameChannel(ctx):
    await ctx.voice_client.disconnect()
  elif is_connected(ctx):
    await ctx.send('tentou me tirar do outro canal ne fdp')
  else:
    await ctx.send('nao da pra desconectar oq nao ta conectado besta')

@bot.command(aliases = ['list', 'queue'], brief = briefs['Queue']['list'])
async def check(ctx):
  if len(queue[ctx.guild.id]) == 0:
    await ctx.send('nao tem nenhuma musica na queue')
  else:
    desc = ""

    for index, x in enumerate(queue[ctx.guild.id]):
      desc += str(index + 1) + ". " + "[" + "**" + get_video_title(x['url']) + "**" + "]" + "(" + x['url'] + ")" + "\n"

    await ctx.send(embed=discord.Embed(description=desc))  

@bot.command(brief = briefs['Miscellaneous']['playlist'])
async def playlist(ctx, arg):
  # checks if whoever issued the command is in voice
  # and connects in case it isnt already
  if ctx.message.author.voice and not is_connected(ctx):
    channel = ctx.message.author.voice.channel
    await channel.connect()
  elif is_connected(ctx):
    pass
  else:
    await ctx.channel.send('{}, se tem q ta conectado num canal pra eu entrar. Mas ja digo q se entrar num canal eh viado'.format(ctx.message.author.name))
    return

  # play requested song from arg
  if is_connected(ctx) and sameChannel(ctx):
    if arg.lower().startswith(('http://', 'https://')) and 'list=' in arg:
      url = arg
    else:
      await ctx.send('not a valid playlist')

    playlist = pafy.get_playlist2(url)
    for i in playlist['items']:
      print(i['pafy']['ID'])
      url = "https://www.youtube.com/watch?v=" + i['pafy']['ID']
      add_queue(i['pafy'], url, ctx.guild.id)
  
    n = random.randint(1,11)

    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
      # it's a song
      if get_song_info(queue[ctx.guild.id][0]['url'])['name']:
        note = ':musical_note:'
      else:
        note = '🎬'

      await ctx.send(embed=discord.Embed(description="{} {} pediu pra tocar:\n".format("O/A ", ctx.message.author.mention) + "[" + "**" + get_video_title(queue[ctx.guild.id][0]['url']) + "**" + "]" + "(" + queue[ctx.guild.id][0]['url'] + ") " + note))

      ctx.voice_client.play(queue[ctx.guild.id][0]['source'],after=lambda e: play_next(ctx))
      ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source, 1.0)
      ctx.voice_client.is_playing()

    else:
      if ctx.voice_client.is_paused():
        await ctx.send(embed=discord.Embed(description="to pausado, **-resume** pra eu pode tocar o resto das musicas"))

      await ctx.send(embed=discord.Embed(description="Queued " + "[" + "**" + playlist.title + "**" + "]" + "(" + url + ")" + "{}".format(ctx.message.author.mention)))

  elif is_connected(ctx):
    await ctx.channel.send('to num outro canal bobao')

@bot.command(brief = briefs['Miscellaneous']['lyrics'])
async def lyrics(ctx):
  if len(queue[ctx.guild.id]) == 0:
    await ctx.send('nao tem nenhuma musica tocando')
  else:
    name = get_song_info(queue[ctx.guild.id][0]['url'])['name']
    artist = get_song_info(queue[ctx.guild.id][0]['url'])['artist']

    songs = (genius.search_song(name, artist))
    hyperlinks_removed = re.sub(r"[0-9]+EmbedShare URLCopyEmbedCopy",'',songs.lyrics)
    
    try:
      await ctx.send(embed=discord.Embed(title=name,description=hyperlinks_removed))
    except discord.errors.HTTPException:
      await ctx.send(embed=discord.Embed(description="Lyrics are too big... tipo o meu pau"))

@bot.command(aliases = ['vol'], brief = briefs['Volume']['volume'])
async def volume(ctx, *arg):
  if len(queue[ctx.guild.id]) == 0:
    await ctx.send('nao tem nenhuma musica tocando')
    return
  # sends current volume
  curVol = float(ctx.voice_client.source.volume)
  if arg == ():
    await ctx.send(embed=discord.Embed(description="{}".format(int((curVol) * 100)) + "%"))
    return
  try:
    vol = float(arg[0])
    if vol >= 0 and vol <= 100:
      pass
    else:
      raise ValueError("Expected int from 0-100.")
  except:
    await ctx.send(embed=discord.Embed(description='Please input a number from 0-100 to set the volume'))
    return

  vol = vol / 100

  if vol == 0:
    await ctx.message.add_reaction("🔇")
    await ctx.send(embed=discord.Embed(description="Bot has been muted"))
  elif curVol < vol:
    await ctx.message.add_reaction("🔊")
  else:
    await ctx.message.add_reaction("🔉")

  ctx.voice_client.source.volume = vol

@bot.command(aliases = ['mutar'], brief = briefs['Volume']['mute'])
async def mute(ctx):
  if len(queue[ctx.guild.id]) == 0:
    await ctx.send('nao tem nenhuma musica tocando')
  else:
    await ctx.message.add_reaction("🔇")
    ctx.voice_client.source.volume = 0

@bot.command(aliases = ['desmutar'], brief = briefs['Volume']['unmute'])
async def unmute(ctx):
  if len(queue[ctx.guild.id]) == 0:
    await ctx.send('nao tem nenhuma musica tocando')
  elif ctx.voice_client.source.volume != 0:
    await ctx.send('nao to mutado besta')
  else:
    await ctx.message.add_reaction("🔈")
    ctx.voice_client.source.volume = 1

@bot.command(brief = briefs['Miscellaneous']['mask'])
async def mask(ctx, user: discord.Member):
  # changes bot's nickname within server
  await ctx.message.guild.me.edit(nick=user.name)
  # converts avatar url format to bytes
  avatar_bytes = await user.avatar_url.read()
  # changes bot's avatar
  await bot.user.edit(avatar = avatar_bytes)

@bot.command(brief = briefs['Miscellaneous']['default'])
async def default(ctx):
  # resets avatar and nickname to default
  await ctx.message.guild.me.edit(nick = bot.user.name)
  avatar_bytes = await bot.user.default_avatar_url.read()
  try:
    await bot.user.edit(avatar = avatar_bytes)
  except discord.errors.HTTPException:
    pass

@bot.command(aliases = ['xingue'], brief = briefs['Miscellaneous']['xingue'])
async def xinga(ctx, arg):
  n = random.randint(1,11)

  await ctx.send('{} {}'.format(arg, "cool"))

#@bot.command()
#async def help(ctx):
#  await ctx.send('```')

@bot.event
async def on_guild_join(guild):
  for channel in guild.text_channels:
    if channel.permissions_for(guild.me).send_messages:
      await channel.send('Eae seus gays, leu mamou :heart:')
    break

keep_alive()
bot.run(TOKEN)
