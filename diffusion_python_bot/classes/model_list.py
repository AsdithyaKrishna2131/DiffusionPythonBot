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
        self.example_model_list_path = os.path.join(model_list_path, "example.json")

        if not os.path.exists(self.config_path):
            with open(self.example_config_path, "r") as example_file:
                example_config = json.load(example_file)

            with open(self.config_path, "w") as config_file:
                json.dump(example_config, config_file, indent=4)

        with open(self.config_path, "r") as config_file:
            self.config = json.load(config_file)
    def get_concurrent_slots(self):
        return self.config.get("concurrent_slots", 1)

    def get_command_prefix(self):
        return self.config.get("cmd_prefix", "+")

    def get_max_resolution_by_aspect_ratio(self, aspect_ratio: str):
        return self.config.get("maxres", {}).get(aspect_ratio, {"width": self.get_max_resolution_width(aspect_ratio=aspect_ratio), "height": self.get_max_resolution_height(aspect_ratio=aspect_ratio)})

    def get_max_resolution_width(self, aspect_ratio: str):
        return self.config.get("maxres", {}).get(aspect_ratio, {}).get("width", 800)
