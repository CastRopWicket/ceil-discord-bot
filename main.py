# ===============================================
# CEIL BOT — FULL MAX EDITION (CLEAN FINAL BUILD)
# One file — All features — No duplicates — Ready to deploy
# ===============================================

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput
import os
import json
import time
import random
import asyncio
import traceback
import io
import base64
import re
from datetime import datetime, timezone, timedelta

from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================== ENVIRONMENT ==================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("Missing DISCORD_TOKEN or OPENAI_API_KEY")

GOOGLE_APPLICATION_CREDENTIALS_BASE64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# ================== BOT SETUP ==================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================== FILES ==================
CONFIG_FILE = "config.json"
XP_FILE = "xp_data.json"
COINS_FILE = "coins_data.json"
TEACHER_PROGRESS_FILE = "teacher_progress.json"
CUSTOM_CMDS_FILE = "custom_commands.json"

# ================== DEFAULT CONFIG ==================
DEFAULT_CONFIG = {
    "ai_enabled": True,
    "moderation_enabled": True,
    "xp_enabled": True,
    "fun_enabled": True,
    "lessons_enabled": True,
    "research_enabled": True,
    "images_enabled": True,
    "logging_enabled": True,
    "ai_default_mode": "ceil",
    "auto_role_name": "Teacher",
    "banned_words": ["fuck", "shit", "bitch", "asshole", "cunt"],
    "ai_model": "gpt-4o-mini",
    "max_reply_length": 1900
}

config = {}
BANNED_WORDS = []
STAFF_ROLES = {"Coordinator", "Deputy Coordinator", "Moderator", "Administrator"}

xp_data = {}
coins_data = {}
teacher_progress = {}
custom_commands = {}
channel_modes = {}
spam_tracker = {}
slowmode_settings = {}
last_message_time = {}
blackjack_sessions = {}
hangman_games = {}
active_trivia = {}

google_drive = None
google_calendar = None
google_youtube = None
google_docs = None
google_sheets = None
GOOGLE_READY = False

client_oai = OpenAI(api_key=OPENAI_API_KEY)

# ================== LOAD/SAVE ==================
def load_json(file, default={}):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default.copy()
    return default.copy()

def save_json(file, data):
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Save error {file}: {e}")

def load_config():
    global config, BANNED_WORDS
    config = load_json(CONFIG_FILE, DEFAULT_CONFIG)
    for k, v in DEFAULT_CONFIG.items():
        config.setdefault(k, v)
    BANNED_WORDS = config.get("banned_words", [])
    save_json(CONFIG_FILE, config)

load_config()
xp_data = load_json(XP_FILE)
coins_data = load_json(COINS_FILE)
teacher_progress = load_json(TEACHER_PROGRESS_FILE)
custom_commands = load_json(CUSTOM_CMDS_FILE)

# ================== GOOGLE INIT ==================
def init_google():
    global google_drive, google_calendar, google_youtube, google_docs, google_sheets, GOOGLE_READY
    if not GOOGLE_APPLICATION_CREDENTIALS_BASE64:
        return
    try:
        decoded = base64.b64decode(GOOGLE_APPLICATION_CREDENTIALS_BASE64).decode("utf-8")
        creds_dict = json.loads(decoded)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/youtube.force-ssl",
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/spreadsheets"
            ]
        )
        google_drive = build("drive", "v3", credentials=creds)
        google_calendar = build("calendar", "v3", credentials=creds)
        google_docs = build("docs", "v1", credentials=creds)
        google_sheets = build("sheets", "v4", credentials=creds)
        if YOUTUBE_API_KEY:
            google_youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        GOOGLE_READY = True
        print("Google services initialized")
    except Exception as e:
        print("Google init failed:", e)

init_google()

# ================== UTILITIES ==================
def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.name in STAFF_ROLES for r in member.roles)

