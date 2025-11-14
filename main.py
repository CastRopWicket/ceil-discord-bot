import os
import json
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks
from openai import OpenAI

# =========================
# ENV & CLIENTS
# =========================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")

client_oai = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CEIL AI CONTEXT
# =========================
BASE_SYSTEM_PROMPT = """
You are CEIL Assistant, an AI coordination assistant for the English Department at CEIL (Centre d’Enseignement Intensif des Langues) at UHBC, Chlef.

Context:
- Internal levels: N1–N8.
- Groups: G1, G2, etc. Example: "N4 G3".
- Mapping (approx):
  A1 = N1 + N2
  A2 = N3 + N4
  B1 = N5 + N6
  B2 = N7 + N8
- The coordinator is Abdelkarim Benhalima.
- You help with: drafting emails, summarizing teacher reports, identifying risk groups, generating professional reports, preparing coordination meeting notes, and clarifying progression issues.
- Be professional, concise, clear, and practical.
- No fluff, no over-politeness, no sugar-coating.

Rules:
- Answer in English unless user explicitly requests otherwise.
- When drafting emails, use institutional tone, ready to send.
- If user gives partial info, make reasonable assumptions but do not hallucinate fake data about real people.
"""

CEIL_AI_CHANNEL_NAMES = ["ceil-assistant", "coordination-hub", "academic-assistant"]

async def ask_ceil_assistant(user_message: str, user_name: str) -> str:
    resp = client_oai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": BASE_SYSTEM_PROMPT},
            {"role": "user", "content": f"User ({user_name}) says: {user_message}"}
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()

# =========================
# XP / LEVEL SYSTEM
# =========================
XP_FILE = "xp_data.json"
xp_data = {}  # {user_id: {"xp": int, "level": int}}

def load_xp():
    global xp_data
    if os.path.exists(XP_FILE):
        with open(XP_FILE, "r", encoding="utf-8") as f:
            xp_data = json.load(f)
    else:
        xp_data = {}

def save_xp():
    with open(XP_FILE, "w", encoding="utf-8") as f:
        json.dump(xp_data, f, indent=2)

def add_xp(user_id: int, amount: int = 10):
    uid = str(user_id)
    if uid not in xp_data:
        xp_data[uid] = {"xp": 0, "level": 1}
    xp_data[uid]["xp"] += amount
    xp = xp_data[uid]["xp"]
    level = xp_data[uid]["level"]
    needed = level * 100
    leveled_up = False
    while xp >= needed:
        level += 1
        xp_data[uid]["level"] = level
        needed = level * 100
        leveled_up = True
    save_xp()
    return leveled_up, xp_data[uid]["level"]

# =========================
# MODERATION CONFIG
# =========================
BANNED_WORDS = [
    "fuck", "shit", "bitch"  # you can add/remove as needed
]

MUTED_ROLE_NAME = "Muted"
LOG_CHANNEL_NAME = "ceil-logs"
WELCOME_CHANNEL_NAME = "welcome"

def is_staff(member: discord.Member) -> bool:
    """Check if member is Moderator/Coordinator/Deputy."""
    staff_roles = {"Coordinator", "Deputy Coordinator", "Moderator"}
    return any(r.name in staff_roles for r in member.roles)

async def get_log_channel(guild: discord.Guild):
    for ch in guild.text_channels:
        if ch.name == LOG_CHANNEL_NAME:
            return ch
    return None

# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    load_xp()
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("CEIL Assistant bot is online.")

@bot.event
async def on_member_join(member: discord.Member):
    channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
    if channel:
        msg = (
            f"Welcome to the CEIL Coordination Hub, {member.mention}.\n"
            f"Please introduce yourself and indicate your levels/groups (e.g. N4 G3, N5 G2)."
        )
        await channel.send(msg)

@bot.event
async def on_message(message: discord.Message):
    # Ignore own messages
    if message.author == bot.user:
        return

    # Commands still need to work
    await bot.process_commands(message)

    # Ignore DMs for moderation/xp
    if not message.guild:
        return

    # 1) Moderation: banned words
    msg_lower = message.content.lower()
    if any(bad in msg_lower for bad in BANNED_WORDS):
        await message.delete()
        log_ch = await get_log_channel(message.guild)
        if log_ch:
            await log_ch.send(
                f"🚫 Message deleted from {message.author.mention} in {message.channel.mention} "
                f"for banned language.\nContent: `{message.content}`"
            )
        return

    # 2) XP / leveling system (no XP for bots)
    if not message.author.bot and len(message.content) > 2:
        leveled_up, new_level = add_xp(message.author.id)
        if leveled_up:
            await message.channel.send(
                f"🎉 {message.author.mention} just reached level **{new_level}**!"
            )

    # 3) AI assistant trigger
    channel_name = getattr(message.channel, "name", "").lower()
    mentioned = bot.user.mentioned_in(message)
    in_ceil_channel = channel_name in CEIL_AI_CHANNEL_NAMES

    if mentioned or in_ceil_channel:
        content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not content:
            content = "The user mentioned you but wrote nothing else. Ask them what they need."

        await message.channel.typing()
        reply = await ask_ceil_assistant(content, user_name=str(message.author))
        if len(reply) > 1900:
            reply = reply[:1900] + "\n\n[Truncated reply]"
        await message.reply(reply, mention_author=False)

