import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import datetime
import asyncio
import os
import threading
from flask import Flask

# ====== CONFIGURATION ======
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

TOKEN = os.getenv("TOKEN")
FREE_GAMES_CHANNEL_ID = int(os.getenv("FREE_GAMES_CHANNEL_ID", "0"))

if TOKEN is None:
    print("❌ TOKEN non défini dans .env")
    exit(1)

# ====== DONNÉES ======
notes = {}  # {plat: {user_id: note}}
jeux = []
films = []
embed_configs = {
    "notes": {"titre": "Notes des plats", "couleur": 0xffccff},
    "classement": {"titre": "Classement des plats", "couleur": 0xffccff},
    "jeux": {"titre": "Liste des jeux", "couleur": 0xaaffaa},
    "films": {"titre": "Liste des films/séries", "couleur": 0xaaaaff},
}

countdowns = []
rappels = []

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
    print(f"✅ Connecté en tant que {bot.user}")
    countdown_loop.start()
    rappel_loop.start()

# ====== INTERFACES ======

class EmbedBuilder(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.embed = discord.Embed(title="Nouveau titre", description="Description ici", color=0xffccff)
        self.message = None

    async def send_preview(self, interaction):
        if self.message is None:
            self.message = await interaction.channel.send(embed=self.embed, view=self)
        else:
            await self.message.edit(embed=self.embed, view=self)

    @discord.ui.button(label="Modifier le titre", style=discord.ButtonStyle.primary)
    async def modif_titre(self, interaction: discord.Interaction, button: discord.ui.Button):
        class TitreModal(Modal, title="Modifier le titre"):
            titre = TextInput(label="Titre", max_length=256)
            async def on_submit(self, modal_interaction):
                self.view.embed.title = self.titre.value
                await self.view.send_preview(modal_interaction)
                await modal_interaction.response.defer()
        await interaction.response.send_modal(TitreModal(view=self))

    @discord.ui.button(label="Modifier la description", style=discord.ButtonStyle.primary)
    async def modif_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        class DescModal(Modal, title="Modifier la description"):
            desc = TextInput(label="Description", style=discord.TextStyle.paragraph)
            async def on_submit(self, modal_interaction):
                self.view.embed.description = self.desc.value
                await self.view.send_preview(modal_interaction)
                await modal_interaction.response.defer()
        await interaction.response.send_modal(DescModal(view=self))

    @discord.ui.button(label="Changer la couleur", style=discord.ButtonStyle.secondary)
    async def modif_couleur(self, interaction: discord.Interaction, button: discord.ui.Button):
        class CouleurModal(Modal, title="Changer la couleur"):
            couleur = TextInput(label="Couleur HEX (ex: #ffccff)")
            async def on_submit(self, modal_interaction):
                try:
                    self.view.embed.color = int(self.couleur.value.replace("#", ""), 16)
                    await self.view.send_preview(modal_interaction)
                except:
                    await modal_interaction.response.send_message("Couleur invalide.", ephemeral=True)
                await modal_interaction.response.defer()
        await interaction.response.send_modal(CouleurModal(view=self))

    @discord.ui.button(label="Ajouter une image", style=discord.ButtonStyle.secondary)
    async def modif_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        class ImageModal(Modal, title="Ajouter une image"):
            url = TextInput(label="URL de l'image")
            async def on_submit(self, modal_interaction):
                self.view.embed.set_image(url=self.url.value)
                await self.view.send_preview(modal_interaction)
                await modal_interaction.response.defer()
        await interaction.response.send_modal(ImageModal(view=self))

    @discord.ui.button(label="Définir un footer", style=discord.ButtonStyle.secondary)
    async def modif_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        class FooterModal(Modal, title="Définir un footer"):
            text = TextInput(label="Texte du footer")
            async def on_submit(self, modal_interaction):
                self.view.embed.set_footer(text=self.text.value)
                await self.view.send_preview(modal_interaction)
                await modal_interaction.response.defer()
        await interaction.response.send_modal(FooterModal(view=self))

# ====== COMMANDES EMBED BUILDER ======

@tree.command(name="embedcreer", description="Créer un embed interactif personnalisé")
async def cmd_embedcreer(interaction: discord.Interaction):
    view = EmbedBuilder()
    await interaction.response.send_message("🎨 Création d'un embed cottage-core/rose :", ephemeral=True)
    await view.send_preview(interaction)

# ====== COMPTE À REBOURS (format assisté) ======

@tree.command(name="comptearebours", description="Créer un compte à rebours")
@app_commands.describe(titre="Titre du compte à rebours", date="Date/heure (ex: 2025-08-21 14:30)")
async def cmd_comptearebours(interaction: discord.Interaction, titre: str, date: str):
    try:
        dt = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M")
        countdowns.append({"titre": titre, "date": dt, "channel": interaction.channel_id})
        await interaction.response.send_message(f"⏳ Compte à rebours **{titre}** enregistré pour {date}", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ Format de date invalide. Exemple : 2025-08-21 14:30", ephemeral=True)

# ====== DÉMARRAGE DU BOT ======

if __name__ == "__main__":
    bot.run(TOKEN)
