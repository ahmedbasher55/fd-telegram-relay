# Telegram ↔ Claude relay

Personal relay: every 5 minutes GitHub Actions checks one private Telegram bot (locked to its owner's chat ID).
When there is a message it runs Claude Code with the owner's own subscription on his private project repo and
replies on Telegram. No secrets are in this repo; they live in encrypted Actions secrets. Logs print no content.
