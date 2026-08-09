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
                    )
            finally:
                # Don't forget to restore the original stdout after the image generation is done
                # sys.stdout = original_stdout
                sys.stderr = original_stderr

    def get_available_models(self):
        base_dir = self.config.get_local_model_path()

        model_prefix = "models--"
        local_models = []
        for subdir in os.listdir(base_dir):
            if subdir.startswith(model_prefix):
                subdir_path = os.path.join(base_dir, subdir)
                if os.path.isdir(subdir_path):
                    # Remove "models-" prefix and replace "--" with "/"
                    model_id = subdir[len(model_prefix) :].replace("--", "/")
                    local_models.append(model_id)

        return local_models

    async def list_available_resolutions(self, user_id=None, resolution=None):
        if resolution is not None:
            width, height = map(int, resolution.split("x"))
            if any(
                r["width"] == width and r["height"] == height for r in self.resolutions
            ):
                return True
            else:
                return False

        indicator = "**"  # Indicator variable
        indicator_length = len(indicator)

        # Group resolutions by aspect ratio
        grouped_resolutions = {}
        for r in self.resolutions:
            ar = self.aspect_ratio(r)
            if ar not in grouped_resolutions:
                grouped_resolutions[ar] = []
            grouped_resolutions[ar].append(r)

        # Sort resolution groups by width and height
        for ar, resolutions in grouped_resolutions.items():
            grouped_resolutions[ar] = sorted(resolutions, key=lambda r: (r["width"], r["height"]))

        # Calculate the maximum number of rows for the table
        max_rows = max(len(resolutions) for resolutions in grouped_resolutions.values())

        # Calculate the maximum field text width for each column, including the indicator
        max_field_widths = {}
        for ar, resolutions in grouped_resolutions.items():
            max_field_widths[ar] = max(len(f"{r['width']}x{r['height']}") + 2 * indicator_length for r in resolutions)

        # Generate resolution list in Markdown columns with padding
        header_row = "| " + " | ".join(ar.ljust(max_field_widths[ar]) for ar in grouped_resolutions.keys()) + " |\n"
        
        # Update the separator_row generation
        separator_row = "+-" + "-+-".join("-" * (max_field_widths[ar]) for ar in grouped_resolutions.keys()) + "-+\n"
        
        resolution_list = header_row + separator_row

        for i in range(max_rows):
            row_text = "| "
            for ar, resolutions in grouped_resolutions.items():
                if i < len(resolutions):
                    r = resolutions[i]
                    current_resolution_indicator = ""
                    if user_id is not None:
                        user_resolution = self.config.get_user_setting(
                            user_id, "resolution", {"width": 800, "height": 456}
                        )
                        if user_resolution is not None:
                            if (
                                user_resolution["width"] == r["width"]
                                and user_resolution["height"] == r["height"]
                            ):
                                current_resolution_indicator = indicator
                    res_str = (
                        current_resolution_indicator
                        + f"{r['width']}x{r['height']}"
                        + current_resolution_indicator
                    )
                    row_text += res_str.ljust(max_field_widths[ar]) + " | "
                else:
                    row_text += " ".ljust(max_field_widths[ar]) + " | "
            resolution_list += row_text + "\n"

        # Wrap the output in triple backticks for fixed-width formatting in Discord
        return f"```\n{resolution_list}\n```"

    def get_scaling_factor(self, width, height, scaled_resolutions):
        for res in scaled_resolutions:
            if res["width"] == width and res["height"] == height:
                return int(res["scaling_factor"])
        return None

    def is_valid_resolution(self, width, height):
        for res in self.resolutions:
            if res["width"] == width and res["height"] == height:
                return True
        return False
    def aspect_ratio(self, resolution_item: dict):
        from math import gcd
        width = resolution_item["width"]
        height = resolution_item["height"]
        # Calculate the greatest common divisor of width and height
        divisor = gcd(width, height)

        # Calculate the aspect ratio
        ratio_width = width // divisor
        ratio_height = height // divisor

        # Return the aspect ratio as a string in the format "width:height"
        return f"{ratio_width}:{ratio_height}"

    def nearest_scaled_resolution(self, resolution: dict, user_config: dict, max_resolution_config: dict):
        # We will scale by default, to 4x the requested resolution. Big energy!
        factor = user_config.get("resize_factor", 1)
        logging.info("Resize configuration is set by user factoring at " + str(factor))
        if factor == 1 or factor == 0:
            # Do not bother rescaling if it's set to 1 or 0
            return resolution
        width = resolution["width"]
        height = resolution["height"]
        aspect_ratio = self.aspect_ratio(resolution)

        new_width = int(width * factor)
        new_height = int(height * factor)
        new_aspect_ratio = self.aspect_ratio({"width": new_width, "height": new_height})
        max_resolution = self.get_highest_resolution(aspect_ratio, max_resolution_config)
        if aspect_ratio != new_aspect_ratio:
            logging.info("Aspect ratio changed after scaling, using max resolution " + str(max_resolution) + " instead.")
            return max_resolution
        if not self.is_valid_resolution(new_width, new_height):
            logging.info("Nearest resolution for AR " + str(aspect_ratio) + " not found, using max resolution: " + str(max_resolution) + " instead.")
            return max_resolution

    def get_highest_resolution(self, aspect_ratio: str, max_resolution_config: dict):
        # Calculate the aspect ratio of the input image
        # Filter the resolutions list to only include resolutions with the same aspect ratio as the input image
        filtered_resolutions = [r for r in self.resolutions if self.aspect_ratio(r) == aspect_ratio]

        # Sort the filtered resolutions list by scaling factor in descending order
        sorted_resolutions = sorted(filtered_resolutions, key=lambda r: r["scaling_factor"], reverse=False)

        # Check for a maximum resolution cap in the configuration
        max_res_cap = max_resolution_config.get(aspect_ratio)

        # If there's a cap, filter the sorted resolutions list to only include resolutions below the cap
        if max_res_cap:
            sorted_resolutions = [r for r in sorted_resolutions if r["width"] <= max_res_cap["width"] and r["height"] <= max_res_cap["height"]]

        # Return the first (highest) resolution from the sorted list, or None if the list is empty
        return sorted_resolutions[0] if sorted_resolutions else None
