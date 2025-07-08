import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
from datetime import datetime, timedelta
from flask import Flask

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Stockages temporaires
films = []
jeux = []
notes = {}

class MonBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def setup_hook(self):
        await self.bot.tree.sync()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Connecté en tant que {self.bot.user}")

    # /note
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
        await interaction.response.send_message(f"🍽️ {interaction.user.display_name} a noté **{nom}** : {note}/10\nMoyenne actuelle : {moyenne:.1f}/10")

    # /notesperso
    @app_commands.command(name="notesperso", description="Affiche vos notes données aux plats")
    async def notesperso(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        lignes = [f"**{plat}** : {note}/10" for plat, users in notes.items() if user_id in users for note in [users[user_id]]]
        description = "\n".join(lignes) or "Aucune note trouvée."
        embed = discord.Embed(title="Vos notes personnelles", description=description, color=0xdeb887)
        await interaction.response.send_message(embed=embed)

    # /supprnote
    @app_commands.command(name="supprnote", description="Supprime votre note pour un plat")
    async def supprnote(self, interaction: discord.Interaction, nom: str):
        user_id = interaction.user.id
        if nom in notes and user_id in notes[nom]:
            del notes[nom][user_id]
            await interaction.response.send_message(f"Votre note pour **{nom}** a été supprimée.")
        else:
            await interaction.response.send_message(f"Vous n'avez pas noté ce plat.")

    # /ajoutfilm
    @app_commands.command(name="ajoutfilm", description="Ajoute un film à la liste")
    async def ajoutfilm(self, interaction: discord.Interaction, nom: str):
        films.append(nom)
        await interaction.response.send_message(f"🎬 Film **{nom}** ajouté à la liste !")

    # /supprfilm
    @app_commands.command(name="supprfilm", description="Supprime un film de la liste")
    async def supprfilm(self, interaction: discord.Interaction, nom: str):
        if nom in films:
            films.remove(nom)
            await interaction.response.send_message(f"🎬 Film **{nom}** supprimé.")
        else:
            await interaction.response.send_message("Ce film n'est pas dans la liste.")

    # /films
    @app_commands.command(name="films", description="Affiche la liste des films")
    async def films_cmd(self, interaction: discord.Interaction):
        description = "\n".join(f"🎬 {film}" for film in films) or "Aucun film dans la liste."
        embed = discord.Embed(title="Films à voir", description=description, color=0xc4a484)
        await interaction.response.send_message(embed=embed)

    # /ajoutjeu
    @app_commands.command(name="ajoutjeu", description="Ajoute un jeu à la liste")
    async def ajoutjeu(self, interaction: discord.Interaction, nom: str):
        jeux.append(nom)
        await interaction.response.send_message(f"🎮 Jeu **{nom}** ajouté à la liste !")

    # /supprjeu
    @app_commands.command(name="supprjeu", description="Supprime un jeu de la liste")
    async def supprjeu(self, interaction: discord.Interaction, nom: str):
        if nom in jeux:
            jeux.remove(nom)
            await interaction.response.send_message(f"🎮 Jeu **{nom}** supprimé.")
        else:
            await interaction.response.send_message("Ce jeu n'est pas dans la liste.")

    # /jeux
    @app_commands.command(name="jeux", description="Affiche la liste des jeux")
    async def jeux_cmd(self, interaction: discord.Interaction):
        description = "\n".join(f"🎮 {jeu}" for jeu in jeux) or "Aucun jeu dans la liste."
        embed = discord.Embed(title="Jeux à jouer", description=description, color=0xa67b5b)
        await interaction.response.send_message(embed=embed)

    # /classement
    @app_commands.command(name="classement", description="Classement des plats selon la moyenne")
    async def classement(self, interaction: discord.Interaction):
        moyennes = [(plat, sum(users.values()) / len(users)) for plat, users in notes.items() if users]
        sorted_moyennes = sorted(moyennes, key=lambda x: x[1], reverse=True)
        lignes = [f"**{plat}** : {moyenne:.1f}/10" for plat, moyenne in sorted_moyennes]
        embed = discord.Embed(title="🍽️ Classement des plats", description="\n".join(lignes), color=0x8b5e3c)
        await interaction.response.send_message(embed=embed)

    # /rappel
    @app_commands.command(name="rappel", description="Crée un rappel")
    async def rappel(self, interaction: discord.Interaction, message: str, jours: int = 0, heures: int = 0, minutes: int = 0):
        delay = timedelta(days=jours, hours=heures, minutes=minutes).total_seconds()
        await interaction.response.send_message(f"⏰ Rappel dans {jours}j {heures}h {minutes}m : {message}")
        await asyncio.sleep(delay)
        await interaction.channel.send(f"🔔 Rappel : {message}")

    # /comptearebours
    @app_commands.command(name="comptearebours", description="Lance un compte à rebours")
    async def comptearebours(self, interaction: discord.Interaction, titre: str, jours: int = 0, heures: int = 0, minutes: int = 0):
        total_sec = timedelta(days=jours, hours=heures, minutes=minutes).total_seconds()
        end_time = datetime.utcnow() + timedelta(seconds=total_sec)
        embed = discord.Embed(title=f"⏳ {titre}", color=0xf4e2d8)
        message = await interaction.response.send_message(embed=embed)

        async def update_embed():
            while True:
                remaining = end_time - datetime.utcnow()
                if remaining.total_seconds() <= 0:
                    await interaction.followup.send(f"🎉 Fin du compte à rebours pour **{titre}** !")
                    break
                embed.description = f"Temps restant : {str(remaining).split('.')[0]}"
                await message.edit(embed=embed)
                await asyncio.sleep(60)

        await update_embed()

    # /embedcreer
    @app_commands.command(name="embedcreer", description="Créer un embed personnalisable")
    async def embedcreer(self, interaction: discord.Interaction, titre: str, description: str):
        embed = discord.Embed(title=titre, description=description, color=0xdccca3)
        await interaction.response.send_message(embed=embed)

    # /embedmodifier
    @app_commands.command(name="embedmodifier", description="Modifie un embed existant (id requis)")
    async def embedmodifier(self, interaction: discord.Interaction, message_id: str, titre: str = None, description: str = None):
        try:
            msg = await interaction.channel.fetch_message(int(message_id))
            if msg.embeds:
                embed = msg.embeds[0]
                if titre:
                    embed.title = titre
                if description:
                    embed.description = description
                await msg.edit(embed=embed)
                await interaction.response.send_message("✅ Embed modifié.", ephemeral=True)
            else:
                await interaction.response.send_message("Ce message ne contient pas d'embed.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Erreur : {e}", ephemeral=True)

async def main():
    await bot.add_cog(MonBot(bot))

bot.loop.create_task(main())

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Discord actif."

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.run(os.getenv("TOKEN"))
