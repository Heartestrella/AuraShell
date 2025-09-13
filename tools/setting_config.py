from pathlib import Path
import json
import os
# Setting Config Manager


class SCM:
    def __init__(self):
        config_dir = Path.home() / ".config"
        config_dir.mkdir(exist_ok=True)

        self.config_path = Path.home() / ".config" / "setting-config.json"
        if not os.path.exists(self.config_path):
            self.init_config("Dark", None, "12", True,
                             "#FFFFFF", 100, 720, 680, False, "system")
            print("Config file created at:", self.config_path)

    def write_config(self, config_data):
        """写入配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Failed to write config file: {e}")

    def init_config(self, *parameter):
        '''
        Parameter order: Sets the order of page options.

        0 -> bg_color: Background color ("Dark" or "Light")

        1 -> bg_pic: Background image path (Path or None)

        2 -> font_size: Font size (int 12-30)

        3 -> locked_ratio: Whether to lock the aspect ratio (Bool)

        4 -> ssh_widget_text_color: SSH session page font color

        5 -> background_opacity: Background image opacity

        8 -> follow_cd: The file manager follows the new directory after using cd.
        '''
        config = {
            "bg_color": parameter[0],  # Dark or Light
            "bg_pic": parameter[1],  # Path or None
            "font_size": parameter[2],  # 12-30
            "locked_ratio": parameter[3],  # Bool
            "ssh_widget_text_color": parameter[4],  # color code
            "background_opacity": parameter[5],  # int 0-100
            "window_last_width": parameter[6],  # int
            "window_last_height": parameter[7],  # int
            "follow_cd": parameter[8],  # bool
            "language": parameter[9]  # system, EN, CN, JP, RU
        }
        self.write_config(config)

    def revise_config(self, key, value):
        config = self.read_config()
        config[key] = value
        self.write_config(config)

    def read_config(self) -> dict:
        with open(self.config_path, mode="r", encoding="utf-8") as f:
            config_dict = json.load(f)
        return config_dict
