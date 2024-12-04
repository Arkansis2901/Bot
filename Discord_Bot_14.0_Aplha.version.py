import discord
from discord.ext import commands
from discord import app_commands
import random
from collections import deque
from youtubesearchpython import SearchVideos
import yt_dlp
import json
import time
from datetime import datetime, date
import math
import asyncio
import youtube_search
import aiohttp
from dotenv import load_dotenv
import os
from discord.ext import commands
from datetime import datetime, timedelta
from discord import app_commands
import re
import os
import discord
from discord.ext import commands
from youtubesearchpython import SearchVideos
from yt_dlp import YoutubeDL
import asyncio
import uuid  # Für eindeutige Dateinamen
import shutil
import discord
from discord.ext import commands
from multiprocessing import Process
import os
import yt_dlp
from discord.ui import Button, View

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
#Alle benötigten Intents

intents = discord.Intents.all()
intents.members = True
intents.typing = True
intents.presences = True
intents.voice_states = True
intents.message_content = True
intents.moderation = True
ffmpegSource = None
voice_client = None
ban_Members = True
client = commands.Bot(command_prefix='?', intents=intents)
client.remove_command ("help")  
bot = client
user_data = {}
music_queue = {}


video_title = {}


def get_voice_client(ctx):
    """Hilfsfunktion, um den Voice-Client eines Servers zu holen."""
    return discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)

@client.command()
async def play(ctx: commands.Context, *, search_term):
    if not ctx.author.voice:
        await ctx.send("Du musst in einem Sprachkanal sein, um Musik abzuspielen!")
        return

    voice_channel = ctx.author.voice.channel
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)

    # Song suchen
    search_results = SearchVideos(search_term, offset=1, mode="json", max_results=1).result()
    search_results = json.loads(search_results)
    video_info = search_results['search_result'][0]
    video_url = video_info['link']
    video_title = video_info.get('title', 'N/A')

    # Song herunterladen
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a'}],
        'outtmpl': f'./Musik-Dateien/{ctx.guild.id}_current_song.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    # Verbindung zum Voice-Channel herstellen
    if voice_client is None:
        voice_client = await voice_channel.connect()

    # Audio abspielen
    try:
        source = f"./Musik-Dateien/{ctx.guild.id}_current_song.m4a"
        voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=source))
        await ctx.send(f"Jetzt läuft: {video_title}\n{video_url}")
    except Exception as e:
        print(f"Fehler beim Abspielen: {e}")
        await ctx.send("Es gab einen Fehler beim Abspielen des Songs.")

# Song zur Warteschlange hinzufügen
@client.command()
async def queue_add(ctx, *, song_name: str):
    global music_queue
    guild_id = ctx.guild.id

    if guild_id not in music_queue:
        music_queue[guild_id] = []

    ydl_opts = {"format": "bestaudio"}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{song_name}", download=False)
        video = info['entries'][0]
        video_title = video['title']
        video_url = video['webpage_url']

    music_queue[guild_id].append((video_title, video_url))

    embed = discord.Embed(
        title="🎶 Song hinzugefügt!",
        description=f"**{video_title}** wurde der Warteschlange hinzugefügt.",
        color=0x1abc9c
    )
    await ctx.send(embed=embed)

# Warteschlange anzeigen
@client.command()
async def queue_sight(ctx):
    global music_queue
    guild_id = ctx.guild.id

    if guild_id not in music_queue or len(music_queue[guild_id]) == 0:
        description = "Die Warteschlange ist leer."
    else:
        description = "\n".join([f"**{i + 1}.** [{song[0]}]({song[1]})" for i, song in enumerate(music_queue[guild_id])])

    embed = discord.Embed(title="🎶 Warteschlange", description=description, color=0x3498db)
    await ctx.send(embed=embed)

