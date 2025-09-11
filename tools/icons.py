from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

import sys
import os


def resource_path(relative_path):
    """获取资源文件的绝对路径（兼容 PyInstaller）"""
    if hasattr(sys, "_MEIPASS"):
        # 打包后
        base_path = sys._MEIPASS
    else:
        # 源码运行
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# 用 resource_path 获取路径
Folder_Path = resource_path(os.path.join("resource", "icons", "folder.png"))
File_Path = resource_path(os.path.join(
    "resource", "icons", "default_file_icon.png"))


class My_Icons:
    Folder_Icon = None
    File_Icon = None

    def __init__(self):
        print(f"Folder_Path: {Folder_Path}\nFile_Path: {File_Path}")
        self.Folder_Icon = QPixmap(Folder_Path).scaled(
            64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.File_Icon = QPixmap(File_Path).scaled(
            64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
