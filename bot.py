import os
import asyncio
import logging
import sqlite3
from contextlib import closing

import discord
from discord import app_commands
from aiohttp import web

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("promotion-bot")

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SERVER_INVITE = os.getenv("SERVER_INVITE", "https://discord.gg/UFvjK5Uy5e")
DB_PATH = os.getenv("DB_PATH", "subscriptions.sqlite3")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing")
if OWNER_ID <= 0:
    raise RuntimeError("Set OWNER_ID to your Discord user ID")

def db_init():
    with closing(sqlite3.connect(DB_PATH)) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            subscribed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        con.commit()

def is_subscribed(user_id: int) -> bool:
    with closing(sqlite3.connect(DB_PATH)) as con:
        row = con.execute("SELECT 1 FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()
        return row is not None

def set_subscription(user_id: int, enabled: bool):
    with closing(sqlite3.connect(DB_PATH)) as con:
        if enabled:
            con.execute("INSERT OR IGNORE INTO subscriptions(user_id) VALUES (?)", (user_id,))
        else:
            con.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
        con.commit()

def promotion_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎉 JOIN MASTI MAZAK!",
        description=(
            "Masti Mazak server has officially opened its invite event!\n\n"
            "🎁 **3 invites = Dough Fruit**\n"
            "⭐ Legit **250+ vouches** in the server\n"
            "🎊 Regular giveaways hosted\n\n"
            f"🔗 [View vouches / Join the server]({SERVER_INVITE})"
        ),
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="MASTI MAZAK • Thanks for checking us out!")
    return embed

def welcome_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Welcome to MASTI MAZAK! 👋",
        description=(
            "Thanks for joining our server!\n\n"
            "Our invite event is live: **3 invites = Dough Fruit**, with regular giveaways.\n"
            f"[Open the server invite]({SERVER_INVITE})\n\n"
            "Want occasional promotion updates by DM? Use **/subscribe** in the server. "
            "You can stop them any time with **/unsubscribe**. You are not subscribed automatically."
        ),
        color=discord.Color.blurple(),
    )
    return embed

class PromotionBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        db_init()
        await self.tree.sync()
        log.info("Global application commands synced")

    async def on_ready(self):
        log.info("Logged in as %s (%s)", self.user, self.user.id)

    async def on_member_join(self, member: discord.Member):
        # One-time welcome message only; joining does not subscribe the member.
        try:
            await member.send(embed=welcome_embed())
        except (discord.Forbidden, discord.HTTPException):
            log.info("Could not send welcome DM to member %s", member.id)

bot = PromotionBot()

@bot.tree.command(name="subscribe", description="Opt in to occasional MASTI MAZAK promotion DMs")
async def subscribe(interaction: discord.Interaction):
    set_subscription(interaction.user.id, True)
    await interaction.response.send_message(
        "✅ You're subscribed to occasional promotion updates. Use /unsubscribe any time.",
        ephemeral=True,
    )

@bot.tree.command(name="unsubscribe", description="Stop receiving promotion DMs")
async def unsubscribe(interaction: discord.Interaction):
    set_subscription(interaction.user.id, False)
    await interaction.response.send_message(
        "✅ You're unsubscribed. You won't receive future promotion broadcasts.",
        ephemeral=True,
    )

@bot.tree.command(name="dmall", description="Send the promotion to members who opted in")
@app_commands.describe(confirm="Set this to true to confirm the opted-in broadcast")
async def dmall(interaction: discord.Interaction, confirm: bool):
    if interaction.user.id != OWNER_ID and not (
        isinstance(interaction.user, discord.Member)
        and interaction.user.guild_permissions.manage_guild
    ):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    if not confirm:
        await interaction.response.send_message(
            "No messages sent. Run /dmall again with confirm=true to message opted-in members.",
            ephemeral=True,
        )
        return
    if interaction.guild is None:
        await interaction.response.send_message("Use this command inside your server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    opted_ids = await asyncio.to_thread(load_subscriber_ids)
    targets = [m for m in interaction.guild.members if m.id in opted_ids and not m.bot]
    sent = 0
    failed = 0
    for member in targets:
        try:
            await member.send(embed=promotion_embed())
            sent += 1
        except (discord.Forbidden, discord.HTTPException):
            failed += 1
        await asyncio.sleep(1.2)  # conservative pacing

    summary = f"Broadcast finished. Sent: **{sent}** • Failed: **{failed}** • Opted-in members found: **{len(targets)}**."
    await interaction.followup.send(summary, ephemeral=True)
    try:
        owner = await bot.fetch_user(OWNER_ID)
        await owner.send(f"📊 **MASTI MAZAK delivery report**\n{summary}")
    except (discord.Forbidden, discord.HTTPException):
        log.warning("Could not DM the owner delivery report")

def load_subscriber_ids() -> set[int]:
    with closing(sqlite3.connect(DB_PATH)) as con:
        return {int(row[0]) for row in con.execute("SELECT user_id FROM subscriptions").fetchall()}

async def health(_request):
    return web.json_response({"status": "ok", "bot_ready": bot.is_ready()})

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("Health server listening on port %s", port)

async def main():
    await start_health_server()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
