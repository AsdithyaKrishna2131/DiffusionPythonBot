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
        resolution = self.config.get_user_setting(
            message.author.id, "resolution", {"width": 800, "height": 456}
        )
        num_inference_steps = self.config.get_user_setting(
            message.author.id, "steps", 250
        )
        width = resolution["width"]
        height = resolution["height"]
        for attachment in message.attachments:
            if attachment.content_type.startswith("image/"):
                image_data = await attachment.read()
                input_image = Image.open(BytesIO(image_data))
                prompt = message.content # Not used yet, but, good to have.
                ctx = message.channel # Channel/Thread context.
                # Redirect sys.stdout to capture tqdm output
                original_stdout = sys.stdout
                original_stderr = sys.stderr
                # Create an instance of the custom DiscordProgressBar
                discord_progress_bar = DiscordProgressBar(self, ctx, 100, original_stdout)
                tqdm_capture = TqdmCapture(discord_progress_bar, self.bot.loop, original_stdout, original_stderr)
                sys.stderr = tqdm_capture
                image = self.image_generator.generate_image_variations(resolution["width"], resolution["height"], input_image, num_inference_steps, tqdm_capture)
                try:
                    async with self.lock:
                        generated_images = await self.bot.loop.run_in_executor(
                            None,
                            self.image_generator.generate_image_variations,
                            width,
                            height,
                            input_image,
                            num_inference_steps,
                            tqdm_capture
                        )
                    for i, image in enumerate(generated_images):
                        buffer = BytesIO()
                        image.resize({1920, 1080}).save(buffer, "PNG")
                        buffer.seek(0)
                        await message.channel.send(
                            file=discord.File(buffer, f"variant_{i}.png")
                        )
                except Exception as e:
                    error_message = f"Error generating image variant: {e}\n\nStack trace:\n{traceback.format_exc()}"
                    await message.channel.send(error_message)
                finally:
                    sys.stderr = original_stderr

    async def send_large_message(self, ctx, text, max_chars=2000):
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
                    thread = await first_message.create_thread(name="Model List")
                else:
                    await thread.send_message(buffer)
                buffer = ""
            buffer += line + "\n"

        if buffer:
            await thread.send_message(buffer)

    def setup_logger(self, ctx):
        logger = logging.getLogger('discord_image_pipeline')
        logger.setLevel(logging.DEBUG)

        discord_handler = DiscordLogHandler(ctx)
        discord_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        discord_handler.setFormatter(formatter)
        logger.addHandler(discord_handler)

        return logger
# draft note 1359
