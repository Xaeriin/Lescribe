import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import asyncio
import os
import threading
from flask import Flask

# ====== CONFIGURATION ======
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

TOKEN = os.getenv("TOKEN")
FREE_GAMES_CHANNEL_ID = int(os.getenv("FREE_GAMES_CHANNEL_ID", "0"))

if TOKEN is None:
    print("\u274c TOKEN non d\u00e9fini dans .env")
    exit(1)

# ====== DONN\u00c9ES ======
notes = {}  # Structure: {"plat": {"user_id": note, ...}}
jeux = []
films = []
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

# ====== UTILS ======
def moyenne_notes(note_dict):
    return round(sum(note_dict.values()) / len(note_dict), 2) if note_dict else 0

async def get_username(guild, user_id):
    try:
        member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        return member.display_name
    except:
        return f"<@{user_id}>"

# ====== \u00c9V\u00c9NEMENTS ======
@bot.event
async def on_ready():
    await tree.sync()
    print(f"\u2705 Connect\u00e9 en tant que {bot.user}")
    countdown_loop.start()
    rappel_loop.start()

# ====== COMMANDES ======
@tree.command(name="note", description="Faire ou modifier une \u00e9valuation")
@app_commands.describe(nom="Nom du plat", note="Note sur 10")
async def cmd_note(interaction: discord.Interaction, nom: str, note: int):
    if not (0 <= note <= 10):
        await interaction.response.send_message("Merci de donner une note entre 0 et 10.", ephemeral=True)
        return

    user_id = interaction.user.id
    if nom not in notes:
        notes[nom] = {}

    notes[nom][user_id] = note

    embed = discord.Embed(title=f"\ud83c\udf7d\ufe0f {nom}", color=0xffa500)

    for uid, n in notes[nom].items():
        username = await get_username(interaction.guild, uid)
        embed.add_field(name=username, value=f"{n}/10", inline=False)

    moyenne = moyenne_notes(notes[nom])
    embed.add_field(name="\u2b50 Note moyenne", value=f"{moyenne}/10", inline=False)

    await interaction.response.send_message(embed=embed)

@tree.command(name="supprnote", description="Supprimer une \u00e9valuation")
@app_commands.describe(nom="Nom du plat")
async def cmd_supprnote(interaction: discord.Interaction, nom: str):
    user_id = interaction.user.id
    if nom in notes and user_id in notes[nom]:
        del notes[nom][user_id]
        if not notes[nom]:
            del notes[nom]
        await interaction.response.send_message(f"Note supprim\u00e9e pour **{nom}**.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Aucune note trouv\u00e9e pour **{nom}**.", ephemeral=True)

@tree.command(name="classement", description="Voir le classement des plats")
async def cmd_classement(interaction: discord.Interaction):
    if not notes:
        await interaction.response.send_message("Aucune note enregistr\u00e9e.", ephemeral=True)
        return

    moyenne_dict = {nom: moyenne_notes(votes) for nom, votes in notes.items()}
    classement = sorted(moyenne_dict.items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="\ud83c\udf1f Classement des plats", color=0x00ff00)
    for nom, moyenne in classement:
        embed.add_field(name=nom, value=f"{moyenne}/10", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="notesperso", description="Voir tes notes personnelles")
async def cmd_notesperso(interaction: discord.Interaction):
    user_id = interaction.user.id
    embed = discord.Embed(title=f"\ud83d\udc64 Notes de {interaction.user.display_name}", color=0x1abc9c)
    for plat, votes in notes.items():
        if user_id in votes:
            embed.add_field(name=plat, value=f"{votes[user_id]}/10", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="ajoutjeu", description="Ajouter un jeu")
@app_commands.describe(nom="Nom du jeu", plateforme="Plateforme")
async def cmd_ajoutjeu(interaction: discord.Interaction, nom: str, plateforme: str):
    jeux.append({"nom": nom, "plateforme": plateforme})
    await interaction.response.send_message(f"Jeu **{nom}** ajout\u00e9 sur **{plateforme}**.", ephemeral=True)

@tree.command(name="jeux", description="Voir la liste des jeux")
async def cmd_jeux(interaction: discord.Interaction):
    embed = discord.Embed(title="\ud83c\udfae Liste des jeux", color=0x7289da)
    for jeu in jeux:
        embed.add_field(name=jeu["nom"], value=jeu["plateforme"], inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="modifjeux", description="Modifier le titre et couleur de la liste des jeux")
@app_commands.describe(titre="Nouveau titre", couleur_hex="Couleur hex (ex: #FF0000)")
async def cmd_modifjeux(interaction: discord.Interaction, titre: str, couleur_hex: str):
    try:
        couleur = int(couleur_hex.lstrip("#"), 16)
    except:
        await interaction.response.send_message("Couleur invalide.", ephemeral=True)
        return

    embed = discord.Embed(title=titre, color=couleur)
    for jeu in jeux:
        embed.add_field(name=jeu["nom"], value=jeu["plateforme"], inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="embedcreer", description="Cr\u00e9er un embed personnalis\u00e9 avec interface interactive")
async def cmd_embedcreer(interaction: discord.Interaction):
    class EmbedEditor(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=300)
            self.embed = discord.Embed(title="Titre", description="Description", color=0x3498db)

        @discord.ui.button(label="Titre", style=discord.ButtonStyle.primary)
        async def titre(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Quel est le nouveau titre ?", ephemeral=True)
            msg = await bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=60)
            self.embed.title = msg.content
            await interaction.followup.send(embed=self.embed, ephemeral=True, view=self)

        @discord.ui.button(label="Description", style=discord.ButtonStyle.secondary)
        async def description(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Nouvelle description ?", ephemeral=True)
            msg = await bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=60)
            self.embed.description = msg.content
            await interaction.followup.send(embed=self.embed, ephemeral=True, view=self)

        @discord.ui.button(label="Couleur", style=discord.ButtonStyle.success)
        async def couleur(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Couleur hex ? (ex: #00ff00)", ephemeral=True)
            msg = await bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=60)
            try:
                self.embed.color = discord.Color(int(msg.content.lstrip('#'), 16))
            except:
                pass
            await interaction.followup.send(embed=self.embed, ephemeral=True, view=self)

        @discord.ui.button(label="Envoyer", style=discord.ButtonStyle.green)
        async def envoyer(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.channel.send(embed=self.embed)
            await interaction.response.send_message("Embed envoy\u00e9 !", ephemeral=True)
            self.stop()

        @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger)
        async def annuler(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Annul\u00e9.", ephemeral=True)
            self.stop()

    view = EmbedEditor()
    await interaction.response.send_message("Edition de l'embed ci-dessous:", embed=view.embed, view=view, ephemeral=True)

# ====== T\u00c2CHES DE FOND ======
@tasks.loop(seconds=60)
async def countdown_loop():
    now = datetime.datetime.now()
    for cd in countdowns[:]:
        if cd["date"] <= now:
            channel = bot.get_channel(cd["channel"])
            if channel:
                await channel.send(f"\u23f0 **{cd['titre']}** est arriv\u00e9 !")
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

# ====== LANCEMENT ======
bot.run(TOKEN)