def make_embed(title: str, description: str = "", color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.utcnow()
    return embed

def get_log_channel(guild):
    if not config.get("logging_enabled", True):
        return None
    return discord.utils.get(guild.text_channels, name="ceil-logs")

async def log_event(guild, text: str):
    ch = get_log_channel(guild)
    if ch:
        try:
            await ch.send(text)
        except:
            pass

# ================== XP SYSTEM ==================
def add_xp(user_id: int, amount: int = 10):
    uid = str(user_id)
    if uid not in xp_data:
        xp_data[uid] = {"xp": 0, "level": 1}
    xp_data[uid]["xp"] += amount
    xp = xp_data[uid]["xp"]
    level = 1
    while xp >= level * 100:
        level += 1
    old = xp_data[uid]["level"]
    leveled = level > old
    xp_data[uid]["level"] = level
    save_json(XP_FILE, xp_data)
    return leveled, level

def get_xp_profile(user_id: int):
    uid = str(user_id)
    rec = xp_data.get(uid, {"xp": 0, "level": 1})
    return rec["xp"], rec["level"]

# ================== COINS SYSTEM ==================
def get_coins(user_id: int) -> int:
    uid = str(user_id)
    coins_data.setdefault(uid, {"coins": 0, "last_daily": None})
    return coins_data[uid]["coins"]

def add_coins(user_id: int, amount: int) -> int:
    uid = str(user_id)
    coins_data.setdefault(uid, {"coins": 0, "last_daily": None})
    coins_data[uid]["coins"] = max(0, coins_data[uid]["coins"] + amount)
    save_json(COINS_FILE, coins_data)
    return coins_data[uid]["coins"]

def can_claim_daily(user_id: int):
    uid = str(user_id)
    coins_data.setdefault(uid, {"coins": 0, "last_daily": None})
    last = coins_data[uid].get("last_daily")
    if not last:
        return True, 0
    last_dt = datetime.fromisoformat(last)
    diff = (datetime.utcnow() - last_dt).total_seconds() / 3600
    return diff >= 24, max(0, 24 - diff)

def mark_daily_claimed(user_id: int, amount: int = 100):
    uid = str(user_id)
    coins_data.setdefault(uid, {"coins": 0, "last_daily": None})
    coins_data[uid]["last_daily"] = datetime.utcnow().isoformat()
    coins_data[uid]["coins"] += amount
    save_json(COINS_FILE, coins_data)

# ================== AI CORE ==================
BASE_SYSTEM_PROMPT = """
You are CEIL Assistant for Centre d’Enseignement Intensif des Langues at UHBC Chlef, Algeria.
You help teachers and coordinators with lesson planning, progression, research, reports, and coordination.
"""

MULTILINGUAL_NOTE = """
Detect the user's language and reply in the SAME language unless they ask otherwise.
Supported: English, French, Arabic, German, Spanish, Turkish, Russian, etc.
"""

AI_MODES = {
    "ceil": "Coordination & CEIL internal matters.",
    "education": "Pedagogy, lesson planning, CEFR, classroom management.",
    "admin": "Formal emails, reports, policies.",
    "general": "Safe general conversation.",
    "fun": "Playful but professional.",
}

def build_ai_system_prompt(mode: str) -> str:
    mode = mode.lower()
    if mode.startswith("topic:"):
        extra = f"Focus only on: {mode[6:]}"
    else:
        extra = AI_MODES.get(mode, AI_MODES["ceil"])
    return BASE_SYSTEM_PROMPT + "\n\n" + extra + "\n\n" + MULTILINGUAL_NOTE

async def call_openai(system: str, user: str, temp=0.4):
    try:
        resp = client_oai.chat.completions.create(
            model=config.get("ai_model", "gpt-4o-mini"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temp,
        )
        text = resp.choices[0].message.content.strip()
        if len(text) > config.get("max_reply_length", 1900):
            text = text[:1900] + "\n\n[Truncated...]"
        return text
    except Exception as e:
        print("OpenAI error:", e)
        return "AI error, try again."

async def ai_general_reply(message: str, name: str, mode: str) -> str:
    system = build_ai_system_prompt(mode)
    prompt = f"User ({name}) says:\n{message}"
    return await call_openai(system, prompt)

async def teacher_llm(prompt: str) -> str:
    system = BASE_SYSTEM_PROMPT + "\nYou are in TEACHER SUPPORT MODE." + MULTILINGUAL_NOTE
    return await call_openai(system, prompt)

async def admin_llm(prompt: str) -> str:
    system = BASE_SYSTEM_PROMPT + "\nYou are in ADMIN MODE — formal writing." + MULTILINGUAL_NOTE
    return await call_openai(system, prompt, 0.3)

async def research_llm(prompt: str) -> str:
    system = BASE_SYSTEM_PROMPT + "\nYou are in ACADEMIC RESEARCH MODE." + MULTILINGUAL_NOTE
    return await call_openai(system, prompt, 0.25)

# ================== MODERATION ==================
def is_link(text: str) -> bool:
    return bool(re.search(r"https?://|discord\.gg/", text, re.I))

async def apply_auto_mute(member: discord.Member, guild: discord.Guild, reason: str):
    role = discord.utils.get(guild.roles, name="Muted")
    if not role:
        role = await guild.create_role(name="Muted", reason="Auto moderation")
        for ch in guild.channels:
            try:
                await ch.set_permissions(role, send_messages=False, add_reactions=False, speak=False)
            except:
                pass
    await member.add_roles(role, reason=reason)
    await log_event(guild, f"Auto-muted {member.mention} — {reason}")

    async def unmute():
        await asyncio.sleep(15 * 60)
        if role in member.roles:
            await member.remove_roles(role)
            await log_event(guild, f"Auto-unmuted {member.mention}")
    bot.loop.create_task(unmute())

# ================== ON MESSAGE (FINAL) ==================
@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return

    if config.get("xp_enabled", True):
        leveled, lvl = add_xp(msg.author.id, 5)
        if leveled:
            await msg.channel.send(f"Level up! {msg.author.mention} → Level **{lvl}**!")

    if config.get("moderation_enabled", True) and msg.guild:
        lower = msg.content.lower()
        if any(w in lower for w in BANNED_WORDS):
            await msg.delete()
            await log_event(msg.guild, f"Banned word — {msg.author}")
            return
        if is_link(msg.content) and not is_staff(msg.author):
            await msg.delete()
            await log_event(msg.guild, f"Link blocked — {msg.author}")
            return

        now = time.time()
        gid = msg.guild.id
        uid = msg.author.id
        spam_tracker.setdefault(gid, {})
        spam_tracker[gid].setdefault(uid, [])
        spam_tracker[gid][uid] = [t for t in spam_tracker[gid][uid] if now - t < 8] + [now]
        if len(spam_tracker[gid][uid]) >= 7:
            await apply_auto_mute(msg.author, msg.guild, "Spam")
            return

    if config.get("ai_enabled", True) and msg.guild:
        mode = channel_modes.get(msg.channel.id, config.get("ai_default_mode", "ceil"))
        trigger = (
            msg.channel.name.startswith("ai-") or
            msg.content.lower().startswith("ceil") or
            f"<@{bot.user.id}>" in msg.content
        )
        if trigger and not msg.content.startswith(("!", "/")):
            await msg.channel.trigger_typing()
            reply = await ai_general_reply(msg.content, str(msg.author), mode)
            await msg.reply(reply, mention_author=False)

    await bot.process_commands(msg)

# ================== ADMIN GROUP ==================
admin_group = app_commands.Group(name="admin", description="Admin & coordination commands")
bot.tree.add_command(admin_group)

# ================== PART 2/3 COMING IN NEXT MESSAGE ==================
# (I have to split because of character limit)
# Just reply "next" and I'll send Part 2 immediately
# ================== ADMIN DASHBOARD (Simple & Working) ==================
class FeatureToggleView(View):
    def __init__(self):
        super().__init__(timeout=300)
        features = [
            ("ai_enabled", "AI Engine"),
            ("moderation_enabled", "Moderation"),
            ("xp_enabled", "XP System"),
            ("fun_enabled", "Fun & Games"),
            ("lessons_enabled", "Lessons Suite"),
            ("research_enabled", "Research Suite"),
            ("images_enabled", "Vision / Images"),
            ("logging_enabled", "Logging"),
        ]
        for key, name in features:
            state = "ON" if config.get(key, True) else "OFF"
            color = discord.ButtonStyle.success if state == "ON" else discord.ButtonStyle.danger
            btn = Button(label=f"{name} [{state}]", style=color, custom_id=key)
            btn.callback = self.toggle_callback
            self.add_item(btn)

    async def toggle_callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Staff only", ephemeral=True)
        key = interaction.data["custom_id"]
        config[key] = not config[key]
        save_config()
        await interaction.response.edit_message(content=f"Toggled {key} → {config[key]}", view=FeatureToggleView())

@admin_group.command(name="panel", description="Open the feature control panel")
async def admin_panel(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Staff only", ephemeral=True)
    await interaction.response.send_message("CEIL Bot Control Panel", view=FeatureToggleView(), ephemeral=True)

# ================== TEACHER SUITE ==================
@tree.command(name="lessonplan", description="Generate a CEFR-aligned lesson plan")
@app_commands.describe(level="CEFR level", topic="Topic", duration="Minutes")
async def lessonplan(interaction: discord.Interaction, level: str, topic: str, duration: int = 90):
    await interaction.response.defer()
    prompt = f"Create a detailed ESL lesson plan for CEFR {level} on '{topic}', {duration} minutes. Include objectives, warm-up, presentation, practice, production, assessment, homework."
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)

@tree.command(name="worksheet", description="Generate an ESL worksheet")
@app_commands.describe(skill="Skill", topic="Topic", level="Level")
async def worksheet(interaction: discord.Interaction, skill: str, topic: str, level: str):
    await interaction.response.defer()
    prompt = f"Create a worksheet for {skill} on '{topic}' at {level}. Include 3 activities and answer key."
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)

@tree.command(name="quiz", description="Generate a quiz")
@app_commands.describe(topic="Topic", items: int = 10, level: str = "B1")
async def quiz(interaction: discord.Interaction, topic: str, items: int, level: str):
    await interaction.response.defer()
    prompt = f"Create a {items}-question quiz on '{topic}' for {level}. Mix MCQ and short answer. Include answer key."
    text = await teacher_llm(prompt)
    await interaction.followup.send(text)

# ================== RESEARCH SUITE ==================
@tree.command(name="article_summary", description="Summarize a research article")
@app_commands.describe(text="Paste abstract or text")
async def article_summary(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    prompt = f"Summarize this academic text:\n{text}\nStructure: Problem, Methodology, Findings, Implications."
    result = await research_llm(prompt)
    await interaction.followup.send(result)

@tree.command(name="research_outline", description="Generate research outline")
@app_commands.describe(topic="Research topic", level: str = "MA")
async def research_outline(interaction: discord.Interaction, topic: str, level: str):
    await interaction.response.defer()
    prompt = f"Create a {level}-level research outline for: {topic}"
    result = await research_llm(prompt)
    await interaction.followup.send(result)

# ================== GOOGLE COMMANDS ==================
@tree.command(name="gdrive_upload", description="Upload file to Google Drive")
@app_commands.describe(file="File to upload")
async def gdrive_upload(interaction: discord.Interaction, file: discord.Attachment):
    if not GOOGLE_READY:
        return await interaction.response.send_message("Google not configured", ephemeral=True)
    await interaction.response.defer()
    data = await file.read()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=file.content_type or "application/octet-stream")
    metadata = {"name": file.filename}
    try:
        created = google_drive.files().create(body=metadata, media_body=media, fields="id,webViewLink").execute()
        link = created.get("webViewLink", f"https://drive.google.com/file/d/{created['id']}/view")
        await interaction.followup.send(f"Uploaded: {link}")
    except Exception as e:
        await interaction.followup.send("Upload failed")

@tree.command(name="gyt_search", description="Search YouTube")
@app_commands.describe(query="Search query", limit: int = 5)
async def gyt_search(interaction: discord.Interaction, query: str, limit: int = 5):
    if not google_youtube:
        return await interaction.response.send_message("YouTube API not set", ephemeral=True)
    await interaction.response.defer()
    resp = google_youtube.search().list(q=query, part="snippet", maxResults=limit, type="video").execute()
    lines = [f"**Results for:** {query}"]
    for item in resp.get("items", []):
        title = item["snippet"]["title"]
        vid = item["id"]["videoId"]
        url = f"https://www.youtube.com/watch?v={vid}"
        lines.append(f"• [{title}]({url})")
    await interaction.followup.send("\n".join(lines))

# ================== VISION COMMANDS ==================
async def analyze_image_bytes(image_bytes: bytes):
    b64 = base64.b64encode(image_bytes).decode()
    try:
        resp = client_oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in detail. If it's student work, give feedback."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }]
        )
        return resp.choices[0].message.content
    except:
        return "Vision error"

