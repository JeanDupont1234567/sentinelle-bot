import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import os
import random
from dotenv import load_dotenv

# ┌─────────────────────────────────────────────────────────┐
# │                    CONFIGURATION                      │
# └─────────────────────────────────────────────────────────┘

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1376941684147097660  # Remplace par ton Guild ID

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Salon où les annonces publiques sont postées
ANNOUNCE_CHANNEL = "achats-publics"

# ┌─────────────────────────────────────────────────────────┐
# │              DONNÉES EXEMPLES (À CHANGER)              │
# └─────────────────────────────────────────────────────────┘

# Produits / catégories (à remplacer par Google Sheets plus tard)
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
            "nom": "Stussy x Nike - L",
            "prix_euro": 14,
            "prix_volts": 140,
            "stock": 5,
            "image": "https://example.com/tshirt2.jpg",
            "desc": "Taille L, modèle oversize.",
            "rarete": "uncommon"
        },
        {
            "nom": "Supreme x CDG - S",
            "prix_euro": 25,
            "prix_volts": 250,
            "stock": 1,
            "image": "https://example.com/tshirt3.jpg",
            "desc": "Rare, taille S.",
            "rarete": "rare"
        },
        {
            "nom": "Nike Dunk Low - Noir",
            "prix_euro": 90,
            "prix_volts": 900,
            "stock": 2,
            "image": "https://example.com/dunk1.jpg",
            "desc": "Sneaker premium.",
            "rarete": "epic"
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
        },
        {
            "nom": "Jordan 4 Retro",
            "prix_euro": 250,
            "prix_volts": 2500,
            "stock": 1,
            "image": "https://example.com/jordan4.jpg",
            "desc": "Deadstock, taille 42.",
            "rarete": "legendary"
        }
    ]
}
CATEGORY_LIST = list(CATEGORIES.keys())

# Utilisateurs stockés en mémoire
user_volts = {}           # user_id: nombre de Volts
user_slots = {}           # user_id: slots restants ce mois
user_badges = {}          # user_id: liste de badges gagnés
user_referrals = {}       # code: parrain_id
user_filleuls = {}        # parrain_id: liste de filleul_ids
user_sales = {}           # user_id: nombre de ventes réalisées
referral_codes = {}       # user_id: code généré
user_loots = {}           # user_id: liste d'items looteés

# Rangs selon Volts acquis
RANKS = [
    ("Explorateur", 0, 2, "🧭", 0x888888),
    ("Businessman", 1000, 8, "💼", 0xdb143c),
    ("Légende", 5000, 10, "👑", 0xffd700),
    ("Mythique", 20000, None, "💎", 0x00ffff)
]


# ┌─────────────────────────────────────────────────────────┐
# │                   AIDE / UTILITAIRES                   │
# └─────────────────────────────────────────────────────────┘

def get_user_rank(user_id: int):
    volts = user_volts.get(user_id, 0)
    rank_name, _, slots, emoji, color = RANKS[0]
    for r in RANKS:
        name, threshold, slot_count, emj, col = r
        if volts >= threshold:
            rank_name, slots, emoji, rank_color = name, slot_count, emj, col
    return rank_name, slots, emoji, rank_color


def format_volts(volts: int):
    return f"{volts} ⚡"


def generate_referral_code(user_id: int):
    code = f"REF{user_id}{random.randint(1000, 9999)}"
    referral_codes[user_id] = code
    user_referrals[code] = user_id
    return code


def assign_referral(filleul_id: int, code: str):
    parrain_id = user_referrals.get(code)
    if parrain_id:
        user_filleuls.setdefault(parrain_id, []).append(filleul_id)
        # Récompense initiale
        user_volts[parrain_id] = user_volts.get(parrain_id, 0) + 50
        user_volts[filleul_id] = user_volts.get(filleul_id, 0) + 50
        return parrain_id
    return None


def get_leaderboard_by_volts(limit=10):
    sorted_users = sorted(user_volts.items(), key=lambda x: x[1], reverse=True)
    return sorted_users[:limit]


# ┌─────────────────────────────────────────────────────────┐
# │                     BOT SETUP                          │
# └─────────────────────────────────────────────────────────┘

class Sentinelle(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",  # slash commands utilisés
            intents=intents,
            application_id=None
        )

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synchronisées sur la guilde.")


bot = Sentinelle()


@bot.event
async def on_ready():
    print(f"✅ Sentinelle connectée en tant que {bot.user}")


