import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import asyncio
import os
import threading
import aiohttp
from flask import Flask

# ====== CONFIGURATION ======
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

TOKEN = os.getenv("TOKEN")
FREE_GAMES_CHANNEL_ID = int(os.getenv("FREE_GAMES_CHANNEL_ID", "0"))

if TOKEN is None:
    print("\u274c TOKEN non d\u00e9fini dans .env")
    exit(1)

# ====== DONNÉES ======
notes = {}  # Format : {nom_plat: {user_id: note, ...}}
countdowns = []
rappels = []
films = []
jeux = []

# ====== FLASK POUR RENDER ======
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot Discord actif !"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

# ====== ÉVÉNEMENTS ======

@bot.event
async def on_ready():
    await tree.sync()
    print(f"\u2705 Connecté en tant que {bot.user}")
    countdown_loop.start()
    rappel_loop.start()
    check_free_games.start()

# ====== COMMANDES ======

@tree.command(name="note", description="Faire ou modifier une évaluation")
@app_commands.describe(nom="Nom du plat", note="Note sur 10")
async def cmd_note(interaction: discord.Interaction, nom: str, note: int):
    if not (0 <= note <= 10):
        await interaction.response.send_message("Merci d'entrer une note entre 0 et 10.", ephemeral=True)
        return

    user = interaction.user
    if nom not in notes:
        notes[nom] = {}
    notes[nom][user.id] = note

    # Préparer l'embed
    embed = discord.Embed(title=f"\ud83c\udf7d\ufe0f {nom}", color=0xf39c12)
    total = 0
    count = 0
    for user_id, n in notes[nom].items():
        member = await bot.fetch_user(user_id)
        embed.add_field(name=member.name, value=f"{n}/10", inline=False)
        total += n
        count += 1

    moyenne = total / count
    embed.add_field(name="\u2b50 Note moyenne", value=f"{moyenne:.1f}/10", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="classement", description="Voir le classement des plats")
async def cmd_classement(interaction: discord.Interaction):
    moyennes = {}
    for nom, user_notes in notes.items():
        if user_notes:
            moyenne = sum(user_notes.values()) / len(user_notes)
            moyennes[nom] = moyenne

    classement = sorted(moyennes.items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="\ud83c\udf1f Classement des plats", color=0x2ecc71)
    for nom, moyenne in classement:
        embed.add_field(name=nom, value=f"{moyenne:.1f}/10", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="notesperso", description="Voir ton classement perso")
async def cmd_notesperso(interaction: discord.Interaction):
    user_id = interaction.user.id
    perso = [(nom, notes[nom][user_id]) for nom in notes if user_id in notes[nom]]
    if not perso:
        await interaction.response.send_message("Tu n'as noté aucun plat.", ephemeral=True)
        return

    perso.sort(key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title=f"\ud83d\udd8a\ufe0f Notes de {interaction.user.name}", color=0x3498db)
    for nom, note in perso:
        embed.add_field(name=nom, value=f"{note}/10", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="supprnote", description="Supprimer une note")
@app_commands.describe(nom="Nom du plat")
async def cmd_supprnote(interaction: discord.Interaction, nom: str):
    user_id = interaction.user.id
    if nom in notes and user_id in notes[nom]:
        del notes[nom][user_id]
        if not notes[nom]:
            del notes[nom]
        await interaction.response.send_message(f"Note supprimée pour **{nom}**.", ephemeral=True)
    else:
        await interaction.response.send_message("Aucune note trouvée pour ce plat.", ephemeral=True)

@tree.command(name="ajoutjeu", description="Ajouter un jeu à la liste")
@app_commands.describe(nom="Nom du jeu", plateforme="Plateforme")
async def cmd_ajoutjeu(interaction: discord.Interaction, nom: str, plateforme: str):
    jeux.append({"nom": nom, "plateforme": plateforme})
    await interaction.response.send_message(f"Jeu **{nom}** ajouté sur **{plateforme}**.", ephemeral=True)

