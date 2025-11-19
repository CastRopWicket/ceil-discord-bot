###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 1/8)
# SYSTEM BOOT + CONFIG + UTILITIES + XP ENGINE
###############################################
from google.oauth2.service_account import Credentials as GoogleServiceAccountCredentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import json


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
from discord.ui import View, Button, Select
from discord import SelectOption

# =============== GOOGLE CENTER BASE CONFIG ==================

import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_APPLICATION_CREDENTIALS_BASE64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Google runtime flags
GOOGLE_READY = False
google_credentials = None
google_drive = None
google_calendar = None
google_youtube = None

# =============== LOAD GOOGLE SERVICES =======================

try:
    if GOOGLE_APPLICATION_CREDENTIALS_BASE64:
        decoded = base64.b64decode(GOOGLE_APPLICATION_CREDENTIALS_BASE64).decode("utf-8")
        creds_dict = json.loads(decoded)

        google_credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/youtube.force-ssl",
                "https://www.googleapis.com/auth/youtube.upload"
            ]
        )

        # Initialize clients
        google_drive = build("drive", "v3", credentials=google_credentials)
        google_calendar = build("calendar", "v3", credentials=google_credentials)
        google_youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        GOOGLE_READY = True
        print("✅ Google services initialized.")

    else:
        print("⚠ GOOGLE_APPLICATION_CREDENTIALS_BASE64 not set — Google Center disabled.")

except Exception as e:
    print(f"❌ Google initialization failed: {e}")
###############################################################
# GOOGLE CENTER (Drive + Calendar + YouTube)
###############################################################
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
GOOGLE_APPLICATION_CREDENTIALS_BASE64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64", "")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Runtime flags + service holders
GOOGLE_READY = False
google_credentials = None
google_drive = None
google_calendar = None
google_youtube = None

try:
    if GOOGLE_APPLICATION_CREDENTIALS_BASE64:
        decoded_json = base64.b64decode(GOOGLE_APPLICATION_CREDENTIALS_BASE64).decode("utf-8")
        creds_dict = json.loads(decoded_json)

        google_credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/youtube.force-ssl"
            ]
        )

        # Initialize Drive
        google_drive = build("drive", "v3", credentials=google_credentials)

        # Initialize Calendar
        google_calendar = build("calendar", "v3", credentials=google_credentials)

        # Initialize YouTube
        if YOUTUBE_API_KEY:
            google_youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        else:
            print("⚠ YOUTUBE_API_KEY not set — YouTube disabled.")

        GOOGLE_READY = True
        print("✅ Google services initialized.")
    else:
        print("⚠ GOOGLE_APPLICATION_CREDENTIALS_BASE64 not set — Google disabled.")

except Exception as e:
    GOOGLE_READY = False
    print(f"❌ Google initialization failed: {e}")


# ============ FIX: GUARANTEE admin_group ALWAYS EXISTS ============
# Some chunks load out of order during Railway hot reloads.
# This ensures admin_group exists BEFORE any decorators use it.

from discord import app_commands

try:
    admin_group
except NameError:
    admin_group = app_commands.Group(
        name="admin",
        description="Admin & Coordination Commands"
    )

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
# ===============================
# GOOGLE API AUTHENTICATION
# ===============================

GOOGLE_CREDS_ENV = os.getenv("GOOGLE_CREDS_JSON")

google_creds = None

def load_google_credentials():
    global google_creds

    if not GOOGLE_CREDS_ENV:
        print("⚠️ GOOGLE_CREDS_JSON not found in environment.")
        return None

    try:
        decoded = base64.b64decode(GOOGLE_CREDS_ENV)
        data = json.loads(decoded)
    except Exception:
        print("❌ Invalid GOOGLE_CREDS_JSON encoding.")
        return None

    try:
        creds = Credentials.from_authorized_user_info(data)
        google_creds = creds
        return creds
    except Exception as e:
        print("❌ Error loading Google credentials:", e)
        return None


def build_google_service(api_name, api_version):
    """
    Generic Google service builder, used for Drive, YouTube, Calendar, etc.
    """
    if google_creds is None:
        load_google_credentials()

    if google_creds:
        return build(api_name, api_version, credentials=google_creds)
    else:
        print("❌ Google credentials not available.")
        return None

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
# ================== ADMIN DASHBOARD V2 ==================

def build_admin_dashboard_embed() -> discord.Embed:
    """
    Build a snapshot of current config toggles for the dashboard.
    """
    feature_keys = [
        ("ai_enabled", "AI Engine / Chat"),
        ("moderation_enabled", "Moderation (filters, spam, links)"),
        ("xp_enabled", "XP / Level System"),
        ("fun_enabled", "Fun & Games"),
        ("lessons_enabled", "Teacher Lesson Tools"),
        ("research_enabled", "Research & Academic Tools"),
        ("images_enabled", "Vision / Image Tools"),
        ("logging_enabled", "Logging / #ceil-logs"),
        ("reminders_enabled", "Reminders"),
        ("polls_enabled", "Polls / Votes"),
    ]

    lines = []
    for key, label in feature_keys:
        val = config.get(key, DEFAULT_CONFIG.get(key, True))
        emoji = "🟢" if val else "🔴"
        lines.append(f"{emoji} **{label}** — `{key}` = `{val}`")

    desc = "\n".join(lines) or "No configuration loaded."

    embed = make_embed(
        title="🛠 CEIL Admin Dashboard v2",
        description=desc,
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="How to use",
        value=(
            "• Use the **select menu** below to toggle features ON/OFF.\n"
            "• Use **Edit Banned Words** to change filters.\n"
            "• Use **Reload / Save config** to sync with `config.json`.\n"
            "• For XP tools: `/admin xp_add`, `/admin xp_remove`, `/admin xp_set`, `/admin xp_show`."
        ),
        inline=False,
    )

    return embed
    # Discord UI components (must be imported BEFORE the dashboard)
from discord.ui import View, Button, Select, Modal, TextInput
from discord import TextStyle

class FeatureToggleSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="AI Engine", value="ai_enabled", description="Toggle AI auto-reply & /ceil"),
            discord.SelectOption(label="Moderation", value="moderation_enabled", description="Banned words, links, spam"),
            discord.SelectOption(label="XP System", value="xp_enabled", description="XP gain + levels"),
            discord.SelectOption(label="Fun & Games", value="fun_enabled", description="Blackjack, hangman, trivia, etc."),
            discord.SelectOption(label="Lessons Tools", value="lessons_enabled", description="Lesson plans, worksheets, quizzes"),
            discord.SelectOption(label="Research Tools", value="research_enabled", description="Research outlines, APA, reviews"),
            discord.SelectOption(label="Image / Vision", value="images_enabled", description="Image analysis, OCR, handwriting"),
            discord.SelectOption(label="Logging", value="logging_enabled", description="#ceil-logs events"),
            discord.SelectOption(label="Reminders", value="reminders_enabled", description="Reminder tools (if any)"),
            discord.SelectOption(label="Polls", value="polls_enabled", description="Poll / vote utilities"),
        ]
        super().__init__(
            placeholder="Select a feature to toggle…",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        current = config.get(key, DEFAULT_CONFIG.get(key, True))
        config[key] = not current
        save_config()

        embed = build_admin_dashboard_embed()
        await interaction.response.edit_message(
            content=f"✅ Toggled `{key}` → `{config[key]}`",
            embed=embed,
            view=self.view,
        )


class BannedWordsModal(Modal):
    def __init__(self):
        super().__init__(title="Edit Banned Words")

        default_text = ", ".join(BANNED_WORDS) if BANNED_WORDS else ""
        self.words = TextInput(
            label="Banned words (comma separated)",
            default=default_text,
            style=TextStyle.paragraph,
            required=False,
            max_length=400,
        )
        self.add_item(self.words)

    async def on_submit(self, interaction: discord.Interaction):
        global BANNED_WORDS, config
        raw = self.words.value or ""
        words = [w.strip().lower() for w in raw.split(",") if w.strip()]

        config["banned_words"] = words
        BANNED_WORDS = words
        save_config()

        await interaction.response.send_message(
            f"✅ Updated banned words: {', '.join(words) if words else 'none'}",
            ephemeral=True,
        )


class BannedWordsButton(Button):
    def __init__(self):
        super().__init__(
            label="Edit Banned Words",
            style=discord.ButtonStyle.danger,
            emoji="🚫",
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

        modal = BannedWordsModal()
        await interaction.response.send_modal(modal)


class ReloadConfigButton(Button):
    def __init__(self):
        super().__init__(
            label="Reload config.json",
            style=discord.ButtonStyle.secondary,
            emoji="🔁",
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

        load_config()
        embed = build_admin_dashboard_embed()
        await interaction.response.edit_message(
            content="✅ Reloaded configuration from disk.",
            embed=embed,
            view=self.view,
        )


class SaveConfigButton(Button):
    def __init__(self):
        super().__init__(
            label="Save to config.json",
            style=discord.ButtonStyle.success,
            emoji="💾",
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

        save_config()
        embed = build_admin_dashboard_embed()
        await interaction.response.edit_message(
            content="✅ Saved current configuration to `config.json`.",
            embed=embed,
            view=self.view,
        )


class AdminDashboardView(View):
    def __init__(self, invoker: discord.Member):
        super().__init__(timeout=600)
        self.invoker_id = invoker.id

        # Components
        self.add_item(FeatureToggleSelect())
        self.add_item(BannedWordsButton())
        self.add_item(ReloadConfigButton())
        self.add_item(SaveConfigButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Only the invoker (or other staff) can use this dashboard.
        """
        if interaction.user.id == self.invoker_id:
            return True
        if isinstance(interaction.user, discord.Member) and is_staff(interaction.user):
            return True

        await interaction.response.send_message(
            "❌ This dashboard session is not for you.",
            ephemeral=True,
        )
        return False


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
# ECONOMY SYSTEM — COINS FOR FUN FEATURES (BLACKJACK ETC.)
###############################################################

COINS_FILE = "coins_data.json"
coins_data: dict = {}  # { "user_id": { "coins": int, "last_daily": "ISO string or None" } }


def load_coins():
    global coins_data
    if os.path.exists(COINS_FILE):
        try:
            with open(COINS_FILE, "r", encoding="utf-8") as f:
                coins_data = json.load(f)
        except Exception:
            coins_data = {}
    else:
        coins_data = {}


def save_coins():
    try:
        with open(COINS_FILE, "w", encoding="utf-8") as f:
            json.dump(coins_data, f, indent=2)
    except Exception as e:
        print(f"❌ ERROR writing {COINS_FILE}: {e}")


def _ensure_coin_record(user_id: int):
    uid = str(user_id)
    if uid not in coins_data:
        coins_data[uid] = {
            "coins": 0,
            "last_daily": None,
        }
    return coins_data[uid]


def get_coins(user_id: int) -> int:
    rec = _ensure_coin_record(user_id)
    return int(rec.get("coins", 0))


def set_coins(user_id: int, amount: int):
    rec = _ensure_coin_record(user_id)
    rec["coins"] = max(0, int(amount))
    save_coins()


def add_coins(user_id: int, amount: int) -> int:
    rec = _ensure_coin_record(user_id)
    rec["coins"] = max(0, int(rec.get("coins", 0) + amount))
    save_coins()
    return rec["coins"]


def can_claim_daily(user_id: int, hours: int = 24) -> tuple[bool, float]:
    """
    Returns (can_claim, hours_left).
    """
    rec = _ensure_coin_record(user_id)
    last = rec.get("last_daily")
    if not last:
        return True, 0.0

    try:
        last_dt = datetime.fromisoformat(last)
    except Exception:
        return True, 0.0

    now = datetime.utcnow()
    diff_hours = (now - last_dt).total_seconds() / 3600.0
    if diff_hours >= hours:
        return True, 0.0
    return False, hours - diff_hours


def mark_daily_claimed(user_id: int):
    rec = _ensure_coin_record(user_id)
    rec["last_daily"] = datetime.utcnow().isoformat()
    save_coins()

    ###############################################################
# 8b. COINS SYSTEM (LIGHT ECONOMY FOR GAMES)
###############################################################

COINS_FILE = "coins_data.json"
coins_data: dict[str, dict] = {}   # { "user_id": { "coins": int, "last_daily": "YYYY-MM-DD" } }


def load_coins():
    """Load coins data from disk."""
    global coins_data
    if os.path.exists(COINS_FILE):
        try:
            with open(COINS_FILE, "r", encoding="utf-8") as f:
                coins_data = json.load(f)
        except Exception:
            coins_data = {}
    else:
        coins_data = {}


def save_coins():
    """Persist coins data."""
    try:
        with open(COINS_FILE, "w", encoding="utf-8") as f:
            json.dump(coins_data, f, indent=2)
    except Exception as e:
        print(f"❌ ERROR writing {COINS_FILE}: {e}")


def get_coins(user_id: int) -> int:
    """Return coin balance for user (0 if new)."""
    uid = str(user_id)
    if uid not in coins_data:
        coins_data[uid] = {"coins": 0, "last_daily": None}
    return int(coins_data[uid].get("coins", 0))


def set_coins(user_id: int, amount: int):
    """Hard set coin balance."""
    uid = str(user_id)
    if uid not in coins_data:
        coins_data[uid] = {"coins": 0, "last_daily": None}
    coins_data[uid]["coins"] = int(amount)
    save_coins()


def add_coins(user_id: int, amount: int) -> int:
    """Add (or subtract) coins; returns new balance."""
    uid = str(user_id)
    if uid not in coins_data:
        coins_data[uid] = {"coins": 0, "last_daily": None}
    coins_data[uid]["coins"] = int(coins_data[uid].get("coins", 0)) + int(amount)
    save_coins()
    return coins_data[uid]["coins"]


def can_claim_daily(user_id: int) -> bool:
    """True if user can claim today's daily reward."""
    uid = str(user_id)
    from datetime import datetime
    today = datetime.utcnow().date().isoformat()

    if uid not in coins_data:
        coins_data[uid] = {"coins": 0, "last_daily": None}
        return True

    last = coins_data[uid].get("last_daily")
    return last != today


def mark_daily_claim(user_id: int, amount: int) -> int:
    """Mark daily as claimed and add coins. Returns new balance."""
    uid = str(user_id)
    from datetime import datetime
    today = datetime.utcnow().date().isoformat()

    if uid not in coins_data:
        coins_data[uid] = {"coins": 0, "last_daily": None}

    coins_data[uid]["last_daily"] = today
    coins_data[uid]["coins"] = int(coins_data[uid].get("coins", 0)) + int(amount)
    save_coins()
    return coins_data[uid]["coins"]

    ###############################################################
# COIN SYSTEM (for Blackjack + future fun features)
###############################################################

COINS_FILE = "coins_data.json"
coins_data = {}   # { "user_id": coins_int }


def load_coins():
    """Load coins from disk."""
    global coins_data
    if os.path.exists(COINS_FILE):
        try:
            with open(COINS_FILE, "r", encoding="utf-8") as f:
                coins_data = json.load(f)
        except Exception:
            coins_data = {}
    else:
        coins_data = {}


def save_coins():
    """Persist coins to disk."""
    try:
        with open(COINS_FILE, "w", encoding="utf-8") as f:
            json.dump(coins_data, f, indent=2)
    except Exception as e:
        print(f"❌ ERROR writing {COINS_FILE}: {e}")


def get_coins(user_id: int) -> int:
    uid = str(user_id)
    return int(coins_data.get(uid, 0))


def set_coins(user_id: int, amount: int):
    uid = str(user_id)
    coins_data[uid] = max(0, int(amount))
    save_coins()


def add_coins(user_id: int, delta: int):
    uid = str(user_id)
    current = int(coins_data.get(uid, 0))
    coins_data[uid] = max(0, current + int(delta))
    save_coins()
    return coins_data[uid]

###############################################################
# GOOGLE CENTER (Drive + Calendar + YouTube)
###############################################################
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_APPLICATION_CREDENTIALS_BASE64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64", "")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

GOOGLE_READY = False
google_credentials = None
google_drive = None
google_calendar = None
google_youtube = None

try:
    if GOOGLE_APPLICATION_CREDENTIALS_BASE64:
        decoded_json = base64.b64decode(GOOGLE_APPLICATION_CREDENTIALS_BASE64).decode("utf-8")
        creds_dict = json.loads(decoded_json)

        google_credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/youtube.force-ssl"
            ]
        )

        google_drive = build("drive", "v3", credentials=google_credentials)
        google_calendar = build("calendar", "v3", credentials=google_credentials)

        if YOUTUBE_API_KEY:
            google_youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        else:
            print("⚠ YOUTUBE_API_KEY not set — YouTube disabled.")

        GOOGLE_READY = True
        print("✅ Google services initialized.")

    else:
        print("⚠ GOOGLE_APPLICATION_CREDENTIALS_BASE64 not set — Google Center disabled.")
except Exception as e:
    print("❌ Google initialization failed:", e)

###############################################################
# GOOGLE DRIVE COMMANDS
###############################################################

@bot.tree.command(name="gdrive_upload", description="Upload a file from Discord to Google Drive.")
async def gdrive_upload_slash(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.defer(thinking=True)

    drive = build_google_service("drive", "v3")
    if not drive:
        return await interaction.followup.send("Google Drive is not configured (check GOOGLE_SERVICE_ACCOUNT_JSON).", ephemeral=True)

    data = await file.read()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=file.content_type or "application/octet-stream", resumable=False)

    file_metadata = {"name": file.filename}
    try:
        created = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()
    except Exception as e:
        print("❌ Drive upload error:", e)
        return await interaction.followup.send("Failed to upload file to Drive.", ephemeral=True)

    link = created.get("webViewLink") or f"https://drive.google.com/file/d/{created['id']}/view"
    await interaction.followup.send(f"✅ Uploaded to Google Drive:\n{link}")


@bot.tree.command(name="gdrive_list", description="List your most recent files in Google Drive.")
async def gdrive_list_slash(interaction: discord.Interaction, limit: int = 5):
    await interaction.response.defer(thinking=True)

    drive = build_google_service("drive", "v3")
    if not drive:
        return await interaction.followup.send("Google Drive is not configured.", ephemeral=True)

    limit = max(1, min(limit, 10))

    try:
        result = drive.files().list(
            pageSize=limit,
            fields="files(id, name, webViewLink)",
            orderBy="modifiedTime desc"
        ).execute()
    except Exception as e:
        print("❌ Drive list error:", e)
        return await interaction.followup.send("Failed to list files from Drive.", ephemeral=True)

    files = result.get("files", [])
    if not files:
        return await interaction.followup.send("No files found on Drive.", ephemeral=True)

    lines = ["**Recent Google Drive files:**"]
    for f in files:
        name = f["name"]
        link = f.get("webViewLink") or f"https://drive.google.com/file/d/{f['id']}/view"
        lines.append(f"- [{name}]({link})")

    await interaction.followup.send("\n".join(lines))
###############################################################
# YOUTUBE COMMANDS
###############################################################

@bot.tree.command(name="gyt_search", description="Search YouTube videos.")
async def gyt_search_slash(interaction: discord.Interaction, query: str, limit: int = 5):
    await interaction.response.defer(thinking=True)

    yt = build_youtube_service()
    if not yt:
        return await interaction.followup.send("YouTube API not configured (check YOUTUBE_API_KEY).", ephemeral=True)

    limit = max(1, min(limit, 10))

    try:
        resp = yt.search().list(
            q=query,
            part="snippet",
            maxResults=limit,
            type="video"
        ).execute()
    except Exception as e:
        print("❌ YouTube search error:", e)
        return await interaction.followup.send("Failed to search YouTube.", ephemeral=True)

    items = resp.get("items", [])
    if not items:
        return await interaction.followup.send("No YouTube results found.", ephemeral=True)

    lines = [f"**YouTube results for:** `{query}`"]
    for it in items:
        title = it["snippet"]["title"]
        vid = it["id"]["videoId"]
        url = f"https://www.youtube.com/watch?v={vid}"
        lines.append(f"- [{title}]({url})")

    await interaction.followup.send("\n".join(lines))
###############################################################
# GOOGLE CALENDAR COMMANDS
###############################################################

@bot.tree.command(name="gcal_events", description="List upcoming Google Calendar events.")
async def gcal_events_slash(interaction: discord.Interaction, max_events: int = 5):
    await interaction.response.defer(thinking=True)

    cal = build_google_service("calendar", "v3")
    if not cal:
        return await interaction.followup.send("Google Calendar not configured.", ephemeral=True)

    max_events = max(1, min(max_events, 10))

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    try:
        events_result = cal.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_events,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
    except Exception as e:
        print("❌ Calendar list error:", e)
        return await interaction.followup.send("Failed to fetch calendar events.", ephemeral=True)

    events = events_result.get("items", [])
    if not events:
        return await interaction.followup.send("No upcoming events found.", ephemeral=True)

    lines = ["**Upcoming events (Google Calendar):**"]
    for ev in events:
        start = ev["start"].get("dateTime", ev["start"].get("date", ""))
        summary = ev.get("summary", "(no title)")
        lines.append(f"- `{start}` — {summary}")

    await interaction.followup.send("\n".join(lines))
###############################################################
# GOOGLE DOCS COMMANDS
###############################################################

@bot.tree.command(name="gdoc_create", description="Create a Google Doc with a title and content.")
async def gdoc_create_slash(interaction: discord.Interaction, title: str, content: str):
    await interaction.response.defer(thinking=True)

    docs = build_google_service("docs", "v1")
    if not docs:
        return await interaction.followup.send("Google Docs not configured.", ephemeral=True)

    try:
        doc = docs.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]

        docs.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content
                        }
                    }
                ]
            },
        ).execute()
    except Exception as e:
        print("❌ Docs create error:", e)
        return await interaction.followup.send("Failed to create Google Doc.", ephemeral=True)

    link = f"https://docs.google.com/document/d/{doc_id}/edit"
    await interaction.followup.send(f"📄 Google Doc created:\n{link}")
###############################################################
# GOOGLE SHEETS COMMANDS
###############################################################

@bot.tree.command(
    name="gsheet_append",
    description="Append a row of values to a Google Sheet."
)
async def gsheet_append_slash(
    interaction: discord.Interaction,
    sheet_id: str,
    range_a1: str,
    values_csv: str,
):
    """
    sheet_id: the spreadsheet ID (from the URL)
    range_a1: e.g. 'Sheet1!A1:D1'
    values_csv: comma-separated values for the row
    """
    await interaction.response.defer(thinking=True)

    sheets = build_google_service("sheets", "v4")
    if not sheets:
        return await interaction.followup.send("Google Sheets not configured.", ephemeral=True)

    values = [[v.strip() for v in values_csv.split(",")]]

    body = {"values": values}

    try:
        sheets.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_a1,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
    except Exception as e:
        print("❌ Sheets append error:", e)
        return await interaction.followup.send("Failed to append to Google Sheet.", ephemeral=True)

    await interaction.followup.send("✅ Row appended to Google Sheet.")

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

import re

def is_link(text: str) -> bool:
    # only block REAL hyperlinks
    pattern = r"(https?://[^\s]+|discord\.gg/[^\s]+)"
    return bool(re.search(pattern, text.lower()))
    
@bot.event
async def on_message(msg: discord.Message):

    # DEBUG — SEE ALL MESSAGES
    print(f"MSG RECEIVED: {msg.content}")

    # 1. Ignore bot messages
    if msg.author.bot:
        return

    guild = msg.guild

    # 2. XP system
    if config.get("xp_enabled", True):
        leveled_up, new_level = add_xp(msg.author.id, amount=5)
        if leveled_up:
            try:
                await msg.channel.send(
                    f"🎉 {msg.author.mention} leveled up! **Level {new_level}!**"
                )
            except:
                pass

    # 3. Moderation
    if config.get("moderation_enabled", True):

        # safer link detection
        import re
        def is_link(text: str):
            pattern = r"(https?://[^\s]+|discord\.gg/[^\s]+)"
            return bool(re.search(pattern, text.lower()))

        # banned words
        lower_text = msg.content.lower()
        if any(bad in lower_text for bad in BANNED_WORDS):
            try:
                await msg.delete()
            except:
                pass
            await log_event(guild, f"🚨 Deleted banned word from {msg.author}")
            return

        # link filter
        if is_link(msg.content):
            if not is_staff(msg.author):
                try:
                    await msg.delete()
                except:
                    pass
                await log_event(guild, f"🔗 Blocked link from {msg.author}")
                return

        # spam tracking
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

        # slowmode
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

    # 4. Auto AI conversation
    if config.get("ai_enabled", True):

        if msg.guild is not None:
            mode = channel_modes.get(msg.channel.id, config.get("ai_default_mode", "ceil"))
            content = msg.content.strip()

            # ignore commands
            if content.startswith("!") or content.startswith("/"):
                return await bot.process_commands(msg)

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

    # Finally — process prefix commands
    await bot.process_commands(msg)



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

# ============================================================
# SAFE WRAPPER: call_ai_simple()
# Makes new V2 commands use your existing AI engine.
# ============================================================