@client.command()
async def skip(ctx):
    """Überspringt den aktuellen Song und spielt den nächsten in der Warteschlange ab."""
    voice_client = get_voice_client(ctx)
    guild_id = ctx.guild.id

    if not voice_client or not voice_client.is_playing():
        return await ctx.send("❌ Es läuft gerade kein Song, der übersprungen werden kann.")

    # Aktuellen Song stoppen
    voice_client.stop()

    # Prüfen, ob es einen nächsten Song in der Warteschlange gibt
    if guild_id in music_queue and len(music_queue[guild_id]) > 0:
        # Nächsten Song holen
        next_song = music_queue[guild_id].pop(0)
        video_title, video_url = next_song

        # Song herunterladen
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a'}],
            'outtmpl': f'./Musik-Dateien/{guild_id}_next_song.%(ext)s',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Abspielen des nächsten Songs
        source = f"./Musik-Dateien/{guild_id}_next_song.m4a"
        voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=source),
                          after=lambda e: play_next(ctx))
        await ctx.send(f"⏭️ Song übersprungen! Jetzt läuft: **{video_title}**\n🔗 {video_url}")
    else:
        await ctx.send("⏭️ Song übersprungen! Keine weiteren Songs in der Warteschlange.")
        if voice_client.is_connected():
            await voice_client.disconnect()

# Nächsten Song abspielen
def play_next(ctx):
    voice_client = get_voice_client(ctx)
    guild_id = ctx.guild.id

    if guild_id in music_queue and len(music_queue[guild_id]) > 0:
        next_song = music_queue[guild_id].pop(0)
        video_title, video_url = next_song
        source = discord.FFmpegPCMAudio(executable="ffmpeg", source=f'./Musik-Dateien/{guild_id}_current_song.m4a')
        voice_client.play(source, after=lambda e: play_next(ctx))
        ctx.send(f"🎵 Jetzt läuft: **{video_title}**\n🔗 {video_url}")
    else:
        if voice_client.is_connected():
            ctx.bot.loop.create_task(voice_client.disconnect())
