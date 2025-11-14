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
# GLOBAL CONFIG
# =========================
LOG_CHANNEL_NAME = "ceil-logs"
WELCOME_CHANNEL_NAME = "welcome"
TICKETS_CHANNEL_NAME = "tickets"
MUTED_ROLE_NAME = "Muted"

# channels where AI is naturally active (plus any channel with a mode set)
DEFAULT_AI_CHANNEL_NAMES = ["ceil-assistant", "coordination-hub", "academic-assistant"]

# roles that count as staff for moderation
STAFF_ROLES = {"Coordinator", "Deputy Coordinator", "Moderator"}

# banned words for auto-moderation
BANNED_WORDS = ["fuck", "shit", "bitch"]  # edit for your context

# spam protection settings
SPAM_WINDOW_SECONDS = 8
SPAM_MAX_MESSAGES = 7
AUTO_MUTE_MINUTES = 15

# =========================
# CEIL AI MODES
# =========================

# per-channel AI mode: {channel_id: mode_name}
channel_modes: dict[int, str] = {}

AI_MODES = {
    "ceil": "You are in CEIL Coordination Mode. Focus on CEIL internal matters: N1–N8 levels, groups, progression, reports, emails, and academic coordination.",
    "education": "You are in Education Mode. Focus on teaching methodology, grammar explanations, lesson ideas, assessment, and learner support.",
    "admin": "You are in Admin Mode. Focus on formal emails, reports, policies, procedures, and institutional communication.",
    "general": "You are in General Knowledge Mode. You can talk about any safe topic: history, science, technology, culture, etc.",
    "fun": "You are in Fun Mode. Remain polite and safe, but slightly more relaxed, conversational, and playful.",
    # topic:<something> will be generated dynamically
}

BASE_SYSTEM_PROMPT = """
You are CEIL Assistant, an AI assistant for CEIL (Centre d’Enseignement Intensif des Langues) at UHBC, Chlef.

Core context:
- Internal levels: N1–N8.
- Groups are written as G1, G2, etc. Example: "N4 G3".
- Mapping (approx):
  A1 = N1 + N2
  A2 = N3 + N4
  B1 = N5 + N6
  B2 = N7 + N8
- The coordinator is Abdelkarim Benhalima.
- You can handle CEIL coordination, academic questions, general knowledge, and light fun conversation depending on mode.

Rules:
- Always be clear, concise, and grounded.
- Use professional tone for coordination/admin; more relaxed but still respectful in fun/general modes.
- Do not invent real personal data. Stay within safe, non-harmful topics.
"""

def build_system_prompt(mode: str) -> str:
    """Return system prompt combining base prompt and mode-specific instructions."""
    mode = (mode or "ceil").lower()
    if mode.startswith("topic:"):
        topic = mode.split(":", 1)[1].strip() or "general conversation"
        extra = f"You are in Topic Mode about '{topic}'. Stay mostly on this topic unless the user clearly changes it."
    else:
        extra = AI_MODES.get(
            mode,
            AI_MODES["ceil"]
        )
    return BASE_SYSTEM_PROMPT + "\n\n" + extra

async def ask_ceil_assistant(user_message: str, user_name: str, mode: str) -> str:
    system_prompt = build_system_prompt(mode)
    resp = client_oai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User ({user_name}) says: {user_message}"}
        ],
        temperature=0.4,
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
# MODERATION HELPERS
# =========================
def is_staff(member: discord.Member) -> bool:
    return any(r.name in STAFF_ROLES for r in member.roles)

async def get_log_channel(guild: discord.Guild):
    if guild is None:
        return None
    for ch in guild.text_channels:
        if ch.name == LOG_CHANNEL_NAME:
            return ch
    return None

# spam tracking: {guild_id: {user_id: [timestamps]}}
spam_tracker: dict[int, dict[int, list[float]]] = {}

# slowmode: {channel_id: seconds}
slowmode_settings: dict[int, int] = {}
# last message per (channel,user): {(channel_id, user_id): timestamp}
last_message_time: dict[tuple[int, int], float] = {}

# daily stats (reset approx once per day)
messages_today: dict[int, int] = {}        # guild_id -> count
new_members_today: dict[int, int] = {}     # guild_id -> count
last_stats_reset_date: dict[int, datetime.date] = {}

