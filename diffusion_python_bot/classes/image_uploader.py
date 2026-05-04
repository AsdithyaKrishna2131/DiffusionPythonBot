import os
from imgur_python import Imgur
from diffusion_python_bot.classes.app_config import AppConfig
import base64
import logging
from PIL import Image

class ImageUploader:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client = Imgur(config.get_imgur_config())
        self.bot = None

    async def set_bot(self, bot):
        self.bot = bot

    async def authorize(self):
        auth_url = self.client.authorize()
        logging.info("Imgur auth URL: " + auth_url)
        logging.info("Imgur config: " + str(self.client.config))
        return auth_url

    async def put_from_file(self, image_path, prompt: str = None, album = None):
        if not os.path.exists(image_path):
            raise Exception("Image file not found")
        uploaded_image = self.client.image_upload(image_path, self.filename_from_prompt(prompt), prompt)
        logging.info("Uploaded image: " + str(uploaded_image))
        return uploaded_image["response"]["data"]["link"]

    async def put_from_pil(self, image: Image, prompt: str):
        try:
            temp_file_name = self.filename_from_prompt(prompt)
            full_temp_path = self.image_dir() + '/' + temp_file_name
            import functools
            # This allows us to use an executor with keyword arguments.
            save_func = functools.partial(image.save, optimize=True)
            # If we were to run this outside an executor, the resize will block the main thread.
            await self.bot.loop.run_in_executor(
                None,
                save_func,
                full_temp_path,
                "PNG"
            )
            image_url = await self.upload_to_imgur(full_temp_path, prompt)
            os.remove(full_temp_path)
            return image_url
        except Exception as e:
            logging.exception(e)
            raise e

    async def put_from_buffer(self, buffer, prompt: str):
        temp_file_name = self.filename_from_prompt(prompt)
        full_temp_path = self.image_dir() + '/' + temp_file_name
        buffer.save(full_temp_path)
        image_url = await self.upload_to_imgur(full_temp_path, prompt)
        os.remove(full_temp_path)
        return image_url

    async def upload_to_imgur(self, image_path, prompt: str = None, album = None):
        link = await self.put_from_file(image_path, prompt, album)
        return link

    def filename_from_prompt(self, prompt):
        return prompt.replace(" ", "_").replace("/", "-").replace("'", "")[:32].lower() + ".png"

    def image_dir(self):
        return self.config.get_image_dir()

# draft note 1344