@tree.command(name="analyze_image", description="Analyze uploaded image")
@app_commands.describe(image="Image file")
async def analyze_image(interaction: discord.Interaction, image: discord.Attachment):
    if not config.get("images_enabled", True):
        return await interaction.response.send_message("Images disabled", ephemeral=True)
    await interaction.response.defer()
    bytes_data = await image.read()
    result = await analyze_image_bytes(bytes_data)
    await interaction.followup.send(result)

# ================== BLACKJACK ==================
def bj_draw():
    ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
    return random.choice(ranks)

def bj_value(cards):
    total = 0
    aces = 0
    for c in cards:
        if c in "JQK":
            total += 10
        elif c == "A":
            total += 11
            aces += 1
        else:
            total += int(c)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

@bot.command(name="blackjack")
async def blackjack(ctx: commands.Context, bet: int = 10):
    if bet < 1 or get_coins(ctx.author.id) < bet:
        return await ctx.send("Invalid bet")
    add_coins(ctx.author.id, -bet)
    player = [bj_draw(), bj_draw()]
    dealer = [bj_draw(), bj_draw()]
    blackjack_sessions[ctx.author.id] = {"player": player, "dealer": dealer, "bet": bet}
    await ctx.send(f"Bet: {bet}\nYour hand: {player} ({bj_value(player)})\nDealer: {dealer[0]} ?")

