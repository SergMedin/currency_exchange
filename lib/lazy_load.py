import os


class LazyMessageLoader:
    def __init__(self, file_path):
        self.file_path = file_path
        self._message = None

    @property
    def message(self):
        if self._message is None:
            if os.path.exists(self.file_path) and os.path.isfile(self.file_path):
                with open(self.file_path, "r", encoding="UTF-8", errors="ignore") as f:
                    self._message = f.read().strip()
            else:
                raise FileNotFoundError(f"File '{self.file_path}' not found")
        return self._message
