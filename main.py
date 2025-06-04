import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import os
import random
from dotenv import load_dotenv
# MAJ du bot par Eliot - 04/06

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

GUILD_ID = 1376941684147097660  # Mets ton Guild ID ici !

# --- Exemples de produits, catégories (à remplacer par les données Google Sheets plus tard) ---
CATEGORIES = {
    "T-Shirts": [
        {
            "nom": "Stussy x Nike J-C - M",
            "prix": 14,
            "stock": 12,
            "image": "https://www.picclickimg.com/5AMAAOSwHYJoONWU/maillot-du-br%C3%A9sil-concept-jesus-nike-saison-24-25.webp",
            "desc": "Taille M, édition limitée. 👕",
        },
        {
            "nom": "Stussy x Nike - L",
            "prix": 14,
            "stock": 5,
            "image": "https://example.com/tshirt2.jpg",
            "desc": "Taille L, modèle oversize.",
        },
        {
            "nom": "Supreme x CDG - S",
            "prix": 25,
            "stock": 1,
            "image": "https://example.com/tshirt3.jpg",
            "desc": "Rare, taille S.",
        },
        {
            "nom": "Nike Dunk Low - Noir",
            "prix": 90,
            "stock": 2,
            "image": "https://example.com/dunk1.jpg",
            "desc": "Sneaker premium.",
        }
    ],
    "Sneakers": [
        {
            "nom": "Air Max 90 White",
            "prix": 130,
            "stock": 3,
            "image": "https://example.com/am90.jpg",
            "desc": "Edition 2024.",
        },
        {
            "nom": "Jordan 4 Retro",
            "prix": 250,
            "stock": 1,
            "image": "https://example.com/jordan4.jpg",
            "desc": "Deadstock, taille 42.",
        }
    ]
}
CATEGORY_LIST = list(CATEGORIES.keys())

# --- Simule une base de points utilisateurs (à migrer sur Sheets plus tard) ---
user_points = {}

# --- Bot Setup ---
class Sentinelle(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",  # peu utilisé avec les slashs
            intents=intents,
            application_id=None
        )

    async def setup_hook(self):
        # Synchro slash commands
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        print("Slash commands synchronisées.")

bot = Sentinelle()

@bot.event
async def on_ready():
    print(f"{bot.user} est prêt et connecté à Discord.")

# --- Canal pour notifications d'achat ---
ANNOUNCE_CHANNEL = "achats-publics"  # à créer sur ton serveur

# --- Vues dynamiques (boutique paginée) ---
class ProductView(View):
    def __init__(self, category, page, user):
        super().__init__(timeout=180)
        self.category = category
        self.page = page
        self.user = user
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        produits = CATEGORIES[self.category]
        start = self.page * 4
        for i, produit in enumerate(produits[start:start+4]):
            self.add_item(ProductButton(label=produit["nom"], produit=produit, user=self.user, category=self.category))
        # Pagination
        if self.page > 0:
            self.add_item(PageButton("⬅️", self.category, self.page - 1, self.user))
        if (self.page + 1) * 4 < len(CATEGORIES[self.category]):
            self.add_item(PageButton("➡️", self.category, self.page + 1, self.user))

class PageButton(Button):
    def __init__(self, emoji, category, page, user):
        super().__init__(style=discord.ButtonStyle.secondary, label=emoji)
        self.category = category
        self.page = page
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("Ce menu ne t'appartient pas.", ephemeral=True)
            return
        view = ProductView(self.category, self.page, self.user)
        await interaction.response.edit_message(view=view, content=f"Catégorie **{self.category}** (Page {self.page+1})")

class ProductButton(Button):
    def __init__(self, label, produit, user, category):
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.produit = produit
        self.user = user
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("Ce menu ne t'appartient pas.", ephemeral=True)
            return
        embed = discord.Embed(
            title=self.produit["nom"],
            description=f"{self.produit['desc']}\nPrix : **{self.produit['prix']}€**\nStock : **{self.produit['stock']}**",
            color=0xdb143c if self.produit["stock"] <= 2 else 0x00ff00
        )
        embed.set_image(url=self.produit["image"])
        view = ProductDetailView(self.produit, self.user, self.category)
        await interaction.response.edit_message(embed=embed, view=view, content="")

class ProductDetailView(View):
    def __init__(self, produit, user, category):
        super().__init__(timeout=120)
        self.produit = produit
        self.user = user
        self.category = category
        self.add_item(CommandButton(produit, user, category))
        self.add_item(Button(label="⬅️ Retour", style=discord.ButtonStyle.secondary, custom_id="retour"))

    @discord.ui.button(label="⬅️ Retour", style=discord.ButtonStyle.secondary, row=1)
    async def retour(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("Ce menu ne t'appartient pas.", ephemeral=True)
            return
        view = ProductView(self.category, 0, self.user)
        await interaction.response.edit_message(embed=None, view=view, content=f"Catégorie **{self.category}** (Page 1)")

class CommandButton(Button):
    def __init__(self, produit, user, category):
        super().__init__(style=discord.ButtonStyle.success, label="🛒 Commander")
        self.produit = produit
        self.user = user
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("Ce menu ne t'appartient pas.", ephemeral=True)
            return
        # Stock check
        if self.produit["stock"] < 1:
            await interaction.response.send_message("Rupture de stock !", ephemeral=True)
            return
        self.produit["stock"] -= 1
        # Points : 10 par commande
        user_points[self.user.id] = user_points.get(self.user.id, 0) + 10
        # Annonce achat (dans le canal public)
        await announce_achat(interaction.guild, self.user, self.produit)
        await interaction.response.send_message(
            f"✅ Ta commande pour **{self.produit['nom']}** est validée !\nTu gagnes 10 points fidélité (total : {user_points[self.user.id]} pts)",
            ephemeral=True
        )

# --- Fonction d'annonce achat ---
async def announce_achat(guild, user, produit):
    for channel in guild.text_channels:
        if channel.name == ANNOUNCE_CHANNEL:
            embed = discord.Embed(
                title="Nouvelle commande !",
                description=f"**{user.mention}** vient de commander : **{produit['nom']}** !\nPrix : {produit['prix']}€",
                color=0xdb143c
            )
            embed.set_image(url=produit["image"])
            await channel.send(embed=embed)
            break

# --- Commandes ---

@bot.tree.command(name="shop", description="Ouvre la boutique interactive")
async def shop_slash(interaction: discord.Interaction):
    select = Select(
        placeholder="Choisis une catégorie",
        options=[discord.SelectOption(label=cat) for cat in CATEGORY_LIST]
    )

    async def select_callback(select_interaction):
        cat = select.values[0]
        view = ProductView(cat, 0, interaction.user)
        await select_interaction.response.edit_message(content=f"Catégorie **{cat}** (Page 1)", view=view, embed=None)

    select.callback = select_callback

    view = View()
    view.add_item(select)
    await interaction.response.send_message(
        "Bienvenue dans la boutique ! Sélectionne une catégorie pour commencer.",
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="points", description="Consulte tes points fidélité")
async def points_slash(interaction: discord.Interaction):
    points = user_points.get(interaction.user.id, 0)
    await interaction.response.send_message(
        f"Tu as **{points}** points fidélité. Commande et interagis pour gagner plus !",
        ephemeral=True
    )

@bot.event
async def on_ready():
    print(f"✅ Sentinelle connectée en tant que {bot.user}")

bot.run(TOKEN)