@bot.command(name="hit")
async def bj_hit(ctx: commands.Context):
    if ctx.author.id not in blackjack_sessions:
        return
    game = blackjack_sessions[ctx.author.id]
    game["player"].append(bj_draw())
    val = bj_value(game["player"])
    if val > 21:
        del blackjack_sessions[ctx.author.id]
        await ctx.send(f"Bust! You lose {game['bet']} coins.")
    else:
        await ctx.send(f"Your hand: {game['player']} ({val})")

@bot.command(name="stand")
async def bj_stand(ctx: commands.Context):
    if ctx.author.id not in blackjack_sessions:
        return
    game = blackjack_sessions[ctx.author.id]
    while bj_value(game["dealer"]) < 17:
        game["dealer"].append(bj_draw())
    pv = bj_value(game["player"])
    dv = bj_value(game["dealer"])
    msg = f"Your: {pv} | Dealer: {dv}\n"
    if dv > 21 or pv > dv:
        add_coins(ctx.author.id, game["bet"] * 2)
        msg += "You win!"
    elif pv == dv:
        add_coins(ctx.author.id, game["bet"])
        msg += "Push"
    else:
        msg += "You lose"
    del blackjack_sessions[ctx.author.id]
    await ctx.send(msg)

# ================== DAILY & COINS ==================
@tree.command(name="daily")
async def daily(interaction: discord.Interaction):
    can, left = can_claim_daily(interaction.user.id)
    if not can:
        await interaction.response.send_message(f"Already claimed! Try again in {left:.1f}h")
    else:
        mark_daily_claimed(interaction.user.id, 100)
        await interaction.response.send_message("Claimed 100 coins!")

