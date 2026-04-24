import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "cogs.progression",
    "cogs.updates",
    "cogs.admin",
]

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")
    await bot.sync_commands()
    print("✅ Commandes slash synchronisées")

async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"✅ Cog chargé : {cog}")
            except Exception as e:
                print(f"❌ Erreur chargement {cog} : {e}")
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
