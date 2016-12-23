# classes/app_config.py

import json
import os
import sys
from io import BytesIO


class AppConfig:
    def __init__(self):
        from pathlib import Path

        parent = os.path.dirname(Path(__file__).resolve().parent)