# ┌─────────────────────────────────────────────────────────┐
# │              EMBEDS & UX STYLING                       │
# └─────────────────────────────────────────────────────────┘

def make_embed(title: str, description: str, color: int):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="La Planque • Sentinelle")
    return embed


def product_embed(produit: dict):
    color_map = {
        "common": 0x00ff00,
        "uncommon": 0x00ffff,
        "rare": 0x0080ff,
        "epic": 0x8000ff,
        "legendary": 0xdb143c
    }
    color = color_map.get(produit.get("rarete", "common"), 0x00ff00)
    embed = discord.Embed(
        title=produit["nom"],
        description=f"{produit['desc']}\n\n**Prix :** {produit['prix_euro']}€ / {produit['prix_volts']} Volts\n**Stock :** {produit['stock']}",
        color=color
    )
    embed.set_image(url=produit["image"])
    embed.set_footer(text="Clique sur un bouton pour interagir")
    return embed


# ┌─────────────────────────────────────────────────────────┐
# │           VUES DYNAMIQUES : BOUTIQUE PAGINÉE            │
# └─────────────────────────────────────────────────────────┘

class ProductView(View):
    def __init__(self, category: str, page: int, user: discord.User):
        super().__init__(timeout=180)
        self.category = category
        self.page = page
        self.user = user
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        produits = CATEGORIES[self.category]
        start = self.page * 4
        for prod in produits[start:start + 4]:
            label = prod["nom"][:80]
            self.add_item(ProductButton(label=label, produit=prod, user=self.user, category=self.category))
        # Pagination
        if self.page > 0:
            self.add_item(PageButton("⬅️", self.category, self.page - 1, self.user))
        if (self.page + 1) * 4 < len(CATEGORIES[self.category]):
            self.add_item(PageButton("➡️", self.category, self.page + 1, self.user))


class PageButton(Button):
    def __init__(self, emoji: str, category: str, page: int, user: discord.User):
        super().__init__(style=discord.ButtonStyle.secondary, label=emoji)
        self.category = category
        self.page = page
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        view = ProductView(self.category, self.page, self.user)
        embed = make_embed(f"Catégorie : {self.category} (Page {self.page + 1})",
                           "Sélectionne un produit ci-dessous :", 0x222222)
        await interaction.response.edit_message(embed=embed, view=view, content=None)


class ProductButton(Button):
    def __init__(self, label: str, produit: dict, user: discord.User, category: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label[:80])
        self.produit = produit
        self.user = user
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        embed = product_embed(self.produit)
        view = ProductDetailView(self.produit, self.user, self.category)
        await interaction.response.edit_message(embed=embed, view=view, content=None)