@client.event
async def on_command_error(ctx:commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Dieser Befehl existiert nicht.")
    else:
        print(f"Fehler beim Ausführen des Befehls: {error}")

@client.command()
async def help (ctx:commands.Context):
    embed = discord.Embed(
            title="Here are some Commands, that you can use.",
            description="**?play <searchterm>**\n**?pause**\n**?stop**\n**?resume**\n**?leave**\n**?roulette <black or red>**\n**?qod**\n**?queue_add**\n**queue_sight**\n**?queue_clear**\n**?GitHub_ticket**\n**ticket_open**\n**ticket_close**",
            color=0x2ecc71  # Schöne grüne Farbe
            )

            # Sende das Embed
    await ctx.send(embed=embed)
@client.command()
async def pause (ctx:commands.Context):
    for schleife in ctx.author.voice.channel.members:
        if schleife.id == bot.user.id:
            voice_channel = ctx.author.voice.channel
            voice_client = discord.utils.get(client.voice_clients, channel=voice_channel)
            embed = discord.Embed(
            title="PAUSING!",
            description="**Paused** ⏸️",
            color=0x2ecc71  # Schöne grüne Farbe
            )

            # Sende das Embed
            await ctx.send(embed=embed)
            voice_client.pause()

@client.command()
async def resume (ctx:commands.Context):
    for schleife in ctx.author.voice.channel.members:
        if schleife.id == bot.user.id:
            voice_channel = ctx.author.voice.channel
            voice_client = discord.utils.get(client.voice_clients, channel=voice_channel)
            embed = discord.Embed(
            title="RESUMING!",
            description="**Resume** ⏯️",
            color=0x2ecc71  # Schöne grüne Farbe
            )

            # Sende das Embed
            await ctx.send(embed=embed)
            voice_client.resume()
            
@client.command()
async def stop (ctx:commands.Context):
    for schleife in ctx.author.voice.channel.members:
        if schleife.id == bot.user.id:
            voice_channel = ctx.author.voice.channel
            voice_client = discord.utils.get(client.voice_clients, channel=voice_channel)
            qod = ["**Okay, i'm leaving...**",
                   "**Awww, u don't like me, ok I will leave... (sad)**",
                   "**You don't like the music, THEN JUST CHANGE IT!!! Instead of making me leave :(**",
                   "**No music? Ok, I will leave**",
                   "**Don't want to hear the shitty music of your friends? Then just mute me.**",
                   "**Please don't make me leave! Please! Noooooo....**",
                   "**I hate u don't make me leave!**"]
            qod = random.choice(qod)
            embed = discord.Embed(
            title="STOP!",
            description=qod,
            color=0x2ecc71  # Schöne grüne Farbe
            )

            # Sende das Embed
            await ctx.send(embed=embed)
            await voice_client.disconnect()

@client.command()
async def daily(ctx: commands.Context):
    global user_data

    user_id = str(ctx.author.id)

    if user_id not in user_data:
        user_data[user_id] = {"money": 10, "streak": 0, "last_daily": None}

    user_info = user_data[user_id]

    today = datetime.utcnow().date()

    if user_info["last_daily"] == today.isoformat():
        embed = discord.Embed(
        title="Daily Money already received",
        description=f"You already received your money.",
        color=0x1abc9c
        )
        await ctx.send(embed=embed)
        return

    user_info["last_daily"] = today.isoformat()

    # Check for streak
    if user_info["last_daily"] is not None:
        last_daily_datetime = datetime.fromisoformat(user_info["last_daily"])
        if (today - last_daily_datetime.date()).days == 1:
            user_info["streak"] += 1
        else:
            user_info["streak"] = 1

    # Send a message with options

    embed = discord.Embed(
        title="Daily Money",
        description=f"Do you want to double your money or not? React with 👍 if yes 👎 if no.",
        color=0x1abc9c
        )
    message = await ctx.send(embed=embed)
    await message.add_reaction("👍")  # Thumbs up
    await message.add_reaction("👎")  # Thumbs down

    # Function to check the reaction
    def check(reaction, user):
        return user == ctx.author and not user.bot and str(reaction.emoji) in ['👍', '👎']
    print ("T1")
    try:
        reaction, _ = await client.wait_for('reaction_add', timeout=60.0, check=check)
        if str(reaction.emoji) == '👍':  # If user reacted with thumbs up
            roulette_result = await roulette_daily(ctx)
            if roulette_result:
                print ("T2.2")
                user_info["money"] += 200  # Double the daily reward if the user wins in roulette
                embed = discord.Embed(
                title="YOU WIN!",
                description=f"You doubled your daily bonus! Streak: {user_info['streak']}",
                color=0x1abc9c
                )
                message = await ctx.send(embed=embed)
            else:
                user_info["money"] = 0  # Lose all money in Double or Nothing if the user loses in roulette
                embed = discord.Embed(
                title="YOU LOSE!",
                description=f"You lost your daily bonus! Nothing there, try better next time! Streak: {user_info['streak']}",
                color=0x1abc9c
                )
                message = await ctx.send(embed=embed)
        
        else:
            print ("T2.2")
            user_info["money"] += 100
            embed = discord.Embed(
            title="Money will be transfered",
                description=f"The Money will be transfered any time. You get 100 Arkani Points!",
                color=0x1abc9c
                )
            message = await ctx.send(embed=embed)

    except asyncio.TimeoutError:
        embed = discord.Embed(
        title="Timeout",
        description=f"You didn't react to the messsage Times up.",
        color=0x1abc9c
        )
        await ctx.send (embed=embed)
    return


@client.command()
async def roulette_daily(ctx: commands.Context):
    global user_data

    user_id = str(ctx.author.id)
    user_info = user_data.get(user_id, {"money": 10, "streak": 0, "last_daily": str(date.today())})

    # Prüfen, ob der Benutzer genug Geld hat
    if user_info["money"] <= 0:
        await ctx.send("You don't have enough money to play roulette.")
        return False

    embed = discord.Embed(
        title="Roulette Daily",
        description=f"Welcome to the roulette game! You have {user_info['money']} coins. Bet on Red or Black to play.",
        color=0x2ecc71
    )
    await ctx.send(embed=embed)

    # Interaktive Buttons erstellen
    async def red_button(interaction: discord.Interaction):
        await handle_choice("red", interaction)

    async def black_button(interaction: discord.Interaction):
        await handle_choice("black", interaction)

    async def handle_choice(user_choice, interaction):
        user_id = str(interaction.user.id)
        user_info = user_data.get(user_id, {"money": 10, "streak": 0, "last_daily": str(date.today())})

        if user_info["money"] <= 0:
            embed = discord.Embed(
                title="Not enough money",
                description="You don't have enough money to place the bet.",
                color=0x2ecc71
            )
            await interaction.response.send_message(embed=embed)
            return

        result = random.choice(["black", "red"])

        embed = discord.Embed(
            title="Roulette Result",
            description=f"The result is {result.capitalize()}!",
            color=0x1abc9c
        )
        await interaction.response.send_message(embed=embed)

        # Berechnung des Gewinns/Verlusts
        if user_choice == result:
            user_info["money"] += 10  # Beispiel: 10 Münzen gewinnen
            result_text = "You win!"
        else:
            user_info["money"] -= 10  # Beispiel: 10 Münzen verlieren
            result_text = "You lose!"

        embed = discord.Embed(
            title=f"{result_text}",
            description="Your new balance is {user_info['money']} coins.",
            color=0x1abc9c
        )
        await interaction.followup.send(embed=embed)

    # Buttons erstellen
    red_button_obj = Button(label="Red", style=discord.ButtonStyle.red)
    black_button_obj = Button(label="Black", style=discord.ButtonStyle.green)

    # Button-Interaktionen verbinden
    red_button_obj.callback = red_button
    black_button_obj.callback = black_button

    # View mit den Buttons
    view = View()
    view.add_item(red_button_obj)
    view.add_item(black_button_obj)

    # Sende die Nachricht mit den Buttons
    await ctx.send("Please choose your bet!", view=view)

    # Warte auf eine Interaktion
    await view.wait()

@client.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx: commands.Context, duration: int):
    # Die Person, die den Befehl ausführt
    member = ctx.author
    duration = 20
    # Nachricht senden, bevor der Bann durchgeführt wird
    await ctx.send("The ban hammer will destroy you. MUAHAHAHAHAHAHAHAHAHHA")

    # Bann durchführen
    await ctx.guild.ban(member, reason="Testbann durch den Befehl")
    await ctx.send(f"{member} wurde für {duration} Sekunden gebannt.")

    # Warten für die angegebene Dauer und dann entbannen
    await asyncio.sleep(duration)
    await ctx.guild.unban(member)
    await ctx.send(f"Keine Angst, {member}. Das war nur ein Testbann.")
    
