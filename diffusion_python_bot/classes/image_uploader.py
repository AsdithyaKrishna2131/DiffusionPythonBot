import os
from imgur_python import Imgur
from diffusion_python_bot.classes.app_config import AppConfig
import base64
import logging
from PIL import Image

class ImageUploader:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client = Imgur(config.get_imgur_config())
        self.bot = None

    async def set_bot(self, bot):
        self.bot = bot

    async def authorize(self):
        auth_url = self.client.authorize()
        logging.info("Imgur auth URL: " + auth_url)
        logging.info("Imgur config: " + str(self.client.config))
        return auth_url
