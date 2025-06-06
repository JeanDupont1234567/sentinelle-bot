import discord
from discord.ext import commands
from discord.ui import View, Button
import os

# -------- CONFIG --------
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1376941684147097660

CATEGORIES = {
    "T-shirts": [
        {
            "nom": "Nike x Stussy Concept",
            "prix": 34.99,
            "stock": 8,
            "image": "https://exemple.com/nike_stussy.png"
        },
        {
            "nom": "Maillot PSG 23/24",
            "prix": 59.99,
            "stock": 2,
            "image": "https://exemple.com/psg2324.png"
        },
        {
            "nom": "Maillot Vintage Italie 90",
            "prix": 39.99,
            "stock": 7,
            "image": "https://exemple.com/italie90.png"
        }
    ],
    "Sneakers": [
        {
            "nom": "Nike Dunk Low Panda",
            "prix": 119.99,
            "stock": 3,
            "image": "https://exemple.com/dunk_panda.png"
        },
        {
            "nom": "Adidas Samba OG",
            "prix": 129.99,
            "stock": 4,
            "image": "https://exemple.com/sambaog.png"
        }
    ]
}
CATEGORY_LIST = list(CATEGORIES.keys())
ITEMS_PER_PAGE = 3

user_carts = {}  # user_id: { "produit_id": { ... }, ... }

# -------- BOT SETUP --------
intents = discord.Intents.default()
intents.message_content = True

