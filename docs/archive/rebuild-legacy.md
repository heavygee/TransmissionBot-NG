# TransmissionBot Rebuild Plan (Slash Command Refactor)

## Overview
This document outlines the comprehensive plan for refactoring TransmissionBot to use modern Discord API features, slash commands, role-based permissions, and SQLite for state. The focus is on getting a working MVP before full feature completion.

---

## 1. Goals & Principles
- Migrate to `discord.py 2.x+` (or maintained fork) for slash command support.
- Use **slash commands only** (no prefix commands).
- Enforce permissions via Discord roles (no whitelists).
- Store all state (torrents, users, etc.) in SQLite (async via `aiosqlite`).
- All notifications are ephemeral/in-channel (no DMs).
- Docker is the only supported deployment method.
- Get a minimal working bot before full feature parity.

---

## 2. Command Inventory & Permissions

| Command         | Description                        | Args/Options         | User Role | Admin Role | Notes                        |
|-----------------|------------------------------------|----------------------|:---------:|:----------:|------------------------------|
| /list           | List torrents                      | filters, search      | ✅        | ✅         | Admin sees all, user sees own|
| /summary        | Torrent summary (aggregate only)   | filters              | ✅        | ✅         | Shows only aggregate info (counts, totals, rates, etc.) about torrents visible to the user. Does NOT list individual torrents. |
| /add            | Add torrent (magnet/file)          | magnet/file          | ✅        | ✅         | File upload supported        |
| /pause          | Pause torrent(s)                   | torrent id(s)        | ✅        | ✅         | User: own torrents only      |
| /resume         | Resume torrent(s)                  | torrent id(s)        | ✅        | ✅         | User: own torrents only      |
| /remove         | Remove torrent(s)                  | torrent id(s)        | ✅        | ✅         | User: own torrents only      |
| /legend         | Show legend for torrent states      |                      | ✅        | ✅         |                              |
| /compact        | Toggle compact output              |                      | ✅        | ✅         |                              |
| /help           | Show help                          |                      | ✅        | ✅         |                              |
| /info           | Bot/system info                    |                      | ❌        | ✅         | Admin only                   |
| /notifications  | Toggle notifications               | on/off               | ✅        | ✅         | Ephemeral only               |

- **Role enforcement:** Use Discord role checks for admin/user commands.
- **No whitelists:** All access is role-based.

---

## 3. State & Data Handling
- Replace all in-memory and JSON state with SQLite (via `aiosqlite`).
- Store: torrent hash, user ID, status, timestamps, etc.
- Migrate any needed data from old JSON on first run.

---

## 4. Notifications
- All notifications are ephemeral and in-channel.
- Use Discord ephemeral message support for slash commands.

---

## 5. Deployment & OAuth
- Docker-only deployment (update Dockerfile/compose for new deps).
- Ensure bot has `applications.commands` scope and permissions:
  - Send Messages, Read Message History, Attach Files, Use Slash Commands
  - (Optional) Manage Messages for admin features
- Message Content Intent is NOT required for slash commands.

---

## 6. Testing & Rollback
- Use a private Discord server for development/testing.
- Add basic unit tests for DB and command logic.
- Manual integration testing for Discord interactions.
- Keep legacy branch as fallback.

---

## 7. Order of Work (MVP First)

1. **Library Upgrade**
   - Update `requirements.txt` and `Dockerfile` for `discord.py 2.x+` and `aiosqlite`.
   - Remove old/unused dependencies.

2. **Bot Skeleton**
   - Set up a minimal bot with `/help` and `/info` as slash commands.
   - Implement role-based permission checks.
   - Confirm bot can connect and respond in Discord.

3. **State Migration**
   - Scaffold SQLite DB and models for torrent/user state.
   - Implement basic add/list functionality using DB.
   - Migrate any needed data from JSON.

4. **Core Command Migration**
   - Re-implement `/add`, `/list`, `/summary`, `/pause`, `/resume`, `/remove` as slash commands.
   - Enforce role-based permissions and user scoping.
   - Use ephemeral responses for all output.

5. **Notification Refactor**
   - Switch all notifications to ephemeral/in-channel.
   - Remove DM and persistent notification logic.

6. **Testing**
   - Test all commands and flows in a private server.
   - Add/expand unit tests as needed.

7. **Documentation**
   - Update README, help, and usage docs for new system.
   - Document Docker-only deployment and Discord app setup.

8. **Feature Parity & Enhancements**
   - Add autocomplete for slash command options (torrent names, filters).
   - Add ephemeral responses for privacy (where appropriate).
   - Consider web dashboard or webhook integration (optional).

9. **Release**
   - Merge to main, tag release, and update Docker Hub (if used).

---

## 8. Migration Notes
- Slash commands require registration with Discord and may take up to an hour to propagate.
- Some features (like reactions) may need to be rethought or replaced with buttons/selects.
- The bot will need the "applications.commands" OAuth2 scope and appropriate permissions.
- Message content intent is not required for slash commands, but may be needed for legacy support.

---

## References
- [discord.py Slash Commands Guide](https://discordpy.readthedocs.io/en/stable/interactions/api.html)
- [Discord Developer Portal](https://discord.com/developers/applications) 