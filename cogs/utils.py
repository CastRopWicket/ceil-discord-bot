
import os, json
from datetime import datetime
from typing import Dict, Any, Tuple
import discord
from discord.ext import commands
from openai import OpenAI

CONFIG_FILE = "config.json"
XP_FILE = "xp_data.json"
TEACHER_PROGRESS_FILE = "teacher_progress.json"

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
  "banned_words": ["fuck","shit","bitch"],
  "ai_model": "gpt-4.1-mini",
  "max_reply_length": 1900,
  "log_channel_name": "ceil-logs"
}

STAFF_ROLES = {"Coordinator","Deputy Coordinator","Moderator","Administrator"}

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE,"r",encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = DEFAULT_CONFIG.copy()
    else:
        cfg = DEFAULT_CONFIG.copy()
        save_config(cfg)
    for k,v in DEFAULT_CONFIG.items():
        cfg.setdefault(k,v)
    return cfg

def save_config(cfg: Dict[str, Any]) -> None:
    with open(CONFIG_FILE,"w",encoding="utf-8") as f:
        json.dump(cfg,f,indent=2)

def load_xp() -> Dict[str, Any]:
    if os.path.exists(XP_FILE):
        try:
            with open(XP_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_xp(xp: Dict[str, Any]) -> None:
    with open(XP_FILE,"w",encoding="utf-8") as f:
        json.dump(xp,f,indent=2)

def add_xp(bot: commands.Bot, user_id: int, amount: int = 10) -> Tuple[bool,int]:
    uid = str(user_id)
    if uid not in bot.xp_data:
        bot.xp_data[uid] = {"xp":0,"level":1}
    bot.xp_data[uid]["xp"] += amount
    xp = bot.xp_data[uid]["xp"]
    level = bot.xp_data[uid]["level"]
    leveled = False
    while xp >= level*100:
        level += 1
        bot.xp_data[uid]["level"] = level
        leveled = True
    save_xp(bot.xp_data)
    return leveled, level

def load_teacher_progress() -> Dict[str, Any]:
    if os.path.exists(TEACHER_PROGRESS_FILE):
        try:
            with open(TEACHER_PROGRESS_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_teacher_progress(data: Dict[str, Any]) -> None:
    with open(TEACHER_PROGRESS_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2)

def make_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)

async def call_openai(bot: commands.Bot, system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
    client = bot.oai_client
    model = bot.config.get("ai_model","gpt-4.1-mini")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":user_prompt}
            ],
            temperature=temperature,
        )
        content = resp.choices[0].message.content.strip()
        max_len = bot.config.get("max_reply_length",1900)
        if len(content) > max_len:
            content = content[:max_len] + "\n\n[Truncated]"
        return content
    except Exception as e:
        print("OpenAI error:", e)
        return "⚠ AI error."

def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.name in STAFF_ROLES for r in member.roles)

def staff_only():
    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member) or not is_staff(ctx.author):
            await ctx.reply("❌ You are not allowed to use this command.",mention_author=False)
            return False
        return True
    return commands.check(predicate)

def get_log_channel(bot: commands.Bot, guild: discord.Guild | None):
    if not guild or not bot.config.get("logging_enabled",True):
        return None
    name = bot.config.get("log_channel_name","ceil-logs")
    return discord.utils.get(guild.text_channels, name=name)

async def log_event(bot: commands.Bot, guild: discord.Guild, message: str):
    ch = get_log_channel(bot,guild)
    if ch:
        try:
            await ch.send(message)
        except Exception:
            pass

def make_embed(title: str, description: str = "", color: discord.Color = discord.Color.blue()):
    e = discord.Embed(title=title,description=description,color=color)
    e.timestamp = datetime.utcnow()
    return e

BASE_SYSTEM_PROMPT = "You are CEIL Assistant, an AI assistant for CEIL (Centre d’Enseignement Intensif des Langues) at UHBC, Chlef, Algeria."
MULTILINGUAL_NOTE = "You work in a multilingual centre. Detect the language of the user and respond in that language by default."

def build_ai_system_prompt(mode: str) -> str:
    mode = (mode or "ceil").lower()
    if mode.startswith("topic"):
        extra = "Focus only on the given topic."
    elif mode == "education":
        extra = "Focus on pedagogy, CEFR, lesson planning and teaching practice."
    elif mode == "admin":
        extra = "Focus on administrative, formal writing."
    elif mode == "fun":
        extra = "Be playful and light but still appropriate."
    else:
        extra = "Focus on CEIL internal matters and language teaching."
    return BASE_SYSTEM_PROMPT + "\n\n" + extra + "\n\n" + MULTILINGUAL_NOTE

class UtilsCog(commands.Cog, name="Utils"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        from discord.ext.commands import MissingRequiredArgument, CheckFailure
        if isinstance(error, MissingRequiredArgument):
            await ctx.reply("⚠ Missing argument. Check the syntax.", mention_author=False)
            return
        if isinstance(error, CheckFailure):
            return
        print("Command error:", error)
        await ctx.reply("❌ An error occurred while running this command.", mention_author=False)
