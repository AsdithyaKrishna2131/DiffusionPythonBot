from discord.ext import commands
from asyncio import Lock


class UserCommands(commands.Cog):
    def __init__(self, bot, appconfig_lock, config):
        self.bot = bot
