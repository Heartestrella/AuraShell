import requests
from PyQt5.QtCore import pyqtSignal, QThread
import base64
HASH_URL = "https://api.github.com/repos/Heartestrella/AuraShell/contents/update_hash.txt"


class CheckUpdate(QThread):
    hash = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        self.check()

    def check(self):
        try:
            response = requests.get(HASH_URL, timeout=100)
            if response.status_code == 200:
                file_data = response.json()
                content = base64.b64decode(
                    file_data['content']).decode('utf-8')
                self.hash.emit(True, content)
            else:
                self.hash.emit(False, "Cant get hash")
        except Exception as e:
            self.hash.emit(False, e)
