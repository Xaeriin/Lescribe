import os
import threading
import asyncio
import re
from flask import Flask
import discord
from discord.ext import commands
from discord import app_commands, Embed, Interaction, ui

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

# --- Utilitaires ---

def parse_duration(text: str) -> int:
    """
    Parse un string comme '1mois 2semaines 3j 4h 5m 6s' en secondes.
    Exemples acceptés:
     - 2h30m
     - 1j 2h
     - 3semaines 4j
    """
    regex = re.compile(r'(\d+)\s*(mois|semaines|sem|jours|j|heures|h|minutes|min|m|secondes|s)')
    seconds_per_unit = {
        'mois': 30*24*3600,
        'semaines': 7*24*3600,
        'sem': 7*24*3600,
        'jours': 24*3600,
        'j': 24*3600,
        'heures': 3600,
        'h': 3600,
        'minutes': 60,
        'min': 60,
        'm': 60,
        'secondes': 1,
        's': 1,
    }
    total_seconds = 0
    for amount, unit in regex.findall(text.lower()):
        total_seconds += int(amount) * seconds_per_unit[unit]
    return total_seconds

# --- Commandes ---

# /note
@bot.tree.command(name="note", description="Note un plat avec ton/ta partenaire")
@app_commands.describe(
    plat="Nom du plat que vous avez goûté",
    note="Ta note personnelle sur 10"
)
async def note(interaction: discord.Interaction, plat: str, note: float):
    if not (0 <= note <= 10):
        await interaction.response.send_message("La note doit être comprise entre 0 et 10.", ephemeral=True)
        return

    await interaction.response.defer()
    channel = interaction.channel
    message_reference = None

    async for message in channel.history(limit=100):
        if message.author == bot.user and message.embeds:
            embed = message.embeds[0]
            if embed.title == f"🍽️ Dégustation : {plat}":
                message_reference = message
                break

    username = interaction.user.display_name
    user_id = str(interaction.user.id)

    emoji_note = "🧺"
    emoji_moyenne = "🍯"

    notes = {}
    if message_reference:
        embed = message_reference.embeds[0]

        # Extraire les notes existantes depuis les champs
        for field in embed.fields:
            notes[field.name] = float(field.value.replace("/10", ""))

        # Mettre à jour ou ajouter la note de l'utilisateur
        notes[username] = note

        # Recalcul de la moyenne
        moyenne = round(sum(notes.values()) / len(notes), 2)

        # Construire la description
        description = f"{emoji_note} **Nom du plat** : {plat}\n"
        for user, n in notes.items():
            description += f"**{user}** : {n}/10\n"
        description += f"{emoji_moyenne} **Moyenne** : {moyenne}/10"

        # Mettre à jour l'embed
        embed.description = description
        embed.clear_fields()
        for user, n in notes.items():
            embed.add_field(name=user, value=f"{n}/10", inline=False)

        await message_reference.edit(embed=embed)
        await interaction.followup.send("Ta note a été mise à jour.", ephemeral=True)

    else:
        moyenne = round(note, 2)
        description = (
            f"{emoji_note} **Nom du plat** : {plat}\n"
            f"**{username}** : {note}/10\n"
            f"{emoji_moyenne} **Moyenne** : {moyenne}/10"
        )
        embed = discord.Embed(
            title=f"🍽️ Dégustation : {plat}",
            description=description,
            color=discord.Color.blurple()
        )
        embed.add_field(name=username, value=f"{note}/10", inline=False)
        await channel.send(embed=embed)
        await interaction.followup.send("Ton évaluation a été publiée dans un nouvel embed.", ephemeral=True)


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

# /supprjeu (ajout)
@tree.command(name="supprjeu", description="Supprimer un jeu de la liste")
@app_commands.describe(nom="Nom du jeu à supprimer")
async def supprjeu(interaction: Interaction, nom: str):
    global jeux
    before_len = len(jeux)
    jeux = [j for j in jeux if j['nom'].lower() != nom.lower()]
    if len(jeux) < before_len:
        await interaction.response.send_message(f"Jeu '{nom}' supprimé.")
    else:
        await interaction.response.send_message(f"Jeu '{nom}' non trouvé.", ephemeral=True)

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
        ("/supprjeu [nom]", "Supprimer un jeu"),
        ("/classement", "Afficher le classement des plats"),
        ("/rappel [message] [temps]", "Créer un rappel (ex: 1h30m)"),
        ("/embedcreer", "Créer un embed modifiable"),
        ("/embedmodifier [nom]", "Modifier un embed sauvegardé"),
        ("/comptearebours [temps]", "Créer un compte à rebours (ex: 2j3h)")
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
    before_len = len(films)
    films = [f for f in films if f['nom'].lower() != nom.lower()]
    if len(films) < before_len:
        await interaction.response.send_message(f"Film '{nom}' supprimé.")
    else:
        await interaction.response.send_message(f"Film '{nom}' non trouvé.", ephemeral=True)

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

# --- Embed Creator & Modifier avec interface interactive ---

class EmbedEditorView(ui.View):
    def __init__(self, embed: Embed, name: str, user_id: int):
        super().__init__(timeout=600)  # 10 minutes
        self.embed = embed
        self.name = name
        self.user_id = user_id
        self.message = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Tu ne peux pas modifier cet embed.", ephemeral=True)
            return False
        return True

    async def update_message(self):
        if self.message:
            await self.message.edit(embed=self.embed, view=self)

    @ui.button(label="Modifier Titre", style=discord.ButtonStyle.primary)
    async def modify_title(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Envoie le nouveau titre de l'embed :", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé.", ephemeral=True)
            return
        self.embed.title = msg.content
        await interaction.followup.send(f"Titre modifié en : {msg.content}", ephemeral=True)
        await self.update_message()

    @ui.button(label="Modifier Description", style=discord.ButtonStyle.primary)
    async def modify_description(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Envoie la nouvelle description de l'embed :", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=120)
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé.", ephemeral=True)
            return
        self.embed.description = msg.content
        await interaction.followup.send(f"Description modifiée.", ephemeral=True)
        await self.update_message()

    @ui.button(label="Modifier Couleur", style=discord.ButtonStyle.primary)
    async def modify_color(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Envoie la nouvelle couleur HEX (ex: #FF00FF) :", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel and re.match(r"^#?[0-9A-Fa-f]{6}$", m.content)

        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé ou format invalide.", ephemeral=True)
            return
        color_hex = msg.content.strip().lstrip('#')
        self.embed.color = int(color_hex, 16)
        await interaction.followup.send(f"Couleur modifiée en #{color_hex.upper()}.", ephemeral=True)
        await self.update_message()


    @ui.button(label="Ajouter Image", style=discord.ButtonStyle.secondary)
    async def add_image(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Envoie une **URL d'image ou GIF** valide :", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel and m.content.startswith("http")

        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏳ Temps écoulé ou URL invalide.", ephemeral=True)
            return
        self.embed.set_image(url=msg.content)
        await interaction.followup.send("✅ Image ajoutée à l'embed.", ephemeral=True)
        await self.update_message()


    @ui.button(label="Sauvegarder", style=discord.ButtonStyle.success)
    async def save_embed(self, interaction: Interaction, button: ui.Button):
        embeds_saved[self.name] = self.embed.to_dict()
        await interaction.response.send_message(f"Embed '{self.name}' sauvegardé !", ephemeral=True)
        self.stop()

    @ui.button(label="Annuler", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Modification annulée.", ephemeral=True)
        self.stop()

# /embedcreer
@tree.command(name="embedcreer", description="Créer un embed modifiable")
async def embedcreer(interaction: Interaction):
    embed = Embed(title="Titre par défaut", description="Description par défaut", color=0x3498db)
    view = EmbedEditorView(embed, name=f"embed_{interaction.user.id}", user_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()

# /embedmodifier
@tree.command(name="embedmodifier", description="Modifier un embed sauvegardé")
@app_commands.describe(nom="Nom de l'embed à modifier")
async def embedmodifier(interaction: Interaction, nom: str):
    saved = embeds_saved.get(nom)
    if not saved:
        await interaction.response.send_message(f"Aucun embed nommé '{nom}'.", ephemeral=True)
        return
    embed = Embed.from_dict(saved)
    view = EmbedEditorView(embed, name=nom, user_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()

# /rappel
@tree.command(name="rappel", description="Créer un rappel")
@app_commands.describe(message="Message du rappel", temps="Temps (ex: 1h30m, 2j)")
async def rappel(interaction: Interaction, message: str, temps: str):
    secondes = parse_duration(temps)
    if secondes <= 0:
        await interaction.response.send_message("Durée invalide.", ephemeral=True)
        return
    await interaction.response.send_message(f"Rappel créé dans {temps}.", ephemeral=True)
    await asyncio.sleep(secondes)
    await interaction.channel.send(f"⏰ Rappel : {message}")

# /comptearebours
@tree.command(name="comptearebours", description="Créer un compte à rebours")
@app_commands.describe(temps="Temps (ex: 1h30m, 2j)")
async def comptearebours(interaction: Interaction, temps: str):
    secondes = parse_duration(temps)
    if secondes <= 0:
        await interaction.response.send_message("Durée invalide.", ephemeral=True)
        return
    embed = Embed(title="Compte à rebours", description=f"Temps restant : {temps}", color=0xFF4500)
    message = await interaction.response.send_message(embed=embed)

    # Affichage approximatif: update toutes les 10 secondes
    start = asyncio.get_event_loop().time()
    end = start + secondes
    msg = await interaction.original_response()
    task = asyncio.create_task(asyncio.sleep(0))  # dummy pour déclaration
    comptearebours_tasks[interaction.user.id] = asyncio.current_task()
    while True:
        now = asyncio.get_event_loop().time()
        reste = int(end - now)
        if reste <= 0:
            break
        # Formattage du temps restant en j h m s
        j = reste // 86400
        h = (reste % 86400) // 3600
        m = (reste % 3600) // 60
        s = reste % 60
        desc = f"Temps restant : {j}j {h}h {m}m {s}s"
        new_embed = Embed(title="Compte à rebours", description=desc, color=0xFF4500)
        try:
            await msg.edit(embed=new_embed)
        except:
            break
        await asyncio.sleep(10)
    # Fin du compte à rebours
    await msg.edit(embed=Embed(title="Compte à rebours terminé !", color=0x32CD32))
    await interaction.channel.send("⏰ Le compte à rebours est terminé!")

# compte à rebours stop
@tree.command(name="compteareboursstop", description="Annule ton compte à rebours en cours")
async def compteareboursstop(interaction: Interaction):
    task = comptearebours_tasks.pop(interaction.user.id, None)
    if task and not task.done():
        task.cancel()
        await interaction.response.send_message("⛔ Ton compte à rebours a été annulé.")
    else:
        await interaction.response.send_message("❌ Aucun compte à rebours en cours.", ephemeral=True)

comptearebours_tasks = {}


# --- Events ---
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    await tree.sync()

# --- Main ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(os.environ["TOKEN"])
