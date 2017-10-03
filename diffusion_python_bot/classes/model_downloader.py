import os
import threading


class ModelDownloader:
    def __init__(self):
        self.local_models = []
        self.base_dir = "."
        self.download_lock = threading.Lock()

    def download_model(self, subdir):
        with self.download_lock:
