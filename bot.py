import os
import re
import sys
DEBUG = os.environ.get("DEBUG", "0") == "1"

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
from db import init_db, add_torrent, list_torrents, update_torrent_status, get_torrent, update_torrent_name, update_torrent_stats, remove_torrent
import transmission_rpc
import random
import tempfile
import math
import time

# Load config/token
TOKEN = os.environ.get("DISCORD_TOKEN")
TS_CONFIG = None
if not TOKEN:
    try:
        from config import CONFIG
        TOKEN = CONFIG.get("bot_token")
        TS_CONFIG = CONFIG.get("tsclient", {})
    except ImportError:
        raise RuntimeError("No Discord token found in environment or config.json!")

# Always prefer environment variables for Transmission config
TS_HOST = os.environ.get("TRANSMISSION_HOST")
TS_PORT = os.environ.get("TRANSMISSION_PORT")
TS_USER = os.environ.get("TRANSMISSION_USER")
TS_PASS = os.environ.get("TRANSMISSION_PASSWORD")
if TS_HOST and TS_PORT and TS_USER and TS_PASS:
    TS_CONFIG = {
        "host": TS_HOST,
        "port": int(TS_PORT),
        "user": TS_USER,
        "password": TS_PASS,
    }
elif TS_CONFIG is None:
    # Fallback to config.json if env vars not set
    try:
        from config import CONFIG
        TS_CONFIG = CONFIG.get("tsclient", {})
    except ImportError:
        raise RuntimeError("No Transmission config found in environment or config.json!")

GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
if GUILD_ID:
    GUILD_ID = int(GUILD_ID)

ADMIN_ROLE = os.environ.get("DISCORD_ADMIN_ROLE", "admin")

log_level = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("transmissionbot")

intents = discord.Intents.default()
intents.message_content = True  # Enable privileged intent (even if not needed for slash commands)
client = commands.Bot(command_prefix="!", intents=intents)

# Transmission RPC client
TSCLIENT = transmission_rpc.Client(
    host=TS_CONFIG["host"],
    port=TS_CONFIG["port"],
    username=TS_CONFIG["user"],
    password=TS_CONFIG["password"]
)

UNC_BASE = r"\\192.168.86.73\games"

# Name cleanup: set NAME_CLEANUP_REPLACE and NAME_CLEANUP_REMOVE as comma-separated pairs in env, e.g.
# NAME_CLEANUP_REPLACE='+: ,%20: ', NAME_CLEANUP_REMOVE='FitGirl,rutor.info'
def clean_torrent_name(name):
    replace = os.environ.get("NAME_CLEANUP_REPLACE", "+: ,%20: ")
    remove = os.environ.get("NAME_CLEANUP_REMOVE", "FitGirl,rutor.info")
    # Apply replacements
    for pair in replace.split(","):
        if ":" in pair:
            k, v = pair.split(":", 1)
            name = name.replace(k, v)
    # Remove substrings
    for word in remove.split(","):
        if word.strip():
            name = re.sub(re.escape(word.strip()), "", name, flags=re.IGNORECASE)
    # Collapse double spaces
    name = re.sub(r"\s+", " ", name).strip()
    return name

def is_admin(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    return any(role.name == ADMIN_ROLE for role in interaction.user.roles)

NOTIFY_MODE = os.environ.get("NOTIFY_MODE", "dm").lower()
NOTIFY_CHANNEL_ID = int(os.environ.get("NOTIFY_CHANNEL_ID", "0"))

# Legend for status and metrics
LEGEND = {
    'downloading': '🔻',
    'seeding': '🌱',
    'paused': '⏸',
    'verifying': '🔬',
    'queued': '🚧',
    'finished': '🏁',
    'any': '↕️',
    'download_rate': '⬇️',
    'upload_rate': '⬆️',
    'total_downloaded': '⏬',
    'total_uploaded': '⏫',
    'seed_ratio': '⚖️',
    'eta': '⏳',
    'pause': '⏸',
    'resume': '▶️',
    'remove': '❌',
    'remove_delete': '🗑',
    'verify': '🔬',
    'error': '‼️',
    'none': '✅',
    'tracker_warning': '⚠️',
    'tracker_error': '🌐',
    'local_error': '🖥',
    'stalled': '🐢',
    'active': '🐇',
    'running': '🚀',
    'private': '🔐',
    'public': '🔓',
}

# --- Robust DB Initialization and Cleanup ---
LEGACY_DBS = ["torrents.db"]
# Use the mounted file for the DB, new name for clean start
DB_PATH = "/app/transbotdata.db"

def robust_db_init():
    # Remove legacy DBs
    for db in LEGACY_DBS:
        if os.path.exists(db):
            try:
                os.remove(db)
                print(f"Removed legacy DB: {db}")
            except Exception as e:
                print(f"Failed to remove legacy DB {db}: {e}")
    # Ensure correct DB exists and schema is valid
    import aiosqlite
    import asyncio
    async def check_schema():
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("CREATE TABLE IF NOT EXISTS torrents (hash TEXT PRIMARY KEY, name TEXT NOT NULL, user_id INTEGER NOT NULL, status TEXT, added_at TEXT);")
                await db.commit()
                # Check schema
                cursor = await db.execute("PRAGMA table_info(torrents);")
                cols = await cursor.fetchall()
                if len(cols) < 5:
                    print("torrents table schema is invalid or missing columns!")
                    sys.exit(1)
        except Exception as e:
            print(f"Failed to initialize/check DB: {e}")
            sys.exit(1)
    asyncio.get_event_loop().run_until_complete(check_schema())
    print(f"Database {DB_PATH} initialized and checked.")
# --- End Robust DB Initialization ---

robust_db_init()

async def notify_completed_torrents():
    await client.wait_until_ready()
    notified = set()
    while not client.is_closed():
        try:
            torrents = await list_torrents()
            for t in torrents:
                if t["status"] != "finished":
                    try:
                        tor = TSCLIENT.get_torrent(t["hash"])
                        db_torrent = await get_torrent(t["hash"])
                        if not db_torrent or "user_id" not in db_torrent:
                            logger.error(f"No user_id found for torrent {t['hash']}")
                            continue
                        # Update name in DB if it has changed (magnet got real name)
                        if tor.name and db_torrent["name"] != tor.name:
                            await update_torrent_name(t["hash"], tor.name)
                        if tor.status == "seeding" and t["hash"] not in notified:
                            user_id = db_torrent["user_id"]
                            # Use configurable UNC base if available
                            unc_base = os.environ.get("UNC_BASE", UNC_BASE)
                            unc_path = f"{unc_base}\\{clean_torrent_name(tor.name)}"
                            msg = f"✅ <@{user_id}> Your download is complete and available at: `{unc_path}`"
                            
                            # Send notification based on mode
                            if NOTIFY_MODE == "channel" and NOTIFY_CHANNEL_ID:
                                try:
                                    channel = client.get_channel(int(NOTIFY_CHANNEL_ID))
                                    if channel:
                                        await channel.send(msg)
                                    else:
                                        logger.error(f"Could not find notification channel with ID {NOTIFY_CHANNEL_ID}")
                                except ValueError:
                                    logger.error(f"Invalid notification channel ID: {NOTIFY_CHANNEL_ID}")
                                except Exception as channel_err:
                                    logger.error(f"Error sending channel notification: {channel_err}")
                            else:
                                try:
                                    user = await client.fetch_user(user_id)
                                    await user.send(msg)
                                except discord.errors.NotFound:
                                    logger.error(f"User with ID {user_id} not found for notification")
                                except Exception as dm_err:
                                    logger.error(f"Error sending DM notification: {dm_err}")
                            
                            notified.add(t["hash"])
                            await update_torrent_status(t["hash"], "finished")
                    except transmission_rpc.error.TransmissionError as te:
                        logger.error(f"Transmission error for torrent {t['hash']}: {te}")
                    except Exception as e:
                        logger.error(f"Error checking torrent {t['hash']}: {e}")
        except Exception as main_error:
            logger.error(f"Critical error in notification loop: {main_error}")
        
        await asyncio.sleep(60)

async def periodic_stats_refresh():
    await client.wait_until_ready()
    import time
    while not client.is_closed():
        try:
            torrents = await list_torrents()
            for t in torrents:
                try:
                    tor = TSCLIENT.get_torrent(t["hash"])
                    stats = {
                        'total_size': getattr(tor, 'total_size', 0),
                        'downloaded_ever': getattr(tor, 'downloaded_ever', 0),
                        'uploaded_ever': getattr(tor, 'uploaded_ever', 0),
                        'rate_download': getattr(tor, 'rate_download', 0),
                        'rate_upload': getattr(tor, 'rate_upload', 0),
                        'upload_ratio': getattr(tor, 'upload_ratio', 0.0),
                    }
                    await update_torrent_stats(t["hash"], stats)
                    await update_torrent_status(t["hash"], tor.status)
                except Exception as e:
                    logger.error(f"Error updating stats for {t['hash']}: {e}")
            logger.info("Periodic stats refresh complete.")
        except Exception as e:
            logger.error(f"Error in periodic stats refresh: {e}")
        await asyncio.sleep(300)  # 5 minutes

@client.event
async def on_ready():
    logger.info(f"Bot connected as {client.user}")
    await init_db()
    try:
        if GUILD_ID:
            synced = await client.tree.sync(guild=discord.Object(id=GUILD_ID))
        else:
            synced = await client.tree.sync()
        logger.info(f"Synced {len(synced)} commands.")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    client.loop.create_task(notify_completed_torrents())
    client.loop.create_task(periodic_stats_refresh())

@client.tree.command(name="help", description="Show help for TransmissionBot")
async def help_cmd(interaction: discord.Interaction):
    help_text = (
        "**TransmissionBot Slash Commands**\n"
        "/help - Show this help message\n"
        "/info - Show bot/system info (admin only)\n"
        "/add - Add a torrent (magnet or file)\n"
        "/list - List your torrents\n"
        "/summary - Show a summary of your torrents\n"
        "/pause - Pause a torrent by name or hash (with autocomplete)\n"
        "/resume - Resume a torrent by name or hash (with autocomplete)\n"
        "/remove - Remove a torrent by name or hash (autocomplete, optional delete_data to also delete files)\n"
        "/legend - Show the meaning of status/metrics emojis\n"
        "\nYou can use torrent names or hashes for /pause, /resume, and /remove. Autocomplete is available for these commands!\n"
        "For /remove, set delete_data=True to also delete downloaded files."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

@client.tree.command(name="info", description="Show bot/system info (admin only)")
async def info_cmd(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    info_text = f"Bot user: {client.user}\nGuild: {interaction.guild.name if interaction.guild else 'DM'}"
    await interaction.response.send_message(info_text, ephemeral=True)

@client.tree.command(name="add", description="Add a torrent (magnet or file)")
@app_commands.describe(magnet="Magnet link for the torrent", file="Upload a .torrent file")
async def add_cmd(interaction: discord.Interaction, magnet: str = None, file: discord.Attachment = None):
    if DEBUG:
        logger.debug(f"/add called by {interaction.user} (id={interaction.user.id}) with magnet={magnet} file={file}")
    await interaction.response.defer(ephemeral=True)
    if not magnet and not file:
        await interaction.followup.send("Please provide a magnet link or upload a .torrent file.", ephemeral=True)
        return
    download_dir = "/data/games"
    if DEBUG:
        logger.debug(f"Setting download_dir to {download_dir}")
    try:
        if file:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                await file.save(tmp.name)
                if DEBUG:
                    logger.debug(f"Saved uploaded file to {tmp.name}")
                with open(tmp.name, 'rb') as f:
                    tor = TSCLIENT.add_torrent(torrent=f, download_dir=download_dir)
                    if DEBUG:
                        logger.debug(f"add_torrent(torrent=f, download_dir=...) returned: {tor}")
                os.unlink(tmp.name)
                if DEBUG:
                    logger.debug(f"Deleted temp file {tmp.name}")
        else:
            if DEBUG:
                logger.debug(f"Adding magnet: {magnet}")
            tor = TSCLIENT.add_torrent(magnet, download_dir=download_dir)
            if DEBUG:
                logger.debug(f"add_torrent(magnet, download_dir=...) returned: {tor}")
        real_hash = tor.hashString
        real_name = tor.name
        if DEBUG:
            logger.debug(f"Torrent added: hash={real_hash}, name={real_name}")
        await add_torrent(real_hash, real_name, interaction.user.id)
        await interaction.followup.send(f"Added torrent: **{clean_torrent_name(real_name)}** (`{real_hash[:6]}`)", ephemeral=True)
    except Exception as e:
        logger.error(f"Error adding torrent: {e}")
        await interaction.followup.send(f"Failed to add torrent: {e}", ephemeral=True)

def progress_bar(pct):
    blocks = 10
    filled = int(pct * blocks)
    bar = '█' * filled + '░' * (blocks - filled)
    if pct >= 0.8:
        color = ''  # green (use bold)
    elif pct >= 0.4:
        color = ''  # yellow (use italics)
    else:
        color = ''  # red (use underline)
    return f"{bar} {int(pct*100)}%"

@client.tree.command(name="list", description="List your torrents")
async def list_cmd(interaction: discord.Interaction):
    # Admins see all torrents, users see only their own
    if is_admin(interaction):
        torrents = await list_torrents()
    else:
        torrents = await list_torrents(user_id=interaction.user.id)
    if not torrents:
        await interaction.response.send_message("You have no torrents.", ephemeral=True)
        return
    lines = []
    for t in torrents:
        try:
            tor = TSCLIENT.get_torrent(t["hash"])
            # Update DB with latest stats
            stats = {
                'total_size': getattr(tor, 'total_size', 0),
                'downloaded_ever': getattr(tor, 'downloaded_ever', 0),
                'uploaded_ever': getattr(tor, 'uploaded_ever', 0),
                'rate_download': getattr(tor, 'rate_download', 0),
                'rate_upload': getattr(tor, 'rate_upload', 0),
                'upload_ratio': getattr(tor, 'upload_ratio', 0.0),
            }
            await update_torrent_stats(t["hash"], stats)
            await update_torrent_status(t["hash"], tor.status)
            status = tor.status
            status_emoji = LEGEND.get(str(status).lower(), f"[{status}]")
            pct = tor.progress / 100.0
            eta = tor.eta
            bar = progress_bar(pct)
        except Exception as e:
            status = t["status"]
            status_emoji = LEGEND.get(str(status).lower(), f"[{status}]")
            bar = "?"
            eta = "--"
        lines.append(f"`{t['hash'][:6]}` {clean_torrent_name(t['name'])} {status_emoji} {bar} ETA: {eta}")
    msg = "**Your Torrents:**\n" + "\n".join(lines)
    await interaction.response.send_message(msg, ephemeral=True)

@client.tree.command(name="summary", description="Show a summary of your torrents")
async def summary_cmd(interaction: discord.Interaction):
    # Admins see all torrents, users see only their own
    if is_admin(interaction):
        torrents = await list_torrents()
    else:
        torrents = await list_torrents(user_id=interaction.user.id)
    if not torrents:
        await interaction.response.send_message("You have no torrents.", ephemeral=True)
        return
    total = len(torrents)
    completed = 0
    in_progress = 0
    total_size = 0
    total_downloaded = 0
    total_uploaded = 0
    total_rate_download = 0
    total_rate_upload = 0
    total_seed_ratio = 0
    seed_ratio_count = 0
    for t in torrents:
        # Use only DB values, do not query Transmission
        pct = 1.0 if t.get('status', '').lower() in ('seeding', 'finished', 'stopped') or t.get('downloaded_ever', 0) >= t.get('total_size', 0) > 0 else 0.0
        if pct >= 1.0:
            completed += 1
        else:
            in_progress += 1
        total_size += t.get('total_size', 0)
        total_downloaded += t.get('downloaded_ever', 0)
        total_uploaded += t.get('uploaded_ever', 0)
        total_rate_download += t.get('rate_download', 0)
        total_rate_upload += t.get('rate_upload', 0)
        if t.get('upload_ratio') is not None:
            total_seed_ratio += t.get('upload_ratio', 0.0)
            seed_ratio_count += 1
    percent = completed / total if total else 0
    avg_seed_ratio = (total_seed_ratio / seed_ratio_count) if seed_ratio_count else 0
    def fmt_bytes(num):
        for unit in ['B','KB','MB','GB','TB']:
            if abs(num) < 1024.0:
                return f"{num:3.2f} {unit}"
            num /= 1024.0
        return f"{num:.2f} PB"
    msg = (
        f"**Summary:**\n"
        f"Total torrents: {total}\n"
        f"Completed: {completed}\n"
        f"In progress: {in_progress}\n"
        f"Completion: {int(percent*100)}%\n"
        f"Total size: {fmt_bytes(total_size)}\n"
        f"Total downloaded: {fmt_bytes(total_downloaded)}\n"
        f"Total uploaded: {fmt_bytes(total_uploaded)}\n"
        f"Current download speed: {fmt_bytes(total_rate_download)}/s\n"
        f"Current upload speed: {fmt_bytes(total_rate_upload)}/s\n"
        f"Average seed ratio: {avg_seed_ratio:.2f}"
    )
    await interaction.response.send_message(msg, ephemeral=True)

async def torrent_name_autocomplete(interaction: discord.Interaction, current: str):
    # Admins see all, users see only their own
    if is_admin(interaction):
        torrents = await list_torrents()
    else:
        torrents = await list_torrents(user_id=interaction.user.id)
    # Filter by name
    options = []
    for t in torrents:
        name = clean_torrent_name(t['name'])
        if current.lower() in name.lower():
            # Discord autocomplete: value (hash), name (display)
            options.append(app_commands.Choice(name=f"{name} [{t['hash'][:6]}]", value=t['hash']))
        if len(options) >= 25:
            break
    return options

@client.tree.command(name="pause", description="Pause a torrent by name or hash (autocomplete supported)")
@app_commands.autocomplete(hash=torrent_name_autocomplete)
async def pause_cmd(interaction: discord.Interaction, hash: str):
    try:
        tor = TSCLIENT.get_torrent(hash)
        active_statuses = ["downloading", "seeding", "verifying", "queued"]
        if str(tor.status).lower() not in active_statuses:
            await interaction.response.send_message(f"Torrent **{clean_torrent_name(tor.name)}** (`{hash[:6]}`) is not active (status: {tor.status}). Cannot pause.", ephemeral=True)
            return
        TSCLIENT.stop_torrent(hash)
        await update_torrent_status(hash, 'paused')
        await interaction.response.send_message(f"Paused torrent: **{clean_torrent_name(tor.name)}** (`{hash[:6]}`)", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to pause: {e}", ephemeral=True)

@client.tree.command(name="resume", description="Resume a torrent by name or hash (autocomplete supported)")
@app_commands.autocomplete(hash=torrent_name_autocomplete)
async def resume_cmd(interaction: discord.Interaction, hash: str):
    try:
        tor = TSCLIENT.get_torrent(hash)
        inactive_statuses = ["stopped", "paused", "finished"]
        if str(tor.status).lower() not in inactive_statuses:
            await interaction.response.send_message(f"Torrent **{clean_torrent_name(tor.name)}** (`{hash[:6]}`) is already active (status: {tor.status}). Cannot resume.", ephemeral=True)
            return
        TSCLIENT.start_torrent(hash)
        await update_torrent_status(hash, 'downloading')
        await interaction.response.send_message(f"Resumed torrent: **{clean_torrent_name(tor.name)}** (`{hash[:6]}`)", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to resume: {e}", ephemeral=True)

@client.tree.command(name="remove", description="Remove a torrent by name or hash (autocomplete supported)")
@app_commands.describe(delete_data="Also delete downloaded files (default: False)")
@app_commands.autocomplete(hash=torrent_name_autocomplete)
async def remove_cmd(interaction: discord.Interaction, hash: str, delete_data: bool = False):
    try:
        # Check if torrent exists
        tor = TSCLIENT.get_torrent(hash)
        TSCLIENT.remove_torrent(hash, delete_data=delete_data)
        await remove_torrent(hash)
        name = clean_torrent_name(tor.name)
        msg = f"Removed torrent: **{name}** (`{hash[:6]}`)"
        if delete_data:
            msg += " and deleted downloaded files."
        await interaction.response.send_message(msg, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to remove: {e}", ephemeral=True)

@client.tree.command(name="legend", description="Show the meaning of status/metrics emojis")
async def legend_cmd(interaction: discord.Interaction):
    legend_text = (
        "**Legend**\n"
        "Status 🔍\n"
        "🔻—downloading\n"
        "🌱—seeding\n"
        "⏸—paused\n"
        "🔬—verifying\n"
        "🚧—queued\n"
        "🏁—finished\n"
        "\nMetrics 📊\n"
        "⬇️—download rate\n"
        "⬆️—upload rate\n"
        "⏬—total downloaded\n"
        "⏫—total uploaded\n"
        "⚖️—seed ratio\n"
        "⏳—ETA\n"
        "\nModifications 🧰\n"
        "⏸—pause\n"
        "▶️—resume\n"
        "❌—remove\n"
        "🗑—remove and delete\n"
        "\nError ‼️\n"
        "✅—none\n"
        "⚠️—tracker warning\n"
        "🌐—tracker error\n"
        "🖥—local error\n"
    )
    await interaction.response.send_message(legend_text, ephemeral=True)

if __name__ == "__main__":
    client.run(TOKEN)
