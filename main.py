
import os
import discord
from discord.ext import commands

from cogs import utils
from cogs.moderation import ModerationCog
from cogs.fun import FunCog
from cogs.ai import AICog
from cogs.education import EducationCog
from cogs.research import ResearchCog
from cogs.admin import AdminCog
from cogs.vision import VisionCog

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

bot.config = utils.load_config()
bot.xp_data = utils.load_xp()
bot.teacher_progress = utils.load_teacher_progress()
bot.oai_client = utils.make_openai_client(OPENAI_API_KEY)

@bot.event
async def on_ready():
    await bot.add_cog(utils.UtilsCog(bot))
    await bot.add_cog(ModerationCog(bot))
    await bot.add_cog(FunCog(bot))
    await bot.add_cog(AICog(bot))
    await bot.add_cog(EducationCog(bot))
    await bot.add_cog(ResearchCog(bot))
    await bot.add_cog(AdminCog(bot))
    await bot.add_cog(VisionCog(bot))

    try:
        await bot.tree.sync()
        synced = True
    except Exception as e:
        print("Slash sync error:", e)
        synced = False

    print("===================================")
    print(f"CEIL BOT logged in as {bot.user} (ID: {bot.user.id})")
    print("Slash commands synced:", synced)
    print("===================================")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if bot.config.get("xp_enabled", True):
        leveled, lvl = utils.add_xp(bot, message.author.id, 5)
        if leveled:
            try:
                await message.channel.send(f"🎉 {message.author.mention} reached level {lvl}!")
            except Exception:
                pass

    mod_cog = bot.get_cog("ModerationCog")
    if mod_cog:
        blocked = await mod_cog.handle_incoming_message(message)
        if blocked:
            return

    ai_cog = bot.get_cog("AICog")
    if ai_cog:
        handled = await ai_cog.maybe_auto_reply(message)
        if handled:
            return

    await bot.process_commands(message)

def main():
    print("Starting CEIL bot...")
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