def track_daily_message(guild: discord.Guild):
    if not guild:
        return
    gid = guild.id
    today = datetime.utcnow().date()
    if gid not in last_stats_reset_date or last_stats_reset_date[gid] != today:
        last_stats_reset_date[gid] = today
        messages_today[gid] = 0
        new_members_today[gid] = new_members_today.get(gid, 0)
    messages_today[gid] = messages_today.get(gid, 0) + 1

def track_new_member(guild: discord.Guild):
    if not guild:
        return
    gid = guild.id
    today = datetime.utcnow().date()
    if gid not in last_stats_reset_date or last_stats_reset_date[gid] != today:
        last_stats_reset_date[gid] = today
        messages_today[gid] = messages_today.get(gid, 0)
        new_members_today[gid] = 0
    new_members_today[gid] = new_members_today.get(gid, 0) + 1

# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    load_xp()
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("CEIL Assistant MEGA PACK is online.")
    hourly_tasks.start()

@bot.event
async def on_member_join(member: discord.Member):
    track_new_member(member.guild)
    channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
    if channel:
        msg = (
            f"Welcome to the CEIL Coordination Hub, {member.mention}.\n"
            f"Please introduce yourself and indicate your levels/groups (e.g. N4 G3, N5 G2)."
        )
        await channel.send(msg)

@bot.event
async def on_message(message: discord.Message):
    # Ignore self
    if message.author == bot.user:
        return

    # Let commands work
    await bot.process_commands(message)

    # Ignore DMs for moderation/xp/ai
    if not message.guild:
        return

    guild = message.guild
    author = message.author

    # ======================
    # BASIC MODERATION: BANNED WORDS
    # ======================
    msg_lower = message.content.lower()
    if any(bad in msg_lower for bad in BANNED_WORDS):
        await message.delete()
        log_ch = await get_log_channel(guild)
        if log_ch:
            await log_ch.send(
                f"🚫 Message deleted from {author.mention} in {message.channel.mention} "
                f"for banned language.\nContent: `{message.content}`"
            )
        return

    # ======================
    # ANTI-LINK (for non-staff)
    # ======================
    link_triggers = ["http://", "https://", "discord.gg/", ".com", ".net", ".org"]
    if not author.bot and not is_staff(author):
        if any(t in msg_lower for t in link_triggers):
            await message.delete()
            log_ch = await get_log_channel(guild)
            if log_ch:
                await log_ch.send(
                    f"🔗 Auto-deleted link from {author.mention} in {message.channel.mention}.\n"
                    f"Content: `{message.content}`"
                )
            return

    # ======================
    # SLOWMODE
    # ======================
    if not author.bot:
        ch_id = message.channel.id
        if ch_id in slowmode_settings:
            delay = slowmode_settings[ch_id]
            key = (ch_id, author.id)
            now = datetime.utcnow().timestamp()
            last = last_message_time.get(key, 0)
            if now - last < delay and not is_staff(author):
                # Too fast -> delete
                await message.delete()
                try:
                    await message.author.send(
                        f"You are sending messages too quickly in {message.channel.mention}. "
                        f"Slowmode is set to {delay} seconds."
                    )
                except Exception:
                    pass
                return
            last_message_time[key] = now

    # ======================
    # ANTI-SPAM
    # ======================
    if not author.bot:
        gid = guild.id
        uid = author.id
        now = datetime.utcnow().timestamp()
        if gid not in spam_tracker:
            spam_tracker[gid] = {}
        if uid not in spam_tracker[gid]:
            spam_tracker[gid][uid] = []
        spam_tracker[gid][uid].append(now)
        # keep only last SPAM_WINDOW_SECONDS
        spam_tracker[gid][uid] = [
            t for t in spam_tracker[gid][uid] if now - t <= SPAM_WINDOW_SECONDS
        ]
        if len(spam_tracker[gid][uid]) >= SPAM_MAX_MESSAGES and not is_staff(author):
            # auto-mute
            muted_role = discord.utils.get(guild.roles, name=MUTED_ROLE_NAME)
            if not muted_role:
                muted_role = await guild.create_role(name=MUTED_ROLE_NAME)
                for channel in guild.channels:
                    await channel.set_permissions(muted_role, send_messages=False, speak=False)
            await author.add_roles(muted_role)
            log_ch = await get_log_channel(guild)
            if log_ch:
                await log_ch.send(
                    f"🤖 Auto-muted {author.mention} for spam in {message.channel.mention} "
                    f"for {AUTO_MUTE_MINUTES} minutes."
                )

            async def unmute_later():
                await asyncio.sleep(AUTO_MUTE_MINUTES * 60)
                if muted_role in author.roles:
                    await author.remove_roles(muted_role)
                    if log_ch:
                        await log_ch.send(
                            f"🔈 Auto-unmuted {author.mention} after spam timeout."
                        )
            bot.loop.create_task(unmute_later())

    # ======================
    # XP / LEVEL UP
    # ======================
    if not author.bot and len(message.content.strip()) > 2:
        track_daily_message(guild)
        leveled_up, new_level = add_xp(author.id)
        if leveled_up:
            await message.channel.send(
                f"🎉 {author.mention} just reached level **{new_level}**!"
            )

    # ======================
    # AI ASSISTANT TRIGGER
    # ======================
    channel_name = getattr(message.channel, "name", "").lower()
    mentioned = bot.user.mentioned_in(message)

    # AI channel if:
    # - channel has a mode set, OR
    # - channel is in default AI list, OR
    # - bot is mentioned
    mode_for_channel = channel_modes.get(message.channel.id)
    in_default_ai = channel_name in DEFAULT_AI_CHANNEL_NAMES
    should_ai_reply = mentioned or in_default_ai or (mode_for_channel is not None)

    if should_ai_reply:
        content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not content:
            content = "The user mentioned you but wrote nothing else. Ask them what they need."

        mode = mode_for_channel or "ceil"

        await message.channel.typing()
        reply = await ask_ceil_assistant(content, user_name=str(author), mode=mode)
        if len(reply) > 1900:
            reply = reply[:1900] + "\n\n[Truncated reply]"
        await message.reply(reply, mention_author=False)

# =========================
# BACKGROUND TASKS
# =========================
@tasks.loop(minutes=60)
async def hourly_tasks():
    """Runs every hour: daily + weekly reminders & summaries."""
    now = datetime.utcnow()
    for guild in bot.guilds:
        coord_channel = discord.utils.get(guild.text_channels, name="coordination-hub")
        if coord_channel is None:
            continue

        # Daily reminder around 20:00 UTC
        if now.hour == 20:
            gid = guild.id
            msgs = messages_today.get(gid, 0)
            joins = new_members_today.get(gid, 0)
            text = (
                f"📊 **Daily Coordination Summary**\n"
                f"- Approx. messages today: **{msgs}**\n"
                f"- New members today: **{joins}**\n\n"
                f"Please ensure progression reports for all active groups are updated.\n"
                f"If you haven't uploaded your report, kindly do so today.\n"
            )
            await coord_channel.send(text)

        # Weekly note on Friday (weekday=4) at 18:00 UTC
        if now.weekday() == 4 and now.hour == 18:
            text = (
                "🗓 **Weekly CEIL Coordination Reminder**\n"
                "- Check progression for N1–N8.\n"
                "- Identify weak groups (attendance, grammar, reading).\n"
                "- Prepare any issues to raise in the next coordination meeting.\n"
                "- Update reports and Drive folders accordingly.\n"
            )
            await coord_channel.send(text)

# =========================
# COMMANDS – AI
# =========================
@bot.command(name="ceil")
async def ceil_command(ctx: commands.Context, *, query: str):
    """Manual AI call: !ceil <your text>"""
    mode = channel_modes.get(ctx.channel.id, "ceil")
    await ctx.trigger_typing()
    reply = await ask_ceil_assistant(query, user_name=str(ctx.author), mode=mode)
    if len(reply) > 1900:
        reply = reply[:1900] + "\n\n[Truncated reply]"
    await ctx.reply(reply, mention_author=False)

@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.reply(f"Pong! Latency: {round(bot.latency * 1000)} ms", mention_author=False)

