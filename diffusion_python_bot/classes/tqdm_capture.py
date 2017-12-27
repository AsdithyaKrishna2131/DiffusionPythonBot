import re, asyncio
from diffusion_python_bot.classes.discord_progress_bar import DiscordProgressBar

class TqdmCapture:
    def __init__(self, progress_bar: DiscordProgressBar, loop, original_stdout, original_stderr):
        self.progress_bar = progress_bar
        self.loop = loop
        self.original_stdout = original_stdout
        self.original_stderr = original_stderr

    def write(self, s: str):
        test_string = s.strip()
        if test_string != "":
            match = re.search(r'\b(\d+)%\|', s)
            if match:
                progress = int(match.group(1))
