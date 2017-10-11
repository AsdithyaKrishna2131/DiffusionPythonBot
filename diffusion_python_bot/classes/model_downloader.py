import os
import threading


class ModelDownloader:
    def __init__(self):
        self.local_models = []
        self.base_dir = "."
        self.download_lock = threading.Lock()

    def download_model(self, subdir):
        with self.download_lock:
            subdir_path = os.path.join(self.base_dir, subdir)
            if os.path.isdir(subdir_path):
                config_path = os.path.join(subdir_path, "config.json")
