import discord
from discord.ext import commands
from discord import ui, Interaction, ButtonStyle
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

jeux = {}
notes = {}  # {plat: {"utilisateur": note, "auteur": note}}
classement = []
films = []
countdown_task = None
countdown_msg = None

# --- COMMANDES DE BASE ---

@bot.command()
async def ajoutjeu(ctx, nom: str, *, description: str):
    jeux[nom] = description
    await ctx.send(f"Jeu '{nom}' ajouté.")

@bot.command()
async def supprjeu(ctx, nom: str):
    if nom in jeux:
        del jeux[nom]
        await ctx.send(f"Jeu '{nom}' supprimé.")
    else:
        await ctx.send(f"Jeu '{nom}' non trouvé.")

@bot.command()
async def listejeux(ctx):
    if not jeux:
        await ctx.send("Aucun jeu enregistré.")
        return
    embed = discord.Embed(title="🎮 Liste des jeux")
    for nom, desc in jeux.items():
        embed.add_field(name=nom, value=desc, inline=False)
    await ctx.send(embed=embed)

# --- COMPTE A REBOURS ---

@bot.group(invoke_without_command=True)
async def comptearebours(ctx, duree: int):
    global countdown_task, countdown_msg

    if countdown_task and not countdown_task.done():
        await ctx.send("Un compte à rebours est déjà en cours.")
        return

    countdown_msg = await ctx.send(f"⏱️ Compte à rebours démarré : {duree} secondes")

    async def countdown():
        global countdown_msg
        remaining = duree
        while remaining > 0:
            await countdown_msg.edit(content=f"Temps restant : {remaining} secondes")
            await asyncio.sleep(1)
            remaining -= 1
        await countdown_msg.edit(content="⌛ Temps écoulé !")

    countdown_task = asyncio.create_task(countdown())

@comptearebours.command()
async def stop(ctx):
    global countdown_task, countdown_msg
    if countdown_task and not countdown_task.done():
        countdown_task.cancel()
        countdown_task = None
        if countdown_msg:
            await countdown_msg.edit(content="❌ Compte à rebours annulé.")
        await ctx.send("Compte à rebours arrêté.")
    else:
        await ctx.send("Aucun compte à rebours en cours.")

# --- NOTE ---

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

    emoji_note = "🧀"
    emoji_moyenne = "🍷"

    user_data = {
        "user_id": user_id,
        "username": username,
        "note": note
    }

    if message_reference:
        embed = message_reference.embeds[0]
        fields = embed.fields
        updated = False
        other_note = None
        other_user = None

        for i, field in enumerate(fields):
            if field.name == username:
                embed.set_field_at(i, name=username, value=f"{note}/10", inline=False)
                updated = True
            else:
                other_user = field.name
                other_note = float(field.value.replace("/10", ""))

        if not updated:
            embed.add_field(name=username, value=f"{note}/10", inline=False)

        # Calculer la moyenne si deux notes
        notes = [note]
        if other_note is not None:
            notes.append(other_note)
        moyenne = round(sum(notes) / len(notes), 2)

        embed.description = (
            f"{emoji_note} **Nom du plat** : {plat}\n"
            f"**{other_user if other_user != username else username}** : {other_note if other_user != username else note}/10\n"
            f"**{username if username != other_user else other_user}** : {note if username != other_user else other_note}/10\n"
            f"{emoji_moyenne} **Moyenne** : {moyenne}/10"
        )
        await message_reference.edit(embed=embed)
        await interaction.followup.send("Ta note a été mise à jour dans l'embed existant.", ephemeral=True)

    else:
        embed = discord.Embed(
            title=f"🍽️ Dégustation : {plat}",
            description=(
                f"{emoji_note} **Nom du plat** : {plat}\n"
                f"**{username}** : {note}/10\n"
                f"{emoji_moyenne} **Moyenne** : {note}/10"
            ),
            color=discord.Color.blurple()
        )
        embed.add_field(name=username, value=f"{note}/10", inline=False)
        await channel.send(embed=embed)
        await interaction.followup.send("Ton évaluation a été publiée dans un nouvel embed.", ephemeral=True)

# --- CLASSEMENT ---

@bot.group(invoke_without_command=True)
async def classement(ctx):
    await ctx.send("Usage : /classement show")