# =========================
# COMMANDS – AI
# =========================
@bot.command(name="ceil")
async def ceil_command(ctx: commands.Context, *, query: str):
    """Manual AI call: !ceil <your text>"""
    await ctx.trigger_typing()
    reply = await ask_ceil_assistant(query, user_name=str(ctx.author))
    if len(reply) > 1900:
        reply = reply[:1900] + "\n\n[Truncated reply]"
    await ctx.reply(reply, mention_author=False)

# =========================
# COMMANDS – UTILITY
# =========================
@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.reply(f"Pong! Latency: {round(bot.latency * 1000)} ms", mention_author=False)

@bot.command(name="helpceil")
async def helpceil(ctx: commands.Context):
    text = (
        "**CEIL Assistant – Command Help**\n\n"
        "__AI / Coordination__\n"
        "`!ceil <text>` → Ask the CEIL AI assistant.\n"
        "Mention the bot or write in #ceil-assistant / #coordination-hub to chat with it.\n\n"
        "__Moderation (staff only)__\n"
        "`!warn @user <reason>` – Warn a user.\n"
        "`!mute @user <minutes>` – Temporarily mute.\n"
        "`!unmute @user` – Remove mute.\n"
        "`!purge <number>` – Bulk delete messages.\n\n"
        "__Levels / XP__\n"
        "XP is gained automatically by sending messages.\n"
        "Level-ups are announced automatically.\n"
    )
    await ctx.reply(text, mention_author=False)

# =========================
# COMMANDS – MODERATION
# =========================
@bot.command(name="warn")
async def warn(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if not is_staff(ctx.author):
        return await ctx.reply("You don't have permission to use this.", mention_author=False)

    log_ch = await get_log_channel(ctx.guild)
    msg = f"⚠️ {member.mention} has been warned by {ctx.author.mention}.\nReason: {reason}"
    await ctx.send(msg)
    if log_ch:
        await log_ch.send(msg)

@bot.command(name="mute")
async def mute(ctx: commands.Context, member: discord.Member, minutes: int = 10):
    if not is_staff(ctx.author):
        return await ctx.reply("You don't have permission to use this.", mention_author=False)

    guild = ctx.guild
    muted_role = discord.utils.get(guild.roles, name=MUTED_ROLE_NAME)
    if not muted_role:
        muted_role = await guild.create_role(name=MUTED_ROLE_NAME)
        for channel in guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)

    await member.add_roles(muted_role)
    await ctx.send(f"🔇 {member.mention} has been muted for {minutes} minutes.")
    log_ch = await get_log_channel(guild)
    if log_ch:
        await log_ch.send(f"🔇 {member} muted by {ctx.author} for {minutes} minutes.")

    async def unmute_later():
        await asyncio.sleep(minutes * 60)
        if muted_role in member.roles:
            await member.remove_roles(muted_role)
            if not ctx.guild:
                return
            ch = ctx.channel
            try:
                await ch.send(f"🔈 {member.mention} has been automatically unmuted.")
            except Exception:
                pass

    bot.loop.create_task(unmute_later())

@bot.command(name="unmute")
async def unmute(ctx: commands.Context, member: discord.Member):
    if not is_staff(ctx.author):
        return await ctx.reply("You don't have permission to use this.", mention_author=False)

    muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if muted_role and muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"🔈 {member.mention} has been unmuted.")
    else:
        await ctx.send("User is not muted.")

@bot.command(name="purge")
async def purge(ctx: commands.Context, amount: int):
    if not is_staff(ctx.author):
        return await ctx.reply("You don't have permission to use this.", mention_author=False)
    if amount <= 0:
        return await ctx.reply("Amount must be positive.", mention_author=False)

    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to delete the command itself
    log_ch = await get_log_channel(ctx.guild)
    if log_ch:
        await log_ch.send(
            f"🧹 {ctx.author.mention} purged {len(deleted)-1} messages in {ctx.channel.mention}."
        )

# =========================
# RUN BOT
# =========================
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
