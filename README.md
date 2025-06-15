# TransmissionBot-NG (Next Generation)

A modern, self-hosted Python [Discord.py](https://github.com/Rapptz/discord.py) bot for controlling a [Transmission](https://transmissionbt.com) BitTorrent client from a **private** Discord server, using Discord's slash commands and a privacy-first, Docker-only architecture.

---

## Project Relationship & Credits

**TransmissionBot-NG** is a next-generation rewrite, inspired by the original [TransmissionBot](https://github.com/twilsonco/TransmissionBot) by Tim Wilson and contributors. This project was started fresh to take advantage of Discord's modern slash command API, async/await patterns, and robust Docker deployment. While some utility ideas and patterns are inspired by the original, nearly all code and architecture have been rewritten for clarity, maintainability, and modern best practices.

**Credits:**
- Original inspiration: [TransmissionBot](https://github.com/twilsonco/TransmissionBot) by Tim Wilson
- Thanks to: Rapptz, kkrypt0nn, leighmacdonald, and the Discord.py community

---

## Major Features
- **Slash Commands Only:** All bot interaction is via Discord's modern slash commands (e.g. `/add`, `/list`, `/pause`).
- **Privacy by Default:** Regular users only see/manage their own torrents; admins can see all.
- **Autocomplete:** Pause, resume, and remove commands support autocomplete for torrent names/hashes.
- **Ephemeral Responses:** All command responses are private to the user.
- **Modern Discord API:** Built for Discord.py 2.x+ with explicit intents and up-to-date API usage.
- **SQLite State:** All state is stored in SQLite (via `aiosqlite`), not in-memory or JSON.
- **Docker-Only Deployment:** Designed to run as a container, with healthchecks and easy configuration.
- **Configurable Name Cleanup:** Environment variables allow for custom torrent name display.

---

## Installation Guide

### Prerequisites
1. A Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
2. A running Transmission instance with RPC access enabled
3. Docker and Docker Compose installed on your system

### Step 1: Create Your Discord Bot
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent
5. Save changes
6. Click "Reset Token" and copy your bot token

### Step 2: Configure the Bot
1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/TransmissionBot-NG.git
   cd TransmissionBot-NG
   ```

2. Create your docker-compose.yml file (using the example as a template):
   ```bash
   cp docker-compose.example.yml docker-compose.yml
   ```

3. Edit docker-compose.yml with your settings:
   - Add your Discord bot token
   - Configure your Transmission connection details
   - Adjust other settings as needed

### Step 3: Run the Bot
```bash
docker compose up -d
```

### Step 4: Invite the Bot to Your Server
1. Go back to the Discord Developer Portal
2. Go to "OAuth2" > "URL Generator"
3. Check the scopes "bot" and "applications.commands"
4. In bot permissions, select:
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Use Slash Commands
5. Copy the generated URL and open it in your browser
6. Select your server and authorize the bot

### Step 5: Set Up Admin Role
1. Create a role called `admin` in your Discord server
2. Assign this role to users who should have full torrent management capabilities
3. If you want to use a different role name, set the `DISCORD_ADMIN_ROLE` environment variable

---

## First-Time Setup

If this is your first time running the bot, you must create the database file before starting Docker Compose. Run:

```bash
cp transbotdata.db.empty transbotdata.db
```

This ensures the database file exists and can be mounted by Docker. If you skip this step, Docker may create a zero-byte file, which can cause errors.

---

## Available Commands

### `/add`
Add a new torrent to Transmission
- **Options:**
  - `magnet`: A magnet link to add
  - `file`: Upload a .torrent file to add
- **Notes:**
  - At least one of magnet or file must be provided
  - Response is ephemeral (only visible to you)

### `/list`
List your torrents (admins can see all torrents)
- **Notes:**
  - Regular users can only see their own torrents
  - Admins can see all torrents in the system
  - Shows status, progress, and other details

### `/summary`
Show a summary of your torrents (admins can see all torrents)
- **Notes:**
  - Shows overall download/upload statistics
  - Groups torrents by status
  - Shows total count of torrents

### `/pause`
Pause a torrent
- **Options:**
  - `hash`: Select a torrent to pause (autocomplete enabled)
- **Notes:**
  - Regular users can only pause their own torrents
  - Admins can pause any torrent

### `/resume`
Resume a paused torrent
- **Options:**
  - `hash`: Select a torrent to resume (autocomplete enabled)
- **Notes:**
  - Regular users can only resume their own torrents
  - Admins can resume any torrent

### `/remove`
Remove a torrent
- **Options:**
  - `hash`: Select a torrent to remove (autocomplete enabled)
  - `delete_data`: Whether to also delete downloaded files (default: False)
- **Notes:**
  - Regular users can only remove their own torrents
  - Admins can remove any torrent

### `/legend`
Show a legend explaining the meaning of status emojis
- **Notes:**
  - Explains what each emoji in the status and metrics represents

### `/help`
Show help information about available commands

### `/info` (admin only)
Show system information about the bot and Transmission

---

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DISCORD_TOKEN` | Your Discord bot token | None | Yes |
| `TRANSMISSION_HOST` | Transmission RPC host | None | Yes |
| `TRANSMISSION_PORT` | Transmission RPC port | None | Yes |
| `TRANSMISSION_USER` | Transmission RPC username | None | Yes |
| `TRANSMISSION_PASSWORD` | Transmission RPC password | None | Yes |
| `DEBUG` | Enable debug logging | `0` | No |
| `DISCORD_ADMIN_ROLE` | Role name for admin privileges | `admin` | No |
| `DISCORD_GUILD_ID` | Specific Discord server ID | None | No |
| `NAME_CLEANUP_REPLACE` | Comma-separated pairs for search/replace in torrent names | `+: ,%20: ` | No |
| `NAME_CLEANUP_REMOVE` | Comma-separated strings to remove from torrent names | `FitGirl,rutor.info` | No |
| `NOTIFY_MODE` | Notification mode (`dm` or `channel`) | `dm` | No |
| `NOTIFY_CHANNEL_ID` | Channel ID for notifications when using `channel` mode | None | No |
| `UNC_BASE` | UNC path base for completed download notifications | Varies | No |

---

## Example Docker Compose
See `docker-compose.example.yml` for a full template.

---

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

---

## Troubleshooting

### "Bot doesn't respond to commands"
1. Make sure your bot has the correct permissions
2. Verify you invited the bot with the "applications.commands" scope
3. Discord can take up to an hour to register slash commands; wait and try again

### "Cannot connect to Transmission"
1. Check your Transmission RPC settings are correct
2. Make sure Transmission is running and accessible from the Docker container
3. Verify the RPC whitelist in Transmission allows connections from your bot

### "Only see Command Not Found errors"
- Discord may be taking time to register slash commands. Wait up to an hour and try again.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

For questions, issues, or to contribute, please open an issue or pull request on this repository.