@classement.command()
async def show(ctx):
    if not classement:
        await ctx.send("Aucun classement disponible.")
        return
    embed = discord.Embed(title="🏆 Classement")
    for i, (pseudo, score) in enumerate(sorted(classement, key=lambda x: x[1], reverse=True), start=1):
        embed.add_field(name=f"{i}. {pseudo}", value=f"Score: {score}", inline=False)
    await ctx.send(embed=embed)

# --- FILMS ---

@bot.group(invoke_without_command=True)
async def films(ctx):
    await ctx.send("Usage : /films add <titre> <genre> | /films list")

@films.command()
async def add(ctx, titre: str, genre: str):
    films.append({'titre': titre, 'genre': genre})
    await ctx.send(f"Film '{titre}' ajouté dans le genre '{genre}'.")

@films.command()
async def list(ctx):
    if not films:
        await ctx.send("Aucun film enregistré.")
        return
    embed = discord.Embed(title="🎬 Liste des films")
    for f in films:
        embed.add_field(name=f['titre'], value=f"Genre: {f['genre']}", inline=False)
    await ctx.send(embed=embed)

# --- AIDE ---

@bot.command()
async def aide(ctx):
    embed = discord.Embed(title="✨ Aide - Commandes disponibles", color=discord.Color.blue())
    embed.add_field(name="/ajoutjeu <nom> <description>", value="Ajoute un jeu", inline=False)
    embed.add_field(name="/supprjeu <nom>", value="Supprime un jeu", inline=False)
    embed.add_field(name="/listejeux", value="Liste les jeux", inline=False)
    embed.add_field(name="/comptearebours <duree>", value="Démarre un compte à rebours (secondes)", inline=False)
    embed.add_field(name="/comptearebours stop", value="Arrête le compte à rebours", inline=False)
    embed.add_field(name="/note add <plat> <note>", value="Ajoute une note pour un plat", inline=False)
    embed.add_field(name="/note list", value="Liste toutes les notes", inline=False)
    embed.add_field(name="/classement show", value="Affiche le classement", inline=False)
    embed.add_field(name="/films add <titre> <genre>", value="Ajoute un film", inline=False)
    embed.add_field(name="/films list", value="Liste les films", inline=False)
    embed.add_field(name="/embededit", value="Créer/modifier un embed interactif", inline=False)
    await ctx.send(embed=embed)

# --- EMBED INTERACTIF ---

class EmbedEditor(ui.View):
    def __init__(self, embed=None):
        super().__init__(timeout=300)
        self.embed = embed or discord.Embed(title="Titre", description="Description")
        self.message = None

    @ui.button(label="Modifier Titre", style=ButtonStyle.primary)
    async def edit_title(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Envoie le nouveau titre :", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
            self.embed.title = msg.content
            await self.message.edit(embed=self.embed, view=self)
            await interaction.followup.send("Titre modifié !", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé.", ephemeral=True)

    @ui.button(label="Modifier Description", style=ButtonStyle.primary)
    async def edit_description(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Envoie la nouvelle description :", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await bot.wait_for('message', check=check, timeout=120)
            self.embed.description = msg.content
            await self.message.edit(embed=self.embed, view=self)
            await interaction.followup.send("Description modifiée !", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé.", ephemeral=True)

    @ui.button(label="Ajouter Image/GIF", style=ButtonStyle.success)
    async def add_image(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Envoie le lien de l'image ou gif :", ephemeral=True)
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await bot.wait_for('message', check=check, timeout=120)
            url = msg.content
            if url.startswith("http://") or url.startswith("https://"):
                self.embed.set_image(url=url)
                await self.message.edit(embed=self.embed, view=self)
                await interaction.followup.send("Image ajoutée à l'embed !", ephemeral=True)
            else:
                await interaction.followup.send("URL invalide.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé.", ephemeral=True)

    @ui.button(label="Envoyer Embed", style=ButtonStyle.green)
    async def send_embed(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Embed envoyé !", ephemeral=True)
        await interaction.channel.send(embed=self.embed)
        self.stop()

    @ui.button(label="Annuler", style=ButtonStyle.red)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Modification annulée.", ephemeral=True)
        self.stop()

@bot.command()
async def embededit(ctx):
    view = EmbedEditor()
    message = await ctx.send(embed=view.embed, view=view)
    view.message = message

bot.run("TON_TOKEN_ICI")
