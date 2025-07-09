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

# /note : noter ou modifier une note
@tree.command(name="note", description="Noter un plat avec ton partenaire")
@app_commands.describe(plat="Nom du plat", note="Note sur 10")
async def note(interaction: Interaction, plat: str, note: int):
    if not (0 <= note <= 10):
        await interaction.response.send_message("La note doit être entre 0 et 10.", ephemeral=True)
        return

    user_id = interaction.user.id
    user_display = interaction.user.display_name

    # Enregistrer la note de l'utilisateur
    user_notes = notes.setdefault(user_id, {})
    user_notes[plat] = note

    # Rechercher une autre note pour ce plat
    other_user_note = None
    other_user_display = None
    for uid, plats in notes.items():
        if uid != user_id and plat in plats:
            member = interaction.guild.get_member(uid)
            if member:
                other_user_note = plats[plat]
                other_user_display = member.display_name
                break

    # Calcul de la moyenne
    total, count = note, 1
    if other_user_note is not None:
        total += other_user_note
        count += 1
    moyenne = round(total / count, 2)

    # Construction de l'embed
    embed = Embed(
        title=f"🍽️ Note pour '{plat}'",
        color=0x8FBC8F
    )

    if other_user_note is not None:
        embed.add_field(name="🧙🏼‍♂️ " + other_user_display, value=f"{other_user_note}/10", inline=False)
    else:
        embed.add_field(name="🧙🏼‍♂️ En attente...", value="Pas encore de note", inline=False)

    embed.add_field(name="🧝🏼‍♀️ " + user_display, value=f"{note}/10", inline=False)
    embed.add_field(name="📜 Moyenne", value=f"{moyenne}/10", inline=False)

    await interaction.response.send_message(embed=embed)


# /notesperso : afficher toutes ses notes
@tree.command(name="notesperso", description="Afficher toutes tes notes de plats")
async def notesperso(interaction: Interaction):
    user_notes = notes.get(interaction.user.id, {})
    if not user_notes:
        await interaction.response.send_message("Tu n'as pas encore noté de plat.", ephemeral=True)
        return
    embed = Embed(title=f"Tes notes de plats", color=0xFFD700)
    for plat, note_val in user_notes.items():
        embed.add_field(name=plat, value=f"{note_val}/10", inline=False)
    await interaction.response.send_message(embed=embed)

# /supprnote : supprimer une note d'un plat
@tree.command(name="supprnote", description="Supprimer une note pour un plat")
@app_commands.describe(plat="Nom du plat à supprimer")
async def supprnote(interaction: Interaction, plat: str):
    user_notes = notes.get(interaction.user.id, {})
    if plat in user_notes:
        del user_notes[plat]
        await interaction.response.send_message(f"Note supprimée pour {plat}.")
    else:
        await interaction.response.send_message(f"Tu n'as pas de note pour {plat}.", ephemeral=True)

# /classement : afficher le classement des plats selon moyenne
@tree.command(name="classement", description="Afficher le classement des plats")
async def classement(interaction: Interaction):
    moyenne_plats = {}
    counts = {}
    for user_id, plats in notes.items():
        for plat, note_val in plats.items():
            moyenne_plats[plat] = moyenne_plats.get(plat, 0) + note_val
            counts[plat] = counts.get(plat, 0) + 1
    if not moyenne_plats:
        await interaction.response.send_message("Aucune note de plat pour l'instant.", ephemeral=True)
        return
    classement_list = sorted(((plat, moyenne_plats[plat]/counts[plat]) for plat in moyenne_plats), key=lambda x: x[1], reverse=True)
    embed = Embed(title="Classement des plats", color=0xFFD700)
    for plat, moyenne in classement_list:
        embed.add_field(name=plat, value=f"Moyenne: {moyenne:.2f}/10", inline=False)
    await interaction.response.send_message(embed=embed)

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

    @ui.button(label="Sauvegarder et Quitter", style=discord.ButtonStyle.success)
    async def save_and_quit(self, interaction: Interaction, button: ui.Button):
        embeds_saved[self.name] = self.embed.to_dict()
        await interaction.response.send_message(f"Embed '{self.name}' sauvegardé.", ephemeral=True)
        self.stop()

# /embedcreer
@tree.command(name="embedcreer", description="Créer un embed modifiable")
@app_commands.describe(nom="Nom de l'embed à créer")
async def embedcreer(interaction: Interaction, nom: str):
    if nom in embeds_saved:
        await interaction.response.send_message("Un embed avec ce nom existe déjà.", ephemeral=True)
        return
    embed = Embed(title="Titre par défaut", description="Description par défaut", color=0x3498DB)
    view = EmbedEditorView(embed, nom, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()

# /embedmodifier
@tree.command(name="embedmodifier", description="Modifier un embed sauvegardé")
@app_commands.describe(nom="Nom de l'embed à modifier")
async def embedmodifier(interaction: Interaction, nom: str):
    if nom not in embeds_saved:
        await interaction.response.send_message("Aucun embed avec ce nom.", ephemeral=True)
        return
    embed_dict = embeds_saved[nom]
    embed = Embed.from_dict(embed_dict)
    view = EmbedEditorView(embed, nom, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()

# --- Rappel ---
@tree.command(name="rappel", description="Créer un rappel dans X temps")
@app_commands.describe(message="Message du rappel", temps="Durée (ex: 1h30m)")
async def rappel(interaction: Interaction, message: str, temps: str):
    secondes = parse_duration(temps)
    if secondes <= 0:
        await interaction.response.send_message("Durée invalide.", ephemeral=True)
        return
    await interaction.response.send_message(f"Rappel créé pour dans {temps}.")

    async def rappel_task():
        await asyncio.sleep(secondes)
        try:
            await interaction.user.send(f"Rappel: {message}")
        except:
            pass

    bot.loop.create_task(rappel_task())

# --- Compte à rebours ---
@tree.command(name="comptearebours", description="Créer un compte à rebours")
@app_commands.describe(temps="Durée (ex: 2j3h)")
async def comptearebours(interaction: Interaction, temps: str):
    secondes = parse_duration(temps)
    if secondes <= 0:
        await interaction.response.send_message("Durée invalide.", ephemeral=True)
        return

    message = await interaction.response.send_message(f"Compte à rebours : {temps} démarré.", ephemeral=False)

    async def countdown():
        remaining = secondes
        while remaining > 0:
            heures, rem = divmod(remaining, 3600)
            minutes, secondes_ = divmod(rem, 60)
            await asyncio.sleep(1)
            remaining -= 1
            try:
                await message.edit(content=f"Temps restant : {heures}h {minutes}m {secondes_}s")
            except:
                break
        try:
            await message.edit(content="⏰ Compte à rebours terminé !")
        except:
            pass

    bot.loop.create_task(countdown())

# --- Bot start ---

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    try:
        synced = await tree.sync()
        print(f"Commande slash synchronisées ({len(synced)})")
    except Exception as e:
        print(f"Erreur sync: {e}")

def main():
    # Lancer Flask dans un thread
    threading.Thread(target=run_flask).start()
    # Lancer Discord bot
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        print("Pas de token dans les variables d'environnement.")
        return
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