@client.command()
async def roulette(ctx: commands.Context, bet_amount: int = 10):
    global user_data

    user_id = str(ctx.author.id)
    user_info = user_data.get(user_id, {"money": 10, "streak": 0, "last_daily": str(date.today())})

    # Prüfen, ob der Benutzer genug Geld hat
    if user_info["money"] <= 0:
        await ctx.send("You don't have enough money to play roulette.")
        return False

    embed = discord.Embed(
        title="Roulette Daily",
        description=f"Welcome to the roulette game! You have {user_info['money']} coins. Bet on Red or Black to play.",
        color=0x2ecc71
    )
    await ctx.send(embed=embed)

    # Interaktive Buttons erstellen
    async def red_button(interaction: discord.Interaction):
        await handle_choice("red", interaction)

    async def black_button(interaction: discord.Interaction):
        await handle_choice("black", interaction)

    async def handle_choice(user_choice, interaction):
        user_id = str(interaction.user.id)
        user_info = user_data.get(user_id, {"money": 10, "streak": 0, "last_daily": str(date.today())})

        if user_info["money"] <= 0:
            embed = discord.Embed(
                title="Not enough money",
                description="You don't have enough money to place the bet.",
                color=0x2ecc71
            )
            await interaction.response.send_message(embed=embed)
            return

        result = random.choice(["black", "red"])

        embed = discord.Embed(
            title="Roulette Result",
            description=f"The result is {result.capitalize()}!",
            color=0x1abc9c
        )
        await interaction.response.send_message(embed=embed)

        # Berechnung des Gewinns/Verlusts
        if user_choice == result:
            user_info["money"] += 10  # Beispiel: 10 Münzen gewinnen
            result_text = "You win!"
        else:
            user_info["money"] -= 10  # Beispiel: 10 Münzen verlieren
            result_text = "You lose!"

        embed = discord.Embed(
            title=f"{result_text}",
            description=f"Your new balance is {user_info['money']} coins.",
            color=0x1abc9c
        )
        await interaction.followup.send(embed=embed)

    # Buttons erstellen
    red_button_obj = Button(label="Red", style=discord.ButtonStyle.red)
    black_button_obj = Button(label="Black", style=discord.ButtonStyle.green)

    # Button-Interaktionen verbinden
    red_button_obj.callback = red_button
    black_button_obj.callback = black_button

    # View mit den Buttons
    view = View()
    view.add_item(red_button_obj)
    view.add_item(black_button_obj)

    # Sende die Nachricht mit den Buttons
    await ctx.send("Please choose your bet!", view=view)

    # Warte auf eine Interaktion
    await view.wait()

