# global_logger.py
import logging
from pathlib import Path
from datetime import datetime


def setup_global_logging():
    """全局日志配置"""
    # 创建日志目录
    log_dir = Path.home() / ".config" / "pyqt-ssh" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

    # 配置根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)

    # 设置格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # 测试日志
    root_logger.info("全局日志系统初始化完成")
    root_logger.info("日志文件: %s", log_file)

# 创建一些常用的logger


def get_logger(name):
    """获取指定名称的logger"""
    return logging.getLogger(name)


# 常用模块的预定义logger
main_logger = logging.getLogger("main")
gui_logger = logging.getLogger("setting")
session_logger = logging.getLogger("session")
