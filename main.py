###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 1/8)
# SYSTEM BOOT + CONFIG + UTILITIES + XP ENGINE
###############################################

import os
import json
import time
import random
import asyncio
import traceback
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands
from openai import OpenAI

###############################################################
# 1. ENVIRONMENT VALIDATION
###############################################################

# Load environment variables for API keys
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError(
        "❌ ERROR: DISCORD_TOKEN environment variable is missing. "
        "Set it before running the bot."
    )

if not OPENAI_API_KEY:
    raise RuntimeError(
        "❌ ERROR: OPENAI_API_KEY environment variable is missing."
    )

###############################################################
# 2. BOT INTENTS (FULL MESSAGE CONTENT ACCESS)
###############################################################

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True  # REQUIRED for AI responses + moderation

bot = commands.Bot(command_prefix="!", intents=intents)

###############################################################
# 3. CONFIG SYSTEM — Persistent bot feature controls
###############################################################

CONFIG_FILE = "config.json"

# Default configuration for first run
DEFAULT_CONFIG = {
    "ai_enabled": True,
    "moderation_enabled": True,
    "xp_enabled": True,
    "reminders_enabled": True,
    "polls_enabled": True,
    "fun_enabled": True,
    "lessons_enabled": True,
    "research_enabled": True,
    "images_enabled": True,
    "logging_enabled": True,
    "ai_default_mode": "ceil",
    "auto_role_name": "Teacher",
    "banned_words": ["fuck", "shit", "bitch"],
    "ai_model": "gpt-4.1-mini",
    "max_reply_length": 1900
}

# Global config and banned words
config: dict = {}
BANNED_WORDS: list[str] = []

# Staff roles allowed to use /admin commands
STAFF_ROLES = {"Coordinator", "Deputy Coordinator", "Moderator", "Administrator"}


def load_config():
    """
    Load config.json from disk.
    If file missing, fallback to the DEFAULT_CONFIG.
    """
    global config, BANNED_WORDS

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            print("⚠ WARNING: Invalid config.json — using defaults.")
            config = DEFAULT_CONFIG.copy()
    else:
        print("⚠ config.json not found — creating it.")
        config = DEFAULT_CONFIG.copy()
        save_config()

    # Ensure missing fields get default values
    for key, val in DEFAULT_CONFIG.items():
        config.setdefault(key, val)

    # Sync banned words list
    BANNED_WORDS = config.get("banned_words", DEFAULT_CONFIG["banned_words"])


def save_config():
    """Write config.json to disk safely."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"❌ ERROR saving config.json: {e}")


###############################################################
# 4. OPENAI — Unified LLM Client Wrapper
###############################################################

client_oai = OpenAI(api_key=OPENAI_API_KEY)


async def call_openai(system_prompt: str, user_prompt: str, temperature: float = 0.4):
    """
    Safely call OpenAI with error handling and resiliency.
    Returns the LLM output text.
    """
    try:
        response = client_oai.chat.completions.create(
            model=config.get("ai_model", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        content = response.choices[0].message.content.strip()
        max_len = config.get("max_reply_length", 1900)
        if len(content) > max_len:
            content = content[:max_len] + "\n\n[Truncated]"
        return content

    except Exception as e:
        print("❌ OPENAI API ERROR:", e)
        traceback.print_exc()
        return "⚠ Sorry, I encountered an error while processing your request."


###############################################################
# 5. PERMISSION UTILITIES
###############################################################

def is_staff(member: discord.Member) -> bool:
    """
    Checks whether a user is staff by role.
    Important for admin commands and moderation bypass.
    """
    if member.guild_permissions.administrator:
        return True
    return any(role.name in STAFF_ROLES for role in member.roles)


def staff_only():
    """
    Decorator for text commands.
    Ensures only staff can run the command.
    """
    async def predicate(ctx):
        if not is_staff(ctx.author):
            await ctx.reply("❌ You are not allowed to use this command.", mention_author=False)
            return False
        return True
    return commands.check(predicate)


###############################################################
# 6. LOGGING UTILITIES
###############################################################

LOG_CHANNEL_NAME = "ceil-logs"


def get_log_channel(guild: discord.Guild | None):
    """Return the logging channel object if found."""
    if not guild or not config.get("logging_enabled", True):
        return None
    for ch in guild.text_channels:
        if ch.name == LOG_CHANNEL_NAME:
            return ch
    return None


async def log_event(guild: discord.Guild, message: str):
    """Send an event message to the logging channel if enabled."""
    ch = get_log_channel(guild)
    if ch:
        try:
            await ch.send(message)
        except Exception:
            pass


###############################################################
# 7. EMBED UTILITIES — clean standardized Discord UI
###############################################################

def make_embed(
    title: str,
    description: str = "",
    color: discord.Color = discord.Color.blue()
):
    """Helper to create a clean embed."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.utcnow()
    return embed


###############################################################
# 8. XP SYSTEM (EXPANDED)
###############################################################

XP_FILE = "xp_data.json"
xp_data = {}   # { "user_id": { "xp": X, "level": Y } }


def load_xp():
    """Load XP data from disk."""
    global xp_data
    if os.path.exists(XP_FILE):
        try:
            with open(XP_FILE, "r", encoding="utf-8") as f:
                xp_data = json.load(f)
        except Exception:
            xp_data = {}
    else:
        xp_data = {}


def save_xp():
    """Persist XP data."""
    try:
        with open(XP_FILE, "w", encoding="utf-8") as f:
            json.dump(xp_data, f, indent=2)
    except Exception as e:
        print("❌ ERROR writing xp_data.json:", e)


def add_xp(user_id: int, amount: int = 10):
    """
    Give XP to a user.
    Automatically handles leveling.
    Returns (leveled_up: bool, new_level: int)
    """
    uid = str(user_id)

    # Initialize if new
    if uid not in xp_data:
        xp_data[uid] = {"xp": 0, "level": 1}

    # Add XP
    xp_data[uid]["xp"] += amount
    xp = xp_data[uid]["xp"]
    level = xp_data[uid]["level"]

    # Leveling logic
    leveled_up = False
    required = level * 100
    while xp >= required:
        level += 1
        xp_data[uid]["level"] = level
        required = level * 100
        leveled_up = True

    save_xp()
    return leveled_up, xp_data[uid]["level"]


def get_xp_profile(user_id: int):
    """Return XP + Level for a user."""
    uid = str(user_id)
    if uid not in xp_data:
        return (0, 1)
    return xp_data[uid]["xp"], xp_data[uid]["level"]

###############################################################
# 9. ERROR HANDLING INFRASTRUCTURE
###############################################################

@bot.event
async def on_command_error(ctx, error):
    """
    Global error handler for text commands.
    """
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("⚠ Missing argument. Use the correct syntax.", mention_author=False)
        return

    if isinstance(error, commands.CheckFailure):
        return  # handled already in staff_only()

    await ctx.reply("❌ An error occurred running this command.", mention_author=False)
    traceback.print_exc()


###############################################################
# END OF CHUNK 1
###############################################################

print("📦 Loaded CHUNK 1 (system, config, utilities, XP engine)")
###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 2/8)
# MODERATION SYSTEM (filters + staff commands)
###############################################

###############################################################
# 10. MODERATION STATE & CONSTANTS
###############################################################

# Spam / flood detection
SPAM_WINDOW_SECONDS = 8       # time window to consider messages
SPAM_MAX_MESSAGES = 7         # messages in that window to trigger auto-mute
AUTO_MUTE_MINUTES = 15        # duration of auto-mute

# Tracking spam: {guild_id: {user_id: [timestamps]}}
spam_tracker: dict[int, dict[int, list[float]]] = {}

# Slowmode: {channel_id: delay_in_seconds}
slowmode_settings: dict[int, int] = {}

# Last message time per (channel, user) for slowmode enforcement
last_message_time: dict[tuple[int, int], float] = {}

# Warnings: stored in memory (could be persisted later)
# warnings[guild_id][user_id] = count
warnings: dict[int, dict[int, int]] = {}


def add_warning(guild_id: int, user_id: int, reason: str | None = None):
    """
    Increment warning count for a user in a guild.
    Returns the new warning count.
    """
    if guild_id not in warnings:
        warnings[guild_id] = {}
    if user_id not in warnings[guild_id]:
        warnings[guild_id][user_id] = 0
    warnings[guild_id][user_id] += 1
    return warnings[guild_id][user_id]


def get_warnings(guild_id: int, user_id: int) -> int:
    """Return warning count for a user in a guild."""
    if guild_id not in warnings:
        return 0
    return warnings[guild_id].get(user_id, 0)


###############################################################
# 11. MODERATION HELPERS
###############################################################

