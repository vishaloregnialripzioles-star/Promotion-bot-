# MASTI MAZAK Promotion Bot

A Discord bot with admin-controlled automatic join promotion DMs, opt-in promotion updates, and an owner/admin command for opted-in broadcasts. Subscription and per-server DM settings are stored in Supabase PostgreSQL.

## Render Web Service

- Build command: `pip install -r requirements.txt`
- Start command: `python bot.py`

### Environment variables

| Key | Value |
|---|---|
| DISCORD_TOKEN | Your Discord bot token (keep it secret) |
| OWNER_ID | Your numeric Discord user ID |
| SERVER_INVITE | `https://discord.gg/UFvjK5Uy5e` |
| DATABASE_URL | Supabase PostgreSQL connection string (keep it secret) |

Render provides `PORT` automatically.

## Supabase setup

1. Open your Supabase project.
2. Go to **Connect** (or **Project Settings → Database**) and find the PostgreSQL connection string.
3. Choose the **Session pooler** connection if your Render service cannot use the direct connection, and copy the URI format.
4. In Render, open your Web Service → **Environment** → **Add Environment Variable**.
5. Set the key to `DATABASE_URL` and paste the connection string as its value. Do not put the password in GitHub or share it in chat.
6. Save the variable and redeploy.

The bot creates the `subscriptions` and `guild_dm_settings` tables automatically at startup; you do not need to run SQL manually. If your database password contains URI-reserved characters, use the connection URI supplied by Supabase or URL-encode the password.

## Discord setup

1. Enable **Server Members Intent** in the Discord Developer Portal.
2. Invite the bot with the `bot` and `applications.commands` scopes.
3. Give it permission to view the server and send messages/DMs.
4. A server administrator with **Manage Server** permission can run `/dm on` to enable one promotion DM for each new member joining that server.
5. Run `/dm off` to disable automatic join DMs. The setting is saved separately for each server and survives redeployments.
6. Members can use `/subscribe` to opt in to occasional promotion updates and `/unsubscribe` to opt out.
7. Use `/dmall confirm:true` to send a promotion only to members who explicitly opted in.

When `/dm on` is enabled, only members who join after it is enabled receive the one-time promotion DM. Existing members are not messaged. If a member has DMs closed, the bot logs the delivery failure and continues normally. Automatic join DMs do not subscribe members to broadcasts.

## Database

At startup, the bot creates these tables if they do not already exist:

- `subscriptions`: members who opted in to promotion broadcasts.
- `guild_dm_settings`: whether automatic join DMs are enabled for each server.
