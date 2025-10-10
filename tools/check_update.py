import sys
import os
from .setting_config import SCM
import requests
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication
import time
import zipfile
import subprocess
import psutil
from concurrent.futures import ThreadPoolExecutor
import threading
from .logger import get_logger
import shutil

update_logger = get_logger("update")

ProxySite = "https://ghfast.top/"

def is_pyinstaller_bundle():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_version():
    # if not is_pyinstaller_bundle():
    #     return "dev"
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    version_file_path = os.path.join(base_path, 'version.txt')
    try:
        with open(version_file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def is_internal():
    base_path = os.path.dirname(sys.executable)
    return os.path.exists(os.path.join(base_path, "_internal"))

class CheckUpdate(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress_lock = threading.Lock()
        self.downloaded_size = 0
        self.total_size = 0
        self.updater_executable_path = None

    def run(self):
        # if not is_pyinstaller_bundle():
        #     return
        while True:
            if self.check():
                break
            time.sleep(300)

    def check(self) -> bool:
        config = SCM().read_config()
        channel = config.get("update_channel", "none")
        if channel == "none":
            return False
        local_version = get_version()
        if not local_version:
            return False
        repo_map = {
            "stable": "Heartestrella/AuraShell",
            "insider": "XiaoYingYo/AuraShell"
        }
        repo_path = repo_map.get(channel)
        if not repo_path:
            return False
        try:
            api_url = f"https://api.github.com/repos/{repo_path}/releases/latest"
            response = requests.get(api_url, timeout=120)
            if response.status_code == 200:
                data = response.json()
                remote_version = data.get("tag_name")
                if remote_version and remote_version != local_version:
                    return self.download_asset(data, remote_version)
        except Exception as e:
            update_logger.error(f"Error checking for updates: {e}")
        return False

    def _download_chunk(self, args):
        url, start, end, part_path = args
        headers = {'Range': f'bytes={start}-{end}'}
        while True:
            bytes_written_this_attempt = 0
            try:
                with requests.get(url, headers=headers, stream=True, timeout=10) as r:
                    r.raise_for_status()
                    with open(part_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                            chunk_len = len(chunk)
                            bytes_written_this_attempt += chunk_len
                            with self.progress_lock:
                                self.downloaded_size += chunk_len
                    return part_path
            except Exception as e:
                with self.progress_lock:
                    self.downloaded_size -= bytes_written_this_attempt

    def _prepare_updater_executable(self):
        try:
            updater_dir = os.path.join('tmp', 'update', 'main')
            if os.path.exists(updater_dir):
                shutil.rmtree(updater_dir)
            os.makedirs(updater_dir, exist_ok=True)
            if is_internal():
                base_dir = os.path.dirname(sys.executable)
                source_internal_dir = os.path.join(base_dir, '_internal')
                source_exe = sys.executable
                if os.path.isdir(source_internal_dir):
                    shutil.copytree(source_internal_dir, os.path.join(updater_dir, '_internal'), dirs_exist_ok=True)
                if os.path.isfile(source_exe):
                    shutil.copy2(source_exe, updater_dir)
                self.updater_executable_path = os.path.join(updater_dir, os.path.basename(sys.executable))
            else:
                source_exe = sys.executable
                self.updater_executable_path = os.path.join(updater_dir, os.path.basename(source_exe))
                shutil.copy2(source_exe, self.updater_executable_path)
            return os.path.exists(self.updater_executable_path)
        except Exception as e:
            update_logger.error(f"Failed to create updater copy: {e}", exc_info=True)
            return False

    def download_asset(self, release_data, version):
        if not self._prepare_updater_executable():
            update_logger.error("Failed to prepare updater executable. Aborting update download.")
            return False
        asset_name = None
        if sys.platform == "win32":
            if is_internal():
                asset_name = "AuraShell-Windows.zip"
            else:
                asset_name = "AuraShell.exe"
        elif sys.platform == "linux":
            asset_name = "AuraShell-Linux"
        elif sys.platform == "darwin":
            asset_name = "AuraShell-Macos"
        if not asset_name:
            update_logger.error(f"Unsupported OS for update: {sys.platform}")
            return False
        asset_url = None
        for asset in release_data.get('assets', []):
            if asset.get('name') == asset_name:
                asset_url = f"{ProxySite}{asset.get('browser_download_url')}"
                break
        if not asset_url:
            update_logger.error(f"Asset '{asset_name}' not found in release {version}")
            return False
        download_dir = os.path.join('tmp', 'update', 'download')
        os.makedirs(download_dir, exist_ok=True)
        file_path = os.path.join(download_dir, asset_name)
        num_threads = 12
        temp_files = []
        try:
            with requests.head(asset_url, timeout=120) as r:
                r.raise_for_status()
                self.total_size = int(r.headers.get('content-length', 0))
            self.downloaded_size = 0
            chunk_size = self.total_size // num_threads
            chunks = []
            for i in range(num_threads):
                start = i * chunk_size
                end = start + chunk_size - 1
                if i == num_threads - 1:
                    end = self.total_size - 1
                part_path = f"{file_path}.part{i}"
                temp_files.append(part_path)
                chunks.append((asset_url, start, end, part_path))
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                list(executor.map(self._download_chunk, chunks))
            with open(file_path, 'wb') as final_file:
                for part_path in temp_files:
                    if not os.path.exists(part_path):
                        continue
                    with open(part_path, 'rb') as part_file:
                        final_file.write(part_file.read())
            return self.apply_update(file_path)
        except Exception as e:
            update_logger.error(f"Download failed: {e}")
            return False
        finally:
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        return False

    def apply_update(self, file_path):
        if not is_pyinstaller_bundle():
            return True
        try:
            update_dir = os.path.dirname(file_path)
            source_path = file_path
            if file_path.endswith('.zip'):
                unpacked_dir = os.path.join(update_dir, 'unpacked')
                if os.path.exists(unpacked_dir):
                    import shutil
                    shutil.rmtree(unpacked_dir)
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(unpacked_dir)
                except zipfile.BadZipFile as e:
                    update_logger.error(f"Invalid zip file: {e}")
                    return False
                except Exception as e:
                    update_logger.error(f"Failed to extract zip file: {e}")
                    return False
                extracted_items = os.listdir(unpacked_dir)
                if len(extracted_items) == 1:
                    source_path = os.path.join(unpacked_dir, extracted_items[0])
                else:
                    source_path = unpacked_dir
            current_pid = os.getpid()
            if is_internal():
                target_path = os.path.dirname(sys.executable)
            else:
                target_path = sys.executable
            executable = self.updater_executable_path
            if not executable or not os.path.exists(executable):
                update_logger.error("Updater executable copy not found!")
                return False
            args = [executable, '--update', str(current_pid), source_path, target_path]
            try:
                subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0, close_fds=True)
                return True
            except Exception as e:
                update_logger.error(f"Failed to start updater: {e}")
                return False
        except Exception as e:
            update_logger.error(f"Error during update: {e}")
            return False