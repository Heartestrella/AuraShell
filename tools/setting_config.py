from pathlib import Path
import json
import os
# Setting Config Manager


class SCM:
    def __init__(self):
        self.config_path = Path.home() / ".config" / "setting-config.json"
        if not os.path.exists(self.config_path):
            self.init_config("Dark", None, "12", True,
                             "#FFFFFF", 100, 720, 680, False)

    def write_config(self, config):
        with open(self.config_path, mode="w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def init_config(self, *parameter):
        '''
        parameter 顺序：设置页面选项依次排序 \n
        0 -> bg_color: 背景颜色 ("Dark" 或 "Light") \n
        1 -> bg_pic: 背景图片路径 (Path 或 None) \n
        2 -> font_size 字体大小 (int 12-30) \n
        3 -> locked_ratio: 是否锁定横纵比 (Bool) \n
        4 -> ssh_widget_text_color: SSH会话页面字体颜色\n
        5 -> background_opacity : 背景图片不透明度\n
        8 -> follow_cd 使用cd后文件管理器跟随到新的目录\n
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
            "follow_cd": parameter[8]  # bool
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
