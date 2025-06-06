import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import os
from dotenv import load_dotenv

# ───────────── CONFIG DE BASE ─────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1376941684147097660

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ───────────── DONNÉES PRODUITS ─────────────
PRODUCTS = [
    {
        "id": 1,
        "nom": "T-Shirt Nike x Stussy",
        "categorie": "T-shirt",
        "prix": 24.99,
        "stock": 12,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379958450649305129/Pack_Volts.png"
    },
    {
        "id": 2,
        "nom": "Maillot de foot Real Madrid 2024",
        "categorie": "Maillot",
        "prix": 29.99,
        "stock": 7,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379939202346520730/500V.png"
    },
    {
        "id": 3,
        "nom": "T-Shirt La Planque",
        "categorie": "T-shirt",
        "prix": 19.99,
        "stock": 15,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379941340795764817/1300V.png"
    }
]

user_carts = {}  # user_id : [product_ids]

# ───────────── UI SHOP ─────────────
class ProductButton(Button):
    def __init__(self, product):
        super().__init__(
            label=f"🛒 Ajouter — {product['nom']}",
            style=discord.ButtonStyle.primary,
            custom_id=f"add_{product['id']}"
        )
        self.product = product

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user_carts.setdefault(user_id, []).append(self.product["id"])
        await interaction.response.send_message(f"✅ **{self.product['nom']}** ajouté à ton panier.", ephemeral=True)

class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for product in PRODUCTS:
            self.add_item(ProductButton(product))

# ───────────── COMMANDES ─────────────
@bot.event
async def on_ready():
    synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Bot connecté : {bot.user} — {len(synced)} commandes synchronisées.")

@bot.tree.command(name="achat", description="Ouvre la boutique complète", guild=discord.Object(id=GUILD_ID))
async def achat_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    
    for product in PRODUCTS:
        embed = discord.Embed(
            title=product["nom"],
            description=f"**Catégorie :** {product['categorie']}\n**Prix :** {product['prix']}€\n**Stock :** {product['stock']}",
            color=0x2ecc71
        )
        embed.set_image(url=product["image_url"])
        embed.set_footer(text="Commande avec /checkout à tout moment.")
        await interaction.followup.send(embed=embed, view=ShopView())

# ───────────── LANCEMENT ─────────────
bot.run(TOKEN)
