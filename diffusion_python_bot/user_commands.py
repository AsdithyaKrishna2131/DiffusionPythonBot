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
            user_config = config.get_user_config(user_id=user_id)
            model_id = user_config.get("model", "hakurei/waifu-diffusion")
            steps = config.get_user_setting(user_id, "steps", 50)
            negative_prompt = config.get_user_setting(
                user_id,
                "negative_prompt",
                "(child, baby, deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation",
            )
            positive_prompt = config.get_user_setting(
                user_id, "positive_prompt", "beautiful hyperrealistic"
            )
            resolution = config.get_user_setting(
                user_id, "resolution", {"width": 800, "height": 456}
            )

        message = (
            f"**Hello,** {ctx.author.mention}! Here are your current settings:\n"
            f"🟠 **Model ID**: `{model_id}`\n❓ Change using **!setmodel [model]**, out of the list from **!listmodels**\n"
            f"🟠 **Steps**: `{steps}`\n❓ This represents how many denoising iterations the model will do on your image. Less is more.\n"
            f"🟠 **Negative Prompt:**:\n➡️    `{negative_prompt}`\n❓ Images featuring these keywords are less likely to be generated. Set via `!negative`.\n"