@client.command()
async def qod(ctx: commands.Context):
    # Liste der Zitate
    zitate = [
        "Knowledge is power.",
        "Ask, and it shall be given you; seek, and you shall find.",
        "All the world's a stage, and all the men and women merely players.",
        "Ask not what your country can do for you; ask what you can do for your country.",
        "For those to whom much is given, much is required.",
        "Houston, we have a problem.",
        "I have always depended on the kindness of strangers.",
        "I think therefore I am.",
        "Be yourself!",
        "I've got a feeling we're not in Kansas anymore.",
        "Life is like a box of chocolates. You never know what you’re gonna get.",
        "No one can make you feel inferior without your consent.",
        "Power corrupts; absolute power corrupts absolutely.",
        "That’s one small step for a man, a giant leap for mankind.",
        "Three can keep a secret, if two of them are dead.",
        "Two roads diverged in a wood, and I, I took the one less travelled by, and that has made all the difference.",
        "You must be the change you wish to see in the world.",
        "Parting is such sweet sorrow.",
        "If you want something said, ask a man; if you want something done, ask a woman.",
        "If you build it, they will come."
    ]

    # Wähle ein zufälliges Zitat
    zitat = random.choice(zitate)

    # Erstelle das Embed
    embed = discord.Embed(
        title="Quote of the Day",
        description=zitat,
        color=0x2ecc71  # Schöne grüne Farbe
    )

    # Sende das Embed
    await ctx.send(embed=embed)

@client.command()
async def check_money(ctx: commands.Context):
    global user_data

    user_id = str(ctx.author.id)

    if user_id not in user_data:
        embed = discord.Embed(
        title="Bankaccount",
        description=f"You currently have no Money",
        color=0x1abc9c
        )
        await ctx.send(embed=embed)
    else:
        money_amount = user_data[user_id]["money"]
        embed = discord.Embed(
        title="Bankaccount",
        description=f"You currently have {money_amount} Arkani coins",
        color=0x1abc9c
        )
        await ctx.send(embed=embed)

@client.command()
async def GitHub_Ticket(ctx:commands.Context, description: str):
    await ctx.message.delete() 
    url = f'https://api.github.com/repos/{GITHUB_REPO}/issues'

    # Data for the issue
    data = {
        'title': 'New Issue on the Bot',
        'body': description
    }

    # Header for the request
    headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
    }

    # HTTP POST request to GitHub
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 201:
                    embed = discord.Embed(
                        title="Ticket wurde auf GitHub hinzugefügt unter.",
                        description=f"https://github.com/Arkansis2901/Arkansis/issues",
                        color=0x1abc9c
                    )
    
                    await ctx.send(embed=embed)
                else:
                    error_message = await response.json()
                    await ctx.send(f'Error creating the ticket: {error_message.get("message", "Unknown error")} - Status Code: {response.status}')
    except Exception as e:
        await ctx.send(f'An error occurred: {str(e)}')

# Invite-Command mit einem Embed
@client.command()
async def invite(ctx):
    # Erstelle ein Embed für die Einladungsnachricht
    embed = discord.Embed(
        title="Lade mich auf deinen Server ein!",
        description="Klicke auf den unten stehenden Link, um mich auf deinen Server einzuladen und meine Features zu nutzen!",
        color=0x3498db  # Schöne Blautöne oder eine andere Farbe deiner Wahl
    )
    embed.add_field(
        name="Einladungslink",
        value="[Hier klicken, um den Bot einzuladen](https://discord.com/oauth2/authorize?client_id=1119248408725704886&scope=bot+applications.commands&permissions=8)",
        inline=False
    )
    embed.set_footer(text="Danke, dass du mich zu deinem Server einlädst! 😊")

    # Sende das Embed
    await ctx.send(embed=embed)

