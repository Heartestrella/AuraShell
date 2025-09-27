from PyQt5.QtCore import QThread, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import time


class FileWatchThread(QThread):
    file_saved = pyqtSignal(str)

    def __init__(self, file_path, timeout_hours=1):
        """
        :param file_path: 要监控的文件
        :param timeout_hours: 超时时间（小时），如果这么久没变化就结束线程
        """
        super().__init__()
        self.file_path = os.path.abspath(file_path)
        self._running = True
        self.timeout_hours = timeout_hours
        self._last_event_time = time.time()  # 初始化为当前时间

    def run(self):
        class Handler(FileSystemEventHandler):
            def __init__(self, outer):
                self.outer = outer
                self._last_emit_time = 0

            def on_modified(self, event):
                if os.path.abspath(event.src_path) != self.outer.file_path:
                    return

                now = time.time()
                if now - self._last_emit_time < 1.0:  # 1秒内只触发一次
                    return

                self.outer._last_event_time = now
                self._last_emit_time = now
                self.outer.file_saved.emit(self.outer.file_path)

        event_handler = Handler(self)
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(
            self.file_path), recursive=False)
        observer.start()

        try:
            while self._running:
                if time.time() - self._last_event_time > self.timeout_hours * 3600:
                    print(f"[FileWatchThread] {self.file_path} 超时未修改，自动退出线程")
                    break
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
