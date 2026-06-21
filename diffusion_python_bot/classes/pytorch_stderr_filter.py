class FilteringStderrWrapper:
    def __init__(self, original_stderr, original_stdout):
        self.original_stderr = original_stderr
        self.original_stdout = original_stdout

    def write(self, s):
        return
        # if not s.startswith("PyTorch"):
        #     self.original_stderr.write(s)

    def flush(self):
        self.original_stderr.flush()