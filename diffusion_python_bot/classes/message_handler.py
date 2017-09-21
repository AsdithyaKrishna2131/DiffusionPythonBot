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
        self.config = config
        self.bot = None  # This will be set later
        self.queue = shared_queue
        self.lock = shared_queue_lock
        self.uploader = image_uploader

    def set_bot(self, bot):
        self.bot = bot

    async def handle_message(self, message):
        if message.author.bot:
            return
        in_my_thread = False
        is_in_thread = False
        if isinstance(message.channel, discord.Thread):
            is_in_thread = True
        if message.attachments:
            await self._handle_image_attachment(message)

        # Whether we're in a thread the bot started.
        if is_in_thread and message.channel.owner_id == self.bot.user.id or message.author.bot:
            in_my_thread = True
        if is_in_thread and len(message.content) > 0 and message.content[0] == "*":
            # Respond to * as all bots.
            in_my_thread = True
        # Run only if it's in the bot's thread, and has no image attachments, and, has no "!" commands.
        if in_my_thread and not message.attachments and message.content[0] != "!" and message.content[0] != "+":
            # TODO: Implement the ability to respond to prompts without !generate
            # This will hopefully, not respond to an image attachment.
            print("Attempting to run generate command?")
            await self.invoke_command(message, "generate")
        await self.bot.process_commands(message)
    
    async def invoke_command(self, message, command_name):
        # Get the command object
        ctx = await self.bot.get_context(message)
        command = self.bot.get_command(command_name)
        if command is not None:
            await command(ctx, prompt=' '.join(ctx.message.content.split()))
    
    async def _handle_image_attachment(self, message):
        # Yo, check if the bot is mentioned, bro!
        bot_mention = discord.utils.find(lambda mention: mention.id == self.bot.user.id, message.mentions)

        # Check if both conditions are met
        if not bot_mention or message.author.bot:
            # If not mentioned, just chill and return, bro.
            return
        # If the bot is mentioned, let's do some work, bro!
        user_id = message.author.id
        logging.info("User id: " + str(user_id))
        discord_first_message = await message.channel.send(
            "Yo, "
            + message.author.name
            + "! I gotchu, bro! I'm on it, but it's gonna take a sec."
        )