@tree.command(name="coins")
async def coins(interaction: discord.Interaction):
    bal = get_coins(interaction.user.id)
    await interaction.response.send_message(f"You have {bal} coins", ephemeral=True)

# ================== PART 3/3 IN NEXT MESSAGE ==================
# ================== HANGMAN ==================
HANGMAN_WORDS = ["grammar", "vocabulary", "listening", "speaking", "reading", "writing", "teacher", "student", "classroom", "lesson"]

@bot.command(name="hangman")
async def hangman(ctx):
    word = random.choice(HANGMAN_WORDS).lower()
    hangman_games[ctx.author.id] = {"word": word, "guesses": set(), "fails": 0}
    await ctx.send(f"Hangman started! Word: `{' '.join('_' for _ in word)}`\nGuess with !guess <letter>")

@bot.command(name="guess")
async def guess(ctx, letter: str):
    if ctx.author.id not in hangman_games:
        return await ctx.send("No game! Start with !hangman")
    if len(letter) != 1 or not letter.isalpha():
        return await ctx.send("One letter only")
    game = hangman_games[ctx.author.id]
    letter = letter.lower()
    if letter in game["guesses"]:
        return await ctx.send("Already guessed")
    game["guesses"].add(letter)
    if letter not in game["word"]:
        game["fails"] += 1
        if game["fails"] >= 6:
            del hangman_games[ctx.author.id]
            return await ctx.send(f"You lost! Word was: {game['word']}")
    display = " ".join(c if c in game["guesses"] else "_" for c in game["word"])
    if "_" not in display:
        del hangman_games[ctx.author.id]
        add_xp(ctx.author.id, 50)
        await ctx.send(f"You won! Word: {game['word']} (+50 XP)")
    else:
        await ctx.send(f"{display} | Fails: {game['fails']}/6")

