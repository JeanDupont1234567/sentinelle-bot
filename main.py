import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class MonBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="/",
            intents=intents,
            application_id=None
        )

    async def setup_hook(self):
        # Synchronise les commandes slash au lancement
        await self.tree.sync()
        print("Slash commands synchronisées (global)")

bot = MonBot()

stock_tshirts = [
    {
        "nom": "T-shirt Stussy x Nike J-C - M",
        "quantite": 12,
        "prix": 14,
        "image": "https://www.picclickimg.com/5AMAAOSwHYJoONWU/maillot-du-br%C3%A9sil-concept-jesus-nike-saison-24-25.webp"
    },
    {
        "nom": "T-shirt Stussy x Nike - L",
        "quantite": 5,
        "prix": 14,
        "image": "https://example.com/tshirt2.jpg"
    },
    {
        "nom": "Supreme x CDG - S",
        "quantite": 1,
        "prix": 25,
        "image": "https://example.com/tshirt3.jpg"
    }
]

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")

# Commande /stock
@bot.tree.command(name="stock", description="Affiche le stock de T-shirts")
async def stock_slash(interaction: discord.Interaction):
    for produit in stock_tshirts:
        embed = discord.Embed(
            title=produit["nom"],
            description=f"Quantité dispo : {produit['quantite']}\nPrix : {produit['prix']}€",
            color=0x00ff00
        )
        embed.set_image(url=produit["image"])
        embed.set_footer(text="Clique sur /commander pour acheter")
        await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Voici le stock disponible 👕", ephemeral=True)

# Commande /commander
@bot.tree.command(name="commander", description="Crée un salon privé pour commander un T-shirt")
async def commander_slash(interaction: discord.Interaction):
    guild = interaction.guild
    author = interaction.user

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }

    category = discord.utils.get(guild.categories, name="Commandes")
    if not category:
        category = await guild.create_category("Commandes")

    channel = await guild.create_text_channel(
        name=f"commande-{author.name}",
        overwrites=overwrites,
        category=category
    )

    await channel.send(
        f"Bienvenue {author.mention}, voici ton salon privé pour commander.\n"
        "Tape ici ce que tu veux acheter (modèle, quantité), puis attends validation."
    )

    for produit in stock_tshirts:
        embed = discord.Embed(
            title=produit["nom"],
            description=f"Quantité dispo : {produit['quantite']}\nPrix : {produit['prix']}€",
            color=0x00ff00
        )
        embed.set_image(url=produit["image"])
        embed.set_footer(text="Commande privée")
        await channel.send(embed=embed)

    await interaction.response.send_message(
        "Salon privé créé, vérifie la catégorie 'Commandes' en haut à gauche !", ephemeral=True
    )

bot.run(TOKEN)
