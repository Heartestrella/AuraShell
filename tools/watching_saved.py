from PyQt5.QtCore import QThread, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import time


class FileWatchThread(QThread):
    file_saved = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = os.path.abspath(file_path)
        self._running = True

    def run(self):
        class Handler(FileSystemEventHandler):
            def __init__(self, outer):
                self.outer = outer

            def on_modified(self, event):
                if os.path.abspath(event.src_path) == self.outer.file_path:
                    self.outer.file_saved.emit(self.outer.file_path)

        event_handler = Handler(self)
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(
            self.file_path), recursive=False)
        observer.start()

        try:
            while self._running:
                time.sleep(0.5)
        finally:
            observer.stop()
            observer.join()

    def stop(self):
        """终止线程"""
        self._running = False
        self.wait()

# --------------------------
# 使用示例（放在主线程/GUI中）：

# file_thread = FileWatchThread("example.txt")
# file_thread.file_saved.connect(lambda path: print(f"{path} was saved!"))
# file_thread.start()
#
# # 停止线程：
# file_thread.stop()
