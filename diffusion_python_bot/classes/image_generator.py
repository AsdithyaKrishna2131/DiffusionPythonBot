# classes/image_generator.py
import os
import sys
import logging
from io import BytesIO
from PIL import Image

# Tell TensorFlow to be quiet.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# Import the library
import torch
from torchvision.transforms.functional import pad
from diffusers import StableDiffusionPipeline, StableDiffusionImageVariationPipeline

import time
from .app_config import AppConfig
from asyncio import Lock
from tqdm import tqdm
import traceback

class ImageGenerator:
    resolutions = [
        {"width": 512, "height": 512, "scaling_factor": 30},
        {"width": 768, "height": 768, "scaling_factor": 30},
        {"width": 128, "height": 96, "scaling_factor": 100},
        {"width": 192, "height": 128, "scaling_factor": 94},
        {"width": 256, "height": 192, "scaling_factor": 88},
        {"width": 384, "height": 256, "scaling_factor": 76},
        {"width": 512, "height": 384, "scaling_factor": 64},
        {"width": 768, "height": 512, "scaling_factor": 52},
        {"width": 800, "height": 456, "scaling_factor": 50},
        {"width": 1024, "height": 576, "scaling_factor": 40},
        {"width": 1152, "height": 648, "scaling_factor": 34},
        {"width": 1280, "height": 720, "scaling_factor": 30},
        {"width": 1920, "height": 1080, "scaling_factor": 30},
        {"width": 1920, "height": 1200, "scaling_factor": 30},
        {"width": 3840, "height": 2160, "scaling_factor": 30},
        {"width": 7680, "height": 4320, "scaling_factor": 30},
        {"width": 64, "height": 96, "scaling_factor": 100},
        {"width": 128, "height": 192, "scaling_factor": 80},
        {"width": 256, "height": 384, "scaling_factor": 60},
        {"width": 512, "height": 768, "scaling_factor": 49},
        {"width": 1024, "height": 1536, "scaling_factor": 30},
    ]

    def __init__(
        self, shared_queue_lock: Lock, device="cuda", torch_dtype=torch.float16
    ):
        self.device = torch.device(device)
        self.torch_dtype = torch_dtype
        self.lock = shared_queue_lock
        self.config = AppConfig()
        self.model = None
        self.model_scaling = False
        self.pipe = None

    def get_variation_pipe(self, model_id, use_attention_scaling=False):
        import gc
        gc.collect()
        logging.info("Generating a new variation pipe...")
        pipe = StableDiffusionImageVariationPipeline.from_pretrained(
            pretrained_model_name_or_path=model_id, torch_dtype=self.torch_dtype
        )
        if (use_attention_scaling):
            logging.info(
                "Using attention scaling, because a variation is being crafted! This will make generation run more slowly, but it will be less likely to run out of memory."
            )
            logging.info("Clearing the CUDA cache...")
            torch.cuda.empty_cache()
            pipe.enable_sequential_cpu_offload()
            pipe.enable_attention_slicing(1)

        # torch.backends.cudnn.benchmark = True
        # torch.backends.cudnn.enabled = True
        pipe.safety_checker = lambda images, clip_input: (images, False)
        logging.info("Return the pipe...")
        return pipe

    def get_pipe(self, model_id, use_attention_scaling=False):
        import gc
        gc.collect()
        if self.pipe is not None and self.model_id == model_id and self.model_scaling == use_attention_scaling:
            # Return the current pipe if we're using the same model.
            return self.pipe
        if self.pipe is not None:
            logging.info("We had a pipe, but it's for model " + str(self.model_id) + " - resetting with the new model, " + str(model_id))
        # Create a new pipe and clean the cache.
        logging.info("Clearing the CUDA cache...")
        self.model_id = model_id
        self.model_scaling = use_attention_scaling
        torch.cuda.empty_cache()
        logging.info("Generating a new pipe...")
        if use_attention_scaling is False:
            self.pipe = StableDiffusionPipeline.from_pretrained(
                pretrained_model_name_or_path=model_id, torch_dtype=self.torch_dtype
            )
            self.pipe.to(self.device)
        elif use_attention_scaling:
            logging.info(
                "Using attention scaling, because high resolution was selected! Safety first!!"
            )
            self.pipe = StableDiffusionPipeline.from_pretrained(
                pretrained_model_name_or_path=model_id
            )
            self.pipe.enable_sequential_cpu_offload()
            self.pipe.enable_attention_slicing(1)
            # torch.backends.cudnn.benchmark = True
            # torch.backends.cudnn.enabled = True
        self.pipe.safety_checker = lambda images, clip_input: (images, False)
        logging.info("Return the pipe...")
        return self.pipe

    def generate_image_variations(
        self,
        width: int,
        height: int,
        input_image,
        steps: int,
        tqdm_capture,
        guidance_scale=7.5,
        use_attention_scaling=False,
    ):
        if use_attention_scaling:
            input_image = input_image.resize((512, 384))
        logging.info("Initializing image variation generation pipeline...")
        scaling_factor = self.get_scaling_factor(width, height, self.resolutions)
        if int(steps) > int(scaling_factor):
            steps = int(scaling_factor)
        logging.info(f"Scaling factor for {width}x{height}: {scaling_factor}")
        if scaling_factor < 50:
            logging.info(
                "Resolution "
                + str(width)
                + "x"
                + str(height)
                + " has a pixel count greater than threshold. Using attention scaling expects to take 30 seconds."
            )
            use_attention_scaling = True
        pipe = self.get_variation_pipe(
            "lambdalabs/sd-image-variations-diffusers",
            use_attention_scaling=use_attention_scaling,
        )
        input_image = pad(
            input_image, (input_image.size[0] // 2, input_image.size[1] // 2)
        )
        
        # Generate image variations
        with tqdm(total=steps, ncols=100, file=tqdm_capture) as pbar:
            generated_images = pipe(
                width=width,
                height=height,
                image=input_image,
                guidance_scale=guidance_scale,
                num_inference_steps=int(float(steps)),
            ).images
        return generated_images

    def generate_image(
        self,
        prompt,
        model_id,
        resolution,
        negative_prompt,
        steps,
        positive_prompt,
        tqdm_capture,
        user_config
    ):
        logging.info("Initializing image generation pipeline...")
        is_attn_enabled = self.config.get_attention_scaling_status()
        use_attention_scaling = False
        max_retries = retry_delay = 5
        if resolution is not None and is_attn_enabled:
            scaling_factor = self.get_scaling_factor(
                resolution["width"], resolution["height"], self.resolutions
            )
            logging.info(
                f"Scaling factor for {resolution['width']}x{resolution['height']}: {scaling_factor}"
            )
            if scaling_factor < 50:
                logging.info(
                    "Resolution "
                    + str(resolution["width"])
                    + "x"
                    + str(resolution["height"])
                    + " has a pixel count greater than threshold. Using attention scaling expects to take 30 seconds."
                )
                use_attention_scaling = True
                if steps > scaling_factor:
                    steps = scaling_factor
        # Current request's aspect ratio
        aspect_ratio = self.aspect_ratio(resolution)
        # Get the maximum resolution for the current aspect ratio
        side_x = self.config.get_max_resolution_width(aspect_ratio)
        side_y = self.config.get_max_resolution_height(aspect_ratio)
        logging.info('Aspect ratio ' + str(aspect_ratio) + ' has a maximum resolution of ' + str(side_x) + 'x' + str(side_y) + '.')
        if resolution["width"] <= side_x and resolution["height"] <= side_y:
            side_x = resolution["width"]
            side_y = resolution["height"]

        logging.info("Retrieving pipe for model " + str(model_id))
        pipe = self.get_pipe(model_id, use_attention_scaling)
        logging.info("Copied pipe to the local context")

        logging.info("REDIRECTING THE PRECIOUS, STDOUT... SORRY IF THAT UPSETS YOU")
        # Redirect sys.stdout to capture tqdm output
        original_stderr = sys.stderr
        sys.stderr = tqdm_capture

        # Combine the main prompt and positive_prompt if provided
        entire_prompt = prompt
        if positive_prompt is not None:
            entire_prompt = str(prompt) + " , " + str(positive_prompt)
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"Attempt {attempt}: Generating image...")
                with torch.no_grad():
                    with tqdm(total=steps, ncols=100, file=tqdm_capture) as pbar:
                        image = pipe(
                            prompt=entire_prompt,
                            height=side_y,
                            width=side_x,
                            num_inference_steps=int(float(steps)),
                            negative_prompt=negative_prompt,
                        ).images[0]

                # torch.cuda.empty_cache()
                logging.info("Image generation successful!")
                scaling_target = self.nearest_scaled_resolution(resolution, user_config, self.config.get_max_resolution_by_aspect_ratio(aspect_ratio))
                if scaling_target is not resolution:
                    logging.info("Rescaling image to nearest resolution...")
                    image = image.resize((scaling_target["width"], scaling_target["height"]))
                return image
            except Exception as e:
                logging.error(
                    f"Error generating image: {e}\n\nStack trace:\n{traceback.format_exc()}"
                )
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    raise RuntimeError(
                        "Maximum retries reached, image generation failed"
