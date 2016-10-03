from discord.ext import commands
from asyncio import Lock


class UserCommands(commands.Cog):
    def __init__(self, bot, appconfig_lock, config):
        self.bot = bot
        self.appconfig_lock = appconfig_lock
        self.config = config

    # Other commands in your user_commands cog...

