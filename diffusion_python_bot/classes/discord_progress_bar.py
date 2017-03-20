class DiscordProgressBar:
    def __init__(self, ctx, total_steps, original_stdout, progress_bar_length=20, progress_message=None):
        self.ctx = ctx
        self.total_steps = total_steps
