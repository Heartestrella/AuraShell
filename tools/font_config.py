# font_config.py

import json
from pathlib import Path
from PyQt5.QtGui import QFont, QFontDatabase
import sys


class font_config:
    def __init__(self):
        self.config_path = Path.home() / ".config" / "font-config.json"
        if not self.config_path.exists():
            self.init_config()

    def init_config(self):
        config_dict = {
            'family': 'Courier New',
            'size': 12,
            'bg_color_light': "#888888",
            'bg_color_dark': "#252525"
        }
        with open(self.config_path, mode="w", encoding="utf-8") as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)

    def write_font(self, font_path=None, font_size=None):
        try:
            with open(self.config_path, mode="r", encoding="utf-8") as f:
                config_dict = json.load(f)

            # Unspecified and not the default font
            if font_path is None and config_dict["family"] != "Courier New":
                pass
            elif font_path is not None:
                config_dict["family"] = font_path
            else:
                config_dict["family"] = "Courier New"
            # config_dict["family"] = font_path if font_path is not None else "Courier New"
            if font_size is None and config_dict["size"] != 12:
                pass
            elif font_size is not None:
                config_dict["size"] = font_size
            else:
                config_dict["size"] = 12
            # config_dict["size"] = font_size if font_size is not None else 12

            with open(self.config_path, mode="w", encoding="utf-8") as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Error write font config: {e}")

    def read_font(self):
        try:
            with open(self.config_path, mode="r", encoding="utf-8") as f:
                config_dict = json.load(f)
            return (config_dict["family"], config_dict["size"])
        except Exception as e:
            print(f"Error reading font config: {e}")

    def get_font(self) -> QFont:
        path, size = self.read_font()

        if path:
            import os
            if os.path.isfile(path):
                font_id = QFontDatabase.addApplicationFont(path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        return QFont(families[0], size)
            else:
                return QFont(path, size)

        return QFont("monospace", size)
