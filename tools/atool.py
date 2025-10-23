import sys
from pathlib import Path


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(".").resolve()

    rel_path = Path(relative_path)
    return str(base_path / rel_path)
