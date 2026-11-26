# MASTI MAZAK Promotion Bot

A Discord bot with a one-time welcome DM, opt-in promotion updates, and an owner/admin command for opted-in broadcasts.

## Render Web Service

- Build command: `pip install -r requirements.txt`
- Start command: `python bot.py`

### Environment variables

| Key | Value |
|---|---|
| DISCORD_TOKEN | Your Discord bot token (keep it secret) |
| OWNER_ID | Your numeric Discord user ID |
| SERVER_INVITE | https://discord.gg/UFvjK5Uy5e |
| DB_PATH | Optional; defaults to subscriptions.sqlite3 |

Render provides PORT automatically.

## Discord setup

1. Enable Server Members Intent in the Discord Developer Portal.
2. Invite the bot with the bot and applications.commands scopes.
3. Give it permission to view the server and send messages/DMs.
4. Members use /subscribe to opt in and /unsubscribe to opt out.
5. Use /dmall confirm:true to send only to members who opted in.

New members receive one welcome DM explaining the server and how to opt in. Joining does not subscribe them automatically. The bot does not scrape members or send unsolicited broadcast DMs.

## Storage note

SQLite is local. Render's filesystem can be reset on redeploy/restart unless a persistent disk is configured. To retain subscriptions, attach a persistent disk and set DB_PATH to a file on its mount, such as /var/data/subscriptions.sqlite3.
