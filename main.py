import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# Fichier JSON pour stocker données persistantes
DATA_FILE = "data.json"

# Données en mémoire
data = {
    "notes": {},       # {plat: {"user1_id": note1, "user2_id": note2}}
    "films": [],       # liste de films
    "jeux": [],        # liste de jeux
    "rappels": [],     # liste des rappels (optionnel pour futur)
}

# Chargement / sauvegarde JSON
def load_data():
    global data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- UTIL EMBED COTTAGE-CORE STYLE ---
def create_embed(title: str, description: str, color=0x8B4513, footer_text=None, image_url=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if footer_text:
        embed.set_footer(text=footer_text)
    if image_url:
        embed.set_image(url=image_url)
    return embed

# --- COMMANDES ---

@bot.event
async def on_ready():
    print(f"Connecté comme {bot.user} (ID: {bot.user.id})")
    await bot.tree.sync()
    load_data()

# --- /note ---
@tree.command(name="note", description="Noter un plat à deux (moyenne calculée)")
@app_commands.describe(plat="Nom du plat", note1="Votre note", note2="Note de votre copain")
async def note(interaction: discord.Interaction, plat: str, note1: float, note2: float):
    user_id = str(interaction.user.id)
    plat_key = plat.lower()

    if not (0 <= note1 <= 10 and 0 <= note2 <= 10):
        await interaction.response.send_message("Les notes doivent être entre 0 et 10.", ephemeral=True)
        return

    # Init plat si absent
    if plat_key not in data["notes"]:
        data["notes"][plat_key] = {}

    # Enregistre/Met à jour note de l'utilisateur
    # On suppose que interaction.user est "user1" ici, et le copain "user2"
    # MAIS on a besoin de stocker 2 notes par plat par user (user1_id, user2_id)
    # Vu que le bot ne sait pas qui est le copain, on stocke user1 note1 et "copain" note2 dans special key.
    # Je vais stocker comme ça:
    # data["notes"][plat_key] = {"user1": {"id": user_id, "note": note1}, "user2": {"id": "copain", "note": note2}}
    # Mais on ne sait pas qui est le copain, donc on stocke fixe sous "note1" et "note2" et user_id uniquement pour note1

    # Stockage simplifié:
    data["notes"][plat_key]["note1"] = {"user_id": user_id, "note": note1}
    data["notes"][plat_key]["note2"] = {"user_id": "copain", "note": note2}

    save_data()

    moyenne = (note1 + note2) / 2
    desc = f"**Plat :** {plat}\n" \
           f"**Votre note :** {note1}\n" \
           f"**Note de votre copain :** {note2}\n" \
           f"**Moyenne :** {moyenne:.2f}"

    embed = create_embed("Note du plat", desc, footer_text=f"Demandé par {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# --- /notesperso ---
@tree.command(name="notesperso", description="Voir toutes vos notes données pour les plats")
async def notesperso(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    notes_user = []
    for plat, notes in data["notes"].items():
        # Trouver si user a une note ici
        if "note1" in notes and notes["note1"]["user_id"] == user_id:
            notes_user.append(f"{plat}: {notes['note1']['note']}")
        elif "note2" in notes and notes["note2"]["user_id"] == user_id:
            notes_user.append(f"{plat}: {notes['note2']['note']}")

    if not notes_user:
        await interaction.response.send_message("Vous n'avez pas encore noté de plats.", ephemeral=True)
        return

    desc = "\n".join(notes_user)
    embed = create_embed("Vos notes de plats", desc, footer_text=f"Demandé par {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# --- /supprnote ---
@tree.command(name="supprnote", description="Supprimer la note d'un plat")
@app_commands.describe(plat="Nom du plat à supprimer")
async def supprnote(interaction: discord.Interaction, plat: str):
    user_id = str(interaction.user.id)
    plat_key = plat.lower()
    if plat_key not in data["notes"]:
        await interaction.response.send_message("Ce plat n'existe pas.", ephemeral=True)
        return

    notes = data["notes"][plat_key]
    removed = False

    if "note1" in notes and notes["note1"]["user_id"] == user_id:
        del data["notes"][plat_key]["note1"]
        removed = True
    if "note2" in notes and notes["note2"]["user_id"] == user_id:
        del data["notes"][plat_key]["note2"]
        removed = True

    if removed:
        # Si plus aucune note, supprimer le plat
        if "note1" not in data["notes"][plat_key] and "note2" not in data["notes"][plat_key]:
            del data["notes"][plat_key]
        save_data()
        await interaction.response.send_message(f"Votre note pour **{plat}** a été supprimée.")
    else:
        await interaction.response.send_message("Vous n'avez pas de note pour ce plat.", ephemeral=True)

# --- /aide ---
@tree.command(name="aide", description="Affiche la liste des commandes")
async def aide(interaction: discord.Interaction):
    description = (
        "**/note** - Noter un plat à deux (affiche moyenne)\n"
        "**/notesperso** - Afficher vos notes données\n"
        "**/supprnote** - Supprimer votre note d'un plat\n"
        "**/films** - Afficher la liste des films\n"
        "**/ajoutfilm** - Ajouter un film\n"
        "**/supprfilm** - Supprimer un film\n"
        "**/jeux** - Afficher la liste des jeux\n"
        "**/ajoutjeu** - Ajouter un jeu\n"
        "**/classement** - Afficher classement des plats par moyenne\n"
        "**/rappel** - Créer un rappel dans le salon\n"
        "**/embedcreer** - Créer un embed personnalisable\n"
        "**/embedmodifier** - Modifier un embed existant\n"
        "**/comptearebours** - Démarrer un compte à rebours\n"
    )
    embed = create_embed("Aide - Commandes disponibles", description)
    await interaction.response.send_message(embed=embed)

# --- /films ---
@tree.command(name="films", description="Afficher la liste des films")
async def films(interaction: discord.Interaction):
    if not data["films"]:
        await interaction.response.send_message("La liste des films est vide.")
        return
    desc = "\n".join(f"- {film}" for film in data["films"])
    embed = create_embed("Liste des films", desc)
    await interaction.response.send_message(embed=embed)

# --- /ajoutfilm ---
@tree.command(name="ajoutfilm", description="Ajouter un film à la liste")
@app_commands.describe(film="Nom du film à ajouter")
async def ajoutfilm(interaction: discord.Interaction, film: str):
    if film in data["films"]:
        await interaction.response.send_message("Ce film est déjà dans la liste.", ephemeral=True)
        return
    data["films"].append(film)
    save_data()
    embed = create_embed("Film ajouté", f"Le film **{film}** a été ajouté à la liste.")
    await interaction.response.send_message(embed=embed)

# --- /supprfilm ---
@tree.command(name="supprfilm", description="Supprimer un film de la liste")
@app_commands.describe(film="Nom du film à supprimer")
async def supprfilm(interaction: discord.Interaction, film: str):
    if film not in data["films"]:
        await interaction.response.send_message("Ce film n'est pas dans la liste.", ephemeral=True)
        return
    data["films"].remove(film)
    save_data()
    embed = create_embed("Film supprimé", f"Le film **{film}** a été supprimé de la liste.")
    await interaction.response.send_message(embed=embed)

# --- /jeux ---
@tree.command(name="jeux", description="Afficher la liste des jeux")
async def jeux(interaction: discord.Interaction):
    if not data["jeux"]:
        await interaction.response.send_message("La liste des jeux est vide.")
        return
    desc = "\n".join(f"- {jeu}" for jeu in data["jeux"])
    embed = create_embed("Liste des jeux", desc)
    await interaction.response.send_message(embed=embed)

# --- /ajoutjeu ---
@tree.command(name="ajoutjeu", description="Ajouter un jeu à la liste")
@app_commands.describe(jeu="Nom du jeu à ajouter")
async def ajoutjeu(interaction: discord.Interaction, jeu: str):
    if jeu in data["jeux"]:
        await interaction.response.send_message("Ce jeu est déjà dans la liste.", ephemeral=True)
        return
    data["jeux"].append(jeu)
    save_data()
    embed = create_embed("Jeu ajouté", f"Le jeu **{jeu}** a été ajouté à la liste.")
    await interaction.response.send_message(embed=embed)

# --- /classement ---
@tree.command(name="classement", description="Classement des plats par moyenne")
async def classement(interaction: discord.Interaction):
    if not data["notes"]:
        await interaction.response.send_message("Aucune note disponible pour le classement.")
        return

    # Calcul moyenne par plat
    classement_list = []
    for plat, notes in data["notes"].items():
        n1 = notes.get("note1", {}).get("note")
        n2 = notes.get("note2", {}).get("note")
        if n1 is not None and n2 is not None:
            moyenne = (n1 + n2) / 2
            classement_list.append((plat, moyenne))

    if not classement_list:
        await interaction.response.send_message("Aucune note complète pour classement.")
        return

    classement_list.sort(key=lambda x: x[1], reverse=True)
    desc = "\n".join(f"**{plat}** : {moyenne:.2f}" for plat, moyenne in classement_list)
    embed = create_embed("Classement des plats", desc)
    await interaction.response.send_message(embed=embed)

# --- /rappel ---
@tree.command(name="rappel", description="Créer un rappel dans le salon")
@app_commands.describe(message="Message du rappel")
async def rappel(interaction: discord.Interaction, message: str):
    embed = create_embed("Rappel", f"{interaction.user.mention} a créé un rappel:\n\n{message}")
    await interaction.response.send_message(embed=embed)

# --- /embedcreer & /embedmodifier ---

# Pour simplifier et garder fonctionnel sur Render, on fera ici une version basique (à améliorer ensuite).

@tree.command(name="embedcreer", description="Créer un embed personnalisable")
@app_commands.describe(titre="Titre de l'embed", contenu="Contenu texte", couleur="Couleur hex (ex: #8B4513)", footer="Footer (optionnel)", image="URL d'image (optionnel)")
async def embedcreer(interaction: discord.Interaction, titre: str, contenu: str, couleur: str = "#8B4513", footer: str = None, image: str = None):
    try:
        color_int = int(couleur.strip("#"), 16)
    except:
        color_int = 0x8B4513
    embed = create_embed(titre, contenu, color_int, footer, image)
    await interaction.response.send_message(embed=embed)

@tree.command(name="embedmodifier", description="Modifier un embed existant")
@app_commands.describe(channel="Salon du message", message_id="ID du message", titre="Nouveau titre", contenu="Nouveau contenu", couleur="Couleur hex (ex: #8B4513)", footer="Footer (optionnel)", image="URL d'image (optionnel)")
async def embedmodifier(interaction: discord.Interaction, channel: discord.TextChannel, message_id: int, titre: str, contenu: str, couleur: str = "#8B4513", footer: str = None, image: str = None):
    try:
        color_int = int(couleur.strip("#"), 16)
    except:
        color_int = 0x8B4513
    try:
        msg = await channel.fetch_message(message_id)
    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de la récupération du message: {e}", ephemeral=True)
        return
    embed = create_embed(titre, contenu, color_int, footer, image)
    try:
        await msg.edit(embed=embed)
        await interaction.response.send_message("Embed modifié avec succès.")
    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de la modification: {e}", ephemeral=True)

# --- /comptearebours ---
@tree.command(name="comptearebours", description="Démarrer un compte à rebours")
@app_commands.describe(secondes="Nombre de secondes")
async def comptearebours(interaction: discord.Interaction, secondes: int):
    if secondes <= 0:
        await interaction.response.send_message("Le nombre de secondes doit être positif.", ephemeral=True)
        return
    msg = await interaction.response.send_message(embed=create_embed("Compte à rebours", f"Temps restant : {secondes} secondes"), ephemeral=False)

    message = await interaction.original_response()

    for sec in range(secondes, 0, -1):
        await asyncio.sleep(1)
        embed = create_embed("Compte à rebours", f"Temps restant : {sec-1} secondes", footer_text=f"Demandé par {interaction.user.display_name}")
        try:
            await message.edit(embed=embed)
        except:
            break  # En cas d'erreur d'édition on arrête

    # Fin du compte à rebours
    try:
        await message.edit(embed=create_embed("Compte à rebours", "Temps écoulé !", footer_text=f"Demandé par {interaction.user.display_name}"))
    except:
        pass

# --- RUN BOT ---
bot.run(os.getenv("TOKEN"))
