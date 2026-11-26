import os
import asyncio
import logging

import discord
import psycopg
from discord import app_commands
from aiohttp import web

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("promotion-bot")

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SERVER_INVITE = os.getenv("SERVER_INVITE", "https://discord.gg/UFvjK5Uy5e")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing")
if OWNER_ID <= 0:
    raise RuntimeError("Set OWNER_ID to your Discord user ID")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing; add your Supabase PostgreSQL connection string in Render")


def db_init():
    with psycopg.connect(DATABASE_URL) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id BIGINT PRIMARY KEY,
                subscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS guild_dm_settings (
                guild_id BIGINT PRIMARY KEY,
                enabled BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)


def is_subscribed(user_id: int) -> bool:
    with psycopg.connect(DATABASE_URL) as con:
        row = con.execute(
            "SELECT 1 FROM subscriptions WHERE user_id = %s",
            (user_id,),
        ).fetchone()
        return row is not None


def set_subscription(user_id: int, enabled: bool):
    with psycopg.connect(DATABASE_URL) as con:
        if enabled:
            con.execute(
                "INSERT INTO subscriptions (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (user_id,),
            )
        else:
            con.execute("DELETE FROM subscriptions WHERE user_id = %s", (user_id,))


def load_subscriber_ids() -> set[int]:
    with psycopg.connect(DATABASE_URL) as con:
        rows = con.execute("SELECT user_id FROM subscriptions").fetchall()
        return {int(row[0]) for row in rows}


def set_guild_dm_enabled(guild_id: int, enabled: bool):
    with psycopg.connect(DATABASE_URL) as con:
        con.execute(
            """
            INSERT INTO guild_dm_settings (guild_id, enabled, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (guild_id)
            DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = NOW()
            """,
            (guild_id, enabled),
        )


def get_guild_dm_enabled(guild_id: int) -> bool:
    with psycopg.connect(DATABASE_URL) as con:
        row = con.execute(
            "SELECT enabled FROM guild_dm_settings WHERE guild_id = %s",
            (guild_id,),
        ).fetchone()
        return bool(row[0]) if row else False


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


class PromotionBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await asyncio.to_thread(db_init)
        await self.tree.sync()
        log.info("Global application commands synced")

    async def on_ready(self):
        log.info("Logged in as %s (%s)", self.user, self.user.id)

    async def on_member_join(self, member: discord.Member):
        # Only send the promotion DM when this server's administrators enabled it.
        try:
            enabled = await asyncio.to_thread(get_guild_dm_enabled, member.guild.id)
        except Exception:
            log.exception("Could not read join-DM setting for guild %s", member.guild.id)
            return

        if not enabled:
            return

        try:
            await member.send(
                content=f"Welcome to **{member.guild.name}**! Here's the server's promotion information:",
                embed=promotion_embed(),
            )
            log.info("Sent join promotion DM to member %s in guild %s", member.id, member.guild.id)
        except (discord.Forbidden, discord.HTTPException):
            log.info("Could not send join promotion DM to member %s", member.id)


bot = PromotionBot()


@bot.tree.command(name="subscribe", description="Opt in to occasional MASTI MAZAK promotion DMs")
async def subscribe(interaction: discord.Interaction):
    await asyncio.to_thread(set_subscription, interaction.user.id, True)
    await interaction.response.send_message(
        "✅ You're subscribed to occasional promotion updates. Use /unsubscribe any time.",
        ephemeral=True,
    )


@bot.tree.command(name="unsubscribe", description="Stop receiving promotion DMs")
async def unsubscribe(interaction: discord.Interaction):
    await asyncio.to_thread(set_subscription, interaction.user.id, False)
    await interaction.response.send_message(
        "✅ You're unsubscribed. You won't receive future promotion broadcasts.",
        ephemeral=True,
    )


dm_group = app_commands.Group(name="dm", description="Control the automatic join promotion DM")


@dm_group.command(name="on", description="Enable one welcome promotion DM for new members")
async def dm_on(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        return
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "Only server administrators with Manage Server permission can change this setting.",
            ephemeral=True,
        )
        return

    try:
        await asyncio.to_thread(set_guild_dm_enabled, interaction.guild.id, True)
    except Exception:
        log.exception("Could not enable join DMs for guild %s", interaction.guild.id)
        await interaction.response.send_message(
            "I couldn't save this setting because the database is unavailable. Please try again later.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        "✅ Automatic join promotion DMs are now **ON** for this server. New members will receive one DM when they join. Existing members won't be messaged.",
        ephemeral=True,
    )


@dm_group.command(name="off", description="Disable automatic join promotion DMs")
async def dm_off(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("Use this command inside a server.", ephemeral=True)
        return
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "Only server administrators with Manage Server permission can change this setting.",
            ephemeral=True,
        )
        return

    try:
        await asyncio.to_thread(set_guild_dm_enabled, interaction.guild.id, False)
    except Exception:
        log.exception("Could not disable join DMs for guild %s", interaction.guild.id)
        await interaction.response.send_message(
            "I couldn't save this setting because the database is unavailable. Please try again later.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        "✅ Automatic join promotion DMs are now **OFF** for this server.",
        ephemeral=True,
    )


bot.tree.add_command(dm_group)


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
    try:
        opted_ids = await asyncio.to_thread(load_subscriber_ids)
    except Exception:
        log.exception("Could not load subscriptions from Supabase")
        await interaction.followup.send(
            "The subscription database is temporarily unavailable. No messages were sent.",
            ephemeral=True,
        )
        return

    targets = []
    for user_id in opted_ids:
        try:
            member = await interaction.guild.fetch_member(user_id)
            if not member.bot:
                targets.append(member)
        except discord.NotFound:
            continue
        except (discord.Forbidden, discord.HTTPException):
            log.warning("Could not look up opted-in member %s", user_id)

    sent = 0
    failed = 0
    for member in targets:
        try:
            await member.send(embed=promotion_embed())
            sent += 1
        except (discord.Forbidden, discord.HTTPException):
            failed += 1
        await asyncio.sleep(1.2)

    summary = (
        f"Broadcast finished. Sent: **{sent}** • Failed: **{failed}** "
        f"• Opted-in members found: **{len(targets)}**."
    )
    await interaction.followup.send(summary, ephemeral=True)
    try:
        owner = await bot.fetch_user(OWNER_ID)
        await owner.send(f"📊 **MASTI MAZAK delivery report**\n{summary}")
    except (discord.Forbidden, discord.HTTPException):
        log.warning("Could not DM the owner delivery report")


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
