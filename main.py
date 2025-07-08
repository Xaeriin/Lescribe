import os
import threading
from flask import Flask
import discord
from discord.ext import commands, tasks
from discord import app_commands, ui, Embed, Interaction

# --- Flask minimal pour Render ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Discord actif."

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- Discord bot setup ---
intents = discord.Intents.default()
intents.message_content = True  # si besoin

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# Données en mémoire (à remplacer par DB ou fichier persistant)
notes = {}        # {user_id: {plat: note}}
films = []        # liste de dicts {nom: str, description: str}
jeux = []         # liste de dicts {nom: str, description: str}
rappels = []      # liste de rappels (simple)
embeds_saved = {} # {embed_name: dict embed}

# --- Commandes ---

# /note
@tree.command(name="note", description="Noter un plat avec ton partenaire")
@app_commands.describe(plat="Nom du plat", note="Note sur 10")
async def note(interaction: Interaction, plat: str, note: int):
    if not (0 <= note <= 10):
        await interaction.response.send_message("La note doit être entre 0 et 10.", ephemeral=True)
        return
    user_notes = notes.setdefault(interaction.user.id, {})
    user_notes[plat] = note
    # Calcule moyenne entre les 2 utilisateurs (exemple)
    # Ici on simplifie : moyenne sur toutes les notes données par tous (adapter selon besoin)
    total, count = 0, 0
    for user_id, plats in notes.items():
        if plat in plats:
            total += plats[plat]
            count += 1
    moyenne = round(total / count, 2) if count else "N/A"

    embed = Embed(title=f"Note pour {plat}", description=f"Moyenne actuelle: {moyenne}/10", color=0x8FBC8F)
    embed.add_field(name=f"{interaction.user.display_name}", value=f"Ta note : {note}/10", inline=False)

    await interaction.response.send_message(embed=embed)

# /notesperso
@tree.command(name="notesperso", description="Afficher toutes tes notes de plats")
async def notesperso(interaction: Interaction):
    user_notes = notes.get(interaction.user.id, {})
    if not user_notes:
        await interaction.response.send_message("Tu n'as pas encore noté de plat.", ephemeral=True)
        return
    embed = Embed(title=f"Tes notes de plats", color=0xFFD700)
    for plat, note in user_notes.items():
        embed.add_field(name=plat, value=f"{note}/10", inline=False)
    await interaction.response.send_message(embed=embed)

# /supprnote
@tree.command(name="supprnote", description="Supprimer une note pour un plat")
@app_commands.describe(plat="Nom du plat à supprimer")
async def supprnote(interaction: Interaction, plat: str):
    user_notes = notes.get(interaction.user.id, {})
    if plat in user_notes:
        del user_notes[plat]
        await interaction.response.send_message(f"Note supprimée pour {plat}.")
    else:
        await interaction.response.send_message(f"Tu n'as pas de note pour {plat}.", ephemeral=True)

# /aide
@tree.command(name="aide", description="Afficher le guide du bot")
async def aide(interaction: Interaction):
    embed = Embed(title="Guide du Bot", description="Voici les commandes disponibles :", color=0x00BFFF)
    cmds = [
        ("/note [plat] [note]", "Noter un plat avec ton partenaire (note modifiable)"),
        ("/notesperso", "Afficher toutes tes notes"),
        ("/supprnote [plat]", "Supprimer une note"),
        ("/films", "Afficher la liste des films"),
        ("/ajoutfilm [nom] [desc]", "Ajouter un film"),
        ("/supprfilm [nom]", "Supprimer un film"),
        ("/jeux", "Afficher la liste des jeux"),
        ("/ajoutjeu [nom] [desc]", "Ajouter un jeu"),
        ("/classement", "Afficher le classement des plats"),
        ("/rappel [message] [temps]", "Créer un rappel"),
        ("/embedcreer", "Créer un embed modifiable"),
        ("/embedmodifier [nom]", "Modifier un embed sauvegardé"),
        ("/comptearebours [temps]", "Créer un compte à rebours")
    ]
    for cmd, desc in cmds:
        embed.add_field(name=cmd, value=desc, inline=False)
    await interaction.response.send_message(embed=embed)

# /films
@tree.command(name="films", description="Afficher la liste des films")
async def films_cmd(interaction: Interaction):
    if not films:
        await interaction.response.send_message("Aucun film pour le moment.", ephemeral=True)
        return
    embed = Embed(title="Liste des films", color=0xFF4500)
    for film in films:
        embed.add_field(name=film['nom'], value=film['description'], inline=False)
    await interaction.response.send_message(embed=embed)

