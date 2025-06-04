import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import os
import random
from dotenv import load_dotenv

# ───────────── CONFIGURATION DE BASE ─────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1376941684147097660

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

ANNOUNCE_CHANNEL = "achats-publics"

CATEGORIES = {
    "T-Shirts": [
        {
            "nom": "Stussy x Nike J-C - M",
            "prix_euro": 14,
            "prix_volts": 140,
            "stock": 12,
            "image": "https://www.picclickimg.com/5AMAAOSwHYJoONWU/maillot-du-br%C3%A9sil-concept-jesus-nike-saison-24-25.webp",
            "desc": "Taille M, édition limitée. 👕",
            "rarete": "common"
        },
        {
            "nom": "Supreme x CDG - S",
            "prix_euro": 25,
            "prix_volts": 250,
            "stock": 1,
            "image": "https://example.com/tshirt3.jpg",
            "desc": "Rare, taille S.",
            "rarete": "rare"
        }
    ],
    "Sneakers": [
        {
            "nom": "Air Max 90 White",
            "prix_euro": 130,
            "prix_volts": 1300,
            "stock": 3,
            "image": "https://example.com/am90.jpg",
            "desc": "Edition 2024.",
            "rarete": "common"
        }
    ]
}
CATEGORY_LIST = list(CATEGORIES.keys())

user_volts = {}
user_badges = {}
user_sales = {}
user_loots = {}

RANKS = [
    ("Explorateur", 0, "🧭", 0x888888),
    ("Businessman", 1000, "💼", 0xdb143c),
    ("Légende", 5000, "👑", 0xffd700),
    ("Mythique", 20000, "💎", 0x00ffff)
]

def get_user_rank(user_id):
    volts = user_volts.get(user_id, 0)
    rank_name, emoji, color = RANKS[0][0], RANKS[0][2], RANKS[0][3]
    for name, threshold, emj, col in RANKS:
        if volts >= threshold:
            rank_name, emoji, color = name, emj, col
    return rank_name, emoji, color

def format_volts(volts): return f"{volts} ⚡"

def make_embed(title, description, color):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="La Planque • Sentinelle")
    return embed

def product_embed(prod, user=None):
    color_map = {"common": 0x00ff00, "rare": 0xdb143c, "legendary": 0xffd700}
    color = color_map.get(prod.get("rarete", "common"), 0x00ff00)
    solde = f"\n\n**Ton solde Volts : `{format_volts(user_volts.get(user.id, 0))}`**" if user else ""
    embed = discord.Embed(
        title=prod["nom"],
        description=f"{prod['desc']}\n\n**Prix :** {prod['prix_euro']}€ / {prod['prix_volts']}⚡\n**Stock :** {prod['stock']}{solde}",
        color=color
    )
    embed.set_image(url=prod["image"])
    return embed

