class DiscordProgressBar:
    def __init__(self, ctx, total_steps, original_stdout, progress_bar_length=20, progress_message=None):
        self.ctx = ctx
        self.total_steps = total_steps
        self.progress_bar_length = progress_bar_length
        self.original_stdout = original_stdout
        self.current_step = 0
        self.progress_message = progress_message

    async def update_progress_bar(self, step):
        if step < self.current_step:
            # We do not want time going backwards for a progress bar.
            return
        self.current_step = step
        progress = self.current_step / self.total_steps
        filled_length = int(progress * self.progress_bar_length)
        bar = "█" * filled_length + "-" * (self.progress_bar_length - filled_length)
        percent = round(progress * 100, 1)
        progress_text = "`" + f"[{bar}] {percent}% complete`"
        percent_remainder = percent % 20
        if percent_remainder == 0:
            if self.progress_message is None:
                self.progress_message = await self.ctx.send(progress_text)
            else:
                await self.progress_message.edit(content=progress_text)
# draft note 1366
