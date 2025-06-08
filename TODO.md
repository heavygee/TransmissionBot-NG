# TODO: Refactor TransmissionBot for Modern Discord API and Slash Commands

## Goal
Migrate TransmissionBot from classic prefix-based commands (discord.py 1.x) to a modern, maintained Discord library (discord.py 2.x+, py-cord, nextcord, or similar) and implement Discord slash commands (interactions API).

---

## Migration Plan

### 1. Library Upgrade
- [ ] Evaluate and select a maintained Discord library:
  - [discord.py 2.x+](https://github.com/Rapptz/discord.py) (now supports slash commands)
  - [py-cord](https://github.com/Pycord-Development/pycord)
  - [nextcord](https://github.com/nextcord/nextcord)
  - [discord-py-interactions](https://github.com/goverfl0w/discord-interactions)
- [ ] Update requirements.txt and Dockerfile for the new library.
- [ ] Update all imports and bot initialization as needed.

### 2. Slash Command Migration
- [ ] Replace all classic command decorators (e.g., `@client.command`) with slash command equivalents.
- [ ] Register slash commands with Discord (using decorators or explicit registration).
- [ ] Update command logic to use interaction objects (responding with `interaction.response.send_message`, etc.).
- [ ] Update help and documentation to reflect new usage (`/command` instead of `t/command`).

### 3. Permissions and Intents
- [ ] Review and update required intents for the new library version.
- [ ] Ensure all necessary intents are enabled in the Discord Developer Portal.
- [ ] Update README and config documentation.

### 4. Testing and Validation
- [ ] Test all commands in a private Discord server.
- [ ] Validate that only authorized users can see/manage their torrents.
- [ ] Ensure admin/owner overrides still work.
- [ ] Test notification and DM features.

### 5. Optional Enhancements
- [ ] Add autocomplete for slash command options (e.g., torrent names, filters).
- [ ] Add ephemeral responses for privacy (where appropriate).
- [ ] Consider adding a web dashboard or webhook integration.

---

## Migration Notes
- Slash commands require registration with Discord and may take up to an hour to propagate.
- Some features (like reactions) may need to be rethought or replaced with buttons/selects.
- The bot will need the "applications.commands" OAuth2 scope and appropriate permissions.
- Message content intent is not required for slash commands, but may be needed for legacy support.

---

## References
- [discord.py Slash Commands Guide](https://discordpy.readthedocs.io/en/stable/interactions/api.html)
- [Discord Developer Portal](https://discord.com/developers/applications)
- [Discord API Changelog](https://discord.com/developers/docs/change-log) 