@tree.command(name="jeux", description="Voir la liste des jeux")
async def cmd_jeux(interaction: discord.Interaction):
    if not jeux:
        await interaction.response.send_message("La liste des jeux est vide.", ephemeral=True)
        return
    embed = discord.Embed(title="\ud83c\udfae Liste des jeux", color=0x00ff00)
    for jeu in jeux:
        embed.add_field(name=jeu["nom"], value=jeu["plateforme"], inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="ajoutfilm", description="Ajouter un film ou une série")
@app_commands.describe(titre="Titre du film/série", genre="Genre")
async def cmd_ajoutfilm(interaction: discord.Interaction, titre: str, genre: str):
    films.append({"titre": titre, "genre": genre})
    await interaction.response.send_message(f"Film/Série **{titre}** ajouté(e) au genre **{genre}**.", ephemeral=True)

@tree.command(name="films", description="Voir la liste des films/séries")
async def cmd_films(interaction: discord.Interaction):
    if not films:
        await interaction.response.send_message("La liste est vide.", ephemeral=True)
        return
    embed = discord.Embed(title="\ud83c\udfac Films et séries", color=0x9b59b6)
    for film in films:
        embed.add_field(name=film["titre"], value=film["genre"], inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="comptearebours", description="Créer un compte à rebours")
@app_commands.describe(titre="Titre", date="Date/heure (YYYY-MM-DD HH:MM)")
async def cmd_comptearebours(interaction: discord.Interaction, titre: str, date: str):
    try:
        dt = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M")
        countdowns.append({"titre": titre, "date": dt, "channel": interaction.channel_id})
        await interaction.response.send_message(f"Compte à rebours **{titre}** créé pour {date}.", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("Format invalide. Utilise YYYY-MM-DD HH:MM", ephemeral=True)

@tree.command(name="rappel", description="Mettre un rappel")
@app_commands.describe(message="Message du rappel", date="Date/heure (YYYY-MM-DD HH:MM)")
async def cmd_rappel(interaction: discord.Interaction, message: str, date: str):
    try:
        dt = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M")
        rappels.append({"message": message, "date": dt, "user": interaction.user.id})
        await interaction.response.send_message(f"Rappel créé pour {date}.", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("Format invalide. Utilise YYYY-MM-DD HH:MM", ephemeral=True)

# ====== TÂCHES DE FOND ======

@tasks.loop(seconds=60)
async def countdown_loop():
    now = datetime.datetime.now()
    for cd in countdowns[:]:
        if cd["date"] <= now:
            channel = bot.get_channel(cd["channel"])
            if channel:
                await channel.send(f"\u23f0 **{cd['titre']}** est arrivé !")
            countdowns.remove(cd)

@tasks.loop(seconds=60)
async def rappel_loop():
    now = datetime.datetime.now()
    for r in rappels[:]:
        if r["date"] <= now:
            user = await bot.fetch_user(r["user"])
            if user:
                try:
                    await user.send(f"\ud83d\udd14 Rappel : {r['message']}")
                except:
                    pass
            rappels.remove(r)

@tasks.loop(hours=6)
async def check_free_games():
    global derniers_jeux_gratuits
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=fr-FR&country=FR&allowCountries=FR"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        jeux = data["data"]["Catalog"]["searchStore"]["elements"]
        nouveaux_jeux = []

        for jeu in jeux:
            if jeu["promotions"] and jeu["title"] not in derniers_jeux_gratuits:
                promos = jeu["promotions"]["promotionalOffers"]
                if promos:
                    titre = jeu["title"]
                    lien = f"https://store.epicgames.com/fr/p/{jeu['productSlug']}"
                    derniers_jeux_gratuits.add(titre)
                    nouveaux_jeux.append((titre, lien))

        if nouveaux_jeux:
            channel = bot.get_channel(FREE_GAMES_CHANNEL_ID)
            if channel:
                for titre, lien in nouveaux_jeux:
                    await channel.send(f"\ud83c\udf81 **Jeu gratuit** : **{titre}**\n{lien}")

    except Exception as e:
        print(f"Erreur dans check_free_games : {e}")

# ====== LANCEMENT ======
bot.run(TOKEN)
