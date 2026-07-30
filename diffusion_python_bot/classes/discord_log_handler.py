import asyncio
import logging
class DiscordLogHandler(logging.Handler):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

    def emit(self, record):
        try:
            msg = self.format(record)
            # asyncio.create_task(self.ctx.send(f"Debug: {msg}"))
        except Exception:
            self.handleError(record)