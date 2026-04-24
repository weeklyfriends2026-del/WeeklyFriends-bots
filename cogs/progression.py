import discord
from discord.ext import commands, tasks
from discord import app_commands
import aioftp
import re
from mcrcon import MCRcon
from utils.database import get_db
from utils.servers import get_servers

class Progression(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.servers = get_servers()
        self.sync_loop.start()

    def cog_unload(self):
        self.sync_loop.cancel()

    @app_commands.command(name="link", description="Link your Minecraft username to your Discord account")
    @app_commands.describe(username="Your exact Minecraft username")
    async def link(self, interaction: discord.Interaction, username: str):
        conn = await get_db()
        try:
            await conn.execute("""
                INSERT INTO players (discord_id, minecraft_username)
                VALUES ($1, $2)
                ON CONFLICT (discord_id) DO UPDATE SET minecraft_username = $2
            """, str(interaction.user.id), username)

            embed = discord.Embed(
                title="✅ Account linked!",
                description=f"Your Discord is now linked to **{username}**.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="progression", description="View your progression on all servers")
    async def progression(self, interaction: discord.Interaction):
        conn = await get_db()
        try:
            player = await conn.fetchrow(
                "SELECT * FROM players WHERE discord_id = $1",
                str(interaction.user.id)
            )
            if not player:
                await interaction.response.send_message(
                    "❌ You haven't linked your account yet. Use `/link` first!",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"📊 Progression of {player['minecraft_username']}",
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
                    value=f"✅ Quests: **{quests_count}**\n⏱️ Playtime: **{hours}h {minutes}m**",
                    inline=True
                )

            await interaction.response.send_message(embed=embed)
        finally:
            await conn.close()

    @tasks.loop(minutes=15)
    async def sync_loop(self):
        for server in self.servers:
            await self.sync_playtime(server)
            await self.sync_quests(server)

    @sync_loop.before_loop
    async def before_sync(self):
        await self.bot.wait_until_ready()

    async def sync_playtime(self, server):
        try:
            conn = await get_db()
            players = await conn.fetch("SELECT * FROM players")
            with MCRcon(server["rcon_host"], server["rcon_password"], port=server["rcon_port"]) as rcon:
                for player in players:
                    response = rcon.command(f"playtime query {player['minecraft_username']}")
                    # Format: "X has played for Y days, Z hours, W minutes and V seconds"
                    days = re.search(r"(\d+) day", response)
                    hours = re.search(r"(\d+) hour", response)
                    minutes = re.search(r"(\d+) minute", response)
                    seconds = re.search(r"(\d+) second", response)

                    d = int(days.group(1)) if days else 0
                    h = int(hours.group(1)) if hours else 0
                    m = int(minutes.group(1)) if minutes else 0
                    s = int(seconds.group(1)) if seconds else 0

                    total = d * 86400 + h * 3600 + m * 60 + s
                    await conn.execute("""
                        INSERT INTO playtime (player_id, server_name, total_seconds)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (player_id, server_name) DO UPDATE SET total_seconds = $3, last_updated = NOW()
                    """, player["id"], server["name"], total)
            await conn.close()
        except Exception as e:
            print(f"❌ Sync playtime {server['name']}: {e}")

    async def sync_quests(self, server):
        try:
            async with aioftp.Client.context(
                server["ftp_host"],
                user=server["ftp_user"],
                password=server["ftp_password"]
            ) as ftp_client:
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
                        count = content.count("claimed: 1")
                        await conn.execute("""
                            INSERT INTO quest_progress (player_id, server_name, quests_completed)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (player_id, server_name) DO UPDATE SET quests_completed = $3, last_updated = NOW()
                        """, player["id"], server["name"], count)
                    except Exception:
                        pass

                await conn.close()
        except Exception as e:
            print(f"❌ Sync quests {server['name']}: {e}")

async def setup(bot):
    await bot.add_cog(Progression(bot))
