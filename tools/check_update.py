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

ProxySite = ''

def is_pyinstaller_bundle():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_version():
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
    return os.path.exists("_internal")

class CheckUpdate(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        if not is_pyinstaller_bundle():
            return
        # while True:
        #     if self.check():
        #         break
        #     time.sleep(300)
        self.check()

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
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                remote_version = data.get("tag_name")
                if remote_version and remote_version != local_version:
                    return self.download_asset(data, remote_version)
        except Exception as e:
            print(f"Error checking for updates: {e}")
        return False

    def download_asset(self, release_data, version):
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
            print(f"Unsupported OS for update: {sys.platform}")
            return False
        asset_url = None
        for asset in release_data.get('assets', []):
            if asset.get('name') == asset_name:
                asset_url = asset.get('browser_download_url')
                break
        if not asset_url:
            print(f"Asset '{asset_name}' not found in release {version}")
            return False
        try:
            download_dir = os.path.join('tmp', 'update')
            os.makedirs(download_dir, exist_ok=True)
            file_path = os.path.join(download_dir, asset_name)
            with requests.get(asset_url, stream=True, timeout=10240) as r:
                r.raise_for_status()
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return self.apply_update(file_path)
        except Exception as e:
            print(f"Download failed: {e}")

    def apply_update(self, file_path):
        update_dir = os.path.dirname(file_path)
        source_path = file_path
        if file_path.endswith('.zip'):
            unpacked_dir = os.path.join(update_dir, 'unpacked')
            if os.path.exists(unpacked_dir):
                import shutil
                shutil.rmtree(unpacked_dir)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(unpacked_dir)
            extracted_items = os.listdir(unpacked_dir)
            if len(extracted_items) == 1:
                 source_path = os.path.join(unpacked_dir, extracted_items[0])
            else:
                 source_path = unpacked_dir
        updater_script = os.path.join(sys._MEIPASS, 'tools', 'updater.py') if getattr(sys, 'frozen', False) else os.path.join(os.path.abspath("."), "tools", "updater.py")
        current_pid = os.getpid()
        if is_internal():
             target_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), '..', '_internal'))
        else:
             target_path = sys.executable
        if not os.path.exists(updater_script):
             print("Updater script not found!")
             return False
        args = [sys.executable, updater_script, str(current_pid), source_path, target_path]
        subprocess.Popen(args)
        QApplication.instance().quit()
        return True