@bot.command(name="helpceil")
async def helpceil(ctx: commands.Context):
    text = (
        "**CEIL Assistant – MEGA PACK Help**\n\n"
        "__AI / Coordination__\n"
        "`!ceil <text>` – Ask the CEIL AI assistant.\n"
        "Mention the bot or use AI channels to chat with it.\n"
        "`!mode <name>` – Set AI mode for this channel.\n"
        "`!modes` – List all modes.\n"
        "`!currentmode` – Show channel mode.\n\n"
        "__Moderation (staff only)__\n"
        "`!warn @user <reason>` – Warn a user.\n"
        "`!mute @user <minutes>` – Temporarily mute.\n"
        "`!unmute @user` – Remove mute.\n"
        "`!purge <number>` – Bulk delete messages.\n"
        "`!slowmode <seconds/off>` – Set/disable slowmode.\n"
        "`!ticket <issue>` – Create a ticket in #tickets.\n\n"
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
            if log_ch:
                await log_ch.send(f"🔈 {member} has been automatically unmuted.")
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

@bot.command(name="slowmode")
async def slowmode(ctx: commands.Context, setting: str):
    if not is_staff(ctx.author):
        return await ctx.reply("You don't have permission to use this.", mention_author=False)

    ch_id = ctx.channel.id
    if setting.lower() == "off":
        slowmode_settings.pop(ch_id, None)
        await ctx.send("⏱ Slowmode disabled for this channel.")
    else:
        try:
            seconds = int(setting)
            if seconds < 0:
                raise ValueError
        except ValueError:
            return await ctx.reply("Please provide a valid number of seconds or 'off'.", mention_author=False)

        slowmode_settings[ch_id] = seconds
        await ctx.send(f"⏱ Slowmode set to {seconds} seconds for this channel.")

@bot.command(name="ticket")
async def ticket(ctx: commands.Context, *, issue: str):
    guild = ctx.guild
    tickets_ch = discord.utils.get(guild.text_channels, name=TICKETS_CHANNEL_NAME)
    if tickets_ch is None:
        return await ctx.reply(
            f"No `{TICKETS_CHANNEL_NAME}` channel found. Please ask the Coordinator to create it.",
            mention_author=False,
        )

    embed = discord.Embed(
        title="New Support Ticket",
        description=issue,
        color=discord.Color.blue(),
    )
    embed.add_field(name="Opened by", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
    embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
    embed.timestamp = datetime.utcnow()

    await tickets_ch.send(embed=embed)
    await ctx.reply("✅ Your ticket has been created. The coordination team will review it.", mention_author=False)

# =========================
# COMMANDS – AI MODES
# =========================
@bot.command(name="mode")
async def mode(ctx: commands.Context, *, mode_name: str):
    """Set AI mode for current channel: ceil, education, admin, general, fun, topic <something>."""
    mode_name = mode_name.strip().lower()

    if mode_name.startswith("topic "):
        topic = mode_name.split(" ", 1)[1].strip()
        if not topic:
            return await ctx.reply("Please specify a topic, e.g. `!mode topic football`.", mention_author=False)
        mode_key = f"topic:{topic}"
    else:
        if mode_name not in AI_MODES:
            return await ctx.reply(
                "Unknown mode. Use `!modes` to see available modes, "
                "or `!mode topic <something>`.",
                mention_author=False,
            )
        mode_key = mode_name

    channel_modes[ctx.channel.id] = mode_key
    await ctx.reply(f"✅ AI mode for this channel set to **{mode_key}**.", mention_author=False)

@bot.command(name="currentmode")
async def currentmode(ctx: commands.Context):
    mode = channel_modes.get(ctx.channel.id, "ceil")
    await ctx.reply(f"The AI mode for this channel is **{mode}**.", mention_author=False)

@bot.command(name="modes")
async def modes(ctx: commands.Context):
    base_modes = ", ".join(sorted(AI_MODES.keys()))
    text = (
        "**Available AI modes:**\n"
        f"- {base_modes}\n"
        "\n"
        "Use `!mode <name>` to set one of the above, e.g. `!mode general`.\n"
        "Use `!mode topic <something>` to lock the bot to a specific topic, e.g. `!mode topic football`."
    )
    await ctx.reply(text, mention_author=False)

# =========================
# RUN BOT
# =========================
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
