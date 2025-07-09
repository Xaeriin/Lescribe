import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
from datetime import datetime, timedelta
import re
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

app = Flask(__name__)

@app.route('/')
def home():
    return "Le bot est en ligne"

Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))).start()

notes = {}
rappels = {}
countdowns = {}

#### UTILS ####
def parse_duration(text):
    match = re.match(r"(\d+)([smhd])", text)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    if unit == 's': return timedelta(seconds=value)
    if unit == 'm': return timedelta(minutes=value)
    if unit == 'h': return timedelta(hours=value)
    if unit == 'd': return timedelta(days=value)

#### COMMANDES ####
@tree.command(name="note")
async def noter(interaction: discord.Interaction, plat: str, note: float):
    user_id = str(interaction.user.id)
    if plat not in notes:
        notes[plat] = {}
    notes[plat][user_id] = note
    await interaction.response.send_message(f"\U0001F374 Tu as noté **{plat}** {note}/10 !")

@tree.command(name="notesperso")
async def notesperso(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    perso = [(plat, n[user_id]) for plat, n in notes.items() if user_id in n]
    if not perso:
        await interaction.response.send_message("Tu n'as noté aucun plat.")
        return
    msg = "\n".join(f"{plat} : {note}/10" for plat, note in perso)
    await interaction.response.send_message(f"Tes notes :\n{msg}")

@tree.command(name="supprnote")
async def supprnote(interaction: discord.Interaction, plat: str):
    user_id = str(interaction.user.id)
    if plat in notes and user_id in notes[plat]:
        del notes[plat][user_id]
        await interaction.response.send_message(f"\U0001F5D1️ Note supprimée pour {plat}.")
    else:
        await interaction.response.send_message("Tu n'avais pas noté ce plat.")

@tree.command(name="classement")
async def classement(interaction: discord.Interaction):
    plats = []
    for plat, votes in notes.items():
        try:
            moyenne = sum(votes.values()) / len(votes)
            plats.append((plat, moyenne))
        except Exception:
            continue
    if not plats:
        await interaction.response.send_message("Aucune note disponible.")
        return
    plats.sort(key=lambda x: x[1], reverse=True)
    msg = "\n".join(f"{p} : {round(n, 2)}/10" for p, n in plats)
    await interaction.response.send_message(f"Classement des plats :\n{msg}")

@tree.command(name="aide")
async def aide(interaction: discord.Interaction):
    embed = discord.Embed(title="\u2728 Commandes disponibles", description="Voici les commandes du bot :", color=0x92A8D1)
    embed.add_field(name="/note", value="Noter un plat", inline=False)
    embed.add_field(name="/notesperso", value="Voir ses notes", inline=False)
    embed.add_field(name="/supprnote", value="Supprimer sa note", inline=False)
    embed.add_field(name="/classement", value="Classement des plats", inline=False)
    embed.add_field(name="/films, /ajoutfilm, /supprfilm", value="Gestion des films", inline=False)
    embed.add_field(name="/jeux, /ajoutjeu, /supprjeu", value="Gestion des jeux", inline=False)
    embed.add_field(name="/rappel", value="Créer un rappel avec durée (ex: 1h)", inline=False)
    embed.add_field(name="/comptearebours", value="Lancer un compte à rebours", inline=False)
    embed.add_field(name="/compteareboursstop", value="Annuler le compte à rebours en cours", inline=False)
    await interaction.response.send_message(embed=embed)

films = []
@tree.command(name="films")
async def films_cmd(interaction: discord.Interaction):
    if not films:
        await interaction.response.send_message("Aucun film enregistré.")
        return
    await interaction.response.send_message("\n".join(films))

@tree.command(name="ajoutfilm")
async def ajoutfilm(interaction: discord.Interaction, titre: str):
    films.append(titre)
    await interaction.response.send_message(f"Film **{titre}** ajouté !")

@tree.command(name="supprfilm")
async def supprfilm(interaction: discord.Interaction, titre: str):
    try:
        films.remove(titre)
        await interaction.response.send_message(f"Film **{titre}** supprimé !")
    except ValueError:
        await interaction.response.send_message("Film non trouvé.")

jeux = []
@tree.command(name="jeux")
async def jeux_cmd(interaction: discord.Interaction):
    if not jeux:
        await interaction.response.send_message("Aucun jeu enregistré.")
        return
    await interaction.response.send_message("\n".join(jeux))

@tree.command(name="ajoutjeu")
async def ajoutjeu(interaction: discord.Interaction, nom: str):
    jeux.append(nom)
    await interaction.response.send_message(f"Jeu **{nom}** ajouté !")

@tree.command(name="supprjeu")
async def supprjeu(interaction: discord.Interaction, nom: str):
    try:
        jeux.remove(nom)
        await interaction.response.send_message(f"Jeu **{nom}** supprimé !")
    except ValueError:
        await interaction.response.send_message("Jeu non trouvé.")

@tree.command(name="rappel")
async def rappel(interaction: discord.Interaction, temps: str, message: str):
    delta = parse_duration(temps)
    if not delta:
        await interaction.response.send_message("Format invalide. Utilise s, m, h ou d (ex: 30m)")
        return
    await interaction.response.send_message(f"\u23F0 Rappel dans {temps} : {message}")
    await asyncio.sleep(delta.total_seconds())
    await interaction.followup.send(f"\u2757 {interaction.user.mention} Rappel : {message}")

@tree.command(name="comptearebours")
async def comptearebours(interaction: discord.Interaction, temps: str):
    delta = parse_duration(temps)
    if not delta:
        await interaction.response.send_message("Durée invalide. Format: 10s, 5m, 2h, etc.")
        return
    user_id = interaction.user.id
    if user_id in countdowns:
        await interaction.response.send_message("Un compte à rebours est déjà en cours.")
        return
    countdowns[user_id] = True
    await interaction.response.send_message(f"\u23F3 Compte à rebours de {temps} lancé...")
    await asyncio.sleep(delta.total_seconds())
    if countdowns.get(user_id):
        await interaction.followup.send(f"\uD83C\uDFC1 {interaction.user.mention} Le compte à rebours est terminé !")
        del countdowns[user_id]

@tree.command(name="compteareboursstop")
async def compteareboursstop(interaction: discord.Interaction):
    user_id = interaction.user.id
    if countdowns.get(user_id):
        countdowns[user_id] = False
        await interaction.response.send_message("\u274C Compte à rebours annulé.")
    else:
        await interaction.response.send_message("Aucun compte à rebours en cours.")

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Connecté en tant que {bot.user}")

bot.run(os.environ['TOKEN'])

