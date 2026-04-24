import asyncpg
import os

async def get_db():
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

async def init_db():
    conn = await get_db()
    try:
        # Table joueurs
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY,
                discord_id TEXT UNIQUE NOT NULL,
                minecraft_username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table progression quêtes
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS quest_progress (
                id SERIAL PRIMARY KEY,
                player_id INTEGER REFERENCES players(id),
                server_name TEXT NOT NULL,
                quests_completed INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(player_id, server_name)
            )
        """)

        # Table playtime
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS playtime (
                id SERIAL PRIMARY KEY,
                player_id INTEGER REFERENCES players(id),
                server_name TEXT NOT NULL,
                total_seconds INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(player_id, server_name)
            )
        """)

        # Table versions modpacks (pour suivi updates)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS modpack_versions (
                id SERIAL PRIMARY KEY,
                server_name TEXT UNIQUE NOT NULL,
                curseforge_id TEXT NOT NULL,
                last_version TEXT,
                last_checked TIMESTAMP DEFAULT NOW()
            )
        """)

        print("✅ Base de données initialisée")
    finally:
        await conn.close()
