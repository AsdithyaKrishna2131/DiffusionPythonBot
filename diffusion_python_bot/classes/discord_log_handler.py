import asyncio
import logging
class DiscordLogHandler(logging.Handler):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

    def emit(self, record):
        try:
