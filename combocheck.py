import os

# combocheck.py
class ComboCheck:
    def __init__(self): self._content = ""
    def read_file(self, path):
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                self._content = f.read()
    def contains(self, s): return s in self._content
    def append(self, s): self._content += s

invalid = ComboCheck()
checked = ComboCheck()
locked = ComboCheck()