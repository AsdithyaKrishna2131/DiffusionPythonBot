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