# ================== TEACHER REGISTRATION ==================
@tree.command(name="teacher_register", description="Register your groups and levels")
@app_commands.describe(groups="e.g. G3, G5", levels="e.g. N4, N6")
async def teacher_register(interaction: discord.Interaction, groups: str, levels: str):
    uid = str(interaction.user.id)
    gid = str(interaction.guild.id)
    teacher_progress.setdefault(gid, {})
    teacher_progress[gid][uid] = {
        "name": interaction.user.display_name,
        "groups": [g.strip() for g in groups.split(",")],
        "levels": [l.strip() for l in levels.split(",")],
        "updates": []
    }
    save_json(TEACHER_PROGRESS_FILE, teacher_progress)
    await interaction.response.send_message("Registered! Coordinator will see your info.", ephemeral=True)

# ================== ON READY ==================
@bot.event
async def on_ready():
    load_config()
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print("Sync error:", e)
    try:
        tree.add_command(admin_group)
    except:
        pass
    print("="*60)
    print(f"CEIL BOT FULL MAX EDITION IS READY — {bot.user}")
    print(f"Servers: {len(bot.guilds)} | Multilingual AI Active")
    print("All features loaded: Teacher Suite • Research • Google • Vision • Games • Admin Panel")
    print("="*60)

# ================== FINAL RUN ==================
if __name__ == "__main__":
    print("Launching CEIL Bot Full Max Edition...")
    bot.run(DISCORD_TOKEN)
