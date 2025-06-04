import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import os
import random
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# ───────────── CONFIGURATION DE BASE ─────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1376941684147097660
ADMIN_ROLE_ID = 1376941690309976065  # Remplace par l’ID du rôle admin de ton serveur
ANNOUNCE_CHANNEL = "achats-publics"

VOLT_PACKS = [
    {
        "volts": 100,
        "prix": 8.99,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379938998880964720/100V.png",
        "desc": "Idéal pour tester la puissance ⚡",
        "bonus": "+0% OFFERT"
    },
    {
        "volts": 280,
        "prix": 22.99,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379939121375609023/280V.png",
        "desc": "Prix mini par Volt, boost rapide",
        "bonus": "+9% OFFERT"
    },
    {
        "volts": 500,
        "prix": 36.99,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379939202346520730/500V.png",
        "desc": "Gros pack pour gros joueurs 💎",
        "bonus": "+22% OFFERT"
    },
    {
        "volts": 1300,
        "prix": 89.99,
        "image_url": "https://cdn.discordapp.com/attachments/1379938265079218206/1379941340795764817/1300V.png",
        "desc": "La vraie puissance. Tu deviens une Légende.",
        "bonus": "+30% OFFERT"
    }
]

user_volts = {}
user_badges = {}
user_sales = {}
user_loots = {}
purchase_history = {}

def format_volts(volts): return f"{volts} ⚡"

# ───────────── BOT SETUP ─────────────
class Sentinelle(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synchronisées.")

bot = Sentinelle()

@bot.event
async def on_ready():
    print(f"✅ Sentinelle connectée en tant que {bot.user}")

# ───────────── BOUTIQUE VOLTS / TICKETS ─────────────

def get_next_ticket_number(guild):
    nums = []
    for c in guild.text_channels:
        if c.name.startswith("ticket-achat-"):
            try:
                n = int(c.name.split("-")[-1])
                nums.append(n)
            except: pass
    return max(nums + [0]) + 1

class BuyVoltsView(View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user
        for pack in VOLT_PACKS:
            self.add_item(BuyVoltsButton(pack, user))

class BuyVoltsButton(Button):
    def __init__(self, pack, user):
        super().__init__(
            label=f"{pack['volts']}⚡ — {pack['prix']}€",
            style=discord.ButtonStyle.success
        )
        self.pack = pack
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Ce menu n'est pas à toi.", ephemeral=True)
        guild = interaction.guild
        ticket_number = get_next_ticket_number(guild)
        category = discord.utils.get(guild.categories, name="tickets")
        if not category:
            category = await guild.create_category("tickets")
        admin_role = discord.utils.get(guild.roles, id=ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel_name = f"ticket-achat-{self.user.display_name.lower().replace(' ', '-')}-{ticket_number}"
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category
        )
        embed = discord.Embed(
            title=f"💸 Achat de Volts — Confirmation",
            description=(
                f"**{self.user.mention} souhaite acheter**\n\n"
                f"**{self.pack['volts']} Volts** pour **{self.pack['prix']}€**\n"
                f"{self.pack['desc']}  \n{self.pack['bonus']}\n\n"
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
        await ticket_channel.send(content=f"{self.user.mention} Ticket ouvert pour achat de Volts #{ticket_number}.", embed=embed)
        await interaction.response.send_message(
            f"✅ Ticket d’achat ouvert ici : {ticket_channel.mention}\nMerci de suivre les instructions dans le salon !",
            ephemeral=True
        )
        await announce_purchase(guild, self.user, self.pack)
        bot.loop.create_task(close_ticket_auto(ticket_channel, self.user, delay=7200))

async def close_ticket_auto(channel, user, delay=7200):
    await asyncio.sleep(delay)
    try:
        await channel.send(f"⏳ Ticket fermé automatiquement par sécurité. Si besoin, recommence l’achat, {user.mention}.")
        await channel.delete()
    except:
        pass

@bot.tree.command(name="buyvolts", description="Boutique Volts (paiement PayPal/Revolut)")
async def buyvolts_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚡ Boutique Volts : choisis ton pack ci-dessous pour ouvrir un ticket d’achat sécurisé.",
        description=(
            "• Offre 100% privée, instantanée, réservée aux membres La Planque.\n"
            "• Paiement **PayPal (entre amis)** ou **Revolut** accepté.\n"
            "• Aucune limite d’achat. Conversion immédiate.\n\n"
            "Clique sur le pack qui te correspond."
        ),
        color=0x00ffff
    )
    embed.set_footer(text="La Planque • Sentinelle")
    await interaction.response.send_message(view=BuyVoltsView(interaction.user), embed=embed, ephemeral=True)

# ───────────── FOMO — ANNONCE D'ACHAT PUBLIC ─────────────

async def announce_purchase(guild, user, pack):
    for chan in guild.text_channels:
        if chan.name == ANNOUNCE_CHANNEL:
            embed = discord.Embed(
                title="🔥 NOUVEL ACHAT DE VOLTS",
                description=f"**{user.mention}** vient d’acheter **{pack['volts']}⚡** pour {pack['prix']}€ !",
                color=0xffe600
            )
            embed.set_image(url=pack["image_url"])
            await chan.send(embed=embed)
            break

# ───────────── HISTORIQUE DES ACHATS ─────────────

def add_purchase_history(user_id, pack):
    history = purchase_history.setdefault(user_id, [])
    history.append({
        "volts": pack["volts"],
        "prix": pack["prix"],
        "date": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
        "pack": pack
    })

@bot.tree.command(name="history", description="Consulte ton historique d’achats Volts")
async def history_slash(interaction: discord.Interaction):
    uid = interaction.user.id
    histo = purchase_history.get(uid, [])
    if not histo:
        return await interaction.response.send_message("Aucun achat de Volts enregistré.", ephemeral=True)
    embed = discord.Embed(
        title="🧾 Historique d’achats Volts",
        color=0x00ffff
    )
    for entry in histo[-10:]:
        embed.add_field(
            name=f"{entry['volts']}⚡ — {entry['prix']}€",
            value=f"{entry['date']} • {entry['pack']['desc']}",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ───────────── COMMANDES UTILISATEURS ─────────────

@bot.tree.command(name="volts", description="Affiche ton solde de Volts")
async def volts_slash(interaction: discord.Interaction):
    volts = user_volts.get(interaction.user.id, 0)
    await interaction.response.send_message(
        f"**Solde Volts : `{format_volts(volts)}`\nUtilise `/buyvolts` pour acheter.", ephemeral=True
    )

@bot.tree.command(name="profil", description="Affiche ton profil Sentinelle")
async def profil_slash(interaction: discord.Interaction):
    uid = interaction.user.id
    volts = user_volts.get(uid, 0)
    badges = ", ".join(user_badges.get(uid, [])) or "Aucun"
    sales = user_sales.get(uid, 0)
    embed = discord.Embed(
        title=f"Profil de {interaction.user.display_name}",
        color=0x00ffff
    )
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