class ProductDetailView(View):
    def __init__(self, produit: dict, user: discord.User, category: str):
        super().__init__(timeout=120)
        self.produit = produit
        self.user = user
        self.category = category
        self.add_item(CommandButton(produit, user, category))
        self.add_item(Button(label="⬅️ Retour", style=discord.ButtonStyle.secondary, custom_id="retour"))

    @discord.ui.button(label="⬅️ Retour", style=discord.ButtonStyle.secondary, row=1)
    async def retour(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        view = ProductView(self.category, 0, self.user)
        embed = make_embed(f"Catégorie : {self.category} (Page 1)", "Sélectionne un produit ci-dessous :",
                           0x222222)
        await interaction.response.edit_message(embed=embed, view=view, content=None)


class CommandButton(Button):
    def __init__(self, produit: dict, user: discord.User, category: str):
        super().__init__(style=discord.ButtonStyle.success, label="🛒 Commander")
        self.produit = produit
        self.user = user
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        if self.produit["stock"] < 1:
            return await interaction.response.send_message("❌ Rupture de stock !", ephemeral=True)
        # Débit du stock
        self.produit["stock"] -= 1
        # Gain de Volts : 10% du prix en Volts
        gain = int(self.produit["prix_volts"] * 0.1)
        user_volts[self.user.id] = user_volts.get(self.user.id, 0) + gain
        user_sales[self.user.id] = user_sales.get(self.user.id, 0) + 1
        # Slots consommés
        rank_name, slots, _, _ = get_user_rank(self.user.id)
        if slots is not None:
            user_slots[self.user.id] = user_slots.get(self.user.id, slots) - 1

        # Annonce publique
        await announce_purchase(interaction.guild, self.user, self.produit)

        # Réponse privée
        await interaction.response.send_message(
            f"✅ Ta commande pour **{self.produit['nom']}** est validée !\n"
            f"Tu gagnes **{gain} Volts** (Total : {user_volts[self.user.id]} ⚡)\n"
            f"Slots restants ce mois : {user_slots.get(self.user.id, 0)}",
            ephemeral=True
        )


async def announce_purchase(guild: discord.Guild, user: discord.User, produit: dict):
    for chan in guild.text_channels:
        if chan.name == ANNOUNCE_CHANNEL:
            embed = discord.Embed(
                title="Nouvelle commande !",
                description=f"**{user.mention}** vient de commander **{produit['nom']}** !\n"
                            f"Prix : {produit['prix_euro']}€ / {produit['prix_volts']} Volts",
                color=0xdb143c
            )
            embed.set_image(url=produit["image"])
            await chan.send(embed=embed)
            break


# ┌─────────────────────────────────────────────────────────┐
# │              COMMANDE /shop (INITIALISATION)           │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="shop", description="Ouvre la boutique interactive")
async def shop_slash(interaction: discord.Interaction):
    select = Select(
        placeholder="Choisis une catégorie",
        options=[discord.SelectOption(label=cat) for cat in CATEGORY_LIST]
    )

    async def select_callback(select_interaction: discord.Interaction):
        cat = select.values[0]
        view = ProductView(cat, 0, interaction.user)
        embed = make_embed(f"Catégorie : {cat} (Page 1)", "Sélectionne un produit ci-dessous :", 0x222222)
        await select_interaction.response.edit_message(embed=embed, view=view, content=None)

    select.callback = select_callback
    view = View()
    view.add_item(select)
    await interaction.response.send_message(
        embed=make_embed("Bienvenue dans la boutique !", "Sélectionne une catégorie pour commencer.", 0x222222),
        view=view,
        ephemeral=True
    )


# ┌─────────────────────────────────────────────────────────┐
# │                 COMMANDE /volts                         │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="volts", description="Affiche ton solde de Volts")
async def volts_slash(interaction: discord.Interaction):
    volts = user_volts.get(interaction.user.id, 0)
    embed = make_embed("Solde Volts",
                       f"Tu possèdes **{volts} ⚡**.\n"
                       "Utilise tes Volts pour acheter, looter, ou monter en grade.",
                       0x00ffff)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ┌─────────────────────────────────────────────────────────┐
# │                 COMMANDE /lootbox                        │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="lootbox", description="Ouvre une lootbox aléatoire (coût : 500 Volts)")
async def lootbox_slash(interaction: discord.Interaction):
    cost = 500
    uid = interaction.user.id
    if user_volts.get(uid, 0) < cost:
        return await interaction.response.send_message(
            "❌ Tu n'as pas assez de Volts pour ouvrir une lootbox (500 ⚡ requis).", ephemeral=True
        )
    # Débit Volts
    user_volts[uid] -= cost
    # Définir la table de loot
    table_loot = [
        ("badge_explorateur", 0.4, "Badge Explorateur", "Tu as reçu le badge Explorateur !", 100),
        ("badge_businessman", 0.3, "Badge Businessman", "Tu as reçu le badge Businessman !", 200),
        ("badge_legende", 0.2, "Badge Légende", "Tu as reçu le badge Légende !", 500),
        ("volt_bonus", 0.1, "Bonus Volts", "Bravo, tu gagnes 1000 Volts !", 1000)
    ]
    roll = random.random()
    cum = 0
    result = None
    for key, prob, name, desc, reward in table_loot:
        cum += prob
        if roll <= cum:
            result = (key, name, desc, reward)
            break
    if not result:
        result = ("volt_bonus", "Bonus Volts", "Bravo, tu gagnes 1000 Volts !", 1000)

    key, name, desc, reward = result
    # Appliquer la récompense
    if key.startswith("badge"):
        user_badges.setdefault(uid, []).append(name)
        user_loots.setdefault(uid, []).append(name)
        embed = make_embed("🎁 Lootbox", f"{desc}", 0x8000ff)
    else:
        user_volts[uid] += reward
        embed = make_embed("🎁 Lootbox", f"{desc}", 0x8000ff)
    # Annonce publique si rare ou légendaire
    if key in ("badge_legende",):
        for chan in interaction.guild.text_channels:
            if chan.name == ANNOUNCE_CHANNEL:
                ann = make_embed("🌟 LOOT EXCEPTIONNEL !",
                                 f"**{interaction.user.mention}** vient de looter **{name}** !", 0xdb143c)
                await chan.send(embed=ann)
                break
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ┌─────────────────────────────────────────────────────────┐
# │                 COMMANDE /profil                         │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="profil", description="Affiche ton profil complet")
async def profil_slash(interaction: discord.Interaction):
    uid = interaction.user.id
    rank_name, slots, emoji, color = get_user_rank(uid)
    volts = user_volts.get(uid, 0)
    badges = user_badges.get(uid, [])
    sales = user_sales.get(uid, 0)
    filleuls = user_filleuls.get(uid, [])
    embed = discord.Embed(
        title=f"{emoji} Profil de {interaction.user.name}",
        color=color
    )
    embed.add_field(name="Rang", value=rank_name, inline=True)
    embed.add_field(name="Volts", value=f"{volts} ⚡", inline=True)
    embed.add_field(name="Slots restants", value=(slots if slots is not None else "∞"), inline=True)
    embed.add_field(name="Ventes réalisées", value=sales, inline=True)
    embed.add_field(name="Nombre de filleuls", value=len(filleuls), inline=True)
    embed.add_field(name="Badges", value=", ".join(badges) if badges else "Aucun", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ┌─────────────────────────────────────────────────────────┐
# │             COMMANDE /leaderboard                        │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="leaderboard", description="Affiche le classement des meilleurs Volts")
async def leaderboard_slash(interaction: discord.Interaction):
    top_users = get_leaderboard_by_volts(10)
    embed = make_embed("🏆 Classement Volts", "", 0xeeee00)
    description = ""
    for i, (uid, volts) in enumerate(top_users, start=1):
        user = await bot.fetch_user(uid)
        description += f"**{i}. {user.name}** – {volts} ⚡\n"
    embed.description = description or "Aucun utilisateur trouvé."
    await interaction.response.send_message(embed=embed, ephemeral=False)


# ┌─────────────────────────────────────────────────────────┐
# │             COMMANDE /parrainage                         │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="parrainage", description="Génère et gère ton code de parrainage")
async def parrainage_slash(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid not in referral_codes:
        code = generate_referral_code(uid)
        embed = make_embed("🔑 Code de parrainage généré",
                           f"Ton code : **`{code}`**\n"
                           "Partage-le avec un nouvel arrivant pour gagner 50 Volts chacun.",
                           0x00ffff)
    else:
        code = referral_codes[uid]
        embed = make_embed("🔑 Ton code de parrainage actuel",
                           f"Ton code : **`{code}`**\n"
                           "Partage-le avec un nouvel arrivant pour gagner 50 Volts chacun.",
                           0x00ffff)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="saisir_parrain", description="Saisis le code de ton parrain pour bénéficier de 50 Volts")
@app_commands.describe(code="Le code de parrainage que tu as reçu")
async def saisir_parrain_slash(interaction: discord.Interaction, code: str):
    uid = interaction.user.id
    if uid in user_filleuls.get(user_referrals.get(code, None), []):
        return await interaction.response.send_message("🚫 Tu as déjà utilisé ce code.", ephemeral=True)
    parrain_id = assign_referral(uid, code)
    if parrain_id:
        parent = await bot.fetch_user(parrain_id)
        embed = make_embed("🎉 Parrainage réussi",
                           f"Félicitations ! Tu as été parrainé par **{parent.name}**.\n"
                           "Vous recevez chacun **50 Volts**.", 0x00ffff)
    else:
        embed = make_embed("❌ Code invalide", "Aucun parrain trouvé pour ce code.", 0xdb143c)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ┌─────────────────────────────────────────────────────────┐
# │                 COMMANDE /slots                           │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="slots", description="Affiche tes slots restants ce mois")
async def slots_slash(interaction: discord.Interaction):
    uid = interaction.user.id
    _, default_slots, _, _ = get_user_rank(uid)
    remaining = user_slots.get(uid, default_slots)
    embed = make_embed("📦 Slots Restants",
                       f"Tu as **{remaining}** slots restants ce mois.\n"
                       f"Si tu veux en acheter davantage, utilise tes Volts pour monter de rang.",
                       0x222222)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ┌─────────────────────────────────────────────────────────┐
# │             COMMANDES ADMIN : GÉRER LES VOLTS           │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="givevolts", description="(Admin) Donne des Volts à un membre")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    membre="Le membre à créditer en Volts",
    amount="Le nombre de Volts à ajouter"
)
async def givevolts_slash(interaction: discord.Interaction, membre: discord.Member, amount: int):
    if amount <= 0:
        return await interaction.response.send_message("❌ Le montant doit être positif.", ephemeral=True)
    uid = membre.id
    user_volts[uid] = user_volts.get(uid, 0) + amount
    await interaction.response.send_message(
        f"✅ {amount} Volts ont été ajoutés à **{membre.name}**. Nouveau solde : {user_volts[uid]} ⚡.", 
        ephemeral=True
    )


@bot.tree.command(name="removevolts", description="(Admin) Retire des Volts à un membre")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    membre="Le membre à débiter en Volts",
    amount="Le nombre de Volts à retirer"
)
async def removevolts_slash(interaction: discord.Interaction, membre: discord.Member, amount: int):
    if amount <= 0:
        return await interaction.response.send_message("❌ Le montant doit être positif.", ephemeral=True)
    uid = membre.id
    current = user_volts.get(uid, 0)
    nouveau = max(0, current - amount)
    user_volts[uid] = nouveau
    await interaction.response.send_message(
        f"✅ {amount} Volts ont été retirés de **{membre.name}**. Nouveau solde : {nouveau} ⚡.", 
        ephemeral=True
    )


