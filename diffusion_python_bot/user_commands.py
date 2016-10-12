from discord.ext import commands
from asyncio import Lock


class UserCommands(commands.Cog):
    def __init__(self, bot, appconfig_lock, config):
        self.bot = bot
        self.appconfig_lock = appconfig_lock
        self.config = config

    # Other commands in your user_commands cog...

    @commands.command(name="settings", help="Shows your current settings.")
    async def my_settings(self, ctx):
        user_id = ctx.author.id
        config = self.config
        async with self.appconfig_lock:
