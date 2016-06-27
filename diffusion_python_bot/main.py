import sys
import datetime
import discord
from discord import Thread
import asyncio
from asyncio import ( Lock, Queue, Semaphore )
import traceback
from discord.ext import commands
from PIL import Image
from io import BytesIO
from diffusion_python_bot.classes.app_config import AppConfig
from diffusion_python_bot.classes.image_generator import ImageGenerator
from diffusion_python_bot.classes.message_handler import MessageHandler
from diffusion_python_bot.user_commands import UserCommands
from diffusion_python_bot.utils import _get_project_meta
from diffusion_python_bot.classes.discord_progress_bar import DiscordProgressBar
from diffusion_python_bot.classes.tqdm_capture import TqdmCapture
from diffusion_python_bot.classes.image_uploader import ImageUploader
import logging

pkg_meta = _get_project_meta()
pkg_name = str(pkg_meta["name"])
# The short X.Y version
pkg_version = str(pkg_meta["version"])

config = AppConfig()
# How many concurrent slots to run when generating images.
concurrent_slots = config.get_concurrent_slots()
TOKEN = config.get_discord_api_key()
PREFIX = config.get_command_prefix()

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

from diffusion_python_bot.classes.discord_wrapper import DiscordWrapper
bot = DiscordWrapper(command_prefix=PREFIX, intents=intents)

# Configure the root logger to equate Discord's logging settings.
discord_logger = logging.getLogger('discord')
# Add a file handler to log to a file
file_handler = logging.FileHandler(filename='main.log', encoding='utf-8', mode='w')
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
discord_logger.addHandler(file_handler)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().handlers = discord_logger.handlers

logging.basicConfig(level=logging.INFO)

# Threaded conversation handling
image_queue = Queue()
appconfig_lock = Lock()
image_queue_lock = Lock()
image_generation_semaphore = Semaphore(1)
image_uploader = ImageUploader(config)
asyncio.run(image_uploader.set_bot(bot))
asyncio.run(image_uploader.authorize())
asyncio.run(bot.add_cog(UserCommands(bot, appconfig_lock, config)))
image_generator = ImageGenerator(image_queue_lock)
message_handler = MessageHandler(
    image_generator=image_generator,
    config=config,
    shared_queue=image_queue,
    shared_queue_lock=image_queue_lock,
    image_uploader=image_uploader
)
message_handler.set_bot(bot)


@bot.event
async def on_ready():
    logging.info(f"{bot.user} has connected to Discord!")
    logging.info(f"Server(s) connected: {[guild.name for guild in bot.guilds]}")


async def send_large_message(ctx, text, max_chars=2000):
    if len(text) <= max_chars:
        await ctx.send(text)
        return

    lines = text.split("\n")
    buffer = ""
    first_message = None
    for line in lines:
        if len(buffer) + len(line) + 1 > max_chars:
            if not first_message:
                first_message = await ctx.send(buffer)
                thread = await first_message.channel.create_thread(name="Model List")
            else:
                await thread.send_message(buffer)
            buffer = ""
        buffer += line + "\n"

    if buffer:
        await thread.send_message(buffer)

