import discord
from discord.ext import commands
from discord.ui import View, Button
import os
import requests

# Update 06/06/25

# -------- CONFIG --------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN non défini dans les variables d'environnement !")
    exit(1)
GUILD_ID = 1376941684147097660

# → Remplace ceci par ton endpoint Apps Script déployé
SHEET_API_URL = "https://script.google.com/macros/s/AKfycbwIQcJhrFbsNYucVaLXlgezBniPVpJvUcxzrsxJD3ZcuJb58MBdfc-WCYJjDyL3o7Rvbg/exec"

ITEMS_PER_PAGE = 3
user_carts = {}  # user_id: { "produit_id": { ... }, ... }

# --------- FONCTIONS GOOGLE SHEETS ---------
def fetch_products():
    """Récupère tous les produits du Google Sheets"""
    try:
        r = requests.get(SHEET_API_URL, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[ERREUR FETCH_PRODUCTS] {e}")
        return []

def get_categories_and_products():
    """Renvoie {catégorie: [produits, ...]} avec debug print"""
    data = fetch_products()
    print("\n=== Données reçues de Sheets ===")
    for p in data:
        print(p)
    categories = {}
    for p in data:
        cat = p.get("catégorie", "").strip()  # Robustesse sur la clé et nettoyage
        stock = str(p.get("stock", "0")).strip()
        try:
            stock_int = int(float(stock))  # accepte "2.0" ou "2"
        except Exception:
            stock_int = 0
        if cat and stock_int > 0:
            categories.setdefault(cat, []).append(p)
    print("=== Catégories générées ===", categories.keys())
    return categories

def update_stock(product_id, new_stock, commande_en_cours):
    """Met à jour le stock d'un produit"""
    payload = {
        "id": product_id,
        "stock": new_stock,
        "commande_en_cours": commande_en_cours
    }
    try:
        r = requests.post(SHEET_API_URL, json=payload, timeout=8)
        print(f"Update stock : {payload} → {r.text}")
    except Exception as e:
        print(f"[ERREUR update_stock] {e}")

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
        nom = p.get("nom_produit", "??")
        try:
            prix = float(str(p.get("prix (€)", "0")).replace(",", "."))
        except Exception:
            prix = 0
        qty = p.get("qty", 0)
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
    def __init__(self, user, categories):
        super().__init__(timeout=120)
        self.user = user
        self.categories = categories
        for cat in categories.keys():
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
    categories = get_categories_and_products()
    produits = categories.get(cat, [])
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
        try:
            prix = float(str(p.get("prix (€)", "0")).replace(",", "."))
        except Exception:
            prix = 0
        txt = (
            f"**{p.get('nom_produit', '??')}**\n"
            f"Prix : {prix:.2f}€ | Stock : {p.get('stock', '?')}\n"
            f"Dans ton panier : {panier_qty}"
        )
        embed.add_field(name=f"#{idx+1}", value=txt, inline=False)
        img = p.get("image_url", "")
        if img:
            embed.set_image(url=img)
    await interaction.response.edit_message(embed=embed, view=view)

class ProductCarouselView(View):
    def __init__(self, cat, page, user):
        super().__init__(timeout=180)
        self.cat = cat
        self.page = page
        self.user = user
        categories = get_categories_and_products()
        produits = categories.get(cat, [])
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
        categories = get_categories_and_products()
        produits = categories.get(cat, [])
        produit_name = produits[idx].get("nom_produit", "Produit") if idx < len(produits) else "Produit"
        super().__init__(label=f"+{produit_name}", style=discord.ButtonStyle.success, row=idx%5)
        self.cat = cat
        self.idx = idx
        self.user = user
    async def callback(self, interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        categories = get_categories_and_products()
        produits = categories.get(self.cat, [])
        if self.idx >= len(produits):
            return await interaction.response.send_message("Produit non disponible.", ephemeral=True)
        produit = produits[self.idx]
        uid = produit_uid(self.cat, self.idx)
        add_to_cart(self.user.id, uid, produit, 1)
        await show_product_carousel(interaction, self.cat, self.idx//ITEMS_PER_PAGE, self.user)

class RemoveProductButton(Button):
    def __init__(self, cat, idx, user):
        categories = get_categories_and_products()
        produits = categories.get(cat, [])
        produit_name = produits[idx].get("nom_produit", "Produit") if idx < len(produits) else "Produit"
        super().__init__(label=f"-{produit_name}", style=discord.ButtonStyle.danger, row=idx%5)
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
        cart = get_cart(self.user.id)
        for uid, p in cart.items():
            try:
                product_id = int(p.get("id", 0))
                stock = str(p.get("stock", "0")).strip()
                stock_int = int(float(stock))
                new_stock = stock_int - p.get("qty", 0)
                new_cmd_en_cours = 0  # ou adapte selon ta logique
                update_stock(product_id, new_stock, new_cmd_en_cours)
            except Exception as e:
                print(f"Erreur update stock : {e}")
        await interaction.response.send_message("Merci pour ta commande ! Un admin va la traiter.", ephemeral=True)
        user_carts[self.user.id] = {}  # reset panier

# --------- /SHOP COMMAND ---------
@bot.tree.command(name="shop", description="Ouvre la boutique complète")
async def shop_slash(interaction: discord.Interaction):
    categories = get_categories_and_products()
    view = CategoryView(interaction.user, categories)
    embed = discord.Embed(
        title="🛒 Bienvenue dans la boutique La Planque",
        description="Choisis une catégorie pour découvrir les produits.",
        color=0x00ffff
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --------- LANCEMENT ---------
if __name__ == "__main__":
    print("==== Sentinelle bot starting... ====")
    print("TOKEN:", "OK" if TOKEN else "MISSING")
    print("API SHEET:", SHEET_API_URL)
    bot.run(TOKEN)
