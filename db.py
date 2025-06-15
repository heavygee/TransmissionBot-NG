import aiosqlite
import asyncio
from typing import List, Optional
import datetime

# Use the same DB path as in bot.py, now as a file mount with new name
DB_PATH = "/app/transbotdata.db"

CREATE_TORRENTS_TABLE = """
CREATE TABLE IF NOT EXISTS torrents (
    hash TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT,
    added_at TEXT,
    total_size INTEGER DEFAULT 0,
    downloaded_ever INTEGER DEFAULT 0,
    uploaded_ever INTEGER DEFAULT 0,
    rate_download INTEGER DEFAULT 0,
    rate_upload INTEGER DEFAULT 0,
    upload_ratio REAL DEFAULT 0.0
);
"""

# Health check to ensure DB and schema are correct
async def health_check_db():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(CREATE_TORRENTS_TABLE)
            await db.commit()
            cursor = await db.execute("PRAGMA table_info(torrents);")
            cols = await cursor.fetchall()
            if len(cols) < 5:
                raise RuntimeError("torrents table schema is invalid or missing columns!")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize/check DB: {e}")

# Run health check at import time
asyncio.get_event_loop().run_until_complete(health_check_db())

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TORRENTS_TABLE)
        await db.commit()

async def add_torrent(hash: str, name: str, user_id: int, status: str = "added", stats: dict = None):
    stats = stats or {}
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO torrents (hash, name, user_id, status, added_at, total_size, downloaded_ever, uploaded_ever, rate_download, rate_upload, upload_ratio) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                hash, name, user_id, status, datetime.datetime.utcnow().isoformat(),
                stats.get('total_size', 0),
                stats.get('downloaded_ever', 0),
                stats.get('uploaded_ever', 0),
                stats.get('rate_download', 0),
                stats.get('rate_upload', 0),
                stats.get('upload_ratio', 0.0)
            )
        )
        await db.commit()

async def list_torrents(user_id: Optional[int] = None) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            cursor = await db.execute("SELECT hash, name, status, added_at FROM torrents WHERE user_id = ?", (user_id,))
        else:
            cursor = await db.execute("SELECT hash, name, status, added_at FROM torrents", ())
        rows = await cursor.fetchall()
        return [
            {"hash": row[0], "name": row[1], "status": row[2], "added_at": row[3]} for row in rows
        ]

async def get_torrent(hash: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT hash, name, user_id, status, added_at FROM torrents WHERE hash = ?", (hash,))
        row = await cursor.fetchone()
        if row:
            return {"hash": row[0], "name": row[1], "user_id": row[2], "status": row[3], "added_at": row[4]}
        return None

async def update_torrent_status(hash: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE torrents SET status = ? WHERE hash = ?", (status, hash))
        await db.commit()

async def remove_torrent(hash: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM torrents WHERE hash = ?", (hash,))
        await db.commit()

async def update_torrent_name(hash: str, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE torrents SET name = ? WHERE hash = ?", (name, hash))
        await db.commit()

async def update_torrent_stats(hash: str, stats: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE torrents SET total_size=?, downloaded_ever=?, uploaded_ever=?, rate_download=?, rate_upload=?, upload_ratio=? WHERE hash=?",
            (
                stats.get('total_size', 0),
                stats.get('downloaded_ever', 0),
                stats.get('uploaded_ever', 0),
                stats.get('rate_download', 0),
                stats.get('rate_upload', 0),
                stats.get('upload_ratio', 0.0),
                hash
            )
        )
        await db.commit() 