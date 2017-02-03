# classes/app_config.py

import json
import os
import sys
from io import BytesIO


class AppConfig:
    def __init__(self):
        from pathlib import Path

        parent = os.path.dirname(Path(__file__).resolve().parent)
        config_path = os.path.join(parent, "config")
        self.config_path = os.path.join(config_path, "config.json")
        self.example_config_path = os.path.join(config_path, "example.json")

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
