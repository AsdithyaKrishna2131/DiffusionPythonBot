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
