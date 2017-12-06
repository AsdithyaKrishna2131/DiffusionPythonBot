import re, asyncio
from diffusion_python_bot.classes.discord_progress_bar import DiscordProgressBar

class TqdmCapture:
    def __init__(self, progress_bar: DiscordProgressBar, loop, original_stdout, original_stderr):
