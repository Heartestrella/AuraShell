from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget
from qfluentwidgets import LineEdit, SubtitleLabel, MessageBoxBase,  PasswordLineEdit, PushButton
from tools.font_config import font_config
import requests
import os
from requests.adapters import HTTPAdapter
import ssl
import zipfile
from pathlib import Path
from PyQt5.QtCore import pyqtSignal
BASE_URL = "https://sync_setting.beefuny.shop"


class HostnameIgnoreAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


def upload_zip(username: str, password: str, zip_path: str):
    """
    Upload a ZIP file to the server.
    Returns dict: {"status": "created/updated", "message": str} 或 {"status": "error", "message": str}
    """
    if not os.path.isfile(zip_path):
        return {"status": "error", "message": f"File not found: {zip_path}"}

    url = f"{BASE_URL}/upload"
    s = requests.Session()
    s.mount("https://", HostnameIgnoreAdapter())
    try:
        with open(zip_path, "rb") as f:
            files = {"zipfile": (os.path.basename(
                zip_path), f, "application/zip")}
            data = {"username": username, "password": password}

            try:
                r = s.post(url, data=data, files=files, timeout=10)
            except requests.exceptions.RequestException as e:
                return {"status": "error", "message": f"Request failed: {str(e)}"}

            try:
                result = r.json()
                return {"status": result.get("status", "error"), "message": str(result)}
            except Exception:
                return {"status": "error", "message": r.text}

    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


def download_zip(username: str, password: str, output_path: str):
    """
    Download a ZIP file from the server.
    Returns dict: {"status": "success", "message": saved_path} 或 {"status": "error", "message": str}
    """
    url = f"{BASE_URL}/download"
    payload = {"username": username, "password": password}
    s = requests.Session()
    s.mount("https://", HostnameIgnoreAdapter())
    try:
        try:
            r = s.post(url, json=payload, timeout=10)
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Request failed: {str(e)}"}

        content_type = r.headers.get("Content-Type", "")
        if content_type == "application/zip":
            try:
                with open(output_path, "wb") as f:
                    f.write(r.content)
                return {"status": "success", "message": output_path}
            except Exception as e:
                return {"status": "error", "message": f"Write failed: {str(e)}"}
        else:
            try:
                result = r.json()
                return {"status": "error", "message": str(result)}
            except Exception:
                return {"status": "error", "message": r.text}

    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


class SycnWidget(MessageBoxBase):

    sync_finished = pyqtSignal(str, str)  # status, message

    def __init__(self, parent=None):
        super().__init__(parent)
        font_ = font_config()
        self._font = font_.get_font()

        self.sync_mode = "sync_up"  # or "sync_dl"

        self.titleLabel = SubtitleLabel(self.tr('Sycn Settings'))
        self.yesButton.setText(self.tr("Sycn"))
        self.yesButton.clicked.connect(lambda: self._sync())
        self.cancelButton.setText(self.tr("Cancel"))

        self.username = LineEdit()
        self.password = PasswordLineEdit()

        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel(self.tr("Username:")))
        username_layout.addWidget(self.username)

        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel(self.tr("Password:")))
        password_layout.addWidget(self.password)

        self.modeButton = PushButton(f"Mode: {self.sync_mode}")
        self.modeButton.clicked.connect(self.toggle_mode)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.modeButton)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addLayout(username_layout)
        self.viewLayout.addLayout(password_layout)
        self.viewLayout.addLayout(button_layout)

        self.widget.setMinimumWidth(400)
        self.set_font_recursive(self, self._font)

    def toggle_mode(self):
        """切换模式"""
        self.sync_mode = "sync_dl" if self.sync_mode == "sync_up" else "sync_up"
        self.modeButton.setText(f"Mode: {self.sync_mode}")
        print(f"Switched to mode: {self.sync_mode}")

    def set_font_recursive(self, widget: QWidget, font):
        if font is None:
            return
        widget.setFont(font)
        for child in widget.findChildren(QWidget):
            child.setFont(font)

    def _compression_to_zip(self, source_dir, zip_path=".config.zip"):
        """Compress the source_dir into a zip file at zip_path"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)

    def _sync(self):
        username = self.username.text().strip()
        password = self.password.text().strip()
        if not username or not password:
            return {"status": "error", "message": "Username and password cannot be empty."}

        config_dir = Path.home() / ".config"
        # print(username, password, self.sync_mode, config_dir)
        if self.sync_mode == "sync_up":
            self._compression_to_zip(config_dir, ".config.zip")
            result = upload_zip(username, password, ".config.zip")
            if os.path.exists(".config.zip"):
                os.remove(".config.zip")
            if result["status"] in ["created", "updated"]:
                self.sync_finished.emit("success", self.tr(
                    "Settings uploaded successfully!"))
            else:
                self.sync_finished.emit("error", self.tr(
                    f"Upload failed: {result['message']}"))

        else:  # sync_dl
            result = download_zip(username, password, ".config.zip")
            if result["status"] == "success":
                try:
                    with zipfile.ZipFile(".config.zip", 'r') as zipf:
                        zipf.extractall(config_dir)
                    self.sync_finished.emit("success", self.tr(
                        "Settings downloaded and applied successfully! Please restart the application."))
                except Exception as e:
                    self.sync_finished.emit("error", self.tr(
                        f"Extraction failed: {str(e)}"))
                finally:
                    if os.path.exists(".config.zip"):
                        os.remove(".config.zip")
            else:
                self.sync_finished.emit("error", self.tr(
                    f"Download failed: {result['message']}"))
