# MASTI MAZAK Promotion Bot

A Discord bot with a one-time welcome DM, opt-in promotion updates, and an owner/admin command for opted-in broadcasts. Subscription records are stored in Supabase PostgreSQL.

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

The bot creates the `subscriptions` table automatically at startup; you do not need to run SQL manually. If your database password contains URI-reserved characters, use the connection URI supplied by Supabase or URL-encode the password.

## Discord setup

1. Enable **Server Members Intent** in the Discord Developer Portal.
2. Invite the bot with the `bot` and `applications.commands` scopes.
3. Give it permission to view the server and send messages/DMs.
4. Members use `/subscribe` to opt in and `/unsubscribe` to opt out.
5. Use `/dmall confirm:true` to send only to members who opted in.

New members receive one welcome DM explaining the server and how to opt in. Joining does not subscribe them automatically. The bot does not scrape members or send unsolicited broadcast DMs.

## Database

At startup, the bot creates this table if it does not already exist:

```sql
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id BIGINT PRIMARY KEY,
    subscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
