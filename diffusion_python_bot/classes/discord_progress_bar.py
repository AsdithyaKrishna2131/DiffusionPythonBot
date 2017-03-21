class DiscordProgressBar:
    def __init__(self, ctx, total_steps, original_stdout, progress_bar_length=20, progress_message=None):
        self.ctx = ctx
        self.total_steps = total_steps
        self.progress_bar_length = progress_bar_length
        self.original_stdout = original_stdout
        self.current_step = 0
        self.progress_message = progress_message

    async def update_progress_bar(self, step):