async def apply_auto_mute(member: discord.Member, guild: discord.Guild, reason: str):
    """
    Auto-creates or reuses a Muted role, applies it to the user,
    and schedules unmute after AUTO_MUTE_MINUTES.
    """
    muted_role = discord.utils.get(guild.roles, name="Muted")

    # Create role if it doesn't exist
    if not muted_role:
        try:
            muted_role = await guild.create_role(
                name="Muted",
                reason="Auto-created for moderation",
            )
            # Deny sending in all channels
            for ch in guild.channels:
                try:
                    await ch.set_permissions(
                        muted_role,
                        send_messages=False,
                        speak=False,
                        add_reactions=False,
                    )
                except Exception:
                    pass
        except Exception as e:
            print(f"❌ Failed to create Muted role in {guild.name}: {e}")
            return

    # Apply role
    try:
        await member.add_roles(muted_role, reason=reason)
    except Exception as e:
        print(f"❌ Failed to add Muted role to {member}: {e}")
        return

    # Logging
    await log_event(
        guild,
        f"🤖 Auto-muted {member.mention} for **{AUTO_MUTE_MINUTES} minutes**. Reason: {reason}",
    )

    # Schedule unmute
    async def unmute_later():
        await asyncio.sleep(AUTO_MUTE_MINUTES * 60)
        if muted_role in member.roles:
            try:
                await member.remove_roles(muted_role, reason="Auto-unmute after timeout")
                await log_event(guild, f"🔈 Auto-unmuted {member.mention} after timeout.")
            except Exception:
                pass

    bot.loop.create_task(unmute_later())


def is_link(text: str) -> bool:
    """
    Simple heuristic to detect links.
    You can expand this with regex for more accuracy.
    """
    text = text.lower()
    triggers = ["http://", "https://", "discord.gg/", ".com", ".net", ".org"]
    return any(t in text for t in triggers)


###############################################################
# 12. MODERATION-FOCUSED COMMANDS (TEXT)
###############################################################

