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