class Sentinelle(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

bot = Sentinelle()

@bot.event
async def on_ready():
    print(f"✅ Sentinelle connectée en tant que {bot.user}")

# -------- SHOP SYSTEM --------

def produit_uid(cat, idx):
    return f"{cat}_{idx}"

def get_cart(user_id):
    return user_carts.setdefault(user_id, {})

def add_to_cart(user_id, produit_uid, produit, qty=1):
    cart = get_cart(user_id)
    if produit_uid in cart:
        cart[produit_uid]["qty"] += qty
    else:
        cart[produit_uid] = dict(produit, qty=qty)

def remove_from_cart(user_id, produit_uid, qty=1):
    cart = get_cart(user_id)
    if produit_uid in cart:
        cart[produit_uid]["qty"] -= qty
        if cart[produit_uid]["qty"] <= 0:
            del cart[produit_uid]

def render_panier_embed(user_id):
    cart = get_cart(user_id)
    embed = discord.Embed(
        title="🛒 Ton Panier",
        description="Voici le résumé de tes articles sélectionnés.",
        color=0x00ff88
    )
    total = 0
    for uid, p in cart.items():
        nom, prix, qty = p["nom"], p["prix"], p["qty"]
        embed.add_field(
            name=f"{nom} x{qty}",
            value=f"{prix:.2f}€ • Total : {prix*qty:.2f}€",
            inline=False
        )
        total += prix*qty
    if not cart:
        embed.description = "Ton panier est vide. Ajoute des articles pour commencer !"
    else:
        embed.set_footer(text=f"Total panier : {total:.2f}€")
    return embed

class CategoryView(View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user
        for cat in CATEGORY_LIST:
            self.add_item(CategoryButton(cat, user))
        self.add_item(Button(label="Bientôt...", disabled=True, style=discord.ButtonStyle.secondary))

class CategoryButton(Button):
    def __init__(self, cat, user):
        super().__init__(label=cat, style=discord.ButtonStyle.primary)
        self.cat = cat
        self.user = user
    async def callback(self, interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        await show_product_carousel(interaction, self.cat, 0, self.user)

async def show_product_carousel(interaction, cat, page, user):
    produits = CATEGORIES[cat]
    start = page * ITEMS_PER_PAGE
    end = min(start+ITEMS_PER_PAGE, len(produits))
    produits_page = produits[start:end]
    view = ProductCarouselView(cat, page, user)
    embed = discord.Embed(
        title=f"{cat} ({page+1}/{(len(produits)-1)//ITEMS_PER_PAGE+1})",
        description="Ajoute des articles à ton panier via les boutons ci-dessous.",
        color=0x00ccff
    )
    for idx, p in enumerate(produits_page, start=start):
        uid = produit_uid(cat, idx)
        panier_qty = get_cart(user.id).get(uid, {}).get("qty", 0)
        txt = (
            f"**{p['nom']}**\n"
            f"Prix : {p['prix']:.2f}€ | Stock : {p['stock']}\n"
            f"Dans ton panier : {panier_qty}"
        )
        embed.add_field(name=f"#{idx+1}", value=txt, inline=False)
        embed.set_image(url=p["image"])
    await interaction.response.edit_message(embed=embed, view=view)

class ProductCarouselView(View):
    def __init__(self, cat, page, user):
        super().__init__(timeout=180)
        self.cat = cat
        self.page = page
        self.user = user
        produits = CATEGORIES[cat]
        start = page * ITEMS_PER_PAGE
        end = min(start+ITEMS_PER_PAGE, len(produits))
        for idx in range(start, end):
            uid = produit_uid(cat, idx)
            self.add_item(AddProductButton(cat, idx, self.user))
            self.add_item(RemoveProductButton(cat, idx, self.user))
        if page > 0:
            self.add_item(PageButton(cat, page-1, self.user, "⬅️"))
        if end < len(produits):
            self.add_item(PageButton(cat, page+1, self.user, "➡️"))
        self.add_item(PanierButton(self.user))

class AddProductButton(Button):
    def __init__(self, cat, idx, user):
        super().__init__(label=f"+{CATEGORIES[cat][idx]['nom']}", style=discord.ButtonStyle.success, row=idx%5)
        self.cat = cat
        self.idx = idx
        self.user = user
    async def callback(self, interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        produit = CATEGORIES[self.cat][self.idx]
        uid = produit_uid(self.cat, self.idx)
        add_to_cart(self.user.id, uid, produit, 1)
        await show_product_carousel(interaction, self.cat, self.idx//ITEMS_PER_PAGE, self.user)

class RemoveProductButton(Button):
    def __init__(self, cat, idx, user):
        super().__init__(label=f"-{CATEGORIES[cat][idx]['nom']}", style=discord.ButtonStyle.danger, row=idx%5)
        self.cat = cat
        self.idx = idx
        self.user = user
    async def callback(self, interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        uid = produit_uid(self.cat, self.idx)
        remove_from_cart(self.user.id, uid, 1)
        await show_product_carousel(interaction, self.cat, self.idx//ITEMS_PER_PAGE, self.user)

class PageButton(Button):
    def __init__(self, cat, page, user, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.cat = cat
        self.page = page
        self.user = user
    async def callback(self, interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        await show_product_carousel(interaction, self.cat, self.page, self.user)

class PanierButton(Button):
    def __init__(self, user):
        super().__init__(label="🛒 Voir mon panier", style=discord.ButtonStyle.primary)
        self.user = user
    async def callback(self, interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        embed = render_panier_embed(self.user.id)
        view = PanierView(self.user)
        await interaction.response.edit_message(embed=embed, view=view)

class PanierView(View):
    def __init__(self, user):
        super().__init__(timeout=180)
        self.user = user
        self.add_item(CommanderButton(user))
        self.add_item(Button(label="⬅️ Revenir au shop", style=discord.ButtonStyle.secondary, row=1))

class CommanderButton(Button):
    def __init__(self, user):
        super().__init__(label="✅ Commander", style=discord.ButtonStyle.success)
        self.user = user
    async def callback(self, interaction):
        # Ici tu mets ta logique de validation de commande (ou génération de ticket)
        await interaction.response.send_message("Merci pour ta commande ! Un admin va la traiter.", ephemeral=True)
        user_carts[self.user.id] = {}  # reset panier

# --------- /SHOP COMMAND ---------

@bot.tree.command(name="shop", description="Ouvre la boutique complète")
async def shop_slash(interaction: discord.Interaction):
    view = CategoryView(interaction.user)
    embed = discord.Embed(
        title="🛒 Bienvenue dans la boutique La Planque",
        description="Choisis une catégorie pour découvrir les produits.",
        color=0x00ffff
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --------- LANCEMENT ---------
if __name__ == "__main__":
    bot.run(TOKEN)