async def ai_generate(user, title: str, instruction: str):
    """
    CEIL Unified AI Engine V2
    - title = module name (LOA, PD, REPORT, LESSON, RESEARCH)
    - instruction = the actual prompt
    """

    system = (
        f"You are CEIL AI V2. Module: {title}. "
        f"Respond concisely, professionally, and directly. "
        f"Respect CEIL formatting. Avoid emojis unless explicitly requested."
    )

    try:
        await ai_generate_response(system_msg=sys_prompt, user_msg=prompt)
    except Exception as e:
        print(f"[AI V2 ERROR] {title}:", e)
        return f"❌ AI processing failed in **{title}**."

###########################################################
# GLOBAL AI HELPER FOR ALL V2 MODULES (LOA, PD, REPORT...)
###########################################################

async def ai_generate_response(system_msg: str = None, user_msg: str = None):
    """Unified AI generator used by LOA+, PD+, REPORT+ etc."""
    prompt = ""

    if system_msg:
        prompt += f"System:\n{system_msg}\n\n"
    if user_msg:
        prompt += f"User:\n{user_msg}\n"

    if not prompt.strip():
        return "AI Error: empty prompt received."

    try:
        response = await call_ai_simple(prompt)
        return response
    except Exception as e:
        return f"[AI V2 ERROR] AI failure: {e}"


###############################################################
# UNIVERSAL AI CALL — CLEAN + SAFE
###############################################################
async def ai_generate_response(prompt: str) -> str:
    """Central AI call used by LOA+, PD+, REPORT+."""
    try:
        resp = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert educational AI. Produce clear, structured, pedagogically correct outputs."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[AI V2 ERROR] {type(e).__name__}: {e}"


###############################################################
# LOA+  — Learning Oriented Assessment Generator (UPGRADED)
###############################################################
@bot.tree.command(name="loa_plus", description="Generate a full LOA package (criteria + tasks + progression).")
async def loa_plus_slash(interaction: discord.Interaction, topic: str):
    await interaction.response.defer(ephemeral=True)

    prompt = f"""
Generate a **complete Learning-Oriented Assessment (LOA) package** for the topic: {topic}

Follow CEIL LOA+ v2 standards:

1. **Learning Outcomes**  
2. **Success Criteria**  
3. **Formative Assessment Tasks**  
4. **Student Self-Assessment Prompts**  
5. **Teacher Feedback Frames**  
6. **Progression Tracking Indicators (Beginner–Developing–Competent–Proficient)**  
7. **Mistake-Typology & Corrective Strategy Table**

Produce clear markdown formatting.
"""

    response = await ai_generate_response(prompt)
    await interaction.followup.send(response, ephemeral=True)


###############################################################
# PD+  — Professional Development Generator (UPGRADED)
###############################################################
@bot.tree.command(name="pd_plus", description="Generate a full professional development enhancement plan.")
async def pd_plus_slash(interaction: discord.Interaction, teacher_need: str):
    await interaction.response.defer(ephemeral=True)

    prompt = f"""
Generate a **Professional Development (PD+) Action Plan** for the following teacher need:

**{teacher_need}**

Follow CEIL PD+ v2 framework:

1. **Need Diagnosis**
2. **PD Goal (SMART Format)**
3. **Skill Gaps & Evidence**
4. **Recommended Actions**
5. **Classroom Application Tasks**
6. **Reflection Questions**
7. **Observation Checklist for Supervisors**
8. **Self-Monitoring Sheet**

Produce detailed, structured output in markdown.
"""

    response = await ai_generate_response(prompt)
    await interaction.followup.send(response, ephemeral=True)


###############################################################
# REPORT+ — Upgraded Student Report Generator (UPGRADED)
###############################################################
@bot.tree.command(name="report_plus", description="Generate a complete performance report.")
async def report_plus_slash(interaction: discord.Interaction, student_name: str, skill: str):
    await interaction.response.defer(ephemeral=True)

    prompt = f"""
Generate a **Complete Student Performance Report (REPORT+ V2)**

Student: **{student_name}**  
Skill Area: **{skill}**

Report must include:

1. **Performance Summary**
2. **Strengths (Skill-Based)**
3. **Gaps & Causes**
4. **Evidence-Based Observations**
5. **Actionable Recommendations**
6. **Next-Step Learning Tasks**
7. **Progression Band (A1–C2 or Beginner–Proficient)**

Make it formal, professional, and formatted in markdown.
"""

    response = await ai_generate_response(prompt)
    await interaction.followup.send(response, ephemeral=True)



###############################################################
# LEARNING-ORIENTED ASSESSMENT (LOA) COMMANDS
###############################################################

