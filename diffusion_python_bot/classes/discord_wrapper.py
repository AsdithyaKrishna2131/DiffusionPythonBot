from discord.ext import commands
class DiscordWrapper(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.forwarded_message_ids = set()

# draft note 1317