# /ajoutfilm
@tree.command(name="ajoutfilm", description="Ajouter un film à la liste")
@app_commands.describe(nom="Nom du film", description="Description du film")
async def ajoutfilm(interaction: Interaction, nom: str, description: str):
    films.append({"nom": nom, "description": description})
    await interaction.response.send_message(f"Film '{nom}' ajouté.")

# /supprfilm
@tree.command(name="supprfilm", description="Supprimer un film de la liste")
@app_commands.describe(nom="Nom du film à supprimer")
async def supprfilm(interaction: Interaction, nom: str):
    global films
    films = [f for f in films if f['nom'].lower() != nom.lower()]
    await interaction.response.send_message(f"Film '{nom}' supprimé si existant.")

# /jeux
@tree.command(name="jeux", description="Afficher la liste des jeux")
async def jeux_cmd(interaction: Interaction):
    if not jeux:
        await interaction.response.send_message("Aucun jeu pour le moment.", ephemeral=True)
        return
    embed = Embed(title="Liste des jeux", color=0x32CD32)
    for jeu in jeux:
        embed.add_field(name=jeu['nom'], value=jeu['description'], inline=False)
    await interaction.response.send_message(embed=embed)

# /ajoutjeu
@tree.command(name="ajoutjeu", description="Ajouter un jeu à la liste")
@app_commands.describe(nom="Nom du jeu", description="Description du jeu")
async def ajoutjeu(interaction: Interaction, nom: str, description: str):
    jeux.append({"nom": nom, "description": description})
    await interaction.response.send_message(f"Jeu '{nom}' ajouté.")

# /classement (classement des plats selon moyenne)
@tree.command(name="classement", description="Afficher le classement des plats")
async def classement(interaction: Interaction):
    moyenne_plats = {}
    counts = {}
    for user_id, plats in notes.items():
        for plat, note in plats.items():
            moyenne_plats[plat] = moyenne_plats.get(plat, 0) + note
            counts[plat] = counts.get(plat, 0) + 1
    if not moyenne_plats:
        await interaction.response.send_message("Aucune note de plat pour l'instant.", ephemeral=True)
        return
    classement = sorted(((plat, moyenne_plats[plat]/counts[plat]) for plat in moyenne_plats), key=lambda x: x[1], reverse=True)
    embed = Embed(title="Classement des plats", color=0xFFD700)
    for plat, moyenne in classement:
        embed.add_field(name=plat, value=f"Moyenne: {moyenne:.2f}/10", inline=False)
    await interaction.response.send_message(embed=embed)

# /rappel
@tree.command(name="rappel", description="Créer un rappel")
@app_commands.describe(message="Message du rappel", temps="Temps en secondes")
async def rappel(interaction: Interaction, message: str, temps: int):
    await interaction.response.send_message(f"Rappel créé dans {temps} secondes.", ephemeral=True)
    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=temps))
    await interaction.channel.send(f"⏰ Rappel : {message}")

# /embedcreer (exemple simplifié)
@tree.command(name="embedcreer", description="Créer un embed modifiable")
async def embedcreer(interaction: Interaction):
    embed = Embed(title="Titre par défaut", description="Description par défaut", color=0x3498db)
    message = await interaction.response.send_message(embed=embed, ephemeral=False)
    # Ici, tu peux étendre avec une vraie interface avec boutons pour modifier (exemple simplifié)

# /embedmodifier (exemple simplifié)
@tree.command(name="embedmodifier", description="Modifier un embed sauvegardé")
@app_commands.describe(nom="Nom de l'embed à modifier")
async def embedmodifier(interaction: Interaction, nom: str):
    saved = embeds_saved.get(nom)
    if not saved:
        await interaction.response.send_message(f"Aucun embed nommé '{nom}'.", ephemeral=True)
        return
    embed = Embed.from_dict(saved)
    await interaction.response.send_message(embed=embed)

# /comptearebours
@tree.command(name="comptearebours", description="Créer un compte à rebours")
@app_commands.describe(temps="Temps en secondes")
async def comptearebours(interaction: Interaction, temps: int):
    await interaction.response.send_message(f"Compte à rebours de {temps} secondes commencé.")
    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=temps))
    await interaction.channel.send("⏰ Le compte à rebours est terminé!")

# --- Events ---
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    await tree.sync()

# --- Main ---
if __name__ == "__main__":
    # Lance Flask dans un thread parallèle
    threading.Thread(target=run_flask).start()
    bot.run(os.environ["TOKEN"])