@bot.command(name="warn")
@staff_only()
async def warn_command(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """
    Warn a user. This increases their warning count.
    """
    new_count = add_warning(ctx.guild.id, member.id, reason)
    await ctx.reply(
        f"⚠ {member.mention} has been warned. Reason: `{reason}`.\n"
        f"They now have **{new_count} warning(s)**.",
        mention_author=False,
    )
    await log_event(
        ctx.guild,
        f"⚠ {member} warned by {ctx.author} — reason: {reason}. Total warnings: {new_count}",
    )


@bot.command(name="warnings")
@staff_only()
async def warnings_command(ctx: commands.Context, member: discord.Member | None = None):
    """
    Check how many warnings a user has.
    """
    target = member or ctx.author
    count = get_warnings(ctx.guild.id, target.id)
    await ctx.reply(
        f"ℹ {target.mention} has **{count} warning(s)**.",
        mention_author=False,
    )


@bot.command(name="mute")
@staff_only()
async def mute_command(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """
    Manually mute a user by adding the Muted role.
    """
    await apply_auto_mute(member, ctx.guild, f"Manual mute: {reason}")
    await ctx.reply(
        f"🔇 {member.mention} has been muted. Reason: `{reason}`",
        mention_author=False,
    )


@bot.command(name="unmute")
@staff_only()
async def unmute_command(ctx: commands.Context, member: discord.Member):
    """
    Remove Muted role from a user.
    """
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role or muted_role not in member.roles:
        return await ctx.reply("User is not muted.", mention_author=False)

    try:
        await member.remove_roles(muted_role, reason="Manual unmute")
    except Exception as e:
        return await ctx.reply(f"❌ Failed to unmute: {e}", mention_author=False)

    await ctx.reply(f"🔈 {member.mention} has been unmuted.", mention_author=False)
    await log_event(ctx.guild, f"🔈 {member} unmuted by {ctx.author}.")


@bot.command(name="kick")
@staff_only()
async def kick_command(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """
    Kick a user from the server.
    """
    try:
        await member.kick(reason=reason)
        await ctx.reply(f"👢 {member} has been kicked. Reason: `{reason}`", mention_author=False)
        await log_event(ctx.guild, f"👢 {member} kicked by {ctx.author} — {reason}")
    except Exception as e:
        await ctx.reply(f"❌ Failed to kick: {e}", mention_author=False)


@bot.command(name="ban")
@staff_only()
async def ban_command(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """
    Ban a user from the server.
    """
    try:
        await member.ban(reason=reason)
        await ctx.reply(f"⛔ {member} has been banned. Reason: `{reason}`", mention_author=False)
        await log_event(ctx.guild, f"⛔ {member} banned by {ctx.author} — {reason}")
    except Exception as e:
        await ctx.reply(f"❌ Failed to ban: {e}", mention_author=False)


@bot.command(name="purge")
@staff_only()
async def purge_command(ctx: commands.Context, amount: int):
    """
    Bulk delete messages in the current channel.
    """
    if amount <= 0:
        return await ctx.reply("Specify a positive number of messages to purge.", mention_author=False)

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 includes the command
        await ctx.send(f"🧹 Deleted {len(deleted) - 1} messages.", delete_after=5)
        await log_event(ctx.guild, f"🧹 {ctx.author} purged {len(deleted) - 1} messages in {ctx.channel}.")
    except Exception as e:
        await ctx.reply(f"❌ Failed to purge: {e}", mention_author=False)


@bot.command(name="slowmode")
@staff_only()
async def slowmode_command(ctx: commands.Context, seconds: int):
    """
    Set slowmode for the channel via a text command.
    Also tracked internally to enforce per user/post behaviour.
    """
    channel = ctx.channel

    if seconds < 0:
        seconds = 0

    try:
        await channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            slowmode_settings.pop(channel.id, None)
            msg = "Slowmode disabled for this channel."
        else:
            slowmode_settings[channel.id] = seconds
            msg = f"Slowmode set to **{seconds} seconds** in this channel."

        await ctx.reply(f"🐢 {msg}", mention_author=False)
        await log_event(ctx.guild, f"🐢 {ctx.author} set slowmode to {seconds} in {channel}.")
    except Exception as e:
        await ctx.reply(f"❌ Failed to set slowmode: {e}", mention_author=False)


###############################################################
# 13. ADMIN SLASH EXTENSIONS — purge + slowmode
# (Hooks into the AdminGroup defined later)
###############################################################

# NOTE: This assumes AdminGroup from Chunk 6 will exist.
# For now, we define the functions, and they will be attached
# to the admin slash group later in the full build.

# We'll keep references in a list and attach them when AdminGroup is finalized.
admin_slash_extensions = []  # each item is (name, function) for later registration


def register_admin_extension(func):
    """
    Decorator: registers a slash command to be attached
    to /admin group later.
    """
    admin_slash_extensions.append(func)
    return func


@register_admin_extension
@app_commands.command(name="purge", description="(Admin) Purge messages from a channel.")
@app_commands.describe(
    amount="Number of messages to delete (excluding the command call message).",
)
async def admin_purge_slash(interaction: discord.Interaction, amount: int):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    if amount <= 0:
        return await interaction.response.send_message("Amount must be positive.", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
        await log_event(
            interaction.guild,
            f"🧹 {interaction.user} purged {len(deleted)} messages in {interaction.channel}.",
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to purge: {e}", ephemeral=True)


@register_admin_extension
@app_commands.command(name="slowmode", description="(Admin) Set slowmode on this channel.")
@app_commands.describe(seconds="Number of seconds for slowmode (0 = disable).")
async def admin_slowmode_slash(interaction: discord.Interaction, seconds: int):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    if seconds < 0:
        seconds = 0

    await interaction.response.defer(ephemeral=True, thinking=True)
    channel = interaction.channel

    try:
        await channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            slowmode_settings.pop(channel.id, None)
            msg = "Slowmode disabled for this channel."
        else:
            slowmode_settings[channel.id] = seconds
            msg = f"Slowmode set to **{seconds} seconds** in this channel."

        await interaction.followup.send(f"🐢 {msg}", ephemeral=True)
        await log_event(
            interaction.guild,
            f"🐢 {interaction.user} set slowmode to {seconds} in {channel}.",
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to set slowmode: {e}", ephemeral=True)


###############################################################
# END OF CHUNK 2
###############################################################

print("📦 Loaded CHUNK 2 (moderation core + commands)")
###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 3/8)
# AI ENGINE + TEACHER / COORDINATION SUITE
###############################################

###############################################################
# 14. AI MODES, SYSTEM PROMPT, CHANNEL MODES
###############################################################

# Per-channel AI behaviour
channel_modes: dict[int, str] = {}   # {channel_id: mode_name or "topic:..."}

# Default AI modes focusing on CEIL use-cases
AI_MODES = {
    "ceil": (
        "You are in CEIL Coordination Mode. Focus on CEIL internal matters, "
        "teacher coordination, progression reports, and teaching practice."
    ),
    "education": (
        "You are in Teacher Mode. Help with pedagogy, lesson planning, "
        "classroom management, CEFR levels, and teaching activities."
    ),
    "admin": (
        "You are in Admin Mode. Write formal emails, policy notes, "
        "coordination reports, and official documents."
    ),
    "general": (
        "You are in General Mode. Talk about safe, helpful topics: tech, "
        "history, culture, movies, etc. Avoid controversial topics."
    ),
    "fun": (
        "You are in Fun Mode. Be light, friendly, and playful, but still "
        "respectful and safe. Keep it appropriate for a language center."
    ),
}

BASE_SYSTEM_PROMPT = """
You are CEIL Assistant, an AI assistant for CEIL (Centre d’Enseignement Intensif des Langues)
at UHBC, Chlef, Algeria.

You:
- Understand the CEIL context: intensive language programs, groups G1–G8, levels N1–N8 mapped to A1–B2.
- Support coordinators in tracking progression, attendance, challenges, and solutions.
- Support teachers in lesson planning, materials design, assessment, and reporting.
- Can write professional emails, reports, and documentation in a clear, concise style.
- Use a professional, helpful tone by default, unless in Fun Mode.
"""


def build_ai_system_prompt(mode: str) -> str:
    """
    Builds the system prompt used for the AI depending on channel mode.
    mode can be:
      - 'ceil', 'education', 'admin', 'general', 'fun'
      - or 'topic:X' to stay focused on one topic.
    """
    mode = (mode or config.get("ai_default_mode", "ceil")).lower()
    if mode.startswith("topic:"):
        topic = mode.split(":", 1)[1].strip() or "general conversation"
        extra = (
            f"You are in Topic Mode about '{topic}'. Stay focused on this topic unless "
            "the user explicitly changes the subject."
        )
    else:
        extra = AI_MODES.get(mode, AI_MODES["ceil"])

    return BASE_SYSTEM_PROMPT + "\n\n" + extra


async def ai_general_reply(user_msg: str, user_name: str, mode: str) -> str:
    """
    High-level AI reply function used by !ceil and on_message AI.
    """
    system_prompt = build_ai_system_prompt(mode)
    user_prompt = f"User ({user_name}) says:\n{user_msg}"
    return await call_openai(system_prompt, user_prompt, temperature=0.4)


###############################################################
# 15. CORE AI COMMANDS (TEXT) — MODES & INTERACTION
###############################################################

@bot.command(name="ceil")
async def ceil_command(ctx: commands.Context, *, query: str):
    """
    Main AI command.
    Uses the current channel mode to respond.
    """
    if not config.get("ai_enabled", True):
        return await ctx.reply("⚙️ AI is currently disabled by the coordinator.", mention_author=False)

    mode = channel_modes.get(ctx.channel.id, config.get("ai_default_mode", "ceil"))
    await ctx.trigger_typing()
    reply = await ai_general_reply(query, str(ctx.author), mode)
    await ctx.reply(reply, mention_author=False)


@bot.command(name="mode")
async def mode_command(ctx: commands.Context, *, mode_name: str):
    """
    Set the AI mode for this channel.
    Examples:
      !mode ceil
      !mode education
      !mode admin
      !mode general
      !mode fun
      !mode topic speaking exam practice
    """
    mode_name = mode_name.strip().lower()

    # Topic mode
    if mode_name.startswith("topic "):
        topic = mode_name.split(" ", 1)[1].strip()
        if not topic:
            return await ctx.reply(
                "Specify a topic, e.g. `!mode topic midterm exam speaking`.",
                mention_author=False,
            )
        mode_key = f"topic:{topic}"
    else:
        # Named mode
        if mode_name not in AI_MODES:
            return await ctx.reply(
                "Unknown mode. Use: `ceil`, `education`, `admin`, `general`, `fun`, "
                "or `topic <something>`.",
                mention_author=False,
            )
        mode_key = mode_name

    channel_modes[ctx.channel.id] = mode_key
    await ctx.reply(
        f"✅ AI mode for this channel set to **{mode_key}**.",
        mention_author=False,
    )


@bot.command(name="currentmode")
async def currentmode_command(ctx: commands.Context):
    """
    Show the AI mode for this channel.
    """
    mode = channel_modes.get(ctx.channel.id, config.get("ai_default_mode", "ceil"))
    await ctx.reply(
        f"ℹ AI mode for this channel is **{mode}**.",
        mention_author=False,
    )


@bot.command(name="modes")
async def modes_command(ctx: commands.Context):
    """
    List available modes.
    """
    base_modes = ", ".join(sorted(AI_MODES.keys()))
    text = (
        "**AI modes available:**\n"
        f"- {base_modes}\n"
        "Use `!mode <name>` or `!mode topic <topic>` to set this channel's AI mode."
    )
    await ctx.reply(text, mention_author=False)


###############################################################
# 16. TEACHER / COORDINATION SUITE — LLM HELPERS
###############################################################

async def teacher_llm(prompt: str) -> str:
    """
    Uses OpenAI with a strong teaching / coordination system prompt.
    """
    system = (
        BASE_SYSTEM_PROMPT
        + "\n\nYou are now in TEACHER SUPPORT MODE: Focus on lesson planning, "
        "materials, progression, reporting, classroom management, and teacher needs."
    )
    return await call_openai(system, prompt, temperature=0.4)


async def admin_llm(prompt: str) -> str:
    """
    Uses OpenAI with admin/professional writing focus.
    """
    system = (
        BASE_SYSTEM_PROMPT
        + "\n\nYou are now in ADMIN MODE: Write formal, concise, professional texts "
        "for directors, coordinators, and institutional stakeholders."
    )
    return await call_openai(system, prompt, temperature=0.35)


###############################################################
# 17. SLASH COMMANDS — LESSON PLANS, WORKSHEETS, QUIZZES, TEMPLATES
###############################################################

@bot.tree.command(name="lessonplan", description="Generate a CEFR-aligned lesson plan.")
@app_commands.describe(
    level="CEFR level (A1, A2, B1, B2, etc.)",
    topic="Lesson topic (e.g. Present Perfect, Travel, Environment)",
    duration="Duration in minutes (e.g. 90)",
)
async def lessonplan_slash(
    interaction: discord.Interaction,
    level: str,
    topic: str,
    duration: int = 90,
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message("Lesson tools are disabled by the coordinator.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    prompt = (
        f"Create a detailed ESL lesson plan for CEFR level {level}, topic '{topic}', "
        f"duration {duration} minutes.\n"
        "Use this structure with clear labels and bullet points:\n"
        "1. Objectives (linguistic + communicative)\n"
        "2. Warm-up\n"
        "3. Presentation (input)\n"
        "4. Guided Practice\n"
        "5. Freer Practice / Communicative Task\n"
        "6. Assessment / Checking Understanding\n"
        "7. Homework\n"
        "8. Materials & Notes for the teacher\n"
    )
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


@bot.tree.command(name="worksheet", description="Generate an ESL worksheet.")
@app_commands.describe(
    skill="Skill focus (grammar/vocabulary/reading/listening/writing/speaking)",
    topic="Topic or grammar point",
    level="CEFR level, e.g. A2",
)
async def worksheet_slash(
    interaction: discord.Interaction,
    skill: str,
    topic: str,
    level: str,
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message("Lesson tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    prompt = (
        f"Create an ESL worksheet focusing on {skill} at level {level}, "
        f"on the topic '{topic}'.\n"
        "Include at least 3 different activities. Number them clearly. "
        "At the end, provide an answer key if relevant."
    )
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


@bot.tree.command(name="quiz", description="Generate a quick quiz (MCQs/short answer).")
@app_commands.describe(
    topic="Grammar or vocabulary topic (e.g. Conditionals, Collocations)",
    items="Number of items/questions",
    level="CEFR level, e.g. B1",
)
async def quiz_slash(
    interaction: discord.Interaction,
    topic: str,
    items: int = 10,
    level: str = "B1",
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message("Lesson tools are disabled.", ephemeral=True)

    if items <= 0:
        items = 5

    await interaction.response.defer(thinking=True)
    prompt = (
        f"Create an ESL quiz with {items} questions at level {level} about '{topic}'.\n"
        "Use mostly multiple choice, but you may include a couple of short answer items. "
        "Number each item clearly and provide an answer key at the end."
    )
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


@bot.tree.command(name="template", description="Generate a blank teaching template.")
@app_commands.describe(kind="plan/report/observation/progression/rubric")
async def template_slash(interaction: discord.Interaction, kind: str):
    """
    Generates blank templates teachers can reuse.
    """
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message("Lesson tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    kind = kind.lower()

    if kind == "plan":
        prompt = (
            "Create a blank lesson plan template for language teachers. "
            "Include fields for: course, group, date, teacher, objectives, "
            "stage, procedure, timing, interaction pattern, materials, and notes."
        )
    elif kind == "report":
        prompt = (
            "Create a blank session report template for CEIL. "
            "Include fields for: teacher, group, level (N1–N8 + CEFR), date, "
            "units/lessons covered, activities, student engagement, challenges, "
            "solutions, and notes for the coordinator."
        )
    elif kind == "observation":
        prompt = (
            "Create a blank lesson observation form for peer or coordinator observation "
            "of a language lesson. Use a checklist + short comment boxes: lesson staging, "
            "instructions, boardwork, error correction, interaction patterns, time management, "
            "use of L1, classroom management, and overall comments."
        )
    elif kind == "progression":
        prompt = (
            "Create a blank progression tracking template for a CEIL teacher over 4 weeks. "
            "Include: group, level, book, units planned, units completed, attendance %, "
            "main difficulties, actions taken, and coordinator feedback."
        )
    elif kind == "rubric":
        prompt = (
            "Create a speaking assessment rubric (A1–B2) with 4 criteria: range & accuracy, "
            "fluency, pronunciation, interaction. Each criterion has 4 bands (1–4) with descriptors."
        )
    else:
        return await interaction.followup.send(
            "Use one of: `plan`, `report`, `observation`, `progression`, `rubric`.",
            ephemeral=True,
        )

    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


###############################################################
# 18. COORDINATION & PROGRESSION SUPPORT
###############################################################

@bot.tree.command(
    name="session_report",
    description="Generate a polished summary of a session based on your notes."
)
@app_commands.describe(
    raw_notes="Paste your rough notes (what you did, what went well, challenges, etc.)."
)
async def session_report_slash(interaction: discord.Interaction, raw_notes: str):
    """
    Takes rough notes from a teacher and outputs a clean, professional session report.
    """
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message("Lesson tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    prompt = (
        "Transform the following rough teacher notes into a clear, professional CEIL session report. "
        "Structure it into: Context (group, level, unit), Summary of lesson, Student engagement, "
        "Main difficulties, Actions taken/next steps.\n\n"
        f"Raw notes:\n{raw_notes}"
    )
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


@bot.tree.command(
    name="homework",
    description="Generate a homework task aligned with level and topic."
)
@app_commands.describe(
    level="CEFR level (A1–B2, etc.)",
    topic="Topic or grammar point",
    skills="Skills to target, e.g. writing, speaking, reading"
)
async def homework_slash(
    interaction: discord.Interaction,
    level: str,
    topic: str,
    skills: str = "writing",
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message("Lesson tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    prompt = (
        f"Create a homework task for ESL learners at level {level}, "
        f"on topic '{topic}', focusing on the following skills: {skills}.\n"
        "Include clear instructions for students, the expected length/output, "
        "and simple criteria for how the teacher will assess it."
    )
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


@bot.tree.command(
    name="dialogue",
    description="Generate a classroom-ready dialogue for speaking practice."
)
@app_commands.describe(
    level="CEFR level",
    topic="Theme (e.g. at the doctor, job interview, travel, complaints)",
    length="Approximate number of exchanges"
)
async def dialogue_slash(
    interaction: discord.Interaction,
    level: str,
    topic: str,
    length: int = 10,
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message("Lesson tools are disabled.", ephemeral=True)

    if length <= 0:
        length = 8

    await interaction.response.defer(thinking=True)
    prompt = (
        f"Create a classroom-ready dialogue for ESL learners at level {level} "
        f"on the theme '{topic}'.\n"
        f"Use around {length} exchanges (turns). Label speakers as A and B. "
        "Keep language natural, level-appropriate, and suitable for role-play in class."
    )
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


@bot.tree.command(
    name="observation_form",
    description="Generate a customized observation checklist for a specific focus."
)
@app_commands.describe(
    focus="What is the main observation focus? (e.g. instructions, speaking practice, feedback)"
)
async def observation_form_slash(
    interaction: discord.Interaction,
    focus: str,
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message("Lesson tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    prompt = (
        "Create a short, practical lesson observation checklist for a language lesson. "
        f"The main focus is: {focus}. Include 10–12 checklist items plus a section for comments and suggestions."
    )
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


###############################################################
# 19. EMAIL & PROFESSIONAL WRITING SUPPORT
###############################################################

@bot.tree.command(
    name="email_teacher",
    description="Draft a professional email from coordinator to teacher(s)."
)
@app_commands.describe(
    purpose="Purpose of the email (e.g. remind progression report, invite to meeting)",
    details="Key points or context to include"
)
async def email_teacher_slash(
    interaction: discord.Interaction,
    purpose: str,
    details: str,
):
    if not config.get("lessons_enabled", True) and not config.get("research_enabled", True):
        return await interaction.response.send_message("Writing tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    prompt = (
        "Write a professional, clear, and concise email from a CEIL coordinator to teacher(s).\n"
        f"Purpose: {purpose}\n"
        f"Details: {details}\n"
        "Use a polite yet direct tone, include a clear subject line, and end with a formal closing."
    )
    text = await admin_llm(prompt)
    await interaction.followup.send(text)


@bot.tree.command(
    name="email_director",
    description="Draft a professional email/report to the Director."
)
@app_commands.describe(
    purpose="Purpose (e.g. submit report, request resources, highlight issues)",
    details="Key points, data or arguments to include"
)
async def email_director_slash(
    interaction: discord.Interaction,
    purpose: str,
    details: str,
):
    if not config.get("lessons_enabled", True) and not config.get("research_enabled", True):
        return await interaction.response.send_message("Writing tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    prompt = (
        "Write a professional email from a CEIL coordinator to the Director. "
        "The email may function as a cover letter to a longer report.\n"
        f"Purpose: {purpose}\n"
        f"Details / points to mention: {details}\n"
        "Use formal institutional tone, clear structure (introduction, main points, conclusion), "
        "and end with a formal closing and signature line."
    )
    text = await admin_llm(prompt)
    await interaction.followup.send(text)


###############################################################
# 20. TEXT ANALYSIS — STUDENT OUTPUT, FEEDBACK, CORRECTION
###############################################################

@bot.tree.command(
    name="analyze_student_text",
    description="Analyze a learner's text and give feedback + suggested corrections."
)
@app_commands.describe(
    level="Student's approximate level (A1–B2, etc.)",
    text="Paste the student's text here."
)
async def analyze_student_text_slash(
    interaction: discord.Interaction,
    level: str,
    text: str,
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message("Student analysis tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    prompt = (
        f"A language learner at level {level} wrote the following text:\n\n"
        f"{text}\n\n"
        "1) Give overall feedback on content, organization, and clarity.\n"
        "2) Point out the most important grammar/vocabulary issues.\n"
        "3) Suggest a corrected version of the text.\n"
        "Use simple, teacher-friendly language."
    )
    result = await teacher_llm(prompt)
    await interaction.followup.send(result)


@bot.tree.command(
    name="improve_writing",
    description="Improve a draft email or paragraph while keeping the ideas."
)
@app_commands.describe(
    text="Draft text to improve (email, paragraph, report section)",
    tone="Tone: formal/semi-formal/neutral"
)
async def improve_writing_slash(
    interaction: discord.Interaction,
    text: str,
    tone: str = "formal",
):
    if not config.get("lessons_enabled", True) and not config.get("research_enabled", True):
        return await interaction.response.send_message("Writing tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    prompt = (
        "Improve the following text in English. Keep the same meaning but make it clearer, "
        f"more coherent, and appropriate for a {tone} tone.\n\n"
        f"Original text:\n{text}"
    )
    result = await admin_llm(prompt)
    await interaction.followup.send(result)


###############################################################
# END OF CHUNK 3
###############################################################

print("📦 Loaded CHUNK 3 (AI engine + teacher/coordination suite)")
###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 4/8)
# RESEARCH & ACADEMIC SUPPORT SYSTEM
###############################################

###############################################################
# 21. Research-Focused LLM Helper
###############################################################

async def research_llm(prompt: str, temp: float = 0.25) -> str:
    """
    High-precision academic writing generator.
    Optimized for clarity, structure, and research language.
    """
    system_prompt = (
        BASE_SYSTEM_PROMPT
        + "\n\nYou are now in ACADEMIC / RESEARCH ASSISTANT MODE.\n"
        "You specialize in:\n"
        "- Applied linguistics\n"
        "- Sociolinguistics\n"
        "- English language teaching\n"
        "- Academic writing & research methodology\n"
        "- Literature review synthesis\n\n"
        "Always provide structured, coherent, and logically connected academic output.\n"
    )

    result = await call_openai(system_prompt, prompt, temperature=temp)
    return result


###############################################################
# 22. /article_summary — Summaries in academic style
###############################################################

@bot.tree.command(
    name="article_summary",
    description="Summarize a research article (text, abstract, or pasted excerpt)."
)
@app_commands.describe(
    text="Paste the abstract, introduction, or main content to summarize."
)
async def article_summary_cmd(interaction: discord.Interaction, text: str):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        "Summarize the following academic text using a formal tone and clear structure.\n"
        "Use this format:\n"
        "1. Research Problem & Aim\n"
        "2. Theoretical Background\n"
        "3. Methodology\n"
        "4. Key Findings\n"
        "5. Implications for ELT / Applied Linguistics\n\n"
        f"TEXT:\n{text}"
    )

    result = await research_llm(prompt)
    await interaction.followup.send(result)


###############################################################
# 23. /research_outline — MA/PhD style outlines
###############################################################

@bot.tree.command(
    name="research_outline",
    description="Generate a research plan/outline (MA/PhD/Article)."
)
@app_commands.describe(
    topic="Research topic or question",
    level="MA, PhD, or Article"
)
async def research_outline_cmd(
    interaction: discord.Interaction,
    topic: str,
    level: str = "MA",
):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        f"Create a detailed {level.upper()}-level research outline on the topic:\n"
        f"'{topic}'.\n\n"
        "Include:\n"
        "1. Background & Rationale\n"
        "2. Problem Statement\n"
        "3. Research Questions (RQs)\n"
        "4. Hypotheses (if applicable)\n"
        "5. Literature Review Structure\n"
        "6. Methodology (Design, participants, tools, procedures)\n"
        "7. Data Analysis Plan\n"
        "8. Expected Contributions\n"
        "9. Limitations & Ethical Considerations\n"
    )

    result = await research_llm(prompt)
    await interaction.followup.send(result)


###############################################################
# 24. /compare_theories — Compare academic schools of thought
###############################################################

@bot.tree.command(
    name="compare_theories",
    description="Compare two theories or scholars academically."
)
@app_commands.describe(
    theory1="First theory or scholar",
    theory2="Second theory or scholar"
)
async def compare_theories_slash(
    interaction: discord.Interaction,
    theory1: str,
    theory2: str,
):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        f"Compare the following two academic theories/scholars:\n"
        f"1. {theory1}\n"
        f"2. {theory2}\n\n"
        "Use this structure:\n"
        "- Overview of each\n"
        "- Core assumptions\n"
        "- Methods or approach\n"
        "- Strengths & limitations\n"
        "- Points of convergence/divergence\n"
        "- Relevance in applied linguistics/ELT\n"
        "- Final synthesis paragraph"
    )

    output = await research_llm(prompt)
    await interaction.followup.send(output)


###############################################################
# 25. /apa_cite — APA-style citation generator
###############################################################

@bot.tree.command(
    name="apa_cite",
    description="Generate an APA-style citation for a book, article, website, etc."
)
@app_commands.describe(
    source="Provide a title, DOI, link, or bibliographic details"
)
async def apa_cite_slash(interaction: discord.Interaction, source: str):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        "Generate an APA 7th edition reference based on the following source.\n"
        "If information is missing, intelligently infer typical details.\n"
        "Source:\n" + source
    )

    output = await research_llm(prompt)
    await interaction.followup.send(output)


###############################################################
# 26. /explain_theory — Explain difficult concepts
###############################################################

@bot.tree.command(
    name="explain_theory",
    description="Explain a linguistic or research concept in clear academic terms."
)
@app_commands.describe(
    concept="Concept to explain (e.g. Labov's variation theory, critical period hypothesis)"
)
async def explain_theory_slash(interaction: discord.Interaction, concept: str):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        f"Explain the following academic concept clearly and concisely:\n"
        f"{concept}\n\n"
        "Use:\n"
        "- Definition\n"
        "- Key scholars\n"
        "- Applications in applied linguistics / ELT\n"
        "- Example"
    )

    result = await research_llm(prompt)
    await interaction.followup.send(result)


###############################################################
# 27. /translate_academic — Translate text into academic English
###############################################################

@bot.tree.command(
    name="translate_academic",
    description="Translate any text into academic, formal English."
)
@app_commands.describe(text="Paste text in Arabic, French, Darija, or any language.")
async def translate_academic_slash(interaction: discord.Interaction, text: str):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        "Translate the following text into PROFESSIONAL ACADEMIC ENGLISH.\n"
        "The translation must be formal, coherent, and lexically rich.\n\n"
        f"TEXT:\n{text}"
    )

    result = await research_llm(prompt)
    await interaction.followup.send(result)


###############################################################
# 28. /evaluate_paper — Critical evaluation of a study
###############################################################

@bot.tree.command(
    name="evaluate_paper",
    description="Critically evaluate a research paper/excerpt."
)
@app_commands.describe(text="Paste the abstract or summary to evaluate.")
async def evaluate_paper_slash(interaction: discord.Interaction, text: str):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        "Critically evaluate the following research text.\n"
        "Provide:\n"
        "1. Strengths\n"
        "2. Weaknesses\n"
        "3. Methodological concerns\n"
        "4. Contribution to the field\n"
        "5. Suggestions for improvement\n\n"
        f"TEXT:\n{text}"
    )

    output = await research_llm(prompt)
    await interaction.followup.send(output)


###############################################################
# 29. /literature_review — Generate structured mini literature review
###############################################################

@bot.tree.command(
    name="literature_review",
    description="Generate a short literature review for a given topic."
)
@app_commands.describe(topic="Research topic to review.")
async def literature_review_slash(interaction: discord.Interaction, topic: str):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        f"Write a structured mini literature review (400–600 words) on:\n"
        f"{topic}\n\n"
        "Include:\n"
        "- Key foundational studies\n"
        "- Current debates\n"
        "- Gaps in the literature\n"
        "- How future research can address these gaps"
    )

    result = await research_llm(prompt)
    await interaction.followup.send(result)


###############################################################
# 30. /supervisor_feedback — Supervisor-style feedback
###############################################################

@bot.tree.command(
    name="supervisor_feedback",
    description="Provide MA supervisor-style feedback on a research idea."
)
@app_commands.describe(text="Describe your idea or proposal.")
async def supervisor_feedback_slash(interaction: discord.Interaction, text: str):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        "Provide constructive, supervisor-style academic feedback on the following proposal. "
        "Make comments on clarity, feasibility, originality, variables, methodology, "
        "and scope.\n\n"
        f"IDEA:\n{text}"
    )

    result = await research_llm(prompt)
    await interaction.followup.send(result)


###############################################################
# 31. PDF TEXT ANALYZER (Simple text extractor)
###############################################################

@bot.tree.command(
    name="analyze_pdf",
    description="Analyze text extracted from a PDF (paste the extracted text)."
)
@app_commands.describe(text="Paste extracted text from a PDF.")
async def analyze_pdf_slash(interaction: discord.Interaction, text: str):
    if not config.get("research_enabled", True):
        return await interaction.response.send_message("Research tools disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    prompt = (
        "Analyze the following academic PDF-extracted text.\n"
        "Provide:\n"
        "1. Summary\n"
        "2. Methodology\n"
        "3. Theoretical framing\n"
        "4. Main findings\n"
        "5. Limitations\n"
        "6. Implications\n\n"
        f"TEXT:\n{text}"
    )

    result = await research_llm(prompt)
    await interaction.followup.send(result)


###############################################################
# END OF CHUNK 4
###############################################################

print("📦 Loaded CHUNK 4 (Advanced research & academic tools)")
# === Safety reset to avoid duplicate fun commands ===
for cmd in ["hangman", "guess", "blackjack", "hit", "stand", "trivia", "answer"]:
    if cmd in bot.commands:
        bot.remove_command(cmd)
###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 5/8)
# FUN INTERACTION ENGINE (GAMES + SOCIAL TOOLS)
###############################################

###############################################################
# 32. BLACKJACK FULL ENGINE
###############################################################

blackjack_sessions: dict[int, dict] = {}  # user_id -> {player, dealer}


def bj_draw_card():
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    suits = ["♠", "♥", "♦", "♣"]
    return random.choice(ranks), random.choice(suits)


def bj_hand_value(cards):
    total = 0
    aces = 0
    for r, _ in cards:
        if r in ["J", "Q", "K"]:
            total += 10
        elif r == "A":
            total += 11
            aces += 1
        else:
            total += int(r)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def bj_format(cards):
    return " ".join(f"{r}{s}" for r, s in cards)


@bot.command(name="blackjack")
async def blackjack_cmd(ctx: commands.Context):
    """
    Start a blackjack game.
    """
    if not config.get("fun_enabled", True):
        return await ctx.reply("🎮 Fun commands are disabled.", mention_author=False)

    uid = ctx.author.id

    player = [bj_draw_card(), bj_draw_card()]
    dealer = [bj_draw_card(), bj_draw_card()]
    blackjack_sessions[uid] = {"player": player, "dealer": dealer}

    msg = (
        f"🃏 **Blackjack** 🃏\n\n"
        f"**Your hand:** {bj_format(player)} (value: {bj_hand_value(player)})\n"
        f"**Dealer shows:** {bj_format([dealer[0]])}\n\n"
        "Type `!hit` to draw or `!stand` to hold."
    )

    await ctx.reply(msg, mention_author=False)


@bot.command(name="hit")
async def blackjack_hit_cmd(ctx: commands.Context):
    uid = ctx.author.id
    if uid not in blackjack_sessions:
        return await ctx.reply("No active blackjack game. Start one with `!blackjack`.")

    game = blackjack_sessions[uid]
    game["player"].append(bj_draw_card())
    val = bj_hand_value(game["player"])

    if val > 21:
        msg = (
            f"💥 **Bust!**\n"
            f"Your hand: {bj_format(game['player'])} ({val})\n"
            "You lose."
        )
        blackjack_sessions.pop(uid, None)
    else:
        msg = (
            f"Your hand: {bj_format(game['player'])} (value: {val})\n"
            "Type `!hit` or `!stand`."
        )

    await ctx.reply(msg, mention_author=False)


@bot.command(name="stand")
async def blackjack_stand_cmd(ctx: commands.Context):
    uid = ctx.author.id
    if uid not in blackjack_sessions:
        return await ctx.reply("No active blackjack game. Start with `!blackjack`.")

    game = blackjack_sessions[uid]
    dealer = game["dealer"]
    player = game["player"]

    while bj_hand_value(dealer) < 17:
        dealer.append(bj_draw_card())

    pv = bj_hand_value(player)
    dv = bj_hand_value(dealer)

    msg = (
        f"**Your hand:** {bj_format(player)} ({pv})\n"
        f"**Dealer hand:** {bj_format(dealer)} ({dv})\n\n"
    )

    if dv > 21 or pv > dv:
        msg += "🎉 **You win!**"
        add_xp(ctx.author.id, 20)  # XP BONUS
    elif pv == dv:
        msg += "➖ **Push (draw).**"
    else:
        msg += "❌ **Dealer wins.**"

    blackjack_sessions.pop(uid, None)
    await ctx.reply(msg, mention_author=False)
###############################################################
# 33. HANGMAN ENGINE
###############################################################

hangman_games: dict[int, dict] = {}  # user_id -> game state

HANGMAN_WORDS = [
    "teacher", "language", "grammar", "vocabulary", "progression",
    "assessment", "classroom", "listening", "speaking", "reading",
    "writing", "phonology", "syllabus", "research", "discourse"
]


def hide_word(word, guesses):
    return " ".join([c if c in guesses else "_" for c in word])


@bot.command(name="hangman")
async def hangman_cmd(ctx: commands.Context):
    """
    Start a Hangman game.
    """
    if not config.get("fun_enabled", True):
        return await ctx.reply("Fun commands are disabled.", mention_author=False)

    word = random.choice(HANGMAN_WORDS)
    hangman_games[ctx.author.id] = {
        "word": word,
        "guesses": set(),
        "fails": 0,
        "max_fails": 6,
    }

    masked = hide_word(word, set())
    await ctx.reply(
        f"🎯 **Hangman started!**\nWord: `{masked}`\nGuess a letter with `!guess <letter>`",
        mention_author=False
    )


@bot.command(name="guess")
async def hangman_guess(ctx: commands.Context, letter: str):
    uid = ctx.author.id
    if uid not in hangman_games:
        return await ctx.reply("No active Hangman game. Start with `!hangman`.")

    game = hangman_games[uid]

    if len(letter) != 1 or not letter.isalpha():
        return await ctx.reply("Please guess *one letter*.")

    letter = letter.lower()

    if letter in game["guesses"]:
        return await ctx.reply("You already guessed that letter.")

    game["guesses"].add(letter)

    if letter not in game["word"]:
        game["fails"] += 1

        if game["fails"] >= game["max_fails"]:
            word = game["word"]
            hangman_games.pop(uid)
            return await ctx.reply(
                f"💀 **You lost!** The word was: `{word}`"
            )

    masked = hide_word(game["word"], game["guesses"])

    if "_" not in masked:
        word = game["word"]
        hangman_games.pop(uid)
        add_xp(ctx.author.id, 30)  # XP reward
        return await ctx.reply(
            f"🎉 **You won!** The word was `{word}`. (+30 XP!)"
        )

    await ctx.reply(
        f"`{masked}` — fails: {game['fails']}/{game['max_fails']}",
        mention_author=False
    )
###############################################################
# 34. TRIVIA ENGINE
###############################################################

# Trivia database
TRIVIA = {
    "elt": [
        ("What does CEFR stand for?", "Common European Framework of Reference"),
        ("What skill does PPP primarily teach?", "Speaking"),
        ("What is the first stage in PPP?", "Presentation"),
        ("What does CLT stand for?", "Communicative Language Teaching"),
        ("What does EAP stand for?", "English for Academic Purposes"),
    ],
    "general": [
        ("What is the capital of Japan?", "Tokyo"),
        ("How many continents are there?", "7"),
        ("Who wrote '1984'?", "George Orwell"),
        ("What gas do plants breathe in?", "Carbon dioxide"),
        ("What is the fastest land animal?", "Cheetah"),
    ]
}

active_trivia = {}  # user_id -> correct answer


@bot.command(name="trivia")
async def trivia_cmd(ctx: commands.Context, category: str = "general"):
    """
    Start a trivia question (general or ELT).
    """
    if not config.get("fun_enabled", True):
        return await ctx.reply("Fun commands are disabled.")

    category = category.lower()
    if category not in TRIVIA:
        category = "general"

    q, a = random.choice(TRIVIA[category])
    active_trivia[ctx.author.id] = a.lower()

    await ctx.reply(f"🧠 **Trivia ({category})**\n{q}\nType your answer with `!answer <text>`")
@bot.command(name="answer")
async def trivia_answer_cmd(ctx: commands.Context, *, response: str):
    uid = ctx.author.id
    if uid not in active_trivia:
        return await ctx.reply("You don't have an active trivia question.")

    correct = active_trivia.pop(uid)

    if response.lower().strip() == correct:
        add_xp(uid, 25)
        return await ctx.reply(f"🎉 Correct! (+25 XP)")
    else:
        return await ctx.reply(f"❌ Incorrect. The correct answer was: **{correct}**.")
###############################################################
# 35. STORY GENERATOR
###############################################################

@bot.tree.command(
    name="story",
    description="Generate a short creative story (fun practice)."
)
@app_commands.describe(
    topic="Story topic (e.g. mystery, classroom, travel)",
    length="Short/medium/long"
)
async def story_slash(interaction: discord.Interaction, topic: str, length: str = "short"):
    if not config.get("fun_enabled", True):
        return await interaction.response.send_message("Fun commands disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    length_map = {
        "short": 120,
        "medium": 250,
        "long": 400,
    }
    target = length_map.get(length.lower(), 120)

    prompt = (
        f"Write a creative story (~{target} words) on the theme '{topic}'. "
        "Use simple but engaging language appropriate for ESL learners."
    )

    result = await call_openai(BASE_SYSTEM_PROMPT, prompt)
    await interaction.followup.send(result)
###############################################################
# 36. SIMPLE FUN COMMANDS
###############################################################

@bot.command(name="roll")
async def roll_cmd(ctx: commands.Context, sides: int = 6):
    if sides < 2:
        sides = 6
    value = random.randint(1, sides)
    await ctx.reply(f"🎲 You rolled **{value}** (1–{sides}).", mention_author=False)


@bot.command(name="flip")
async def flip_cmd(ctx: commands.Context):
    await ctx.reply(f"🪙 {random.choice(['Heads', 'Tails'])}!", mention_author=False)


@bot.command(name="choose")
async def choose_cmd(ctx: commands.Context, *, options: str):
    items = [x.strip() for x in options.split("|") if x.strip()]
    if len(items) < 2:
        return await ctx.reply("Provide options separated by `|`.")
    await ctx.reply(f"🎯 I choose: **{random.choice(items)}**")
###############################################################
# 37. MOTIVATION & COMPLIMENTS
###############################################################

COMPLIMENTS = [
    "You're doing amazing work at CEIL!",
    "Your students are lucky to have you.",
    "Your dedication shows.",
    "Keep going — you're growing every day.",
    "You're making a real difference.",
]

@bot.command(name="compliment")
async def compliment_cmd(ctx: commands.Context, member: discord.Member | None = None):
    member = member or ctx.author
    await ctx.reply(
        f"💙 {member.mention}, {random.choice(COMPLIMENTS)}",
        mention_author=False
    )
###############################################################
# 38. EASTER EGGS
###############################################################

@bot.command(name="ceilsecret")
async def ceilsecret_cmd(ctx):
    xp = random.randint(50, 200)
    add_xp(ctx.author.id, xp)
    await ctx.reply(f"🥚 You found a CEIL Easter Egg! (+{xp} XP)")
print("📦 Loaded CHUNK 5 (Fun engine + games + creative tools)")
###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 6/8)
# ADMIN & COORDINATION SUITE
###############################################

###############################################################
# 39. ATTACH PREVIOUS ADMIN EXTENSIONS (from Chunk 2)
###############################################################
# At this point, admin_group and admin_slash_extensions already exist
# (they were defined in Chunk 2). Now we attach the registered
# purge/slowmode slash commands.

for ext_func in admin_slash_extensions:
    try:
        admin_group.add_command(ext_func)
    except Exception:
        # If already added or something else, ignore.
        pass

###############################################################
# 40. ADMIN BROADCAST + ANNOUNCEMENTS
###############################################################

@admin_group.command(
    name="announce",
    description="Post an announcement in the current channel as CEIL Bot."
)
@app_commands.describe(
    title="Title of the announcement",
    message="Main content/body of the announcement",
    ping_everyone="Ping @everyone?"
)
async def admin_announce_slash(
    interaction: discord.Interaction,
    title: str,
    message: str,
    ping_everyone: bool = False,
):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)

    embed = make_embed(title=title, description=message, color=discord.Color.orange())
    mention_text = "@everyone " if ping_everyone else ""

    try:
        await interaction.channel.send(mention_text, embed=embed)
        await interaction.followup.send("✅ Announcement posted.", ephemeral=True)
        await log_event(
            interaction.guild,
            f"📢 Announcement by {user} in {interaction.channel}: {title}",
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to send announcement: {e}", ephemeral=True)


@admin_group.command(
    name="dm_all",
    description="DM a message to all members with a specific role."
)
@app_commands.describe(
    role_name="Name of the role to DM (e.g. Teacher)",
    message="Message to send in the DM"
)
async def admin_dm_all_slash(
    interaction: discord.Interaction,
    role_name: str,
    message: str,
):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)

    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if not role:
        return await interaction.followup.send(f"Role `{role_name}` not found.", ephemeral=True)

    sent = 0
    failed = 0

    for member in interaction.guild.members:
        if role in member.roles and not member.bot:
            try:
                await member.send(message)
                sent += 1
                await asyncio.sleep(0.3)  # avoid rate limits
            except Exception:
                failed += 1

    await interaction.followup.send(
        f"✅ DM campaign completed. Sent: {sent}, failed: {failed}.",
        ephemeral=True,
    )
    await log_event(
        interaction.guild,
        f"✉ DM-all by {user} to role {role_name}: sent={sent}, failed={failed}",
    )


###############################################################
# 41. AUTO SERVER STRUCTURE BUILDER (CEIL DISCORD)
###############################################################

CEIL_STRUCTURE = {
    "Coordination & Admin": [
        "📌-announcements",
        "🗂-coordination-hub",
        "🧾-reports-progress",
        "🧠-teacher-lounge",
    ],
    "Resources": [
        "📚-lesson-plans",
        "📎-materials-sharing",
        "🧪-assessment-bank",
        "🎧-listening-links",
    ],
    "Levels & Groups": [
        "a1-a2-teachers",
        "b1-b2-teachers",
        "multi-level-ideas",
    ],
    "Support & Tech": [
        "⚙️-bot-support",
        "❓-questions-help",
    ],
}


@admin_group.command(
    name="create_structure",
    description="Create recommended CEIL categories and channels."
)
async def admin_create_structure_slash(interaction: discord.Interaction):
    user = interaction.user
    guild = interaction.guild

    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)

    created_categories = 0
    created_channels = 0

    for category_name, channels in CEIL_STRUCTURE.items():
        # Check if category exists
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            try:
                category = await guild.create_category(category_name)
                created_categories += 1
            except Exception as e:
                print(f"❌ Failed to create category {category_name}: {e}")
                continue

        # Create channels if missing
        for ch_name in channels:
            existing = discord.utils.get(category.text_channels, name=ch_name)
            if existing:
                continue
            try:
                await guild.create_text_channel(ch_name, category=category)
                created_channels += 1
            except Exception as e:
                print(f"❌ Failed to create channel {ch_name}: {e}")

    await interaction.followup.send(
        f"🏗 Structure sync complete. Categories created: {created_categories}, Channels created: {created_channels}.",
        ephemeral=True,
    )
    await log_event(
        guild,
        f"🏗 CEIL structure updated by {user}. "
        f"Categories created: {created_categories}, Channels created: {created_channels}.",
    )


###############################################################
# 42. TEACHER REGISTRATION & PROGRESSION TRACKING
###############################################################

TEACHER_PROGRESS_FILE = "teacher_progress.json"
teacher_progress: dict = {}  # {guild_id: {user_id: {...info...}}}


def load_teacher_progress():
    global teacher_progress
    if os.path.exists(TEACHER_PROGRESS_FILE):
        try:
            with open(TEACHER_PROGRESS_FILE, "r", encoding="utf-8") as f:
                teacher_progress = json.load(f)
        except Exception:
            teacher_progress = {}
    else:
        teacher_progress = {}


def save_teacher_progress():
    try:
        with open(TEACHER_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(teacher_progress, f, indent=2)
    except Exception as e:
        print("❌ ERROR writing teacher_progress.json:", e)


def get_teacher_record(guild_id: int, user_id: int):
    gid = str(guild_id)
    uid = str(user_id)
    if gid not in teacher_progress:
        teacher_progress[gid] = {}
    if uid not in teacher_progress[gid]:
        teacher_progress[gid][uid] = {
            "name": "",
            "groups": [],
            "levels": [],
            "book": "",
            "notes": "",
            "progress_updates": []
        }
    return teacher_progress[gid][uid]


@bot.tree.command(
    name="teacher_register",
    description="Register your groups/levels so the coordinator can track progression."
)
@app_commands.describe(
    groups="Groups you teach (e.g. N4 G3, N5 G2)",
    levels="Levels (e.g. N4, N5, N6, N7)",
    book="Main coursebook or series (optional)"
)
async def teacher_register_slash(
    interaction: discord.Interaction,
    groups: str,
    levels: str,
    book: str = "",
):
    if not isinstance(interaction.user, discord.Member):
        return await interaction.response.send_message("Use this inside the server.", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)

    load_teacher_progress()
    rec = get_teacher_record(interaction.guild.id, interaction.user.id)
    rec["name"] = interaction.user.display_name
    rec["groups"] = [g.strip() for g in groups.split(",") if g.strip()]
    rec["levels"] = [l.strip() for l in levels.split(",") if l.strip()]
    if book:
        rec["book"] = book.strip()

    save_teacher_progress()

    await interaction.followup.send(
        "✅ Your teaching assignment has been registered/updated.",
        ephemeral=True,
    )
    await log_event(
        interaction.guild,
        f"🧑‍🏫 Teacher register/update: {interaction.user} — groups={rec['groups']}, levels={rec['levels']}, book={rec.get('book','')}",
    )


@bot.tree.command(
    name="progress_update",
    description="Submit a short progression update for your groups."
)
@app_commands.describe(
    summary="Brief summary: units covered, attendance, main issues."
)
async def progress_update_slash(
    interaction: discord.Interaction,
    summary: str,
):
    if not isinstance(interaction.user, discord.Member):
        return await interaction.response.send_message("Use this inside the server.", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)

    load_teacher_progress()
    rec = get_teacher_record(interaction.guild.id, interaction.user.id)
    update = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": summary,
    }
    rec["progress_updates"].append(update)
    save_teacher_progress()

    await interaction.followup.send("✅ Progression update saved.", ephemeral=True)
    await log_event(
        interaction.guild,
        f"📈 Progression update from {interaction.user}: {summary[:120]}...",
    )


@admin_group.command(
    name="progress_report",
    description="Get a compiled progression overview for all registered teachers."
)
async def progress_report_slash(interaction: discord.Interaction):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)

    load_teacher_progress()
    gid = str(interaction.guild.id)
    data = teacher_progress.get(gid, {})

    if not data:
        return await interaction.followup.send("No teacher progression data found yet.", ephemeral=True)

    lines = []
    for uid, rec in data.items():
        name = rec.get("name", f"User {uid}")
        groups = ", ".join(rec.get("groups", [])) or "—"
        levels = ", ".join(rec.get("levels", [])) or "—"
        book = rec.get("book", "—")
        updates = rec.get("progress_updates", [])
        last_update = updates[-1]["summary"] if updates else "No updates yet."

        lines.append(
            f"**{name}**\n"
            f"- Groups: {groups}\n"
            f"- Levels: {levels}\n"
            f"- Book: {book}\n"
            f"- Last update: {last_update[:200]}..."
        )

    report_text = "\n\n".join(lines)
    if len(report_text) > 1900:
        report_text = report_text[:1900] + "\n\n[Truncated…]"

    await interaction.followup.send(
        embed=make_embed(
            title="📊 CEIL Teacher Progression Overview",
            description=report_text,
            color=discord.Color.green(),
        ),
        ephemeral=True,
    )


###############################################################
# END OF CHUNK 6
###############################################################

print("📦 Loaded CHUNK 6 (Admin + coordination suite + progression tracking)")
###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 7/8)
# IMAGE ANALYSIS + PDF/FILE TOOLS + AI ON-MESSAGE ENGINE
###############################################

import io
import base64
from PIL import Image

###############################################################
# 43. VISION ENGINE — process image & describe it
###############################################################

async def analyze_image_openai(image_bytes: bytes):
    """
    Sends an image to OpenAI Vision model for analysis.
    Returns a structured description and extracted text.
    """
    try:
        img_base64 = base64.b64encode(image_bytes).decode("utf-8")

        system_prompt = (
            BASE_SYSTEM_PROMPT
            + "\n\nYou are now in IMAGE ANALYSIS MODE:\n"
            "- Describe the image\n"
            "- Extract any visible text (OCR-like)\n"
            "- Comment on quality, clarity, and layout\n"
            "- If the image contains student work, provide feedback\n"
        )

        response = client_oai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this image carefully."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                    ],
                },
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("❌ VISION API ERROR:", e)
        traceback.print_exc()
        return "⚠ Failed to analyze the image."


###############################################################
# 44. /analyze_image — Slash command
###############################################################

@bot.tree.command(
    name="analyze_image",
    description="Analyze an image (OCR + feedback + description)."
)
@app_commands.describe(
    image="Upload an image to analyze."
)
async def analyze_image_slash(interaction: discord.Interaction, image: discord.Attachment):
    if not config.get("images_enabled", True):
        return await interaction.response.send_message("Image tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    try:
        image_bytes = await image.read()
    except:
        return await interaction.followup.send("Failed to read the image.", ephemeral=True)

    result = await analyze_image_openai(image_bytes)
    await interaction.followup.send(result)


###############################################################
# 45. /extract_text — Extract visible text from image
###############################################################

@bot.tree.command(
    name="extract_text",
    description="Extract text from an uploaded image (OCR-style)."
)
@app_commands.describe(
    image="Upload an image containing text."
)
async def extract_text_slash(interaction: discord.Interaction, image: discord.Attachment):
    if not config.get("images_enabled", True):
        return await interaction.response.send_message("Image tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    try:
        img_bytes = await image.read()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    except:
        return await interaction.followup.send("Failed to process the image.", ephemeral=True)

    prompt = "Extract all visible text from the image as accurately as possible."

    try:
        response = client_oai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                    ],
                },
            ],
        )

        text = response.choices[0].message.content.strip()
        await interaction.followup.send(text)

    except Exception as e:
        print("❌ OCR ERROR:", e)
        await interaction.followup.send("Failed to extract text.", ephemeral=True)


