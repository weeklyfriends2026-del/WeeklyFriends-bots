import discord
from discord.ext import commands, tasks
import aiohttp
import os
from utils.database import get_db
from utils.servers import get_servers

CURSEFORGE_API_KEY = os.getenv("CURSEFORGE_API_KEY")
UPDATES_CHANNEL_ID = int(os.getenv("UPDATES_CHANNEL_ID", 0))

class Updates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.servers = get_servers()
        self.check_updates.start()

    def cog_unload(self):
        self.check_updates.cancel()

    @tasks.loop(minutes=30)
    async def check_updates(self):
        channel = self.bot.get_channel(UPDATES_CHANNEL_ID)
        if not channel:
            return

        for server in self.servers:
            cf_id = server.get("curseforge_id")
            if not cf_id:
                continue

            try:
                latest = await self.fetch_latest_version(cf_id)
                if not latest:
                    continue

                conn = await get_db()
                row = await conn.fetchrow(
                    "SELECT last_version FROM modpack_versions WHERE server_name = $1",
                    server["name"]
                )

                if row is None:
                    # Premier enregistrement
                    await conn.execute("""
                        INSERT INTO modpack_versions (server_name, curseforge_id, last_version)
                        VALUES ($1, $2, $3)
                    """, server["name"], str(cf_id), latest["version"])
                elif row["last_version"] != latest["version"]:
                    # Nouvelle version détectée !
                    await conn.execute("""
                        UPDATE modpack_versions SET last_version = $1, last_checked = NOW()
                        WHERE server_name = $2
                    """, latest["version"], server["name"])
                    await self.send_update_embed(channel, server["name"], latest)

                await conn.close()
            except Exception as e:
                print(f"❌ Check update {server['name']} : {e}")

    @check_updates.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def fetch_latest_version(self, modpack_id: str):
        url = f"https://api.curseforge.com/v1/mods/{modpack_id}/files"
        headers = {"x-api-key": CURSEFORGE_API_KEY}
        params = {"pageSize": 1, "sortField": 1, "sortOrder": "desc"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                files = data.get("data", [])
                if not files:
                    return None
                file = files[0]
                return {
                    "version": str(file["id"]),
                    "display_name": file.get("displayName", "Inconnu"),
                    "changelog_url": f"https://www.curseforge.com/minecraft/modpacks/{modpack_id}/files/{file['id']}",
                    "game_version": ", ".join(file.get("gameVersions", [])),
                }

    async def send_update_embed(self, channel, server_name: str, info: dict):
        embed = discord.Embed(
            title="🆕 Nouvelle mise à jour disponible !",
            color=discord.Color.orange()
        )
        embed.add_field(name="🌍 Serveur", value=f"**{server_name}**", inline=False)
        embed.add_field(name="📦 Version", value=info["display_name"], inline=True)
        embed.add_field(name="🎮 Minecraft", value=info["game_version"], inline=True)
        embed.add_field(
            name="📋 Changelog",
            value=f"[Voir sur CurseForge]({info['changelog_url']})",
            inline=False
        )
        embed.set_footer(text="WeeklyFriends Bot • Vérification automatique")
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Updates(bot))
