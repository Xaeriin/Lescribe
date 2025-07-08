import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from datetime import datetime, timedelta
from flask import Flask
import threading

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

films = []
jeux = []
notes = {}

class MonBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Sync global des commandes à chaque lancement
        await self.bot.tree.sync()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Connecté en tant que {self.bot.user}")

    # Exemple de commande avec embed et interaction
    @app_commands.command(name="ajoutfilm", description="Ajoute un film à la liste")
    @app_commands.describe(nom="Nom du film")
    async def ajoutfilm(self, interaction: discord.Interaction, nom: str):
        films.append(nom)
        embed = discord.Embed(
            title="Film ajouté 🎬",
            description=f"Le film **{nom}** a été ajouté à la liste.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="listefilms", description="Affiche la liste des films")
    async def listefilms(self, interaction: discord.Interaction):
        if not films:
            await interaction.response.send_message("La liste des films est vide.", ephemeral=True)
            return
        embed = discord.Embed(
            title="Liste des films 🎬",
            description="\n".join(f"- {film}" for film in films),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="supprjeu", description="Supprime un jeu de la liste")
    @app_commands.describe(nom="Nom du jeu à supprimer")
    async def supprjeu(self, interaction: discord.Interaction, nom: str):
        if nom in jeux:
            jeux.remove(nom)
            embed = discord.Embed(
                title="Jeu supprimé 🗑️",
                description=f"Le jeu **{nom}** a été supprimé de la liste.",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="Jeu non trouvé ❌",
                description=f"Le jeu **{nom}** n'est pas dans la liste.",
                color=discord.Color.orange()
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="note", description="Note un plat à deux")
    @app_commands.describe(nom="Nom du plat", note="Note sur 10")
    async def note(self, interaction: discord.Interaction, nom: str, note: int):
        if not 0 <= note <= 10:
            await interaction.response.send_message("La note doit être entre 0 et 10.", ephemeral=True)
            return
        user_id = interaction.user.id
        if nom not in notes:
            notes[nom] = {}
        notes[nom][user_id] = note
        moyenne = sum(notes[nom].values()) / len(notes[nom])
        embed = discord.Embed(
            title="Note enregistrée 🍽️",
            description=f"{interaction.user.display_name} a noté **{nom}** : {note}/10\nMoyenne actuelle : {moyenne:.1f}/10",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    # Tu peux ajouter ici les autres commandes, sans changer leur code sauf pour adapter interaction et embeds si besoin

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

async def main():
    await bot.add_cog(MonBot(bot))

if __name__ == "__main__":
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Bot Discord actif."

    # Lance Flask en thread séparé (utile si tu utilises Render ou Heroku pour garder le bot actif)
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()

    # Lance le bot proprement avec asyncio.run (évite l’erreur 'bot.loop')
    asyncio.run(main())
    bot.run(os.getenv("TOKEN"))
