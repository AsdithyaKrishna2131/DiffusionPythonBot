import inspect
from huggingface_hub import HfApi
from diffusers import StableDiffusionPipeline

api = StableDiffusionPipeline()
# api = HfApi()
methods = inspect.getmembers(api, predicate=inspect.ismethod)

for method_name, method in methods:
