import inspect
from huggingface_hub import HfApi
from diffusers import StableDiffusionPipeline

api = StableDiffusionPipeline()
# api = HfApi()
methods = inspect.getmembers(api, predicate=inspect.ismethod)

for method_name, method in methods:
    method_signature = inspect.signature(method)
    print(f"{method_name}: {method_signature}")

# draft note 1322