# ───────────── BOT SETUP ─────────────
class Sentinelle(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synchronisées.")

bot = Sentinelle()

@bot.event
async def on_ready():
    print(f"✅ Sentinelle connectée en tant que {bot.user}")

# ───────────── VUES DYNAMIQUES ─────────────
class ProductView(View):
    def __init__(self, category, page, user):
        super().__init__(timeout=180)
        self.category, self.page, self.user = category, page, user
        self.update_buttons()
    def update_buttons(self):
        self.clear_items()
        produits = CATEGORIES[self.category]
        start = self.page * 4
        for prod in produits[start:start+4]:
            self.add_item(ProductButton(prod, self.user, self.category))
        if self.page > 0:
            self.add_item(PageButton("⬅️", self.category, self.page - 1, self.user))
        if (self.page + 1) * 4 < len(produits):
            self.add_item(PageButton("➡️", self.category, self.page + 1, self.user))

class PageButton(Button):
    def __init__(self, emoji, category, page, user):
        super().__init__(style=discord.ButtonStyle.secondary, label=emoji)
        self.category, self.page, self.user = category, page, user
    async def callback(self, interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        view = ProductView(self.category, self.page, self.user)
        embed = make_embed(f"Catégorie : {self.category} (Page {self.page + 1})", "Sélectionne un produit ci-dessous :", 0x222222)
        await interaction.response.edit_message(embed=embed, view=view, content=None)

class ProductButton(Button):
    def __init__(self, prod, user, category):
        super().__init__(style=discord.ButtonStyle.primary, label=prod["nom"][:80])
        self.produit, self.user, self.category = prod, user, category
    async def callback(self, interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        embed = product_embed(self.produit, user=interaction.user)
        view = ProductDetailView(self.produit, self.user, self.category)
        await interaction.response.edit_message(embed=embed, view=view, content=None)

class ProductDetailView(View):
    def __init__(self, produit, user, category):
        super().__init__(timeout=120)
        self.produit, self.user, self.category = produit, user, category
        self.add_item(CommandButton(produit, user, category))
        self.add_item(Button(label="⬅️ Retour", style=discord.ButtonStyle.secondary, custom_id="retour"))
    @discord.ui.button(label="⬅️ Retour", style=discord.ButtonStyle.secondary, row=1)
    async def retour(self, interaction, button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        view = ProductView(self.category, 0, self.user)
        embed = make_embed(f"Catégorie : {self.category} (Page 1)", "Sélectionne un produit ci-dessous :", 0x222222)
        await interaction.response.edit_message(embed=embed, view=view, content=None)

class CommandButton(Button):
    def __init__(self, produit, user, category):
        super().__init__(style=discord.ButtonStyle.success, label="🛒 Commander")
        self.produit, self.user, self.category = produit, user, category
    async def callback(self, interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        if self.produit["stock"] < 1:
            return await interaction.response.send_message("❌ Rupture de stock !", ephemeral=True)
        if user_volts.get(self.user.id, 0) < self.produit["prix_volts"]:
            return await interaction.response.send_message(
                "⚡ Tu n'as pas assez de Volts pour acheter ce produit.\nUtilise `/buyvolts` pour recharger.", ephemeral=True
            )
        # Paiement
        user_volts[self.user.id] -= self.produit["prix_volts"]
        self.produit["stock"] -= 1
        user_sales[self.user.id] = user_sales.get(self.user.id, 0) + 1
        await announce_purchase(interaction.guild, self.user, self.produit)
        await interaction.response.send_message(
            f"✅ Commande **{self.produit['nom']}** validée !\nNouveau solde : {format_volts(user_volts[self.user.id])}",
            ephemeral=True
        )

async def announce_purchase(guild, user, produit):
    for chan in guild.text_channels:
        if chan.name == ANNOUNCE_CHANNEL:
            embed = discord.Embed(
                title="Nouvelle commande !",
                description=f"**{user.mention}** a commandé **{produit['nom']}**\nPrix : {produit['prix_volts']}⚡",
                color=0xdb143c
            )
            embed.set_image(url=produit["image"])
            await chan.send(embed=embed)
            break

# ───────────── COMMANDE BUYVOLTS ULTRA UX ─────────────

VOLT_PACKS = [
    {
        "volts": 1000,
        "prix": 8.99,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379938998880964720/100V.png",
        "desc": "Idéal pour tester la puissance ⚡"
    },
    {
        "volts": 2800,
        "prix": 22.99,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379939121375609023/280V.png",
        "desc": "Prix mini par Volt, boost rapide"
    },
    {
        "volts": 5000,
        "prix": 36.99,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379939202346520730/500V.png",
        "desc": "Gros pack pour gros joueurs 💎"
    },
    {
        "volts": 13500,
        "prix": 89.99,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379941340795764817/1300V.png",
        "desc": "La vraie puissance. Tu deviens une Légende."
    }
]

class BuyVoltsView(View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user
        for pack in VOLT_PACKS:
            btn = BuyVoltsButton(pack, user)
            self.add_item(btn)

class BuyVoltsButton(Button):
    def __init__(self, pack, user):
        super().__init__(
            label=f"{pack['volts']}⚡ — {pack['prix']}€",
            style=discord.ButtonStyle.success,
            custom_id=f"buyvolts_{pack['volts']}",
            row=0
        )
        self.pack = pack
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="tickets")  # Catégorie à créer
        if not category:
            category = await guild.create_category("tickets")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-achat-{self.user.display_name}".replace(" ", "-"),
            overwrites=overwrites,
            category=category
        )
        embed = discord.Embed(
            title="💸 Achat de Volts — Confirmation",
            description=(
                f"**{self.user.mention} souhaite acheter**\n\n"
                f"**{self.pack['volts']} Volts** pour **{self.pack['prix']}€**\n"
                f"{self.pack['desc']}\n\n"
                "Pour finaliser l’achat, il faut posséder un compte **PayPal (paiement en ami)** "
                "ou **Revolut (virement entre amis)**.\n"
                "Dès que le paiement est validé, tes Volts sont crédités !\n\n"
                "👉 **Envoie ta preuve de paiement ici.**\n"
                "*Un admin prendra le relais rapidement.*"
            ),
            color=0xdb143c
        )
        embed.set_image(url=self.pack["image_url"])
        embed.set_footer(text="La Planque • Sentinelle")
        await ticket_channel.send(
            content=f"{self.user.mention} Ticket ouvert pour achat de Volts.",
            embed=embed
        )
        await interaction.response.send_message(
            f"✅ Ticket d’achat ouvert ici : {ticket_channel.mention}\nMerci de suivre les instructions dans le salon !",
            ephemeral=True
        )

@bot.tree.command(name="buyvolts", description="Acheter des Volts (paiement PayPal/Revolut)")
async def buyvolts_slash(interaction: discord.Interaction):
    # Un embed par pack, chacun avec image et bouton en dessous
    embeds = []
    for pack in VOLT_PACKS:
        embed = discord.Embed(
            title=f"{pack['volts']} Volts — {pack['prix']}€",
            description=pack["desc"] + "\n\nPaiement **PayPal (entre amis)** ou **Revolut** accepté.",
            color=0x00ffff
        )
        embed.set_image(url=pack["image_url"])
        embed.set_footer(text="Clique sur le bouton ci-dessous pour ouvrir un ticket d'achat.")
        embeds.append(embed)
    view = BuyVoltsView(interaction.user)
    await interaction.response.send_message(embeds=embeds, view=view, ephemeral=True)

# ───────────── COMMANDES UTILISATEURS ─────────────
@bot.tree.command(name="shop", description="Ouvre la boutique interactive")
async def shop_slash(interaction: discord.Interaction):
    select = Select(
        placeholder="Choisis une catégorie",
        options=[discord.SelectOption(label=cat) for cat in CATEGORY_LIST]
    )
    async def select_callback(select_interaction):
        cat = select.values[0]
        view = ProductView(cat, 0, interaction.user)
        embed = make_embed(f"Catégorie : {cat} (Page 1)", "Sélectionne un produit ci-dessous :", 0x222222)
        await select_interaction.response.edit_message(embed=embed, view=view, content=None)
    select.callback = select_callback
    view = View()
    view.add_item(select)
    solde = user_volts.get(interaction.user.id, 0)
    await interaction.response.send_message(
        embed=make_embed(
            "Bienvenue dans la boutique !",
            f"Sélectionne une catégorie pour commencer.\n\n**Ton solde : `{format_volts(solde)}`**", 0x222222),
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="volts", description="Affiche ton solde de Volts")
async def volts_slash(interaction: discord.Interaction):
    volts = user_volts.get(interaction.user.id, 0)
    await interaction.response.send_message(
        f"**Solde Volts : `{format_volts(volts)}`\nUtilise `/shop` ou `/buyvolts` pour acheter.", ephemeral=True
    )

@bot.tree.command(name="profil", description="Affiche ton profil Sentinelle")
async def profil_slash(interaction: discord.Interaction):
    uid = interaction.user.id
    rank, emoji, color = get_user_rank(uid)
    volts = user_volts.get(uid, 0)
    sales = user_sales.get(uid, 0)
    badges = ", ".join(user_badges.get(uid, [])) or "Aucun"
    embed = discord.Embed(
        title=f"{emoji} Profil de {interaction.user.display_name}",
        color=color
    )
    embed.add_field(name="Rang", value=rank, inline=True)
    embed.add_field(name="Volts", value=f"{volts} ⚡", inline=True)
    embed.add_field(name="Ventes réalisées", value=sales, inline=True)
    embed.add_field(name="Badges", value=badges, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ───────────── COMMANDES ADMIN (gestion Volts) ─────────────
@bot.tree.command(name="givevolts", description="(Admin) Donne des Volts à un membre")
@app_commands.checks.has_permissions(administrator=True)
async def givevolts_slash(interaction: discord.Interaction, membre: discord.Member, amount: int):
    if amount <= 0: return await interaction.response.send_message("Montant invalide.", ephemeral=True)
    user_volts[membre.id] = user_volts.get(membre.id, 0) + amount
    await interaction.response.send_message(f"{amount} Volts ajoutés à **{membre.display_name}** ({format_volts(user_volts[membre.id])})", ephemeral=True)

@bot.tree.command(name="removevolts", description="(Admin) Retire des Volts à un membre")
@app_commands.checks.has_permissions(administrator=True)
async def removevolts_slash(interaction: discord.Interaction, membre: discord.Member, amount: int):
    if amount <= 0: return await interaction.response.send_message("Montant invalide.", ephemeral=True)
    user_volts[membre.id] = max(0, user_volts.get(membre.id, 0) - amount)
    await interaction.response.send_message(f"{amount} Volts retirés à **{membre.display_name}** ({format_volts(user_volts[membre.id])})", ephemeral=True)

@bot.tree.command(name="setvolts", description="(Admin) Définit le solde Volts d’un membre")
@app_commands.checks.has_permissions(administrator=True)
async def setvolts_slash(interaction: discord.Interaction, membre: discord.Member, amount: int):
    if amount < 0: return await interaction.response.send_message("Montant invalide.", ephemeral=True)
    user_volts[membre.id] = amount
    await interaction.response.send_message(f"Solde Volts de **{membre.display_name}** mis à **{format_volts(amount)}**", ephemeral=True)

# ───────────── LANCEMENT DU BOT ─────────────
bot.run(TOKEN)