@client.command()
async def rules(ctx):
    # Erstelle die Embed-Nachricht
    # \n macht einen Absatz, **xyz** macht den Text Fett
    embed = discord.Embed(title="Server Regeln", 
                          description="**Bitte akzeptiere die Regeln, um den Server zu betreten.** \n 1. Respekt und Freundlichkeit \n 2. Keine Spam-Nachrichten \n 3. Keine NSFW-Inhalte \n 4. Keine Werbung ohne Erlaubnis \n 5. Richtiger Kanal für das Thema \n 6. Keine politischen oder religiösen Debatten \n 7. Keine unerlaubte Weitergabe persönlicher Informationen \n 8. Befolge Anweisungen des Moderationsteams \n 9. Bots richtig verwenden \n 10. Melde Verstöße an die Moderation",
                         color=0x00ff00)
    
    # Erstelle den Button
    view = discord.ui.View()
    button = discord.ui.Button(label="Akzeptieren", style=discord.ButtonStyle.green)
    view.add_item(button)

    # Funktion, die ausgeführt wird, wenn der Button gedrückt wird
    async def button_callback(interaction):
        # Die Rolle finden, die vergeben werden soll
        role = discord.utils.get(ctx.guild.roles, name="Member")
        if role:
            # Rolle dem Benutzer hinzufügen, der auf den Button geklickt hat
            await interaction.user.add_roles(role)
            embed = discord.Embed(
                        title="Welcome!",
                        description=f"**You succesfully got the member role! Welcome on the Server! Have fun!** ",
                        color=0x1abc9c
                    )
    
            await ctx.author.send(embed=embed)
        else:
            embed = discord.Embed(
                        title="Server doesn't have the Member Role!",
                        description=f"Please contact **the Staff**, that there is a problem with the member Role.",
                        color=0x1abc9c
                    )
    
            await ctx.author.send(embed=embed)
    button.callback = button_callback
    
    # Sende die Regel-Nachricht mit dem Button
    await ctx.send(embed=embed, view=view)

@client.command()
async def queue_clear(ctx):
    # Logik zum Löschen der Warteschlange (Simulation)
    embed = discord.Embed(
        title="🗑️ Warteschlange geleert!",
        description="Die Warteschlange wurde erfolgreich gelöscht.",
        color=0xe74c3c
    )
    await ctx.send(embed=embed)

