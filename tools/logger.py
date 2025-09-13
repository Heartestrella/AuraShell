# global_logger.py
import logging
from pathlib import Path
from datetime import datetime


def setup_global_logging():
    log_dir = Path.home() / ".config" / "pyqt-ssh" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    root_logger.info("Global log system initialization completed")
    root_logger.info("Log files: %s", log_file)


def get_logger(name):
    return logging.getLogger(name)


main_logger = logging.getLogger("main")
gui_logger = logging.getLogger("setting")
session_logger = logging.getLogger("session")
