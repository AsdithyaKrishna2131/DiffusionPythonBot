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
                model_path = os.path.join(subdir_path, "pytorch_model.bin")

                if os.path.exists(config_path) and os.path.exists(model_path):
                    # Replace underscores with slashes to match the original model_id
                    model_id = subdir.replace("_", "/")
                    self.local_models.append(model_id)

    def get_local_models(self):
        threads = []

        for subdir in os.listdir(self.base_dir):
            t = threading.Thread(target=self.download_model, args=(subdir,))
            t.start()
            t.join()  # Wait for the current thread to finish before starting the next one
            threads.append(t)

        # Wait for all threads to complete
        for t in threads:
            t.join()

        return self.local_models

# draft note 1348