@client.command()
async def ticket_open(ctx: commands.Context):
    # Lösche die Nachricht des Benutzers, der den Command ausgeführt hat
    await ctx.message.delete()

    guild = ctx.guild

    # Erstelle den Ticket-Kanal mit speziellen Berechtigungen
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True),
    }

    # Füge hier Rollen hinzu, die den Kanal sehen sollen (Admin, Mod)
    admin_role = discord.utils.get(guild.roles, name="Admin")  # Beispiel: Admin-Rolle
    mod_role = discord.utils.get(guild.roles, name="Moderator")  # Beispiel: Moderator-Rolle
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True)
    if mod_role:
        overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True)

    # Kanal erstellen
    ticket_channel = await guild.create_text_channel(
        name=f'ticket-{ctx.author.name}',
        overwrites=overwrites
    )

    # Ticket eröffnen mit einem schönen Embed
    embed = discord.Embed(
        title="📩 Ticket eröffnet!",
        description="Dein Ticket wurde erfolgreich erstellt! Ein Teammitglied wird sich bald bei dir melden.",
        color=0x2ecc71  # Schöne grüne Farbe
    )
    embed.add_field(
        name="Ticket-Kanal",
        value=f"Dein Ticket ist in diesem Kanal aktiv: {ticket_channel.mention}",
        inline=False
    )
    embed.set_footer(text="Nutze ?ticket_close, um das Ticket zu schließen.")

    # Sende das Embed in den Ticket-Kanal
    await ticket_channel.send(embed=embed)

    # Erstelle ein Embed für die private Nachricht
    dm_embed = discord.Embed(
        title="📩 Ticket eröffnet!",
        description=f"Dein Ticket wurde in {ticket_channel.mention} eröffnet!",
        color=0x2ecc71  # Schöne grüne Farbe
    )
    
    # Sende die private Nachricht als Embed
    await ctx.author.send(embed=dm_embed)

    # Lösche die Nachricht des Benutzers, der den Command ausgeführt hat
    await ctx.message.delete()

    guild = ctx.guild

    # Erstelle den Ticket-Kanal mit speziellen Berechtigungen
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True),
    }

    # Füge hier Rollen hinzu, die den Kanal sehen sollen (Admin, Mod)
    admin_role = discord.utils.get(guild.roles, name="Admin")  # Beispiel: Admin-Rolle
    mod_role = discord.utils.get(guild.roles, name="Moderator")  # Beispiel: Moderator-Rolle
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True)
    if mod_role:
        overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True)

    # Kanal erstellen
    ticket_channel = await guild.create_text_channel(
        name=f'ticket-{ctx.author.name}',
        overwrites=overwrites
    )

    # Ticket eröffnen mit einem schönen Embed
    embed = discord.Embed(
        title="📩 Ticket eröffnet!",
        description="Dein Ticket wurde erfolgreich erstellt! Ein Teammitglied wird sich bald bei dir melden.",
        color=0x2ecc71  # Schöne grüne Farbe
    )
    embed.add_field(
        name="Ticket-Kanal",
        value=f"{ctx.author.mention}, dein Ticket ist in diesem Kanal aktiv: {ticket_channel.mention}",
        inline=False
    )
    embed.set_footer(text="Nutze ?ticket_close, um das Ticket zu schließen.")

    # Sende das Embed in den Ticket-Kanal
    await ticket_channel.send(embed=embed)

    # Erstelle ein Embed für die private Nachricht
    dm_embed = discord.Embed(
        title="📩 Ticket eröffnet!",
        description=f"Dein Ticket wurde in {ticket_channel.mention} eröffnet!",
        color=0x2ecc71  # Schöne grüne Farbe
    )
    
    # Sende die private Nachricht als Embed
    await ctx.author.send(embed=dm_embed)

    # Lösche die Nachricht des Benutzers, der den Command ausgeführt hat
    await ctx.message.delete()

    guild = ctx.guild

    # Erstelle den Ticket-Kanal mit speziellen Berechtigungen
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True),
    }

    # Füge hier Rollen hinzu, die den Kanal sehen sollen (Admin, Mod)
    admin_role = discord.utils.get(guild.roles, name="Admin")  # Beispiel: Admin-Rolle
    mod_role = discord.utils.get(guild.roles, name="Moderator")  # Beispiel: Moderator-Rolle
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True)
    if mod_role:
        overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True)

    # Kanal erstellen
    ticket_channel = await guild.create_text_channel(
        name=f'ticket-{ctx.author.name}',
        overwrites=overwrites
    )

    # Ticket eröffnen mit einem schönen Embed
    embed = discord.Embed(
        title="📩 Ticket eröffnet!",
        description="Dein Ticket wurde erfolgreich erstellt! Ein Teammitglied wird sich bald bei dir melden.",
        color=0x2ecc71  # Schöne grüne Farbe
    )
    embed.add_field(
        name="Ticket-Kanal",
        value=f"{ctx.author.mention}, dein Ticket ist in diesem Kanal aktiv: {ticket_channel.mention}",
        inline=False
    )
    embed.set_footer(text="Nutze ?ticket_close, um das Ticket zu schließen.")

    # Sende das Embed in den Ticket-Kanal
    await ticket_channel.send(embed=embed)

    # Informiere den Benutzer in einer privaten Nachricht
    await ctx.author.send(f"Dein Ticket wurde in {ticket_channel.mention} eröffnet!")
    # Lösche die Nachricht des Benutzers, der den Command ausgeführt hat
    await ctx.message.delete()
    
    guild = ctx.guild

    # Erstelle den Ticket-Kanal mit speziellen Berechtigungen
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True),
    }

    # Füge hier Rollen hinzu, die den Kanal sehen sollen (Admin, Mod)
    admin_role = discord.utils.get(guild.roles, name="Admin")  # Beispiel: Admin-Rolle
    mod_role = discord.utils.get(guild.roles, name="Moderator")  # Beispiel: Moderator-Rolle
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True)
    if mod_role:
        overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True)

    # Kanal erstellen
    ticket_channel = await guild.create_text_channel(
        name=f'ticket-{ctx.author.name}',
        overwrites=overwrites
    )

    # Ticket eröffnen mit einem schönen Embed
    embed = discord.Embed(
        title="📩 Ticket eröffnet!",
        description="Dein Ticket wurde erfolgreich erstellt! Ein Teammitglied wird sich bald bei dir melden.",
        color=0x2ecc71  # Schöne grüne Farbe
    )
    embed.add_field(
        name="Ticket-Kanal",
        value=f"{ctx.author.mention}, dein Ticket ist in diesem Kanal aktiv: {ticket_channel.mention}",
        inline=False
    )
    embed.set_footer(text="Nutze ?ticket_close, um das Ticket zu schließen.")
    
    # Sende das Embed in den Ticket-Kanal
    await ticket_channel.send(embed=embed)
    
    # Informiere den Benutzer im ursprünglichen Kanal
    await ctx.send(f"{ctx.author.mention}, dein Ticket wurde erstellt! Überprüfe den Kanal {ticket_channel.mention}.")

