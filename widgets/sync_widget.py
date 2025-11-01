from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget
from PyQt5.QtCore import Qt
from qfluentwidgets import LineEdit, SubtitleLabel, MessageBoxBase,  PasswordLineEdit, PushButton
from tools.font_config import font_config
import requests
import os
import py7zr
from pathlib import Path
from PyQt5.QtCore import pyqtSignal

# BASE_URL = "https://sync.beefuny.shop"
BASE_URL = "https://sync.neossh.top/"


class DownloadThread(QThread):
    # 信号：下载结果 (status, message)
    download_finished = pyqtSignal(str, str)

    def __init__(self, username: str, password: str, zip_path: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.password = password
        self.zip_path = zip_path

    def run(self):
        """线程执行函数"""
        result = self.download_zip()
        self.download_finished.emit(result["status"], result["message"])

    def download_zip(self):
        """
        从服务器下载ZIP文件
        返回: {"status": "success/error", "message": str}
        """
        url = f"{BASE_URL}/download_sync"
        data = {"username": self.username, "password": self.password}

        try:
            response = requests.post(url, json=data, headers={
                                     'Content-Type': 'application/json'}, timeout=30, stream=True)

            if response.status_code == 200:
                # 保存文件
                with open(self.zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return {"status": "success", "message": "Download completed"}
            else:
                try:
                    error_data = response.json()
                    return {"status": "error", "message": error_data.get("error", response.text)}
                except ValueError:
                    return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}

        except requests.exceptions.Timeout:
            return {"status": "error", "message": "Request timeout"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "message": "Connection error"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}


class UploadThread(QThread):
    # 信号：上传结果 (status, message)
    upload_finished = pyqtSignal(str, str)

    def __init__(self, username: str, password: str, zip_path: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.password = password
        self.zip_path = zip_path

    def run(self):
        """线程执行函数"""
        result = self.upload_zip()
        self.upload_finished.emit(result["status"], result["message"])

    def upload_zip(self):
        """
        上传ZIP文件到服务器
        返回: {"status": "created/updated/error", "message": str}
        """
        if not os.path.isfile(self.zip_path):
            return {"status": "error", "message": f"File not found: {self.zip_path}"}

        url = f"{BASE_URL}/upload_sync"

        try:
            with open(self.zip_path, "rb") as f:
                files = {"zipfile": (os.path.basename(
                    self.zip_path), f, "application/zip")}
                data = {"username": self.username, "password": self.password}

                try:
                    response = requests.post(
                        url, data=data, files=files, timeout=30)

                except requests.exceptions.Timeout:
                    return {"status": "error", "message": "Request timeout"}
                except requests.exceptions.ConnectionError as e:
                    print(e)
                    return {"status": "error", "message": "Connection error"}
                except requests.exceptions.RequestException as e:
                    return {"status": "error", "message": f"Request failed: {str(e)}"}

                # 解析响应
                if response.status_code == 200 or response.status_code == 201:
                    try:
                        result = response.json()
                        status = result.get("status", "error")
                        message = result.get("message", str(result))
                        return {"status": status, "message": message}
                    except ValueError:
                        return {"status": "error", "message": "Invalid JSON response"}
                else:
                    return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}

        except FileNotFoundError:
            return {"status": "error", "message": f"File not found: {self.zip_path}"}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}


class SycnWidget(MessageBoxBase):

    sync_finished = pyqtSignal(str, str)  # status, message

    def __init__(self, parent=None):
        super().__init__(parent)
        font_ = font_config()
        self._font = font_.get_font()
        self._parent = self.window()
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
        self.upload_thread = None
        self.download_thread = None

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
        password = self.password.text().strip()
        with py7zr.SevenZipFile(
            zip_path,
            'w',
            password=password,
            filters=[{"id": py7zr.FILTER_LZMA2, "preset": 1}],
            header_encryption=True
        ) as archive:
            archive.writeall(source_dir, arcname='')

        # with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        #     for root, dirs, files in os.walk(source_dir):
        #         for file in files:
        #             file_path = os.path.join(root, file)
        #             arcname = os.path.relpath(file_path, source_dir)
        #             zipf.write(file_path, arcname)

    def _sync(self):
        username = self.username.text().strip()
        password = self.password.text().strip()
        if not username or not password:
            self.sync_finished.emit(
                "error", "Username and password cannot be empty.")
            return

        config_dir = Path.home() / ".config" / "pyqt-ssh"

        if self.sync_mode == "sync_up":
            # 压缩文件
            self._compression_to_zip(config_dir, ".config.zip")

            # 启动上传线程
            self.upload_thread = UploadThread(
                username, password, ".config.zip")
            self.upload_thread.upload_finished.connect(self.on_upload_finished)
            self.upload_thread.start()

            # 禁用按钮，防止重复点击
            self.yesButton.setEnabled(False)
            self.yesButton.setText(self.tr("Uploading..."))

        else:  # sync_dl
            # 启动下载线程
            self.download_thread = DownloadThread(
                username, password, ".config.zip")
            self.download_thread.download_finished.connect(
                self.on_download_finished)
            self.download_thread.start()

            # 禁用按钮，防止重复点击
            self.yesButton.setEnabled(False)
            self.yesButton.setText(self.tr("Downloading..."))

    def on_upload_finished(self, status, message):
        """上传完成回调"""
        # 清理临时文件
        if os.path.exists(".config.zip"):
            os.remove(".config.zip")

        # 恢复按钮状态
        self.yesButton.setEnabled(True)
        self.yesButton.setText(self.tr("Sync"))

        # 发射完成信号
        self.sync_finished.emit(status, message)

    def on_download_finished(self, status, message):
        """下载完成回调"""
        # 恢复按钮状态
        self.yesButton.setEnabled(True)
        self.yesButton.setText(self.tr("Sync"))
        password = self.password.text().strip()
        if status == "success":
            # 解压文件
            try:
                status = "updated"
                config_dir = Path.home() / ".config" / "pyqt-ssh"
                with py7zr.SevenZipFile(".config.zip", 'r', password=password) as archive:
                    archive.extractall(config_dir)
                message = "Settings downloaded and applied successfully! Please restart the application."
            except Exception as e:
                status = "error"
                message = f"Extraction failed: {str(e)}"
            finally:
                # 清理临时文件
                if os.path.exists(".config.zip"):
                    os.remove(".config.zip")

        # 发射完成信号
        self.sync_finished.emit(status, message)

    def center_on_parent(self):
        parent_rect = self.parent().frameGeometry()
        self_rect = self.frameGeometry()
        self.move(
            parent_rect.center().x() - self_rect.width() // 2,
            parent_rect.center().y() - self_rect.height() // 2
        )

    def showEvent(self, event):
        super().showEvent(event)

        if self._parent:
            parent_geometry = self._parent.geometry()
            self.setGeometry(parent_geometry)
            self.raise_()
            self.activateWindow()