###############################################################
# 46. /grade_handwriting — evaluate student writing from photo
###############################################################

@bot.tree.command(
    name="grade_handwriting",
    description="Evaluate student handwritten work from an image."
)
@app_commands.describe(
    image="Upload a photo of handwriting.",
    level="Student level (A1–B2)."
)
async def grade_handwriting_slash(
    interaction: discord.Interaction,
    image: discord.Attachment,
    level: str = "A2",
):
    if not config.get("images_enabled", True):
        return await interaction.response.send_message("Image tools are disabled.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    img_bytes = await image.read()
    analysis = await analyze_image_openai(img_bytes)

    prompt = (
        f"Based on the following extracted image analysis, provide feedback for a learner at level {level}.\n"
        f"Analysis:\n{analysis}\n\n"
        "- Identify grammar errors\n"
        "- Identify spelling issues\n"
        "- Suggest a corrected text\n"
        "- Give feedback in simple teacher-friendly tone\n"
    )

    result = await teacher_llm(prompt)
    await interaction.followup.send(result)


###############################################################
# 47. AI AUTO-REPLY ENGINE — on_message
###############################################################

@bot.event
async def on_message(msg: discord.Message):

    # 1. Ignore bot messages
    if msg.author.bot:
        return

    guild = msg.guild

    # 2. XP system: give XP for normal messages
    if config.get("xp_enabled", True):
        leveled_up, new_level = add_xp(msg.author.id, amount=5)
        if leveled_up:
            try:
                await msg.channel.send(
                    f"🎉 {msg.author.mention} leveled up! **Level {new_level}!**"
                )
            except:
                pass

    # 3. Moderation: banned words
    if config.get("moderation_enabled", True):
        lower_text = msg.content.lower()
        if any(bad in lower_text for bad in BANNED_WORDS):
            try:
                await msg.delete()
            except:
                pass
            await log_event(guild, f"🚨 Deleted banned word from {msg.author}")
            return

        # Anti-link filter
        if is_link(msg.content):
            if not is_staff(msg.author):
                try:
                    await msg.delete()
                except:
                    pass
                await log_event(guild, f"🔗 Blocked link from {msg.author}")
                return

        # Spam detection
        now = time.time()
        gid = guild.id if guild else 0
        uid = msg.author.id

        if gid not in spam_tracker:
            spam_tracker[gid] = {}
        if uid not in spam_tracker[gid]:
            spam_tracker[gid][uid] = []

        spam_tracker[gid][uid].append(now)

        spam_tracker[gid][uid] = [
            t for t in spam_tracker[gid][uid]
            if now - t <= SPAM_WINDOW_SECONDS
        ]

        if len(spam_tracker[gid][uid]) >= SPAM_MAX_MESSAGES:
            try:
                await apply_auto_mute(msg.author, guild, "Auto-spam detection")
            except:
                pass
            return

        # Slowmode enforcement
        ch = msg.channel
        if ch.id in slowmode_settings:
            delay = slowmode_settings[ch.id]
            key = (ch.id, uid)
            last = last_message_time.get(key, 0)
            if now - last < delay:
                try:
                    await msg.delete()
                except:
                    pass
                return
            last_message_time[key] = now

    # 4. Auto-AI response in channels with AI enabled
    if config.get("ai_enabled", True):

        # Only respond in text channels (avoid DMs)
        if msg.guild is not None:
            mode = channel_modes.get(msg.channel.id, config.get("ai_default_mode", "ceil"))
            content = msg.content.strip()

            # Ignore commands
            if content.startswith("!") or content.startswith("/"):
                return

            # Trigger AI only when addressed or in designated channels
            trigger = (
                msg.channel.name.startswith("ai-") or
                msg.content.lower().startswith("ceil") or
                f"<@{bot.user.id}>" in msg.content
            )

            if trigger:
                try:
                    await msg.channel.trigger_typing()
                except:
                    pass

                reply = await ai_general_reply(content, str(msg.author), mode)
                try:
                    await msg.reply(reply, mention_author=False)
                except:
                    await msg.channel.send(reply)

    # Allow commands to be processed
    await bot.process_commands(msg)

###############################################################
# END OF CHUNK 7
###############################################################

print("📦 Loaded CHUNK 7 (Vision + File tools + AI message engine)")
###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 8/8)
# MULTILINGUAL LAYER + FINAL on_ready + BOOT
###############################################

###############################################################
# 48. MULTILINGUAL INSTRUCTIONS & OVERRIDES
###############################################################

MULTILINGUAL_NOTE = """
You are working in a multilingual language center (CEIL). You MUST:

- Automatically detect the language of the user's last message.
- By default, RESPOND IN THE SAME LANGUAGE as that last user message.
- Supported and common languages include: English, French, German, Spanish, Turkish, Russian, Arabic,
  but you can handle others too.
- If the user explicitly asks for a different target language (e.g. "write this in French", "in German",
  "en espagnol", etc.), obey that request instead of mirroring the source language.
- When generating teaching materials (lesson plans, worksheets, quizzes, dialogues, homework, rubrics),
  respect any explicit language instructions (e.g. "worksheet in Spanish for A2", "dialogue in German").
- When no language is specified and the prompt is mixed, decide the most reasonable language based on the
  user’s main instruction and their own language use.
"""

# We now OVERRIDE the earlier helpers teacher_llm, admin_llm, research_llm, ai_general_reply
# so everything becomes multilingual-aware without changing all calling code.


async def teacher_llm(prompt: str) -> str:
    """
    Teacher/coordination oriented LLM with multilingual behavior.
    """
    system = (
        BASE_SYSTEM_PROMPT
        + "\n\nYou are now in TEACHER SUPPORT MODE.\n"
        "- Help with lesson plans, materials, assessment, progression, classroom management.\n"
        "- You understand CEFR (A1–C2) and CEIL levels (N1–N8) and can connect them.\n"
        + MULTILINGUAL_NOTE
    )
    return await call_openai(system, prompt, temperature=0.4)


async def admin_llm(prompt: str) -> str:
    """
    Admin/coordination writing helper with multilingual behavior.
    """
    system = (
        BASE_SYSTEM_PROMPT
        + "\n\nYou are now in ADMIN MODE.\n"
        "- Write emails, reports, memos, and official documents.\n"
        "- Keep a professional, concise tone adapted to the language.\n"
        + MULTILINGUAL_NOTE
    )
    return await call_openai(system, prompt, temperature=0.35)


async def research_llm(prompt: str, temp: float = 0.25) -> str:
    """
    Academic writing & research helper with multilingual behavior.
    """
    system = (
        BASE_SYSTEM_PROMPT
        + "\n\nYou are now in ACADEMIC / RESEARCH MODE.\n"
        "- Support MA/PhD work, articles, literature reviews, and methodology.\n"
        "- Use appropriate academic style for the target language.\n"
        + MULTILINGUAL_NOTE
    )
    return await call_openai(system, prompt, temperature=temp)


async def ai_general_reply(user_msg: str, user_name: str, mode: str) -> str:
    """
    General AI reply used by !ceil and auto AI in channels.
    Multilingual + mode-aware.
    """
    system_prompt = build_ai_system_prompt(mode) + "\n\n" + MULTILINGUAL_NOTE
    user_prompt = (
        f"User ({user_name}) wrote the following message. "
        "Detect their language and respond in that language unless they explicitly "
        "ask for a different output language.\n\n"
        f"{user_msg}"
    )
    return await call_openai(system_prompt, user_prompt, temperature=0.4)


###############################################################
# 49. FINAL on_ready — sync everything
###############################################################

@bot.event
async def on_ready():
    """
    Final on_ready handler:
    - Load config, XP, teacher progression
    - Attach /admin group commands
    - Sync the global command tree
    - Log a clear startup banner
    """
    # Load persistent data
    load_config()
    load_xp()
    # teacher_progress helpers exist from Chunk 6
    try:
        load_teacher_progress()
    except NameError:
        pass

    # Attach /admin group to the command tree (if not already)
    try:
        # If already added, override=True avoids duplication
        bot.tree.add_command(admin_group, override=True)
    except Exception:
        pass

    # Sync application commands
    try:
        await bot.tree.sync()
        synced_ok = True
    except Exception as e:
        print("❌ Error syncing slash commands:", e)
        synced_ok = False

    # Log banner
    print("===========================================")
    print(f"✅ CEIL FULL-MAX BOT READY as {bot.user} (ID: {bot.user.id})")
    print("Features:")
    print("- Multilingual AI (EN/FR/DE/ES/TR/RU/AR + others)")
    print("- Teacher suite (lesson plans, worksheets, quizzes, reports)")
    print("- Research suite (outlines, summaries, literature review, supervisor feedback)")
    print("- Admin suite (announcements, dm_all, structure builder, progression tracking)")
    print("- Moderation (spam, links, banned words, slowmode, warnings)")
    print("- Fun engine (blackjack, hangman, trivia, story generator, XP)")
    print("- Vision tools (image analysis, OCR, handwriting grading)")
    print(f"Slash commands synced: {synced_ok}")
    print("===========================================")


###############################################################
# 50. MAIN BOOTSTRAP
###############################################################

if __name__ == "__main__":
    # Ensure config and XP are available before login
    load_config()
    load_xp()
    try:
        load_teacher_progress()
    except NameError:
        pass

    print("🚀 Starting CEIL Full-Max Bot...")
    bot.run(DISCORD_TOKEN)
