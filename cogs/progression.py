import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import aioftp
import json
import re
from utils.database import get_db
from utils.servers import get_servers

class Progression(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.servers = get_servers()
        self.sync_loop.start()

    def cog_unload(self):
        self.sync_loop.cancel()

    # ── Slash command : lier son compte Minecraft ──────────────────────────────
    @app_commands.command(name="link", description="Lier ton pseudo Minecraft à ton compte Discord")
    @app_commands.describe(username="Ton pseudo Minecraft exact")
    async def link(self, interaction: discord.Interaction, username: str):
        conn = await get_db()
        try:
            await conn.execute("""
                INSERT INTO players (discord_id, minecraft_username)
                VALUES ($1, $2)
                ON CONFLICT (discord_id) DO UPDATE SET minecraft_username = $2
            """, str(interaction.user.id), username)

            embed = discord.Embed(
                title="✅ Compte lié !",
                description=f"Ton Discord est maintenant lié à **{username}**.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)
        finally:
            await conn.close()

    # ── Slash command : voir sa progression ────────────────────────────────────
    @app_commands.command(name="progression", description="Voir ta progression sur les serveurs")
    async def progression(self, interaction: discord.Interaction):
        conn = await get_db()
        try:
            player = await conn.fetchrow(
                "SELECT * FROM players WHERE discord_id = $1",
                str(interaction.user.id)
            )
            if not player:
                await interaction.response.send_message(
                    "❌ Tu n'as pas encore lié ton compte. Utilise `/link` d'abord !",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"📊 Progression de {player['minecraft_username']}",
                color=discord.Color.blurple()
            )

            for server in self.servers:
                quests = await conn.fetchrow(
                    "SELECT quests_completed FROM quest_progress WHERE player_id = $1 AND server_name = $2",
                    player["id"], server["name"]
                )
                playtime = await conn.fetchrow(
                    "SELECT total_seconds FROM playtime WHERE player_id = $1 AND server_name = $2",
                    player["id"], server["name"]
                )

                quests_count = quests["quests_completed"] if quests else 0
                seconds = playtime["total_seconds"] if playtime else 0
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60

                embed.add_field(
                    name=f"🌍 {server['name']}",
                    value=f"✅ Quêtes : **{quests_count}**\n⏱️ Playtime : **{hours}h {minutes}m**",
                    inline=True
                )

            await interaction.response.send_message(embed=embed)
        finally:
            await conn.close()

    # ── Tâche automatique : sync toutes les 15 minutes ────────────────────────
    @tasks.loop(minutes=15)
    async def sync_loop(self):
        for server in self.servers:
            await self.sync_playtime(server)
            await self.sync_quests(server)

    @sync_loop.before_loop
    async def before_sync(self):
        await self.bot.wait_until_ready()

    # ── Sync playtime via RCON ─────────────────────────────────────────────────
    async def sync_playtime(self, server):
        try:
            from asyncio_rcon import RCONClient
            async with RCONClient(server["rcon_host"], server["rcon_port"], server["rcon_password"]) as rcon:
                conn = await get_db()
                players = await conn.fetch("SELECT * FROM players")
                for player in players:
                    response = await rcon.send(f"minecraft:playtime query {player['minecraft_username']}")
                    # Parse la réponse RCON (format: "X days, Y hours, Z minutes, W seconds")
                    match = re.search(r"(\d+)d.*?(\d+)h.*?(\d+)m.*?(\d+)s", response)
                    if match:
                        d, h, m, s = map(int, match.groups())
                        total = d * 86400 + h * 3600 + m * 60 + s
                        await conn.execute("""
                            INSERT INTO playtime (player_id, server_name, total_seconds)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (player_id, server_name) DO UPDATE SET total_seconds = $3, last_updated = NOW()
                        """, player["id"], server["name"], total)
                await conn.close()
        except Exception as e:
            print(f"❌ Sync playtime {server['name']} : {e}")

    # ── Sync quêtes via FTP ────────────────────────────────────────────────────
    async def sync_quests(self, server):
        try:
            async with aioftp.Client.context(
                server["ftp_host"],
                user=server["ftp_user"],
                password=server["ftp_password"]
            ) as ftp_client:
                # Chemin typique FTB Quests
                path = "/world/serverconfig/ftbquests/data/"
                conn = await get_db()
                players = await conn.fetch("SELECT * FROM players")

                for player in players:
                    player_path = f"{path}{player['minecraft_username']}.snbt"
                    try:
                        async with ftp_client.download_stream(player_path) as stream:
                            data = b""
                            async for block in stream.iter_by_block():
                                data += block
                        content = data.decode("utf-8")
                        # Compter les quêtes complétées (claimed: 1)
                        count = content.count("claimed: 1")
                        await conn.execute("""
                            INSERT INTO quest_progress (player_id, server_name, quests_completed)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (player_id, server_name) DO UPDATE SET quests_completed = $3, last_updated = NOW()
                        """, player["id"], server["name"], count)
                    except Exception:
                        pass  # Joueur pas encore connecté sur ce serveur

                await conn.close()
        except Exception as e:
            print(f"❌ Sync quêtes {server['name']} : {e}")

async def setup(bot):
    await bot.add_cog(Progression(bot))