@bot.tree.command(name="setvolts", description="(Admin) Définit le solde de Volts d’un membre")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    membre="Le membre dont tu veux définir le solde",
    amount="Le nouveau solde de Volts"
)
async def setvolts_slash(interaction: discord.Interaction, membre: discord.Member, amount: int):
    if amount < 0:
        return await interaction.response.send_message("❌ Le montant ne peut pas être négatif.", ephemeral=True)
    uid = membre.id
    user_volts[uid] = amount
    await interaction.response.send_message(
        f"✅ Le solde de **{membre.name}** a été défini à **{amount} ⚡**.", 
        ephemeral=True
    )


# ┌─────────────────────────────────────────────────────────┐
# │                 COMMANDE /annonce                         │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="annonce", description="Publie une annonce (admin uniquement)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(titre="Titre de l'annonce", contenu="Contenu de l'annonce")
async def annonce_slash(interaction: discord.Interaction, titre: str, contenu: str):
    for chan in interaction.guild.text_channels:
        if chan.name == ANNOUNCE_CHANNEL:
            embed = make_embed(f"📢 {titre}", contenu, 0x00ffff)
            await chan.send(embed=embed)
            await interaction.response.send_message("Annonce publiée avec succès.", ephemeral=True)
            return
    await interaction.response.send_message("Salon d'annonce introuvable.", ephemeral=True)


