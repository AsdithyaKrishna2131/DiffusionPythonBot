import discord
import traceback
import sys
from io import BytesIO
from diffusion_python_bot.classes.image_generator import ImageGenerator
from diffusion_python_bot.classes.app_config import AppConfig
from diffusion_python_bot.classes.tqdm_capture import TqdmCapture
import logging
from PIL import Image
from asyncio import Queue
from asyncio import Lock
from diffusion_python_bot.classes.discord_log_handler import DiscordLogHandler
from diffusion_python_bot.classes.discord_progress_bar import DiscordProgressBar
from diffusion_python_bot.classes.image_uploader import ImageUploader

class MessageHandler:
    def __init__(
        self,
        image_generator: ImageGenerator,
        config: AppConfig,
        shared_queue: Queue,
        shared_queue_lock: Lock,
        image_uploader: ImageUploader
    ):
        self.image_generator = image_generator
