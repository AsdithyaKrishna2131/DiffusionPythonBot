import os
import threading


class ModelDownloader:
    def __init__(self):
        self.local_models = []
        self.base_dir = "."
        self.download_lock = threading.Lock()
