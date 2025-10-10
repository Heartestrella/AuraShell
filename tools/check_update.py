import sys
import os
from .setting_config import SCM
import requests
from PyQt5.QtCore import QThread
import time

ProxySite = ''

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
        # while True:
        #     self.check()
        #     time.sleep(300)
        self.check()

    def check(self):
        config = SCM().read_config()
        channel = config.get("update_channel", "none")
        if channel == "none":
            return
        local_version = get_version()
        if not local_version:
            return
        repo_map = {
            "stable": "Heartestrella/AuraShell",
            "insider": "XiaoYingYo/AuraShell"
        }
        repo_path = repo_map.get(channel)
        if not repo_path:
            return
        try:
            api_url = f"https://api.github.com/repos/{repo_path}/releases/latest"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                remote_version = data.get("tag_name")
                if remote_version and remote_version != local_version:
                    self.download_asset(data, remote_version)
        except Exception as e:
            print(f"Error checking for updates: {e}")

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
            return
        asset_url = None
        for asset in release_data.get('assets', []):
            if asset.get('name') == asset_name:
                asset_url = asset.get('browser_download_url')
                break
        if not asset_url:
            print(f"Asset '{asset_name}' not found in release {version}")
            return
        try:
            download_dir = os.path.join('tmp', 'update')
            os.makedirs(download_dir, exist_ok=True)
            file_path = os.path.join(download_dir, f"{asset_name}-{version}")
            with requests.get(asset_url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception as e:
            print(f"Download failed: {e}")