@client.command()
async def ticket_close(ctx: commands.Context):
    # Ticket schließen
    if ctx.channel.name.startswith("ticket-"):
        # Erstelle ein Embed für die private Nachricht
        dm_embed = discord.Embed(
            title="✅ Ticket geschlossen",
            description=f"Dein Ticket in {ctx.channel.mention} wurde erfolgreich geschlossen.",
            color=0xe67e22  # Schöne orange Farbe
        )
        
        # Sende die private Nachricht als Embed
        await ctx.author.send(embed=dm_embed)

        # Sende eine Bestätigung im Ticket-Kanal (optional)
        embed = discord.Embed(
            title="✅ Ticket geschlossen",
            description="Das Ticket wurde erfolgreich geschlossen. Danke, dass du uns kontaktiert hast!",
            color=0xe67e22
        )
        embed.set_footer(text="Falls du weitere Hilfe benötigst, öffne ein neues Ticket mit ?ticket_open.")
        
        await ctx.send(embed=embed)  # Nachricht im Kanal senden

        # Lösche den Ticket-Kanal nach dem Senden der Nachricht
        await ctx.channel.delete()
    else:
        # Sende eine private Nachricht, wenn der Befehl in einem falschen Kanal verwendet wird
        await ctx.author.send('Dieser Kanal ist kein Ticket-Kanal. Du kannst nur in deinem Ticket-Kanal den Befehl verwenden.')

@client.command()
async def ambiente(ctx, *suchbegriff):
    try:
        search_query = " ".join(suchbegriff) + " ambient sound"
        # Eindeutiger Dateiname mit Zeitstempel
        timestamp = int(time.time())
        filename = f"ambient_sound_{timestamp}.mp3"

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'outtmpl': filename,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{search_query}", download=True)
                url = info['entries'][0]['url']
            except Exception as e:
                await ctx.send("Fehler beim Herunterladen des Sounds. Versuche es bitte erneut.")
                print(f"Error: {e}")
                return

        voice_channel = ctx.author.voice.channel if ctx.author.voice else None

        if voice_channel:
            if ctx.voice_client is None:
                voice_client = await voice_channel.connect()
            else:
                voice_client = ctx.voice_client

            voice_client.play(discord.FFmpegPCMAudio(filename))

            await ctx.send(f"Spiele nun '{search_query}' ab.")
            embed = discord.Embed(
                title="Ambiente Sound wird abgespielt",
                description=f"Spiele nun '{search_query}' ab.",
                color=0xffc107
            )
            await ctx.send(embed=embed)

            # Warte, bis das Abspielen beendet ist, bevor die Datei gelöscht wird
            while voice_client.is_playing():
                await asyncio.sleep(1)

            await voice_client.disconnect()
            os.remove(filename)
        else:
            await ctx.send("Du musst dich zuerst in einem Sprachkanal befinden.")
    except Exception as e:
        await ctx.send(f"Ein Fehler ist aufgetreten: {str(e)}")

@client.command()
async def stop_ambient(ctx):
    """Stoppt den aktuellen Ambient-Sound."""
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Ambient-Sound gestoppt.")
    else:
        await ctx.send("Es wird kein Ambient-Sound abgespielt.")

@client.command()
async def fortune(ctx):
    """Gibt ein Glückszitat und eine kleine Challenge für den Tag aus."""
    fortunes = [
        "Die beste Zeit, einen Baum zu pflanzen, war vor 20 Jahren. Die zweitbeste Zeit ist jetzt.",
        "Geduld ist ein Schlüssel zum Glück.",
        "Der Weg ist das Ziel.",
        "Heute ist ein guter Tag, um etwas Neues zu lernen.",
        "Deine Grenzen existieren nur in deinem Kopf."
    ]
    
    challenges = [
        "Schreibe drei Dinge auf, für die du dankbar bist.",
        "Mache heute 10 Minuten Stretching.",
        "Versuche heute, mit drei fremden Leuten freundlich zu sprechen.",
        "Nimm dir 5 Minuten Zeit, um deinen Schreibtisch oder Arbeitsbereich zu organisieren.",
        "Mache eine Pause und genieße einen kurzen Spaziergang."
    ]

    fortune_message = random.choice(fortunes)
    challenge_message = random.choice(challenges)

    embed = discord.Embed(
        title="🍀 Dein Glücksspruch und Challenge für den Tag 🍀",
        description=f"{fortune_message}\n\n**Tages-Challenge:** {challenge_message}",
        color=0xffc107
    )
    await ctx.send(embed=embed)


intents =intents
# Hauptprogramm starten
if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
