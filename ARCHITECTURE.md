# TransmissionBot-NG Architecture Overview

## Overview
TransmissionBot-NG is a modern, privacy-first Discord bot for managing a Transmission BitTorrent client. It is built from the ground up for Discord's slash command API, robust Docker deployment, and persistent state using SQLite.

---

## Key Technologies
- **discord.py 2.x+**: Modern Discord API with full slash command support
- **Slash Commands Only**: All user interaction is via Discord's slash commands (no prefix commands)
- **SQLite + aiosqlite**: All state (torrents, users, stats) is stored persistently in SQLite
- **Docker-Only Deployment**: The bot is designed to run as a container, with healthchecks and easy configuration

---

## Privacy & Permissions
- **Privacy by Default**: Regular users only see/manage their own torrents; admins can see all
- **Role-Based Permissions**: Admins are determined by Discord role (default: `admin`)
- **No Whitelists**: All access is role-based, not by user ID

---

## Command Model
- **/add**: Add a torrent (magnet or file)
- **/list**: List your torrents (admins see all)
- **/summary**: Aggregate stats for your torrents (from DB, not live Transmission)
- **/pause, /resume, /remove**: Manage torrents by name/hash (with autocomplete)
- **/legend**: Show emoji legend for statuses/metrics
- **/help**: Show help
- **/info**: System info (admin only)

All commands use ephemeral responses for privacy.

---

## State & Data Handling
- **Persistent State**: All torrent/user/status data is stored in SQLite, not in-memory or JSON
- **Stats Refresh**: Periodic background task updates stats in the DB from Transmission
- **Notifications**: In-channel or ephemeral notifications for completed downloads

---

## Deployment & Setup
- **Docker-Only**: All deployment is via Docker Compose, with persistent DB volume
- **Config via Env Vars**: All settings (Discord token, Transmission credentials, admin role, etc.) are set via environment variables
- **Healthchecks**: Docker healthcheck ensures the bot is running

---

## Design Decisions
- **No DMs**: All notifications are in-channel or ephemeral
- **No Legacy Features**: No prefix commands, no reaction controls, no web UI
- **Single Transmission Instance**: One Transmission per Discord server (no multi-server support)

---

## Extensibility
- The codebase is structured for easy addition of new slash commands, autocomplete, and future enhancements.

---

For more details, see the README and CHANGELOG. 