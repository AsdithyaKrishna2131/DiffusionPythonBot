class FilteringStderrWrapper:
    def __init__(self, original_stderr, original_stdout):
        self.original_stderr = original_stderr
        self.original_stdout = original_stdout

