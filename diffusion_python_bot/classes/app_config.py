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
