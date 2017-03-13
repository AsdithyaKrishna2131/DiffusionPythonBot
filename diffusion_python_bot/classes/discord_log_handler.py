import asyncio
import logging
class DiscordLogHandler(logging.Handler):
    def __init__(self, ctx):
