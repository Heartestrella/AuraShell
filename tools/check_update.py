import requests
from PyQt5.QtCore import pyqtSignal, QThread
import time


class CheckUpdate(QThread):
    hash_signal = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        self.check()

    def check(self):
        try:
            timestamp = int(time.time())
            url = f"https://raw.githubusercontent.com/Heartestrella/AuraShell/main/resource/update_hash.txt?t={timestamp}"
            response = requests.get(url, timeout=100)
            if response.status_code == 200:
                content = response.text.strip()
                print(content)
                self.hash_signal.emit(True, content)
            else:
                self.hash_signal.emit(False, "Cant get hash")
        except Exception as e:
            self.hash_signal.emit(False, str(e))
