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


@bot.command(name="ping", help="Test command to check if the bot is responding.")
async def ping(ctx):
    await ctx.send("Pong!")


async def generate_image_from_queue():
    while not image_queue.empty():
        ctx, prompt, discord_first_message = await image_queue.get()
        logging.info("Create progress bar using {discord_first_message}...")
        await discord_first_message.edit(content="Begin processing queue item: " + prompt)
        progress_bar = DiscordProgressBar(ctx=ctx, total_steps=100, original_stdout=sys.stdout, progress_message=discord_first_message)
        tqdm_file = TqdmCapture(progress_bar, bot.loop, sys.stdout, sys.stderr)
        logging.info("Editing initial message.")
        await discord_first_message.edit(content="Begin image generation: " + prompt)
        user_id = ctx.author.id
        try:
            await ctx.message.delete()
        except:
            logging.info("Message was already deleted. Dang.")
        async with appconfig_lock:
            user_config = config.get_user_config(user_id)
            steps = config.get_user_setting(user_id, "steps", 50)
            negative_prompt = config.get_user_setting(
                user_id,
                "negative_prompt",
                "(child, baby, deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation",
            )
            positive_prompt = config.get_user_setting(
                user_id, "positive_prompt", "beautiful hyperrealistic"
            )
            resolution = config.get_user_setting(
                user_id, "resolution", {"width": 800, "height": 456}
            )
            model_id = user_config.get("model", "andite/anything-v4.0")
        try:
            # Run the image generation in an executor
            # Acquire the semaphore
            # await image_generation_semaphore.acquire()
            logging.info("Begin capture...")
            image = await bot.loop.run_in_executor(
                None,
                image_generator.generate_image,
                prompt,
                model_id,
                resolution,
                negative_prompt,
                steps,
                positive_prompt,
                tqdm_file,
                user_config
            )

            message = (
                "**Requested by:** "
                + str(ctx.author.mention)
                + "\n**Prompt:** "
                + str(prompt)
                + "\n**Model:** "
                + str(model_id)
                + "\n**Resolution:** "
                + str(resolution["width"])
                + "x"
                + str(resolution["height"])
                + "\n**Steps:** "
                + str(steps)
            )
            if isinstance(ctx.message.channel, Thread):
                thread = ctx.message.channel
            else:
                await discord_first_message.edit(content="Prompt by **" + ctx.author.name + "**: `" + prompt + "`")
                thread = await discord_first_message.create_thread(name=prompt[:97] + '...', auto_archive_duration=60) # You can change the duration (in minutes) as needed
            image_url = await image_uploader.put_from_pil(image, prompt)
            await thread.send(
                content=message + '\n' + str(image_url)
            )
            await discord_first_message.delete()
        except discord.NotFound:
            logging.info("Discord message was already deleted, probably.")
        except Exception as e:
            error_message = (
                f"Error generating image: {e}\n\nStack trace:\n{traceback.format_exc()}"
            )
            await send_large_message(ctx, f"Error generating image: {error_message}")
        finally:
            image_queue.task_done()
            image_generation_semaphore.release()

@bot.command(name="generate", help="Generates an image based on the given prompt.")
async def generate(ctx, *, prompt):
    try:
        print("Begin generate command coroutine.")
        discord_first_message = await ctx.send(f"Adding prompt to queue for processing: " + prompt)
        # Put the context and prompt in a tuple before adding it to the queue
        await image_queue.put((ctx, prompt, discord_first_message))

        # Get the number of concurrent slots
        concurrent_slots = config.get_concurrent_slots()

        # Check if there are any running tasks
        if not hasattr(bot, "image_generation_tasks"):
            bot.image_generation_tasks = []

        # Remove any completed tasks
        bot.image_generation_tasks = [t for t in bot.image_generation_tasks if not t.done()]

        # If there are fewer tasks than allowed slots, create new tasks
        while len(bot.image_generation_tasks) < concurrent_slots:
            task = bot.loop.create_task(generate_image_from_queue())
            bot.image_generation_tasks.append(task)

    except Exception as e:
        await ctx.send(
            f"Error generating image: {e}\n\nStack trace:\n{traceback.format_exc()}"
        )

# Set model command with AppConfig lock
@bot.command(name="setmodel", help="Set the default model for the user.")
async def set_model(ctx, *, model_id=None):
    user_id = ctx.author.id
    async with appconfig_lock:
        user_config = config.get_user_config(user_id)
        if model_id is None:
            model_id = user_config.get("model", None)
            if model_id is None:
                model_id = config.get_default_model()
            await ctx.send(f"Your current model is set to {model_id}.")
            return
        user_config["model"] = model_id
        config.set_user_config(user_id, user_config)
    await ctx.send(
        f"Default model for user {ctx.author.name} has been set to {model_id}."
    )


