# Management of the available models.
import json
import os
import sys
from io import BytesIO


class ModelList:
    def __init__(self):
        from pathlib import Path
        parent = os.path.dirname(Path(__file__).resolve().parent)
        model_list_path = os.path.join(parent, "config")
        self.model_list_path = os.path.join(model_list_path, "config.json")
