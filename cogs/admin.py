import discord
from discord.ext import commands
from discord import app_commands
from utils.database import init_db

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="init", description="[Admin] Initialiser la base de données")
    @app_commands.default_permissions(administrator=True)
    async def init(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await init_db()
            await interaction.followup.send("✅ Base de données initialisée !", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur : {e}", ephemeral=True)

    @app_commands.command(name="sync-now", description="[Admin] Forcer une synchronisation immédiate")
    @app_commands.default_permissions(administrator=True)
    async def sync_now(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            progression_cog = self.bot.get_cog("Progression")
            if progression_cog:
                for server in progression_cog.servers:
                    await progression_cog.sync_playtime(server)
                    await progression_cog.sync_quests(server)
            await interaction.followup.send("✅ Synchronisation effectuée !", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur : {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