@bot.tree.command(
    name="loa_task",
    description="Generate a learning-oriented assessment task (LOA) for your students."
)
@app_commands.describe(
    level="Learner level (e.g. A2, B1, N4, N6)",
    skill="Main skill (reading, writing, listening, speaking)",
    objective="Specific learning objective / CAN-DO statement",
)
async def loa_task_slash(
    interaction: discord.Interaction,
    level: str,
    skill: str,
    objective: str,
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message(
            "Lesson tools are disabled by the coordinator.",
            ephemeral=True,
        )

    await interaction.response.defer(thinking=True)

    prompt = (
        "Design a LEARNING-ORIENTED ASSESSMENT (LOA) task for language learners.\n"
        f"- Level: {level}\n"
        f"- Skill: {skill}\n"
        f"- Target objective: {objective}\n\n"
        "The task must:\n"
        "1) Focus on meaningful communication (not just discrete grammar items).\n"
        "2) Make the criteria transparent for students.\n"
        "3) Include self/peer assessment elements.\n"
        "4) Include teacher feedback prompts.\n\n"
        "Output format:\n"
        "A. Task description (what students do)\n"
        "B. Instructions for students (simple, classroom-ready)\n"
        "C. Success criteria / checklist in simple language\n"
        "D. Self/peer assessment prompts\n"
        "E. Teacher feedback notes (how to comment in a learning-oriented way)\n"
    )

    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


@bot.tree.command(
    name="loa_report",
    description="Turn raw scores/notes into a learning-oriented feedback report."
)
@app_commands.describe(
    level="Learner level (A1–C2 / N1–N8)",
    raw_notes="Your raw notes: scores, typical errors, attitudes, participation, etc."
)
async def loa_report_slash(
    interaction: discord.Interaction,
    level: str,
    raw_notes: str,
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message(
            "Lesson tools are disabled by the coordinator.",
            ephemeral=True,
        )

    await interaction.response.defer(thinking=True)

    prompt = (
        "You are a teacher using LEARNING-ORIENTED ASSESSMENT (LOA).\n"
        f"Learner(s) level: {level}\n"
        "Here are rough notes about their performance:\n"
        f"{raw_notes}\n\n"
        "Write a short LOA feedback report that:\n"
        "- Avoids only talking about scores.\n"
        "- Focuses on what they CAN DO and what they are ALMOST able to do.\n"
        "- Gives 2–3 clear, actionable next steps for learning.\n"
        "- Uses positive, supportive but honest language.\n\n"
        "Structure:\n"
        "1. Brief overview\n"
        "2. Strengths (what they can do)\n"
        "3. Priority areas for improvement\n"
        "4. 2–3 concrete next steps for the learner\n"
    )

    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


###############################################################
# AI TUTOR MODE — LEARNER-ORIENTED MINI LESSONS
###############################################################

@bot.tree.command(
    name="tutor",
    description="AI tutor: generate a mini lesson and practice plan for a student."
)
@app_commands.describe(
    level="Learner level (A1–C2 / N1–N8)",
    focus="Grammar/vocabulary/skill focus (e.g. past simple vs present perfect, listening to lectures)",
    profile="Short profile of the learner(s): age, strengths, weaknesses"
)
async def tutor_slash(
    interaction: discord.Interaction,
    level: str,
    focus: str,
    profile: str,
):
    if not config.get("lessons_enabled", True):
        return await interaction.response.send_message(
            "Tutor tools are disabled by the coordinator.",
            ephemeral=True,
        )

    await interaction.response.defer(thinking=True)

    prompt = (
        "Act as an AI TUTOR for language learners.\n"
        f"- Level: {level}\n"
        f"- Focus: {focus}\n"
        f"- Learner profile: {profile}\n\n"
        "Design a short, learning-oriented mini-lesson the teacher can use or the student can follow alone.\n"
        "Structure it as:\n"
        "1. Quick diagnostic (1–3 questions/tasks to see what they can already do)\n"
        "2. Micro-explanation (simple, focused explanation of the target point)\n"
        "3. Guided practice (3–5 short items with answers)\n"
        "4. Freer practice idea (small task they can do using the language)\n"
        "5. Self-check: simple checklist so the learner can self-assess.\n"
    )

    text = await teacher_llm(prompt)
    await interaction.followup.send(text)


###############################################################
# TEACHER PROFESSIONAL DEVELOPMENT (PD) COMMANDS
###############################################################

@bot.tree.command(
    name="pd_plan",
    description="Generate a professional development (PD) plan for a teacher."
)
@app_commands.describe(
    focus="Main PD focus (e.g. speaking activities, classroom management, assessment)",
    context="Context: groups/levels you teach, constraints, institutional context",
    timeframe="Timeframe (e.g. this semester, 4 weeks, 1 year)"
)
async def pd_plan_slash(
    interaction: discord.Interaction,
    focus: str,
    context: str,
    timeframe: str = "this semester",
):
    if not config.get("lessons_enabled", True) and not config.get("research_enabled", True):
        return await interaction.response.send_message(
            "PD tools are disabled by the coordinator.",
            ephemeral=True,
        )

    await interaction.response.defer(thinking=True)

    prompt = (
        "You are designing a PROFESSIONAL DEVELOPMENT (PD) plan for a language teacher.\n"
        f"PD focus: {focus}\n"
        f"Context: {context}\n"
        f"Timeframe: {timeframe}\n\n"
        "Create a realistic PD plan with:\n"
        "1. PD goals (2–4 specific goals)\n"
        "2. Actions (observations, reading, experimenting with activities, reflection, etc.)\n"
        "3. Simple timeline (what to do week by week or month by month)\n"
        "4. Evidence of progress (what data the teacher will collect)\n"
        "5. Final reflection questions.\n"
    )

    text = await research_llm(prompt)
    await interaction.followup.send(text)


@bot.tree.command(
    name="pd_reflection",
    description="Turn raw teacher reflection notes into a structured PD reflection."
)
@app_commands.describe(
    notes="Paste your raw reflection: what happened in class, what went well, what didn't."
)
async def pd_reflection_slash(
    interaction: discord.Interaction,
    notes: str,
):
    if not config.get("lessons_enabled", True) and not config.get("research_enabled", True):
        return await interaction.response.send_message(
            "PD tools are disabled by the coordinator.",
            ephemeral=True,
        )

    await interaction.response.defer(thinking=True)

    prompt = (
        "Transform the following raw teaching reflection into a structured PD reflection.\n"
        "Organize it as:\n"
        "1. Lesson context\n"
        "2. What went well (with reasons)\n"
        "3. What did not go as planned (with possible causes)\n"
        "4. What I learned about my teaching\n"
        "5. Concrete changes I want to try next time.\n\n"
        f"RAW NOTES:\n{notes}"
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
# ============ FIX: REMOVE DUPLICATE COMMANDS ============
for cmd_name in ["hangman", "guess", "blackjack", "hit", "stand", "trivia", "answer"]:
    if cmd_name in bot.commands:
        bot.remove_command(cmd_name)

###############################################
# CEIL BOT — FULL MAX EDITION (Chunk 5/8)
# FUN INTERACTION ENGINE (GAMES + SOCIAL TOOLS)
###############################################

###############################################################
# 32. BLACKJACK FULL ENGINE + COINS INTEGRATION
###############################################################

blackjack_sessions: dict[int, dict] = {}  # user_id -> {player, dealer, bet}


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
async def blackjack_cmd(ctx: commands.Context, bet: int = 10):
    """
    Start a blackjack game with a coin bet.
    Usage: !blackjack 50
    """
    if not config.get("fun_enabled", True):
        return await ctx.reply("🎮 Fun commands are disabled.", mention_author=False)

    if bet <= 0:
        return await ctx.reply("Bet must be a positive number.", mention_author=False)

    uid = ctx.author.id
    balance = get_coins(uid)
    if balance < bet:
        return await ctx.reply(
            f"❌ You don't have enough coins. Balance: **{balance}**, bet: **{bet}**.",
            mention_author=False,
        )

    # Reserve the bet up-front (so they can't run with the money)
    add_coins(uid, -bet)

    player = [bj_draw_card(), bj_draw_card()]
    dealer = [bj_draw_card(), bj_draw_card()]
    blackjack_sessions[uid] = {"player": player, "dealer": dealer, "bet": bet}

    msg = (
        f"🃏 **Blackjack** (bet: **{bet}** coins)\n\n"
        f"**Your hand:** {bj_format(player)} (value: {bj_hand_value(player)})\n"
        f"**Dealer shows:** {bj_format([dealer[0]])}\n\n"
        "Type `!hit` to draw or `!stand` to hold."
    )

    await ctx.reply(msg, mention_author=False)


@bot.command(name="hit")
async def blackjack_hit_cmd(ctx: commands.Context):
    uid = ctx.author.id
    if uid not in blackjack_sessions:
        return await ctx.reply("No active blackjack game. Start one with `!blackjack <bet>`.")

    game = blackjack_sessions[uid]
    game["player"].append(bj_draw_card())
    val = bj_hand_value(game["player"])

    if val > 21:
        # player busts -> lose bet (already deducted)
        bet = game.get("bet", 0)
        blackjack_sessions.pop(uid, None)
        msg = (
            f"💥 **Bust!**\n"
            f"Your hand: {bj_format(game['player'])} ({val})\n"
            f"You lose your bet of **{bet}** coins.\n"
            f"New balance: **{get_coins(uid)}** coins."
        )
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
        return await ctx.reply("No active blackjack game. Start with `!blackjack <bet>`.")

    game = blackjack_sessions[uid]
    dealer = game["dealer"]
    player = game["player"]
    bet = game.get("bet", 0)

    while bj_hand_value(dealer) < 17:
        dealer.append(bj_draw_card())

    pv = bj_hand_value(player)
    dv = bj_hand_value(dealer)

    msg = (
        f"**Your hand:** {bj_format(player)} ({pv})\n"
        f"**Dealer hand:** {bj_format(dealer)} ({dv})\n\n"
    )

    if dv > 21 or pv > dv:
        # win -> we already removed bet; pay 2 * bet back
        add_coins(uid, bet * 2)
        msg += f"🎉 **You win!** You earn **{bet}** net coins.\n"
    elif pv == dv:
        # push -> refund bet
        add_coins(uid, bet)
        msg += "➖ **Push (draw).** Your bet has been refunded.\n"
    else:
        # lose -> bet was already taken
        msg += "❌ **Dealer wins.** You lose your bet.\n"

    new_balance = get_coins(uid)
    msg += f"Current balance: **{new_balance}** coins."

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
# COINS COMMANDS — BALANCE + DAILY REWARD
###############################################################

@bot.command(name="coins")
async def coins_cmd(ctx: commands.Context):
    """
    Show your current coin balance.
    """
    balance = get_coins(ctx.author.id)
    await ctx.reply(f"💰 {ctx.author.mention}, you have **{balance}** coins.", mention_author=False)


@bot.command(name="balance")
async def balance_cmd(ctx: commands.Context):
    """
    Alias for !coins.
    """
    balance = get_coins(ctx.author.id)
    await ctx.reply(f"💰 {ctx.author.mention}, you have **{balance}** coins.", mention_author=False)


@bot.command(name="daily")
async def daily_cmd(ctx: commands.Context):
    """
    Claim a daily coin reward (once every 24h).
    """
    reward = 100  # you can change this
    can_claim, hours_left = can_claim_daily(ctx.author.id)

    if not can_claim:
        await ctx.reply(
            f"⏳ You already claimed your daily reward. Try again in approx **{hours_left:.1f} hours**.",
            mention_author=False,
        )
        return

    mark_daily_claimed(ctx.author.id)
    new_balance = add_coins(ctx.author.id, reward)
    await ctx.reply(
        f"✅ Daily claimed! You received **{reward}** coins.\n"
        f"New balance: **{new_balance}** coins.",
        mention_author=False,
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
# CEIL BOT CONTROL PANEL (Admin Dashboard UI)
###############################################

from discord.ui import View, Button, Select, Modal, TextInput

panel_group = app_commands.Group(
    name="panel",
    description="Admin control panel for CEIL Bot"
)

def save_and_reload_config():
    save_config()
    load_config()

###############################################
# 1. FEATURES TOGGLE PANEL
###############################################

class FeatureToggleView(View):
    def __init__(self):
        super().__init__(timeout=300)

        # Generate toggle buttons for each feature dynamically
        for feature in [
            "ai_enabled",
            "moderation_enabled",
            "xp_enabled",
            "fun_enabled",
            "lessons_enabled",
            "research_enabled",
            "images_enabled",
        ]:
            state = "ON" if config.get(feature, True) else "OFF"
            color = discord.ButtonStyle.success if state == "ON" else discord.ButtonStyle.danger

            self.add_item(
                Button(
                    label=f"{feature.replace('_',' ').title()} ({state})",
                    style=color,
                    custom_id=feature
                )
            )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Not authorized.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        self.clear_items()

    @discord.ui.button(label="Refresh Panel", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="🔧 Feature Panel (Updated)",
            view=FeatureToggleView()
        )

    async def on_button_click(self, interaction: discord.Interaction):
        feature = interaction.data["custom_id"]

        if feature in config:
            config[feature] = not config[feature]
            save_and_reload_config()

            await interaction.response.edit_message(
                content=f"🔧 Toggled **{feature}** → `{config[feature]}`",
                view=FeatureToggleView()
            )

    async def interaction_check(self, interaction: discord.Interaction):
        # Called for every interaction
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return False
        return True

###############################################
# 2. XP CONTROL PANEL
###############################################

class XPModal(Modal):
    def __init__(self, user: discord.Member, action: str):
        super().__init__(title=f"{action.title()} XP")
        self.user = user
        self.action = action

        self.xp_amount = TextInput(
            label="XP Amount",
            placeholder="Enter value",
            style=discord.TextInputStyle.short,
        )
        self.add_item(self.xp_amount)

    async def callback(self, interaction: discord.Interaction):
        try:
            amount = int(self.xp_amount.value)
        except:
            return await interaction.response.send_message("Invalid number.", ephemeral=True)

        xp, level = get_xp_profile(self.user.id)

        if self.action == "add":
            add_xp(self.user.id, amount)
            result = f"Added **+{amount} XP** to {self.user.mention}."
        elif self.action == "remove":
            new_xp = max(0, xp - amount)
            xp_data[str(self.user.id)]["xp"] = new_xp
            save_xp()
            result = f"Removed **-{amount} XP** from {self.user.mention}."
        elif self.action == "set":
            xp_data[str(self.user.id)] = {"xp": amount, "level": 1}
            save_xp()
            result = f"Set XP of {self.user.mention} to **{amount}**."

        await interaction.response.send_message(result, ephemeral=True)


class XPControlView(View):
    def __init__(self, target: discord.Member):
        super().__init__(timeout=300)
        self.target = target

    @discord.ui.button(label="Add XP", style=discord.ButtonStyle.success)
    async def add_xp_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(XPModal(self.target, "add"))

    @discord.ui.button(label="Remove XP", style=discord.ButtonStyle.danger)
    async def remove_xp_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(XPModal(self.target, "remove"))

    @discord.ui.button(label="Set XP", style=discord.ButtonStyle.primary)
    async def set_xp_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(XPModal(self.target, "set"))

###############################################
# 3. /panel features
###############################################

@panel_group.command(
    name="features",
    description="Open the feature toggle panel."
)
async def panel_features(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

    await interaction.response.send_message(
        "🔧 **CEIL Bot Feature Control Panel**",
        view=FeatureToggleView(),
        ephemeral=True
    )

@panel_group.command(
    name="xp",
    description="Open XP control panel for a user."
)
@app_commands.describe(user="Select user to modify XP")
async def panel_xp(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

    await interaction.response.send_message(
        f"🎮 XP Controls for {user.mention}",
        view=XPControlView(user),
        ephemeral=True
    )

# register panel group
bot.tree.add_command(panel_group)

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
    name="add_custom",
    description="Create a custom AI command for this server."
)
@app_commands.describe(
    name="Short name (no spaces).",
    description="What this command does.",
    prompt="Instruction for the AI (how it should behave)."
)
async def add_custom_command_slash(
    interaction: discord.Interaction,
    name: str,
    description: str,
    prompt: str,
):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    name = name.strip().lower()
    if " " in name or len(name) < 2:
        return await interaction.response.send_message(
            "Use a short name without spaces (e.g. `essay_check`).",
            ephemeral=True,
        )

    load_custom_commands()
    cmds = get_guild_cmds(interaction.guild.id)
    cmds[name] = {
        "description": description,
        "prompt": prompt,
    }
    save_custom_commands()

    await interaction.response.send_message(
        f"✅ Custom command **{name}** created.\n"
        f"Use `/run_custom` with that name to execute it.",
        ephemeral=True,
    )
@admin_group.command(
    name="coins_set",
    description="(Admin) Set coins for a user."
)
@app_commands.describe(
    member="Target member",
    amount="New coin balance"
)
async def admin_coins_set_slash(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int,
):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    if amount < 0:
        amount = 0

    set_coins(member.id, amount)
    await interaction.response.send_message(
        f"✅ Set {member.mention}'s coins to **{amount}**.",
        ephemeral=True,
    )


@admin_group.command(
    name="coins_add",
    description="(Admin) Add or remove coins from a user."
)
@app_commands.describe(
    member="Target member",
    amount="Amount to add (negative to remove)"
)
async def admin_coins_add_slash(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int,
):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    new_balance = add_coins(member.id, amount)
    await interaction.response.send_message(
        f"✅ Updated {member.mention}'s coins by **{amount}**. New balance: **{new_balance}**.",
        ephemeral=True,
    )


@admin_group.command(
    name="list_custom",
    description="List custom commands for this server."
)
async def list_custom_slash(interaction: discord.Interaction):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    load_custom_commands()
    cmds = get_guild_cmds(interaction.guild.id)
    if not cmds:
        return await interaction.response.send_message(
            "No custom commands defined yet.",
            ephemeral=True,
        )

    lines = []
    for name, meta in cmds.items():
        lines.append(f"• **{name}** — {meta.get('description','')}")
    txt = "\n".join(lines)

    await interaction.response.send_message(
        embed=make_embed(
            title="⚙️ Custom Commands",
            description=txt,
            color=discord.Color.blurple(),
        ),
        ephemeral=True,
    )

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
@admin_group.command(
    name="dashboard",
    description="Open interactive Admin Dashboard v2 (feature toggles, banned words, config)."
)
async def admin_dashboard_slash(interaction: discord.Interaction):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    await interaction.response.defer(ephemeral=True, thinking=True)

    view = AdminDashboardView(user)
    embed = build_admin_dashboard_embed()

    await interaction.followup.send(
        content="🛠 Admin Dashboard v2 loaded.",
        embed=embed,
        view=view,
        ephemeral=True,
    )
    # ===========================================
# DASHBOARD V3 (NON-BREAKING UPGRADE)
# ===========================================

def build_dashboard_v3_embed(guild: discord.Guild) -> discord.Embed:
    total_members = guild.member_count or 0
    online_members = sum(1 for m in guild.members if m.status != discord.Status.offline)

    desc = (
        f"### 🛠️ CEIL ADMIN DASHBOARD V3\n\n"
        f"**Members**\n"
        f"- Total: **{total_members}**\n"
        f"- Online: **{online_members}**\n\n"
        f"**Features**\n"
        f"- AI: {'✅' if config.get('ai_enabled', True) else '❌'}\n"
        f"- Moderation: {'✅' if config.get('moderation_enabled', True) else '❌'}\n"
        f"- XP: {'✅' if config.get('xp_enabled', True) else '❌'}\n"
        f"- Fun: {'✅' if config.get('fun_enabled', True) else '❌'}\n"
        f"- Lessons: {'✅' if config.get('lessons_enabled', True) else '❌'}\n"
        f"- Research: {'✅' if config.get('research_enabled', True) else '❌'}\n"
        f"- Images/Vision: {'✅' if config.get('images_enabled', True) else '❌'}\n\n"
        "Use the buttons below to open sub-panels:\n"
        "- **General** → feature toggles\n"
        "- **Teacher / LOA & PD** → assessment & PD tools\n"
        "- **Moderation** → basic moderation info\n"
        "- **XP & Games** → XP / blackjack coins tools\n"
        "- **Google Center** → Google status summary\n"
        "- **Server Tools** → quick links to management commands"
    )

    embed = discord.Embed(
        title="🛠️ CEIL ADMIN DASHBOARD V3",
        description=desc,
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=f"Guild ID: {guild.id}")
    return embed
class DashboardV3View(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

        # Row 0 – main sections
        self.add_item(DashboardV3GeneralButton())
        self.add_item(DashboardV3TeacherButton())
        self.add_item(DashboardV3ModerationButton())

        # Row 1 – more sections
        self.add_item(DashboardV3XPButton())
        self.add_item(DashboardV3GoogleButton())
        self.add_item(DashboardV3ServerToolsButton())

        # Row 2 – close
        self.add_item(DashboardV3CloseButton())


async def _ensure_admin(interaction: discord.Interaction) -> bool:
    """Simple admin guard for dashboard buttons."""
    user = interaction.user
    if not isinstance(user, discord.Member) or not user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ You need **administrator** permissions to use this dashboard.",
            ephemeral=True,
        )
        return False
    return True


class DashboardV3GeneralButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="General",
            emoji="⚙️",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await _ensure_admin(interaction):
            return

        desc = (
            "### ⚙️ General Settings\n\n"
            "Use `/panel features` to toggle:\n"
            "- AI / moderation / XP / games / lessons / research / images\n\n"
            "Use `/panel xp` to adjust XP & coins for users.\n\n"
            "This section is meant as a **quick overview**.\n"
        )
        embed = discord.Embed(
            title="⚙️ General Settings – CEIL",
            description=desc,
            color=discord.Color.blurple(),
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


class DashboardV3TeacherButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Teacher / LOA & PD",
            emoji="📚",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await _ensure_admin(interaction):
            return

        desc = (
            "### 📚 Teacher / LOA & PD Tools\n\n"
            "Suggested commands (depending on what you have enabled):\n"
            "- `/loa_plus` – design a learning-oriented task\n"
            "- `/pd_plus` – build a PD plan\n"
            "- `/teacher_report_plus` – structured lesson observation report\n"
            "- `/coordination_plus` – coordination / meeting summary\n\n"
            "You can pin these commands in a **teachers-only** channel.\n"
        )
        embed = discord.Embed(
            title="📚 Teacher / LOA & PD",
            description=desc,
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


class DashboardV3ModerationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Moderation",
            emoji="🛡️",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await _ensure_admin(interaction):
            return

        desc = (
            "### 🛡️ Moderation Overview\n\n"
            "Use existing moderation commands you already have configured:\n"
            "- warnings / slowmode / link filters / banned words\n\n"
            "Dashboard tip: you can combine this with `/panel features` and your\n"
            "existing admin tools to keep CEIL aligned with **safe interactions**.\n"
        )
        embed = discord.Embed(
            title="🛡️ Moderation Overview",
            description=desc,
            color=discord.Color.red(),
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


class DashboardV3XPButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="XP & Games",
            emoji="🎮",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await _ensure_admin(interaction):
            return

        desc = (
            "### 🎮 XP & Games\n\n"
            "Blackjack & coins are tied into your XP system.\n"
            "Useful commands:\n"
            "- `/panel xp` → open XP control panel\n"
            "- `!blackjack` → play blackjack with coins\n"
            "- `/coins` → show coins (slash version)\n\n"
            "You can limit games to specific channels with your existing config.\n"
        )
        embed = discord.Embed(
            title="🎮 XP & Games",
            description=desc,
            color=discord.Color.gold(),
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


class DashboardV3GoogleButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Google Center",
            emoji="🧩",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await _ensure_admin(interaction):
            return

        google_status = "✅ READY" if GOOGLE_READY else "⚠️ DISABLED (no creds)"
        yt_status = "✅ KEY SET" if os.getenv("YOUTUBE_API_KEY") else "⚠️ NOT SET"

        desc = (
            "### 🧩 Google Center\n\n"
            f"- Service account: **{google_status}**\n"
            f"- YouTube API key: **{yt_status}**\n\n"
            "If something is disabled, check your environment variables:\n"
            "- `GOOGLE_APPLICATION_CREDENTIALS_BASE64`\n"
            "- `YOUTUBE_API_KEY`\n"
        )
        embed = discord.Embed(
            title="🧩 Google Center",
            description=desc,
            color=discord.Color.dark_teal(),
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


class DashboardV3ServerToolsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Server Tools",
            emoji="🛠️",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await _ensure_admin(interaction):
            return

        desc = (
            "### 🛠️ Server Tools\n\n"
            "Examples of commands you might already have:\n"
            "- `/clean` or `/purge` → clean channels\n"
            "- `/announce` or `/admin announce` → send announcements\n"
            "- XP / role auto-assignment features\n\n"
            "This section is informational so you can align tools with CEIL.\n"
        )
        embed = discord.Embed(
            title="🛠️ Server Tools Overview",
            description=desc,
            color=discord.Color.dark_orange(),
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


class DashboardV3CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Close",
            emoji="❌",
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await _ensure_admin(interaction):
            return
        await interaction.message.delete()
@admin_group.command(
    name="dashboard_v3",
    description="Open the upgraded CEIL admin dashboard (V3).",
)
@app_commands.checks.has_permissions(administrator=True)
async def admin_dashboard_v3_slash(interaction: discord.Interaction):
    """Non-breaking V3 dashboard – uses a new view and embed."""
    guild = interaction.guild
    if guild is None:
        return await interaction.response.send_message(
            "❌ This command can only be used inside a server.",
            ephemeral=True,
        )

    embed = build_dashboard_v3_embed(guild)
    view = DashboardV3View()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    ###############################################################
# COINS SLASH COMMANDS
###############################################################

@bot.tree.command(
    name="coins",
    description="Show your coin balance or another member's."
)
@app_commands.describe(member="Member to check (optional).")
async def coins_slash(interaction: discord.Interaction, member: discord.Member | None = None):
    user = member or interaction.user
    balance = get_coins(user.id)
    own = (user.id == interaction.user.id)

    if own:
        text = f"💰 You have **{balance} coins**."
    else:
        text = f"💰 {user.mention} has **{balance} coins**."

    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(
    name="coins_daily",
    description="Claim your daily coin reward."
)
async def coins_daily_slash(interaction: discord.Interaction):
    DAILY_AMOUNT = 50

    if not can_claim_daily(interaction.user.id):
        return await interaction.response.send_message(
            "⏳ You already claimed your daily reward today.",
            ephemeral=True,
        )

    new_balance = mark_daily_claim(interaction.user.id, DAILY_AMOUNT)
    await interaction.response.send_message(
        f"✅ You claimed **{DAILY_AMOUNT} coins**! New balance: **{new_balance}**.",
        ephemeral=True,
    )


@bot.tree.command(
    name="coins_top",
    description="Show the top 10 users by coins."
)
async def coins_top_slash(interaction: discord.Interaction):
    if not coins_data:
        return await interaction.response.send_message(
            "No coin data yet.",
            ephemeral=True,
        )

    # Sort by coins desc
    sorted_users = sorted(
        coins_data.items(),
        key=lambda kv: int(kv[1].get("coins", 0)),
        reverse=True,
    )[:10]

    lines = []
    for idx, (uid, rec) in enumerate(sorted_users, start=1):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"User {uid}"
        coins_val = rec.get("coins", 0)
        lines.append(f"**#{idx}** — {name}: **{coins_val} coins**")

    desc = "\n".join(lines) if lines else "No data."
    embed = make_embed(
        title="🏆 Coin Leaderboard (Top 10)",
        description=desc,
        color=discord.Color.gold(),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

def _recalculate_level_for_xp(total_xp: int) -> int:
    """
    Recalculate level based on XP using the same logic as add_xp.
    Level 1: 0–99, Level 2: 100–199, etc.
    """
    level = 1
    required = level * 100
    while total_xp >= required:
        level += 1
        required = level * 100
    return level


@admin_group.command(
    name="xp_add",
    description="(Admin) Add XP to a user."
)
@app_commands.describe(
    member="User to give XP to.",
    amount="Amount of XP to add (positive integer)."
)
async def admin_xp_add_slash(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int,
):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    if amount <= 0:
        return await interaction.response.send_message("Amount must be positive.", ephemeral=True)

    leveled, new_level = add_xp(member.id, amount)
    xp, lvl = get_xp_profile(member.id)

    await interaction.response.send_message(
        f"✅ Added **{amount} XP** to {member.mention}.\n"
        f"Total XP: **{xp}**, Level: **{lvl}**",
        ephemeral=True,
    )


@admin_group.command(
    name="xp_remove",
    description="(Admin) Remove XP from a user."
)
@app_commands.describe(
    member="User to remove XP from.",
    amount="Amount of XP to remove (positive integer)."
)
async def admin_xp_remove_slash(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int,
):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    if amount <= 0:
        return await interaction.response.send_message("Amount must be positive.", ephemeral=True)

    uid = str(member.id)
    if uid not in xp_data:
        xp_data[uid] = {"xp": 0, "level": 1}

    xp_data[uid]["xp"] = max(0, xp_data[uid]["xp"] - amount)
    xp_data[uid]["level"] = _recalculate_level_for_xp(xp_data[uid]["xp"])
    save_xp()

    xp = xp_data[uid]["xp"]
    lvl = xp_data[uid]["level"]

    await interaction.response.send_message(
        f"✅ Removed **{amount} XP** from {member.mention}.\n"
        f"Total XP: **{xp}**, Level: **{lvl}**",
        ephemeral=True,
    )


@admin_group.command(
    name="xp_set",
    description="(Admin) Set a user's XP to an exact value."
)
@app_commands.describe(
    member="User to modify.",
    amount="Exact XP total to set (0 or more)."
)
async def admin_xp_set_slash(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int,
):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    if amount < 0:
        return await interaction.response.send_message("XP cannot be negative.", ephemeral=True)

    uid = str(member.id)
    xp_data[uid] = {
        "xp": amount,
        "level": _recalculate_level_for_xp(amount),
    }
    save_xp()

    xp = xp_data[uid]["xp"]
    lvl = xp_data[uid]["level"]

    await interaction.response.send_message(
        f"✅ Set XP for {member.mention} to **{xp}** (Level **{lvl}**).",
        ephemeral=True,
    )


@admin_group.command(
    name="xp_show",
    description="(Admin) Show a user's XP and level."
)
@app_commands.describe(
    member="User to inspect."
)
async def admin_xp_show_slash(
    interaction: discord.Interaction,
    member: discord.Member,
):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    xp, lvl = get_xp_profile(member.id)
    await interaction.response.send_message(
        f"ℹ XP profile for {member.mention}:\n"
        f"• XP: **{xp}**\n"
        f"• Level: **{lvl}**",
        ephemeral=True,
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
# ADMIN: CLEAN CHANNEL UTILITIES
###############################################################

@admin_group.command(
    name="clean_channel",
    description="(Admin) Delete the last N messages in this channel."
)
@app_commands.describe(
    amount="Number of recent messages to delete (1–500)."
)
async def admin_clean_channel_slash(
    interaction: discord.Interaction,
    amount: int,
):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    if amount <= 0:
        return await interaction.response.send_message("Amount must be positive.", ephemeral=True)
    if amount > 500:
        amount = 500

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            f"🧹 Deleted **{len(deleted)}** messages from {interaction.channel.mention}.",
            ephemeral=True,
        )
        await log_event(
            interaction.guild,
            f"🧹 {user} cleaned {len(deleted)} messages in {interaction.channel}.",
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to clean channel: {e}", ephemeral=True)


@admin_group.command(
    name="clean_channel_soft",
    description="(Admin) Delete recent bot messages in this channel (soft clean)."
)
@app_commands.describe(
    amount="How many recent messages to scan (will only delete bot messages)."
)
async def admin_clean_channel_soft_slash(
    interaction: discord.Interaction,
    amount: int = 100,
):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    if amount <= 0:
        amount = 50
    if amount > 500:
        amount = 500

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        # Fetch & delete only bot messages
        def is_bot_msg(m: discord.Message):
            return m.author.bot

        deleted = await interaction.channel.purge(limit=amount, check=is_bot_msg)
        await interaction.followup.send(
            f"🧼 Soft clean: deleted **{len(deleted)}** bot messages.",
            ephemeral=True,
        )
        await log_event(
            interaction.guild,
            f"🧼 {user} soft-cleaned {len(deleted)} bot messages in {interaction.channel}.",
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Failed soft clean: {e}", ephemeral=True)

###############################################################
# AUTO ROLE ON MEMBER JOIN
###############################################################

@bot.event
async def on_member_join(member: discord.Member):
    """
    Automatically assign a role when a user joins (if configured).
    Uses config['auto_role_name'].
    """
    guild = member.guild
    role_name = config.get("auto_role_name")
    if not role_name:
        return

    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        return

    try:
        await member.add_roles(role, reason="Auto-role on join")
        await log_event(
            guild,
            f"👤 Auto-assigned role **{role_name}** to {member.mention} on join."
        )
    except Exception as e:
        print(f"❌ Failed to auto-assign role {role_name} to {member}: {e}")

@admin_group.command(
    name="set_autorole",
    description="Set which role is auto-assigned when members join."
)
@app_commands.describe(
    role="Role to auto-assign on member join."
)
async def set_autorole_slash(
    interaction: discord.Interaction,
    role: discord.Role,
):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    config["auto_role_name"] = role.name
    save_config()
    await interaction.response.send_message(
        f"✅ Auto-role set to **{role.name}**.",
        ephemeral=True,
    )


@admin_group.command(
    name="clear_autorole",
    description="Disable auto-assigning roles on join."
)
async def clear_autorole_slash(interaction: discord.Interaction):
    user = interaction.user
    if not isinstance(user, discord.Member) or not is_staff(user):
        return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    config["auto_role_name"] = ""
    save_config()
    await interaction.response.send_message(
        "✅ Auto-role disabled.",
        ephemeral=True,
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
###############################################################
# CUSTOM AI COMMANDS (per guild)
###############################################################

CUSTOM_CMDS_FILE = "custom_commands.json"
custom_commands: dict = {}  # {guild_id: {name: {description, prompt}}}


def load_custom_commands():
    global custom_commands
    if os.path.exists(CUSTOM_CMDS_FILE):
        try:
            with open(CUSTOM_CMDS_FILE, "r", encoding="utf-8") as f:
                custom_commands = json.load(f)
        except Exception:
            custom_commands = {}
    else:
        custom_commands = {}


def save_custom_commands():
    try:
        with open(CUSTOM_CMDS_FILE, "w", encoding="utf-8") as f:
            json.dump(custom_commands, f, indent=2)
    except Exception as e:
        print("❌ ERROR writing custom_commands.json:", e)


def get_guild_cmds(guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in custom_commands:
        custom_commands[gid] = {}
    return custom_commands[gid]


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
###############################################
# CEIL BOT — ADMIN DASHBOARD V3
# /dashboard — main control center
###############################################

# Small guard so this file can reload without redefining many times
DASHBOARD_V3_ENABLED = True

# --------- Helper: safe google status ----------
def get_google_status_summary():
    # Avoid NameError if GOOGLE_READY or GOOGLE_SERVICE_ACCOUNT_JSON missing
    google_ready = bool(globals().get("GOOGLE_READY", False))
    svc_json_present = bool(globals().get("GOOGLE_SERVICE_ACCOUNT_JSON", None))
    yt_key = os.getenv("YOUTUBE_API_KEY", "")
    yt_ok = bool(yt_key and yt_key.strip())

    lines = []
    lines.append(f"Google service account JSON: {'✅' if svc_json_present else '❌'}")
    lines.append(f"Core Google services initialized: {'✅' if google_ready else '❌'}")
    lines.append(f"YouTube API key: {'✅' if yt_ok else '❌'}")

    project_id = os.getenv("GOOGLE_PROJECT_ID", "")
    if project_id:
        lines.append(f"Project ID: `{project_id}`")
    else:
        lines.append("Project ID: ❌ (GOOGLE_PROJECT_ID not set)")

    return "\n".join(lines)


# --------- Helper: permission check for slash dashboard ----------
async def ensure_admin_interaction(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        try:
            await interaction.response.send_message("❌ You are not allowed to use this dashboard.", ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send("❌ You are not allowed to use this dashboard.", ephemeral=True)
        return False
    return True


# --------- Generic embed factory for the dashboard ----------
def dashboard_embed(title: str, description: str, color=discord.Color.blurple()):
    emb = discord.Embed(title=title, description=description, color=color)
    emb.set_footer(text="CEIL Full-Max Admin Dashboard V3")
    emb.timestamp = datetime.utcnow()
    return emb


###############################################
# DASHBOARD VIEWS & COMPONENTS
###############################################

class DashboardMainView(View):
    """
    Main view: section selector + quick buttons.
    """
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(DashboardSectionSelect())
        # Optional quick buttons
        self.add_item(RefreshButton())
        self.add_item(CloseDashboardButton())


class DashboardSectionSelect(Select):
    def __init__(self):
        options = [
            SelectOption(label="General Settings", value="general", description="Feature toggles, core config"),
            SelectOption(label="AI Engine", value="ai", description="AI modes, auto-reply, languages"),
            SelectOption(label="Teacher Suite", value="teacher", description="Lesson tools, progression, reports"),
            SelectOption(label="Moderation", value="mod", description="Auto-moderation, spam, logging"),
            SelectOption(label="Economy & Games", value="games", description="XP, coins, fun engine"),
            SelectOption(label="Google Center", value="google", description="Drive, Calendar, YouTube status"),
        ]
        super().__init__(
            placeholder="Select a dashboard section…",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await ensure_admin_interaction(interaction):
            return

        section = self.values[0]

        if section == "general":
            view = GeneralSettingsView()
            desc = (
                "Toggle major systems on/off and see core configuration.\n\n"
                f"- AI Engine: {'✅' if config.get('ai_enabled', True) else '❌'}\n"
                f"- Moderation: {'✅' if config.get('moderation_enabled', True) else '❌'}\n"
                f"- XP System: {'✅' if config.get('xp_enabled', True) else '❌'}\n"
                f"- Fun / Games: {'✅' if config.get('fun_enabled', True) else '❌'}\n"
                f"- Lessons / Teacher Suite: {'✅' if config.get('lessons_enabled', True) else '❌'}\n"
                f"- Research Suite: {'✅' if config.get('research_enabled', True) else '❌'}\n"
                f"- Vision / Images: {'✅' if config.get('images_enabled', True) else '❌'}\n"
                f"- Logging: {'✅' if config.get('logging_enabled', True) else '❌'}\n"
            )
            embed = dashboard_embed("⚙️ General Settings", desc, color=discord.Color.gold())

        elif section == "ai":
            view = AiSettingsView()
            mode = config.get("ai_default_mode", "ceil")
            desc = (
                f"Configure the AI engine, default mode and behaviour.\n\n"
                f"- AI enabled: {'✅' if config.get('ai_enabled', True) else '❌'}\n"
                f"- Default mode: `{mode}`\n"
                "Available modes: `ceil`, `education`, `admin`, `general`, `fun`, `topic:<something>`\n"
            )
            embed = dashboard_embed("🤖 AI Engine Settings", desc, color=discord.Color.blurple())

        elif section == "teacher":
            view = TeacherSettingsView()
            desc = (
                "Control lesson tools, worksheet/quiz generation and progression tracking.\n\n"
                f"- Lesson tools: {'✅' if config.get('lessons_enabled', True) else '❌'}\n"
                f"- Research tools: {'✅' if config.get('research_enabled', True) else '❌'}\n"
                "Use the buttons below to toggle suites and get progression overview."
            )
            embed = dashboard_embed("🧑‍🏫 Teacher & Research Suite", desc, color=discord.Color.green())

        elif section == "mod":
            view = ModerationSettingsView()
            desc = (
                "Configure moderation: spam, links, slowmode and logging.\n\n"
                f"- Moderation: {'✅' if config.get('moderation_enabled', True) else '❌'}\n"
                f"- Logging: {'✅' if config.get('logging_enabled', True) else '❌'}\n"
            )
            embed = dashboard_embed("🛡️ Moderation & Safety", desc, color=discord.Color.red())

        elif section == "games":
            view = GamesSettingsView()
            desc = (
                "Configure XP and fun engine.\n\n"
                f"- XP: {'✅' if config.get('xp_enabled', True) else '❌'}\n"
                f"- Fun / Games: {'✅' if config.get('fun_enabled', True) else '❌'}\n"
                "Blackjack, Hangman, Trivia and more use this engine.\n"
            )
            embed = dashboard_embed("🎮 Economy & Games", desc, color=discord.Color.purple())

        elif section == "google":
            view = GoogleSettingsView()
            desc = "Status of Google integrations:\n\n" + get_google_status_summary()
            embed = dashboard_embed("🟩 Google Center", desc, color=discord.Color.green())

        else:
            # fallback to home
            view = DashboardMainView()
            embed = dashboard_embed(
                "🛠️ CEIL ADMIN DASHBOARD V3",
                "Unexpected section, returning to main menu.",
            )

        await interaction.response.edit_message(embed=embed, view=view)


class RefreshButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Refresh", emoji="🔁", row=1)

    async def callback(self, interaction: discord.Interaction):
        if not await ensure_admin_interaction(interaction):
            return

        desc = (
            "Select a section from the dropdown to manage the bot.\n\n"
            f"- AI: {'✅' if config.get('ai_enabled', True) else '❌'}\n"
            f"- Moderation: {'✅' if config.get('moderation_enabled', True) else '❌'}\n"
            f"- XP: {'✅' if config.get('xp_enabled', True) else '❌'}\n"
            f"- Fun: {'✅' if config.get('fun_enabled', True) else '❌'}\n"
            f"- Lessons: {'✅' if config.get('lessons_enabled', True) else '❌'}\n"
            f"- Research: {'✅' if config.get('research_enabled', True) else '❌'}\n"
            f"- Images/Vision: {'✅' if config.get('images_enabled', True) else '❌'}\n"
        )
        embed = dashboard_embed("🛠️ CEIL ADMIN DASHBOARD V3", desc)
        await interaction.response.edit_message(embed=embed, view=DashboardMainView())


class CloseDashboardButton(Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Close",
            emoji="❌",   # fixed emoji
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        if not await ensure_admin_interaction(interaction):
            return
        await interaction.response.edit_message(content="Dashboard closed.", embed=None, view=None)


###############################################
# SECTION: GENERAL SETTINGS
###############################################

class GeneralSettingsView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ToggleFeatureButton("AI", "ai_enabled", row=0))
        self.add_item(ToggleFeatureButton("Moderation", "moderation_enabled", row=0))
        self.add_item(ToggleFeatureButton("XP", "xp_enabled", row=0))
        self.add_item(ToggleFeatureButton("Fun/Games", "fun_enabled", row=1))
        self.add_item(ToggleFeatureButton("Lessons", "lessons_enabled", row=1))
        self.add_item(ToggleFeatureButton("Research", "research_enabled", row=1))
        self.add_item(ToggleFeatureButton("Vision/Images", "images_enabled", row=2))
        self.add_item(ToggleFeatureButton("Logging", "logging_enabled", row=2))
        self.add_item(BackToMainButton(row=3))


class ToggleFeatureButton(Button):
    def __init__(self, label_name: str, config_key: str, row: int = 0):
        emoji = "✅" if config.get(config_key, True) else "❌"
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=f"{label_name}: {emoji}",
            row=row,
        )
        self.config_key = config_key
        self.label_name = label_name

    async def callback(self, interaction: discord.Interaction):
        if not await ensure_admin_interaction(interaction):
            return

        current = config.get(self.config_key, True)
        new_val = not current
        config[self.config_key] = new_val
        save_config()

        # Update button label
        self.label = f"{self.label_name}: {'✅' if new_val else '❌'}"

        # Rebuild description
        desc = (
            "Toggle major systems on/off and see core configuration.\n\n"
            f"- AI Engine: {'✅' if config.get('ai_enabled', True) else '❌'}\n"
            f"- Moderation: {'✅' if config.get('moderation_enabled', True) else '❌'}\n"
            f"- XP System: {'✅' if config.get('xp_enabled', True) else '❌'}\n"
            f"- Fun / Games: {'✅' if config.get('fun_enabled', True) else '❌'}\n"
            f"- Lessons / Teacher Suite: {'✅' if config.get('lessons_enabled', True) else '❌'}\n"
            f"- Research Suite: {'✅' if config.get('research_enabled', True) else '❌'}\n"
            f"- Vision / Images: {'✅' if config.get('images_enabled', True) else '❌'}\n"
            f"- Logging: {'✅' if config.get('logging_enabled', True) else '❌'}\n"
        )
        embed = dashboard_embed("⚙️ General Settings", desc, color=discord.Color.gold())
        await interaction.response.edit_message(embed=embed, view=self.view)


class BackToMainButton(Button):
    def __init__(self, row: int = 2):
        super().__init__(style=discord.ButtonStyle.secondary, label="⬅ Back to main", row=row)

    async def callback(self, interaction: discord.Interaction):
        if not await ensure_admin_interaction(interaction):
            return

        desc = (
            "Select a section from the dropdown to manage the bot.\n\n"
            f"- AI: {'✅' if config.get('ai_enabled', True) else '❌'}\n"
            f"- Moderation: {'✅' if config.get('moderation_enabled', True) else '❌'}\n"
            f"- XP: {'✅' if config.get('xp_enabled', True) else '❌'}\n"
            f"- Fun: {'✅' if config.get('fun_enabled', True) else '❌'}\n"
        )
        embed = dashboard_embed("🛠️ CEIL ADMIN DASHBOARD V3", desc)
        await interaction.response.edit_message(embed=embed, view=DashboardMainView())


###############################################
# SECTION: AI SETTINGS
###############################################

class AiSettingsView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ToggleFeatureButton("AI", "ai_enabled", row=0))
        self.add_item(SetAiModeSelect())
        self.add_item(BackToMainButton(row=2))


class SetAiModeSelect(Select):
    def __init__(self):
        current = config.get("ai_default_mode", "ceil")
        options = [
            SelectOption(label="CEIL Mode", value="ceil", description="Coordination & CEIL-focused"),
            SelectOption(label="Education Mode", value="education", description="Teacher / pedagogy focus"),
            SelectOption(label="Admin Mode", value="admin", description="Formal documents & emails"),
            SelectOption(label="General Mode", value="general", description="General safe conversation"),
            SelectOption(label="Fun Mode", value="fun", description="Light & playful (still safe)"),
        ]
        super().__init__(
            placeholder=f"Default AI mode (current: {current})",
            options=options,
            min_values=1,
            max_values=1,
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        if not await ensure_admin_interaction(interaction):
            return

        mode = self.values[0]
        config["ai_default_mode"] = mode
        save_config()

        desc = (
            f"Configure the AI engine, default mode and behaviour.\n\n"
            f"- AI enabled: {'✅' if config.get('ai_enabled', True) else '❌'}\n"
            f"- Default mode: `{mode}`\n"
            "Available modes: `ceil`, `education`, `admin`, `general`, `fun`, `topic:<something>`\n"
        )
        embed = dashboard_embed("🤖 AI Engine Settings", desc, color=discord.Color.blurple())
        await interaction.response.edit_message(embed=embed, view=self.view)


###############################################
# SECTION: TEACHER & RESEARCH
###############################################

class TeacherSettingsView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ToggleFeatureButton("Lessons", "lessons_enabled", row=0))
        self.add_item(ToggleFeatureButton("Research", "research_enabled", row=0))
        self.add_item(TeacherProgressOverviewButton(row=1))
        self.add_item(BackToMainButton(row=2))


class TeacherProgressOverviewButton(Button):
    def __init__(self, row: int = 1):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Show progression snapshot",
            emoji="📊",
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await ensure_admin_interaction(interaction):
            return

        # Try to reuse teacher_progress from Chunk 6
        global teacher_progress
        try:
            load_teacher_progress()
        except NameError:
            # teacher_progress system not present
            text = "Teacher progression tracking file not found in this build."
            embed = dashboard_embed("📊 Progression Snapshot", text, color=discord.Color.orange())
            await interaction.response.edit_message(embed=embed, view=self.view)
            return

        gid = str(interaction.guild.id)
        data = teacher_progress.get(gid, {})
        if not data:
            text = "No teacher progression data recorded yet."
        else:
            lines = []
            for uid, rec in data.items():
                name = rec.get("name", f"User {uid}")
                groups = ", ".join(rec.get("groups", [])) or "—"
                levels = ", ".join(rec.get("levels", [])) or "—"
                updates = rec.get("progress_updates", [])
                last = updates[-1]["summary"] if updates else "No updates yet."
                lines.append(f"**{name}** — Groups: {groups} | Levels: {levels}\nLast: {last[:160]}…")
            text = "\n\n".join(lines)
            if len(text) > 1900:
                text = text[:1900] + "\n\n[Truncated…]"

        embed = dashboard_embed("📊 Progression Snapshot", text, color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=self.view)


###############################################
# SECTION: MODERATION
###############################################

class ModerationSettingsView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ToggleFeatureButton("Moderation", "moderation_enabled", row=0))
        self.add_item(ToggleFeatureButton("Logging", "logging_enabled", row=0))
        self.add_item(BackToMainButton(row=1))


###############################################
# SECTION: GAMES & ECONOMY
###############################################

class GamesSettingsView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ToggleFeatureButton("XP", "xp_enabled", row=0))
        self.add_item(ToggleFeatureButton("Fun/Games", "fun_enabled", row=0))
        self.add_item(ViewUserXpButton(row=1))
        self.add_item(BackToMainButton(row=2))


class ViewUserXpButton(Button):
    def __init__(self, row: int = 1):
        super().__init__(style=discord.ButtonStyle.secondary, label="XP summary (top 5)", emoji="🏆", row=row)

    async def callback(self, interaction: discord.Interaction):
        if not await ensure_admin_interaction(interaction):
            return

        # Build small leaderboard from xp_data
        if not xp_data:
            text = "No XP data recorded yet."
        else:
            # convert to sortable list
            items = []
            for uid_str, info in xp_data.items():
                try:
                    uid = int(uid_str)
                except ValueError:
                    continue
                xp = info.get("xp", 0)
                level = info.get("level", 1)
                member = interaction.guild.get_member(uid)
                name = member.display_name if member else f"User {uid}"
                items.append((xp, level, name))
            items.sort(reverse=True, key=lambda t: t[0])
            top = items[:5]
            if not top:
                text = "No XP entries found."
            else:
                lines = []
                for rank, (xp, lvl, name) in enumerate(top, start=1):
                    lines.append(f"{rank}. **{name}** — Level {lvl}, XP {xp}")
                text = "\n".join(lines)

        embed = dashboard_embed("🏆 XP Leaderboard (Top 5)", text, color=discord.Color.purple())
        await interaction.response.edit_message(embed=embed, view=self.view)


###############################################
# SECTION: GOOGLE CENTER
###############################################

class GoogleSettingsView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(TestGoogleStatusButton(row=0))
        self.add_item(BackToMainButton(row=1))

    async def refresh_embed(self, interaction: discord.Interaction):
        desc = "Status of Google integrations:\n\n" + get_google_status_summary()
        embed = dashboard_embed("🟩 Google Center", desc, color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=self)


class TestGoogleStatusButton(Button):
    def __init__(self, row: int = 0):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Recheck Google status",
            emoji="🔍",
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await ensure_admin_interaction(interaction):
            return

        # Just rebuild the embed with current env status
        desc = "Status of Google integrations:\n\n" + get_google_status_summary()
        embed = dashboard_embed("🟩 Google Center", desc, color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=self.view)


###############################################
# /dashboard SLASH COMMAND
###############################################

@bot.tree.command(name="dashboard", description="Open the CEIL Admin Dashboard V3")
async def dashboard_slash(interaction: discord.Interaction):
    # Protect with staff permissions
    if not await ensure_admin_interaction(interaction):
        return

    desc = (
        "Welcome to the **CEIL Admin Dashboard V3**.\n\n"
        "Use the dropdown below to manage:\n"
        "- General bot systems\n"
        "- AI Engine modes\n"
        "- Teacher & Research suite\n"
        "- Moderation & logging\n"
        "- Economy & games\n"
        "- Google Center\n"
    )
    embed = dashboard_embed("🛠️ CEIL ADMIN DASHBOARD V3", desc)
    view = DashboardMainView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
@bot.tree.command(
    name="run_custom",
    description="Run a custom AI command defined for this server."
)
@app_commands.describe(
    name="Name of the custom command.",
    input="Your input for the command."
)
async def run_custom_slash(
    interaction: discord.Interaction,
    name: str,
    input: str,
):
    await interaction.response.defer(thinking=True)

    load_custom_commands()
    cmds = get_guild_cmds(interaction.guild.id)
    meta = cmds.get(name.lower())

    if not meta:
        return await interaction.followup.send(
            f"❌ No custom command named `{name}`.",
            ephemeral=True,
        )

    base_prompt = meta.get("prompt", "")
    full_prompt = (
        base_prompt
        + "\n\nUser input:\n"
        + input
    )
    # Use general AI with CEIL context
    result = await ai_general_reply(full_prompt, interaction.user.display_name, "general")
    await interaction.followup.send(result)


###############################################################
# END OF CHUNK 6
###############################################################

print("📦 Loaded CHUNK 6 (Admin + coordination suite + progression tracking)")
###############################################
# CEIL BOT — GOOGLE CENTER (Dashboard + Commands)
###############################################

# -------------------------------
# GOOGLE YOUTUBE SERVICE BUILDER
# -------------------------------
def build_youtube_service():
    """Builds and returns a YouTube Data API service object."""
    global YOUTUBE_API_KEY

    if not YOUTUBE_API_KEY:
        print("⚠ YOUTUBE_API_KEY not set.")
        return None

    try:
        from googleapiclient.discovery import build
        service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        return service

    except Exception as e:
        print("❌ Failed to build YouTube service:", e)
        return None

class GoogleCenterView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Drive", style=discord.ButtonStyle.primary, custom_id="gc_drive")
    async def drive_button(self, interaction: discord.Interaction, button: Button):
        text = (
            "**Google Drive commands:**\n"
            "- `/gdrive_upload` — upload a Discord file to Drive\n"
            "- `/gdrive_list` — list recent files\n"
        )
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.primary, custom_id="gc_youtube")
    async def youtube_button(self, interaction: discord.Interaction, button: Button):
        text = (
            "**YouTube commands:**\n"
            "- `/gyt_search` — search YouTube videos\n"
        )
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(label="Calendar", style=discord.ButtonStyle.primary, custom_id="gc_calendar")
    async def calendar_button(self, interaction: discord.Interaction, button: Button):
        text = (
            "**Google Calendar commands:**\n"
            "- `/gcal_events` — list upcoming events\n"
        )
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(label="Docs", style=discord.ButtonStyle.secondary, custom_id="gc_docs")
    async def docs_button(self, interaction: discord.Interaction, button: Button):
        text = (
            "**Google Docs commands:**\n"
            "- `/gdoc_create` — create a doc with given title + content\n"
        )
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(label="Sheets", style=discord.ButtonStyle.secondary, custom_id="gc_sheets")
    async def sheets_button(self, interaction: discord.Interaction, button: Button):
        text = (
            "**Google Sheets commands:**\n"
            "- `/gsheet_append` — append a row of values to a sheet\n"
        )
        await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(
    name="google_center",
    description="Open the Google integration control panel (Drive, YouTube, Calendar, Docs, Sheets)."
)
async def google_center_slash(interaction: discord.Interaction):
    # If you want this to be staff-only, uncomment:
    # if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
    #     return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)

    embed = make_embed(
        title="🌐 Google Center",
        description=(
            "Control panel for all Google integrations:\n"
            "- Drive: upload/list files\n"
            "- YouTube: search videos\n"
            "- Calendar: view events\n"
            "- Docs: generate documents from CEIL content\n"
            "- Sheets: log progression / XP / attendance\n\n"
            "Use the buttons below to see available commands."
        ),
        color=discord.Color.blurple(),
    )
    view = GoogleCenterView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
# IMAGE GENERATOR — /imagine
###############################################################

@bot.tree.command(
    name="imagine",
    description="Generate an image from a text prompt (poster, avatar, scene, etc.)."
)
@app_commands.describe(
    prompt="Describe what you want to see.",
    size="Image size (512, 768, 1024)."
)
async def imagine_slash(
    interaction: discord.Interaction,
    prompt: str,
    size: int = 1024,
):
    if not config.get("images_enabled", True):
        return await interaction.response.send_message(
            "Image tools are disabled.",
            ephemeral=True,
        )

    if size not in (512, 768, 1024):
        size = 1024

    await interaction.response.defer(thinking=True)

    try:
        img_resp = client_oai.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=f"{size}x{size}",
            n=1,
        )
        b64_data = img_resp.data[0].b64_json
        img_bytes = base64.b64decode(b64_data)

        file = discord.File(
            io.BytesIO(img_bytes),
            filename="imagine.png",
        )
        await interaction.followup.send(
            content=f"🖼️ Prompt: `{prompt}`",
            file=file,
        )
    except Exception as e:
        print("❌ IMAGE GENERATION ERROR:", e)
        await interaction.followup.send(
            "⚠ Failed to generate image.",
            ephemeral=True,
        )
###############################################################
# AI VOICE ASSISTANT — TTS + Voice Reply
###############################################################

@bot.tree.command(
    name="tts",
    description="Text-to-speech: generate an audio file from text."
)
@app_commands.describe(
    text="What should I say?",
    voice_hint="Optional: short hint for style/voice (calm, energetic, teacher, etc.)."
)
async def tts_slash(
    interaction: discord.Interaction,
    text: str,
    voice_hint: str = "teacher",
):
    await interaction.response.defer(thinking=True)

    try:
        audio_resp = client_oai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
        )
        audio_bytes = audio_resp.read()

        file = discord.File(
            io.BytesIO(audio_bytes),
            filename="tts.mp3",
        )
        await interaction.followup.send(
            content=f"🎧 TTS generated (voice hint: `{voice_hint}`)",
            file=file,
        )
    except Exception as e:
        print("❌ TTS ERROR:", e)
        await interaction.followup.send(
            "⚠ Failed to generate audio.",
            ephemeral=True,
        )


@bot.tree.command(
    name="voice_reply",
    description="Send a short voice note; the bot transcribes and replies."
)
@app_commands.describe(
    audio="Upload a short audio file (voice note).",
    mode="Reply style: general, tutor, admin."
)
async def voice_reply_slash(
    interaction: discord.Interaction,
    audio: discord.Attachment,
    mode: str = "general",
):
    await interaction.response.defer(thinking=True)

    try:
        audio_bytes = await audio.read()
    except Exception:
        return await interaction.followup.send(
            "Failed to read audio file.",
            ephemeral=True,
        )

    # Save temporarily in memory
    temp_fp = io.BytesIO(audio_bytes)
    temp_fp.name = "voice_input.m4a"  # name hint

    try:
        transcript_obj = client_oai.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=temp_fp,
            response_format="text",
        )
        transcript = transcript_obj
    except Exception as e:
        print("❌ TRANSCRIPTION ERROR:", e)
        return await interaction.followup.send(
            "⚠ Failed to transcribe audio.",
            ephemeral=True,
        )

    # Route to appropriate LLM helper
    content = transcript
    user_name = interaction.user.display_name

    if mode == "tutor":
        reply = await teacher_llm(
            f"Student voice note (transcribed):\n{content}\n\n"
            "Respond as a supportive tutor."
        )
    elif mode == "admin":
        reply = await admin_llm(
            f"Voice note (transcribed):\n{content}\n\n"
            "Respond in a professional, concise way."
        )
    else:
        reply = await ai_general_reply(content, user_name, "general")

    await interaction.followup.send(
        f"🗣️ **Transcript:**\n{content}\n\n**Reply:**\n{reply}"
    )

###############################################################
# 47. AI AUTO-REPLY ENGINE — on_message
###############################################################

@bot.event
async def on_message(msg: discord.Message):
    # Ignore bots
    if msg.author.bot:
        return

    print(f"MSG RECEIVED: {msg.content}")  # optional debug

    guild = msg.guild
    content = msg.content.strip()
    uid = msg.author.id

    # ======================================================
    # 1. PREFIX COMMANDS MUST RUN FIRST (e.g. !hangman !roll)
    # ======================================================
    if content.startswith("!"):
        return await bot.process_commands(msg)

    # Slash commands handled by Discord — do nothing
    if content.startswith("/"):
        return

    # ======================================================
    # 2. XP SYSTEM
    # ======================================================
    if config.get("xp_enabled", True):
        leveled_up, new_level = add_xp(uid, amount=5)
        if leveled_up:
            try:
                await msg.channel.send(
                    f"🎉 {msg.author.mention} leveled up! **Level {new_level}!**"
                )
            except:
                pass

    # ======================================================
    # 3. MODERATION LAYERS
    # ======================================================
    if config.get("moderation_enabled", True):

        lower = content.lower()

        # banned words
        if any(b in lower for b in BANNED_WORDS):
            try:
                await msg.delete()
            except:
                pass
            await log_event(guild, f"🚨 Banned word removed from {msg.author}")
            return

        # links
        if is_link(content) and not is_staff(msg.author):
            try:
                await msg.delete()
            except:
                pass
            await log_event(guild, f"🔗 Link blocked from {msg.author}")
            return

        # spam detection
        now = time.time()
        gid = guild.id if guild else 0

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

        # slowmode
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

    # ======================================================
    # 4. AUTO AI REPLY (Activated only when triggered)
    # ======================================================
    if config.get("ai_enabled", True) and msg.guild:

        mode = channel_modes.get(msg.channel.id, config.get("ai_default_mode", "ceil"))

        trigger = (
            msg.channel.name.startswith("ai-") or
            content.lower().startswith("ceil") or
            f"<@{bot.user.id}>" in content
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

    # ======================================================
    # 5. Final: allow commands again (safe)
    # ======================================================
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
# AI TUTOR MODE — learning-oriented assessment
###############################################################

async def tutor_llm(prompt: str, level: str | None = None) -> str:
    """
    Tutor mode: focused on learning-oriented assessment,
    step-by-step questioning, and formative feedback.
    """
    level_info = f"Target learner level: {level}.\n" if level else ""
    system = (
        BASE_SYSTEM_PROMPT
        + "\n\nYou are now in AI TUTOR MODE.\n"
          "- Focus on formative assessment, not grades.\n"
          "- Ask short, focused questions.\n"
          "- Give clear, constructive feedback.\n"
          "- Suggest next steps or micro-tasks.\n"
        + MULTILINGUAL_NOTE
    )
    full_prompt = level_info + prompt
    return await call_openai(system, full_prompt, temperature=0.4)


@bot.tree.command(
    name="tutor_session",
    description="Generate a mini tutoring session plan for a learner."
)
@app_commands.describe(
    level="Approximate CEFR level (A1–C1).",
    skill="Main skill: grammar, vocabulary, speaking, writing, etc.",
    topic="Topic or structure (e.g. present perfect, travel, complaints)."
)
async def tutor_session_slash(
    interaction: discord.Interaction,
    level: str,
    skill: str,
    topic: str,
):
    await interaction.response.defer(thinking=True)

    prompt = (
        f"Design a short tutoring sequence for a learner at level {level}.\n"
        f"Skill focus: {skill}\n"
        f"Topic: {topic}\n\n"
        "Include:\n"
        "1) Quick diagnostic question(s)\n"
        "2) Micro-explanation adapted to the level\n"
        "3) 3–5 practice items (with expected answers)\n"
        "4) Feedback rules (how the tutor should respond to mistakes)\n"
        "5) A short homework suggestion."
    )
    result = await tutor_llm(prompt, level=level)
    await interaction.followup.send(result)


@bot.tree.command(
    name="tutor_assess",
    description="Analyze a student's answer and give tutor-style feedback."
)
@app_commands.describe(
    level="Approximate level (A1–C1).",
    task="What was the task? (e.g. write an email, describe a picture).",
    answer="Paste the student's answer here."
)
async def tutor_assess_slash(
    interaction: discord.Interaction,
    level: str,
    task: str,
    answer: str,
):
    await interaction.response.defer(thinking=True)

    prompt = (
        f"Learner level: {level}\n"
        f"Task: {task}\n\n"
        f"Student answer:\n{answer}\n\n"
        "Give learning-oriented feedback:\n"
        "1) Very short overall comment.\n"
        "2) 3–5 key strengths.\n"
        "3) 3–5 priority problems (grammar, vocab, organization, etc.).\n"
        "4) Suggested improved version of a part of the answer.\n"
        "5) 2–3 micro-tasks the learner can do next.\n"
    )
    result = await tutor_llm(prompt, level=level)
    await interaction.followup.send(result)

###############################################################
# 49. FINAL on_ready — sync everything
###############################################################
# ============ FIX: FORCE ADMIN GROUP ATTACH ============
# Railway sometimes reloads chunks before admin_group exists.
# This safely attaches the group to the bot.tree.

try:
    bot.tree.add_command(admin_group, override=True)
except Exception:
    pass

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
    # Load persistent data
    load_config()
    load_xp()
    try:
        load_coins()
    except NameError:
        pass
    # teacher_progress helpers exist from Chunk 6
    try:
        load_teacher_progress()
    except NameError:
        pass
    # Load coins data
    try:
        load_coins()
    except Exception as e:
        print("⚠ Failed to load coins data:", e)

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
###############################################
# GLOBAL HELP CENTER — /help (Discord Embed)
###############################################

@bot.tree.command(name="help", description="Show the full CEIL Bot help panel.")
async def help_slash(interaction: discord.Interaction):

    embed = discord.Embed(
        title="📘 CEIL Full-Max Bot — Help Panel",
        description="All commands available in the CEIL Coordination Bot.",
        color=discord.Color.blue()
    )

    # ----------------------
    # AI & MODES
    # ----------------------
    embed.add_field(
        name="🤖 AI & Modes",
        value=(
            "`!ceil <message>` — Ask the AI in current mode\n"
            "`!mode <topic>` — Change AI mode (teaching / admin / research / fun)\n"
            "`!currentmode` — Show current channel mode\n"
            "`!modes` — List all available modes\n"
        ),
        inline=False
    )

    # ----------------------
    # TEACHING SUITE
    # ----------------------
    embed.add_field(
        name="🧑‍🏫 Teaching Suite",
        value=(
            "`/lessonplan` — Generate CEFR lesson plan\n"
            "`/worksheet` — Create ESL worksheet\n"
            "`/quiz` — Generate quiz\n"
            "`/template` — Create blank teaching templates\n"
            "`/dialogue` — Generate speaking dialogue\n"
            "`/homework` — Create a homework task\n"
            "`/session_report` — Turn raw notes into a session report\n"
            "`/observation_form` — Create an observation form\n"
            "`/analyze_student_text` — Analyze learner writing\n"
            "`/improve_writing` — Rewrite text professionally\n"
        ),
        inline=False
    )

    # ----------------------
    # RESEARCH CENTER
    # ----------------------
    embed.add_field(
        name="📚 Research Tools",
        value=(
            "`/article_summary` — Summarize academic article\n"
            "`/research_outline` — Generate MA/PhD research outline\n"
            "`/compare_theories` — Compare scholars/theories\n"
            "`/apa_cite` — Create APA citation\n"
            "`/explain_theory` — Explain an academic concept\n"
            "`/translate_academic` — Academic translation\n"
            "`/evaluate_paper` — Critical evaluation\n"
            "`/literature_review` — Mini literature review\n"
            "`/supervisor_feedback` — Supervisor-style feedback\n"
        ),
        inline=False
    )

    # ----------------------
    # GOOGLE SERVICES
    # ----------------------
    embed.add_field(
        name="🔧 Google Services",
        value=(
            "`/gdrive_upload` — Upload file to Drive\n"
            "`/gdrive_search` — Search Google Drive\n"
            "`/youtube_search` — Search YouTube videos\n"
            "`/calendar_events` — View upcoming events\n"
            "`/calendar_add_event` — Add Google Calendar event\n"
            "`/sheets_read` — Read range from Sheets\n"
            "`/sheets_update` — Write to Sheets\n"
        ),
        inline=False
    )

    # ----------------------
    # TEACHER PROGRESSION SYSTEM
    # ----------------------
    embed.add_field(
        name="📊 Teacher Progress & Registration",
        value=(
            "`/teacher_register` — Register groups & levels\n"
            "`/progress_update` — Submit progression report\n"
        ),
        inline=False
    )

    # ----------------------
    # VISION & OCR
    # ----------------------
    embed.add_field(
        name="👁️ Vision / OCR / Image AI",
        value=(
            "`/analyze_image` — Describe & analyze image\n"
            "`/extract_text` — Extract text from image\n"
            "`/grade_handwriting` — Evaluate handwriting\n"
        ),
        inline=False
    )

    # ----------------------
    # FUN ENGINE (COINS + REACTIONS)
    # ----------------------
    embed.add_field(
        name="🎮 Fun & Games (Coins System)",
        value=(
            "`!daily` — Claim daily coins\n"
            "`!blackjack` — Start blackjack game (play with 👊 ✋ ❌ reactions)\n"
            "`!hangman` — Start hangman\n"
            "`!guess <letter>` — Guess a letter\n"
            "`!trivia` — Start trivia\n"
            "`!answer <text>` — Answer question\n"
            "`!roll` — Dice roll\n"
            "`!flip` — Coin flip\n"
            "`!choose A | B | C` — Random picker\n"
            "`!compliment` — Random motivation\n"
        ),
        inline=False
    )

    # ----------------------
    # ADMIN & MODERATION
    # ----------------------
    embed.add_field(
        name="🛠 Admin & Moderation",
        value=(
            "`/admin announce` — Post announcement\n"
            "`/admin dm_all` — DM all users with a role\n"
            "`/admin create_structure` — Generate CEIL server layout\n"
            "`/admin progress_report` — Full teacher tracking\n"
            "`!warn <user> <reason>` — Warn user\n"
            "`!warnings <user>` — View warnings\n"
            "`!mute <user>` — Mute\n"
            "`!unmute <user>` — Unmute\n"
            "`!kick <user>` — Kick\n"
            "`!ban <user>` — Ban\n"
            "`!purge <amount>` — Bulk delete\n"
            "`!slowmode <seconds>` — Enable slowmode\n"
        ),
        inline=False
    )

    # ----------------------
    # CLOSE MESSAGE
    # ----------------------
    embed.set_footer(
        text="CEIL Full-Max Bot — AI • Teaching • Research • Admin • Fun",
    )

    await interaction.response.send_message(embed=embed)



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

    try:
        load_coins()
    except Exception as e:
        print("⚠ Failed to load coins data:", e)

    print("🚀 Starting CEIL Full-Max Bot...")
    bot.run(DISCORD_TOKEN)