# ┌─────────────────────────────────────────────────────────┐
# │                COMMANDE /report                            │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="report", description="Signale un problème ou fais une suggestion")
async def report_slash(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🛠️ Envoie-moi en DM les détails de ton rapport, je m'en occupe.", ephemeral=True
    )
    try:
        await interaction.user.send(
            "Merci de détailler ton problème ou suggestion. L'équipe Sentinelle te répondra rapidement."
        )
    except discord.Forbidden:
        await interaction.response.send_message("Impossible de t'envoyer un DM. Vérifie tes paramètres.", ephemeral=True)


# ┌─────────────────────────────────────────────────────────┐
# │                  COMMANDE /help                            │
# └─────────────────────────────────────────────────────────┘

@bot.tree.command(name="help", description="Affiche la liste des commandes disponibles")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="❓ Commandes Sentinelle",
        description=(
            "`/shop` – Ouvre la boutique interactive\n"
            "`/volts` – Affiche ton solde de Volts\n"
            "`/lootbox` – Ouvre une lootbox pour 500 Volts\n"
            "`/profil` – Affiche ton profil complet\n"
            "`/leaderboard` – Classement des meilleurs Volts\n"
            "`/parrainage` – Génère ton code de parrainage\n"
            "`/saisir_parrain` – Saisis un code pour être parrainé\n"
            "`/slots` – Montre tes slots restants ce mois\n"
            "`/annonce` – (Admin) Publie une annonce publique\n"
            "`/report` – Signale un problème ou fais une suggestion\n"
            "`/help` – Affiche ce message\n"
        ),
        color=0x222222
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ┌─────────────────────────────────────────────────────────┐
# │                       LANCEMENT                           │
# └─────────────────────────────────────────────────────────┘

bot.run(TOKEN)
