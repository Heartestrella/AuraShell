# coding:utf-8
import sys
import ctypes
import time
from PyQt5.QtCore import Qt, QTranslator, QTimer, QLocale, QUrl, QEvent, pyqtSignal, QLibraryInfo
from PyQt5.QtGui import QPixmap, QPainter, QDesktopServices, QIcon
from PyQt5.QtWidgets import QApplication, QStackedWidget, QHBoxLayout, QWidget

from qfluentwidgets import (NavigationInterface, NavigationItemPosition, InfoBar,
                            isDarkTheme, setTheme, Theme, InfoBarPosition, FluentIcon as FIF, FluentTranslator, NavigationAvatarWidget, Dialog)
from qframelesswindow import FramelessWindow, StandardTitleBar
from widgets.setting_page import SettingPage
from widgets.home_interface import MainInterface
from tools.font_config import font_config
from tools.session_manager import SessionManager
from tools.logger import setup_global_logging, main_logger
from tools.ssh import SSHWorker
from tools.remote_file_manage import RemoteFileManager, FileManagerHandler
from widgets.sync_widget import SycnWidget
import os
import subprocess
from tools.atool import resource_path
from tools.setting_config import SCM
from widgets.ssh_widget import SSHPage, SSHWidget
from tools.icons import My_Icons
from functools import partial
from tools.watching_saved import FileWatchThread
import magic

font_ = font_config()
setting_ = SCM()
mime_types = [
    "text/plain",
    "text/html",
    "text/css",
    "text/javascript",
    "application/json",
    "application/xml"
]


class Window(FramelessWindow):
    windowResized = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.icons = My_Icons()
        self.active_transfers = {}
        self.watching_dogs = {}
        self._download_debounce_timer = QTimer(self)
        self._download_debounce_timer.setSingleShot(True)
        self._download_debounce_timer.setInterval(500)
        self._download_debounce_timer.timeout.connect(
            self._process_pending_downloads)
        self._pending_download_paths = {}

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.apply_locked_ratio)

        self.setMinimumSize(800, 600)
        self.setTitleBar(StandardTitleBar(self))
        self._bg_ratio = None
        self.setWindowTitle("AuraShell Beta")
        icon = QIcon(resource_path("resource/icons/icon.ico"))
        self.setWindowIcon(icon)
        QApplication.setWindowIcon(icon)
        self.titleBar.raise_()
        self.connect_status_dict = {}
        self.ssh_session = {}
        self.sessionmanager = SessionManager()
        self.session_widgets = {}
        self.file_tree_object = {}
        self._bg_opacity = 1.0
        # self.unprocessed_tasks = ["systemd","kthreadd","pool_workqueue_release","kworker/R-rcu_g"]
        self._bg_pixmap = None
        self.hBoxLayout = QHBoxLayout(self)
        self.navigationInterface = NavigationInterface(
            self, showMenuButton=True)
        self.stackWidget = QStackedWidget(self)

        # create sub interface
        self.MainInterface = MainInterface(self)
        self.MainInterface.sessionClicked.connect(self._on_session_selected)

        self.sycn_widget = SycnWidget(self)
        self.sycn_widget.sync_finished.connect(
            lambda status, msg: InfoBar.success(
                title=msg if status == "success" else self.tr("Error"),
                content="",
                orient=Qt.Vertical,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=5000 if status == "success" else -1,
                parent=self
            ) if status == "success" else InfoBar.error(
                title=self.tr("Error"),
                content=msg,
                orient=Qt.Vertical,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=-1,
                parent=self
            )
        )
        self.sycn_widget.hide()
        # self.sessions = Widget(
        #     self.tr('No conversation selected yet'), True, self)
        self.ssh_page = SSHPage()
        self.ssh_page.menuActionTriggered.connect(self._handle_action)

        self.navigationInterface.setStyleSheet("background: transparent;")
        self.navigationInterface.setCollapsible(True)
        self.stackWidget.setStyleSheet("background: transparent;")

        self.settingInterface = SettingPage(self,)
        self.settingInterface.themeChanged.connect(self._on_theme_changed)
        self.settingInterface.lock_ratio_card.checkedChanged.connect(
            self.apply_locked_ratio)
        self.settingInterface.opacityEdit.valueChanged.connect(
            self.set_background_opacity)
        # Connect transparency setting signal
        # self.settingInterface.bgOpacityChanged.connect(
        #     self.set_background_opacity)
        self._on_theme_changed(
            self.settingInterface.cfg.background_color.value)

        self.initLayout()
        self.initNavigation()

        self.initWindow()

        if setting_.read_config()["maximized"]:
            self.showMaximized()

    def set_background_opacity(self, opacity: float):
        if not self._bg_pixmap:
            return

        # In the case of int, only setting is passed in
        if isinstance(opacity, int):
            opacity = opacity / 100

        self._bg_opacity = max(0.0, min(1.0, opacity))
        self.update()

    def _on_ssh_connected(self, success: bool, msg: str):
        if success:
            InfoBar.success(
                title=msg,
                content="",
                orient=Qt.Vertical,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self
            )

    def _on_ssh_error(self, msg: str):
        InfoBar.error(
            title=self.tr("Connection failed"),
            content=self.tr(f"Error:\n{msg}\nPlease close this session"),
            orient=Qt.Vertical,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=-1,
            parent=self
        )

    def _set_usage(self, widget_key, usage):
        try:
            result = dict(usage)
            parent_key = widget_key.split("-", 1)[0].strip()
            # print(self.session_widgets)
            # print(parent_key)
            widget = self.session_widgets[widget_key]
            if widget:
                connections = result["connections"]
                cpu_percent = result["cpu_percent"]
                mem_percent = result["mem_percent"]
                net_usage = result["net_usage"]
                top_processes = result["top_processes"]
                all_processes = result["all_processes"]
                # 先用第一个切出来的网卡测试 后面加切换网卡
                if net_usage:
                    upload, download = net_usage[1]["tx_kbps"], net_usage[1]["rx_kbps"]
                    widget.task.netmonitor.update_speed(
                        upload, download)
                widget.sys_resources.set_progress("cpu", cpu_percent)
                widget.sys_resources.set_progress("ram", mem_percent)
                for processes in top_processes:
                    processes_cpu_percent = processes["cpu"]
                    processes_name = processes["name"]
                    processes_mem = processes["mem"]
                    widget.task.add_row(
                        f"{processes_mem:.1f}",
                        f"{processes_cpu_percent:.1f}",
                        processes_name
                    )
                if connections and widget.now_ui == "net":
                    widget.net_monitor.updateProcessData(connections)
                    # print(processes_cpu_percent, processes_name, processes_mem)
                if all_processes and widget.now_ui == "task":
                    widget.task_detaile.updateProcessData(all_processes)

            else:
                print("Failed to obtain the SSH Widget")
        except Exception as e:
            print(e)

    def _show_info(self, path: str = None, status: bool = None, msg: str = None, type_: str = None, widget_key: str = None, local_path: str = None, open_it: bool = False):
        no_refresh_types = ["download",
                            "start_upload", "start_download", "info"]
       #  print(f"showinfo : {type_} {widget_key}")
        duration = 3000
        session_widget = self.session_widgets[widget_key]
        if not session_widget:
            return
        title = ""
        if type_ == "upload":
            paths = path if isinstance(path, list) else [path]
            for p in paths:
                # The 'path' from the finished signal is the unique identifier
                file_id = self.active_transfers.get(p, {}).get("id")
                if not file_id:
                    # Fallback for safety, though it should exist
                    file_id = f"{widget_key}_{p}_{time.time()}"

                if status:
                    if p not in self.active_transfers:
                        # This can happen if the file is very small and finishes
                        # before any progress signal is emitted.
                        self._add_transfer_item_if_not_exists(
                            widget_key, p, "upload")
                        file_id = self.active_transfers[p]["id"]

                    if p in self.active_transfers:
                        self.active_transfers[p]['type'] = 'completed'
                        self.active_transfers[p]['progress'] = 100

                    data = {"type": "completed", "progress": 100}
                    session_widget.transfer_progress.update_transfer_item(
                        file_id, data)
                    title = self.tr(f"Upload {p} completed")
                    duration = 2000
                else:
                    title = f"Uoload {p} failure"
                    duration = -1
                    if p in self.active_transfers:
                        session_widget.transfer_progress.remove_transfer_item(
                            self.active_transfers[p]["id"])
                        del self.active_transfers[p]

        elif type_ == "start_upload":
            # This is now handled by _add_transfer_item_if_not_exists
            # It will be called from _handle_files for single files/compressed,
            # or dynamically from progress/finished signals for expanded dirs.
            pass

        elif type_ == "start_download":
            paths = path if isinstance(path, list) else [path]
            for p in paths:
                file_id = f"{widget_key}_{os.path.basename(p)}_{time.time()}"
                data = {
                    "type": "download",
                    "filename": os.path.basename(p),
                    "progress": 0
                }
                self.active_transfers[file_id] = data
                session_widget.transfer_progress.add_transfer_item(
                    file_id, data)

        elif type_ == "download":
            # 'path' is the unique remote path identifier
            if path in self.active_transfers:
                file_id = self.active_transfers[path]["id"]
                if status:
                    self.active_transfers[path]['type'] = 'completed'
                    self.active_transfers[path]['progress'] = 100
                    data = {"type": "completed", "progress": 100}
                    session_widget.transfer_progress.update_transfer_item(
                        file_id, data)

                    if open_it and local_path:
                        try:
                            print(
                                f"From Remote Path : {path}")
                            # Open the directory containing the downloaded file/folder
                            open_path = local_path if os.path.isfile(
                                local_path) else os.path.dirname(local_path)
                            if sys.platform.startswith('darwin'):
                                subprocess.call(('open', open_path))
                            elif os.name == 'nt':
                                os.startfile(open_path)
                                with open(open_path, "rb") as f:
                                    mime = magic.from_buffer(
                                        f.read(2048), mime=True)
                                if mime in mime_types or mime.startswith("text/"):
                                    print("Text file starting watching")
                                    file_thread = FileWatchThread(open_path)
                                    file_thread.file_saved.connect(
                                        lambda local, : self.reupload_when_saved(widget_key, local, path))
                                    file_thread.start()

                                    if widget_key not in self.watching_dogs:
                                        self.watching_dogs[widget_key] = []

                                    self.watching_dogs[widget_key].append(
                                        file_thread)
                                else:
                                    print(
                                        f"File tpye {mime} is not text file won't watching")
                            elif os.name == 'posix':
                                subprocess.call(('xdg-open', open_path))
                        except Exception as e:
                            print(f"Error opening file/folder: {e}")
                else:
                    session_widget.transfer_progress.remove_transfer_item(
                        file_id)
                    del self.active_transfers[path]
            elif status:  # Finished signal for a small file that sent no progress
                self._add_transfer_item_if_not_exists(
                    widget_key, path, "download")
                if path in self.active_transfers:
                    file_id = self.active_transfers[path]["id"]
                    self.active_transfers[path]['type'] = 'completed'
                    self.active_transfers[path]['progress'] = 100
                    data = {"type": "completed", "progress": 100}
                    session_widget.transfer_progress.update_transfer_item(
                        file_id, data)

        else:
            duration = 5000
            title = ""
            if type_ in ("compression", "uncompression"):
                title = self.tr(f"Start to {type_} : {path}")
                msg = ""
            elif type_ == "delete":
                print("delete showinfo")
                if status:
                    title = self.tr(f"Deleted {path} successfully")
                else:
                    title = self.tr(f"Failed to delete {path}\n{msg}")
                    duration = -1
            elif type_ == "paste":
                if status:
                    title = self.tr("Paste Successful")
                    msg = self.tr(f"Pasted {path} to {local_path}")
                else:
                    title = self.tr("Paste Failed")
                    duration = -1
            elif type_ == "rename":
                if status:
                    title = self.tr("Rename Successful")
                    msg = self.tr(f"Renamed {path} to {local_path}")
                else:
                    title = self.tr("Rename Failed")
                    duration = -1
            elif type_ == "mkdir":
                if status:
                    title = self.tr(f"Created directory {path} successfully")
                else:
                    title = self.tr(
                        f"Failed to create directory {path}\n{msg}")
                    duration = -1

        if title:
            InfoBar.info(
                title=title,
                content=msg,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=duration,
                parent=self.window()
            )

        if type_ not in no_refresh_types and widget_key:
            self._refresh_paths(widget_key)
            print(f"刷新路径: {widget_key}")

    def _show_progresses(self, path, percentage, bytes_so_far, total_bytes, widget_key, transfer_type):
        """Handles progress updates for both uploads and downloads."""
        session_widget = self.session_widgets[widget_key]
        if not session_widget:
            return

        # 'path' is the unique identifier (local for upload, remote for download)
        if path not in self.active_transfers:
            self._add_transfer_item_if_not_exists(
                widget_key, path, transfer_type)

        if path in self.active_transfers:
            file_id = self.active_transfers[path]["id"]
            data = self.active_transfers[path]
            data["progress"] = percentage
            data["bytes_so_far"] = bytes_so_far
            data["total_bytes"] = total_bytes
            if percentage >= 100:
                data["type"] = "completed"
            session_widget.transfer_progress.update_transfer_item(
                file_id, data)

    def reupload_when_saved(self, widget_name, local_path, remote_path,):
        remote_path = os.path.dirname(remote_path)
        # print(f"将上传 {local_path} 到 {widget_name}的 {remote_path}")
        file_manager: RemoteFileManager = self.file_tree_object[widget_name]

        if file_manager:
            self._handle_upload_request(widget_key=widget_name, local_path=local_path,
                                        remote_path=remote_path, compression=False, file_manager=file_manager)

    def _start_ssh_connect(self, widget_key):
        parent_key = widget_key.split("-")[0].strip()
        session = self.sessionmanager.get_session_by_name(parent_key)

        def key_verification(file_md5, host_key):
            msg = ''
            session_file_md5 = session.processes_md5
            session_host_key = session.host_key

            if session_file_md5 != file_md5:
                msg += self.tr(
                    f"The MD5 file fingerprint of the Processes file does not match the record.\nMD5:{file_md5}\n")
            if session_host_key != host_key:
                msg += self.tr(
                    f"The host key does not match the recorded one.\n{host_key}\n")

            if msg:
                msg += self.tr("Are you sure to continue?")
                w = Dialog(self.tr("Warning!!!!!"), msg, self)
                if w.exec():
                    self.sessionmanager.update_session_processes_md5(
                        parent_key, file_md5)
                    self.sessionmanager.update_session_host_key(
                        parent_key, host_key)
                    start_real_connection()
                else:
                    return
            else:
                start_real_connection()

        def start_real_connection():
            session_widget = self.session_widgets[widget_key]
            # processes = SSHWorker(session, for_resources=True)
            # processes.key_verification.connect(key_verification)
            self.ssh_session[f'{widget_key}-processes'] = processes
            processes.sys_resource.connect(
                lambda usage, key=widget_key: self._set_usage(key, usage))
            processes.start()

            file_manager = RemoteFileManager(session)
            handler = FileManagerHandler(
                file_manager, session_widget, widget_key, self)

            def on_sftp_ready():
                global home_path
                home_path = file_manager.get_default_path()
                path_list = self.parse_linux_path(home_path)

                session_widget.file_bar.send_signal = False
                for i, path in enumerate(path_list):
                    if i == len(path_list) - 1:
                        session_widget.file_bar.send_signal = True
                    session_widget.file_bar.breadcrumbBar.addItem(path, path)

                session_widget.file_explorer.path = home_path
                file_manager.add_path(home_path)

                def _on_path_check_result(widget_key, path, result):
                    self._update_file_tree_branch_when_cd(path, widget_key)

                file_manager.path_check_result.connect(
                    partial(_on_path_check_result,
                            widget_key), Qt.QueuedConnection
                )

            file_manager.sftp_ready.connect(on_sftp_ready)
            file_manager.start()

            self.file_tree_object[widget_key] = file_manager
            self.file_tree_object[f"{widget_key}-handler"] = handler

            worker = SSHWorker(session, for_resources=False)
            self.ssh_session[widget_key] = worker
            worker.connected.connect(
                lambda success, msg: self._on_ssh_connected(success, msg))
            worker.error_occurred.connect(lambda e: self._on_ssh_error(e))

            try:
                child_widget = self.session_widgets[widget_key]
                if hasattr(child_widget, 'ssh_widget'):
                    child_widget.ssh_widget.set_worker(worker)
                else:
                    print("child_widget does not have an ssh_widget attribute")
            except Exception as e:
                print("Injecting worker failed:", e)

            worker.start()
            session_widget.ssh_widget.directoryChanged.connect(
                lambda path: file_manager.check_path_async(path)
            )
            session_widget.disk_storage.refresh.triggered.connect(
                lambda checked, ck=widget_key: self._refresh_paths(ck)
            )

        processes = SSHWorker(session, for_resources=True)
        processes.key_verification.connect(key_verification)
        processes.start()

    def _open_server_files(self, path: str, type_: str, widget_key: str):
        file_manager: RemoteFileManager = self.file_tree_object[widget_key]
        duration = 2000
        title = self.tr(f"File: {path} Type: {type_}\n")
        msg = self.tr(
            f"Start to download it and open with default program")
        if type_ == "executable":
            title = self.tr(f"{path} is an executable won't start downloading")
            msg = ""

        InfoBar.info(
            title=title,
            content=msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=duration,
            parent=self.window()
        )
        if type_ != "executable":
            file_manager.download_path_async(path, True)

    def _handle_files(self, action_type, full_path, copy_to, cut, widget_key):
        file_manager: RemoteFileManager = self.file_tree_object[widget_key]
        if action_type == "delete":
            file_manager.delete_path(full_path)
        elif action_type == "copy_path":
            paths_to_copy = full_path if isinstance(
                full_path, list) else [full_path]
            clipboard.setText('\n'.join(paths_to_copy))
        elif action_type == "download":
            # Debounce download requests
            if widget_key not in self._pending_download_paths:
                self._pending_download_paths[widget_key] = {
                    "paths": [], "compression": cut}

            # Since _handle_files is called for each item, full_path is a single path string
            self._pending_download_paths[widget_key]["paths"].append(full_path)
            self._pending_download_paths[widget_key]["compression"] = cut
            self._download_debounce_timer.start()

        elif action_type == "paste":
            source_paths = full_path if isinstance(
                full_path, list) else [full_path]
            for source_path in source_paths:
                if source_path and copy_to:
                    print(
                        f"Copy {source_path} to {copy_to} Cut status : {cut}")
                    file_manager.copy_to(source_path, copy_to, cut)
        elif action_type == "rename":
            if copy_to:
                print(f"Rename {full_path} to {copy_to}")
                file_manager.rename(path=full_path, new_name=copy_to)
        elif action_type == "info":
            paths_to_info = full_path if isinstance(
                full_path, list) else [full_path]
            for path in paths_to_info:
                file_manager.get_file_info(path)
        elif action_type == "mkdir":
            if full_path:
                file_manager.mkdir(full_path)

    def _process_pending_downloads(self):
        """Process the accumulated download paths after the debounce delay."""
        if not self._pending_download_paths:
            return

        # Atomically take ownership of the pending paths and reset the shared collection
        paths_to_process_now = self._pending_download_paths
        self._pending_download_paths = {}

        for widget_key, download_info in paths_to_process_now.items():
            paths_to_download = download_info["paths"]
            compression = download_info["compression"]

            if not paths_to_download:
                continue

            file_manager: RemoteFileManager = self.file_tree_object.get(
                widget_key)
            if not file_manager:
                continue

            if not compression:  # Non-compressed download
                path_types = file_manager.check_path_type_list(
                    paths_to_download)
                files_to_add_ui = [
                    p for p, t in path_types.items() if t == "file"]
                for path in files_to_add_ui:
                    self._add_transfer_item_if_not_exists(
                        widget_key, path, "download")
                file_manager.download_path_async(
                    paths_to_download, compression=compression)

            else:  # Compressed download
                print(f"{type(paths_to_download)} {paths_to_download}")
                self._add_transfer_item_if_not_exists(
                    widget_key, paths_to_download[0], "download")
                file_manager.download_path_async(
                    paths_to_download[0], compression=compression)

    def _refresh_paths(self, widget_key: str):
        print("Refresh the page")
        session_widget: SSHWidget = self.session_widgets[widget_key]
        session_widget._update_file_explorer()

    def parse_linux_path(self, path: str) -> list:
        """
        Parse a Linux path into a list of path elements, with each level as an element.

        Example:
            '/home/bee' -> ['/', 'home', 'bee']
            '/' -> ['/']

        Parameters:
            path: str, Linux-style path

        Returns:
            list[str], list from root to deepest directory
        """
        if not path:
            return []

        path_list = []
        if path.startswith('/'):
            path_list.append('/')
        parts = [p for p in path.strip('/').split('/') if p]

        path_list.extend(parts)

        return path_list

    def _update_file_tree_branch_when_cd(self, path: str, widget_key: str):
        file_manager: RemoteFileManager = self.file_tree_object[widget_key]
        file_manager.add_path(path, update_tree_sign=True)
        # path_status = file_manager.check_path_type(path)
        # # print(f"更新目录：{path}")
        # if path_status:
        #     file_manager._add_path_to_tree(path)
        # else:
        #     print(f"{path}不存在")

    def on_file_tree_updated(self, file_tree, sw, path=None):
        """Handling file tree updates"""
        sw.disk_storage.refresh_tree(file_tree)
        if path:
            sw.disk_storage.switch_to(path)

    def on_file_manager_error(self, error_msg):
        InfoBar.error(
            title=self.tr('File management errors'),
            content=self.tr(f'''Error details:\n{error_msg}'''),
            orient=Qt.Vertical,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=-1,
            parent=self
        )

    def _count_sessions_starting_with(self, session_id_prefix):
        """Count the number of sessions starting with the specified prefix"""
        count = 0
        for key in self.session_widgets.keys():
            if key.startswith(session_id_prefix):
                count += 1
        return count

    def _on_session_selected(self, session_id=None, session_name=None):
        """Handling session selection"""

        def _connect_file_explorer_signals(self, widget, widget_key):
            # 文件操作
            widget.file_explorer.file_action.connect(
                partial(self._handle_files, widget_key=widget_key)
            )

            # 目录选择
            widget.disk_storage.directory_selected.connect(
                partial(self._update_file_tree_branch_when_cd,
                        widget_key=widget_key)
            )

            # 取消传输
            widget.transfer_progress.cancelRequested.connect(
                partial(self._handle_transfer_cancellation,
                        widget_key=widget_key)
            )
            self.windowResized.connect(widget.on_main_window_resized)
        if session_name:
            name = session_name.rsplit(" - ", 1)[0]
            session = self.sessionmanager.get_session_by_name(name)

        if session_id:
            session = self.sessionmanager.get_session(session_id=session_id)

        name = session.name

        child_number = 1
        for key in self.session_widgets.keys():
            if key.startswith(f"{name} - "):
                try:
                    existing_num = int(key.split(" - ")[-1])
                    child_number = max(child_number, existing_num + 1)
                except ValueError:
                    continue
        widget_key = f"{name} - {child_number}"
        print(widget_key)
        font_name, font_size = font_.read_font()
        widget = SSHWidget(widget_key, font_name=font_name)
        self.ssh_page.add_session(widget_key, widget_key, widget=widget)
        _connect_file_explorer_signals(self, widget, widget_key)

        self.session_widgets[widget_key] = widget

        self._start_ssh_connect(widget_key)
        self.switchTo(self.ssh_page, widget_key)

    def apply_locked_ratio(self, event=None):
        new_width, new_height = 0, 0
        if not self.isMaximized():
            """Apply background image proportionally to window size"""
            if self.settingInterface._lock_ratio and self._bg_pixmap and self._bg_ratio:
                if event is not None and not isinstance(event, bool):
                    new_width = event.size().width()
                    new_height = event.size().height()
                else:
                    new_width = self.width()
                    new_height = self.height()

                target_ratio = self._bg_ratio

                if abs(new_width / new_height - target_ratio) > 0.01:
                    new_height = int(new_width / target_ratio)
                    self.resize(new_width, new_height)
            if self.settingInterface.init_window_size and new_width and new_height:
                self.settingInterface.save_window_size((new_width, new_height))

    def resizeEvent(self, event):
        self.windowResized.emit()
        self._resize_timer.start(50)
        if not self.isActiveWindow() or not self.underMouse():
            self.apply_locked_ratio(event)
        super().resizeEvent(event)

    def initLayout(self):
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addWidget(self.stackWidget)
        self.hBoxLayout.setStretchFactor(self.stackWidget, 1)

    def initNavigation(self):
        # self.navigationInterface.setAcrylicEnabled(True)

        self.addSubInterface(self.MainInterface, FIF.HOME, self.tr("Home"))

        self.navigationInterface.addSeparator()

        # self.addSubInterface(self.sessions, FIF.ALBUM,
        #                      self.tr("SSH session"), NavigationItemPosition.SCROLL)

        self.addSubInterface(self.ssh_page, FIF.ALBUM, self.tr("SSH Session"))

        self.navigationInterface.addWidget(
            routeKey='sync',
            widget=NavigationAvatarWidget(
                'Sync', resource_path('resource/icons/sync.svg')),
            onClick=lambda: self.sycn_widget.exec_(),
            position=NavigationItemPosition.BOTTOM,
        )

        self.navigationInterface.addWidget(
            routeKey='about',
            widget=NavigationAvatarWidget(
                'Github', resource_path('resource/icons/github.svg')),
            onClick=self._open_github,
            position=NavigationItemPosition.BOTTOM,
        )

        self.addSubInterface(self.settingInterface, FIF.SETTING,
                             self.tr("Setting"), NavigationItemPosition.BOTTOM)
        self.stackWidget.currentChanged.connect(self.onCurrentInterfaceChanged)
        self.stackWidget.setCurrentIndex(0)

    def _open_github(self):
        github_url = QUrl("https://github.com/Heartestrella/P-SSH")
        QDesktopServices.openUrl(github_url)

    def initWindow(self):
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

        self.setQss()

    def _handle_action(self, action, name):
        if action == "close":
            self.remove_interface(name)
        elif action == "copy":
            self._on_session_selected(session_name=name)

    def remove_interface(self, widget_name):
        try:
            self.ssh_page.remove_session(widget_name)
            widget = self.session_widgets[widget_name]
            widget.cleanup()
            self.session_widgets.pop(widget_name, None)
            widget.deleteLater()
            worker = self.ssh_session.pop(widget_name, None)
            worker_processes = self.ssh_session.pop(
                f'{widget_name}-processes', None)
            watching_dogs = self.watching_dogs.pop(widget_name, None)
            if worker:
                worker.close()
            if worker_processes:
                worker_processes.close()
            file_manager = self.file_tree_object.pop(widget_name, None)
            if file_manager:
                file_manager._cleanup()
            file_manager_handler = self.file_tree_object.pop(
                f"{widget_name}-handler", None)
            if file_manager_handler:
                file_manager_handler.cleanup()
            if watching_dogs:
                for dog in watching_dogs:
                    dog.stop()
        except Exception as e:
            InfoBar.error(
                title=self.tr('Error closing session!'),
                content=self.tr(f'''Error details:\n{e}'''),
                orient=Qt.Vertical,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=-1,
                parent=self
            )

    def addSubInterface(self, interface, icon, text: str, position=NavigationItemPosition.TOP, parent=None):
        """ Add a page """
        self.stackWidget.addWidget(interface)
        self.navigationInterface.addItem(
            routeKey=interface.objectName(),
            icon=icon,
            text=text,
            onClick=lambda: self.switchTo(interface),
            position=position,
            tooltip=text,
            parentRouteKey=parent.objectName() if parent else None
        )

    def setQss(self):
        color = 'dark' if isDarkTheme() else 'light'
        with open(resource_path(f'resource/{color}/demo.qss'), encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def switchTo(self, widget, window_tittle=None):
        self.stackWidget.setCurrentWidget(widget)
        if window_tittle:
            self.setWindowTitle(window_tittle)
        elif widget.objectName():
            self.setWindowTitle(widget.objectName())

    def onCurrentInterfaceChanged(self, index):
        widget = self.stackWidget.widget(index)
        self.navigationInterface.setCurrentItem(widget.objectName())

    def _handle_upload_request(self, widget_key, local_path, remote_path, compression, file_manager):
        """Pre-handles upload requests to determine if UI items should be pre-created."""
        # If compression is on and we have a list, create a single UI item for the batch.
        if compression and isinstance(local_path, list):
            task_id = f"compress_upload_{time.time()}"
            self._add_transfer_item_if_not_exists(
                widget_key, local_path, 'upload', task_id=task_id)
            file_manager.upload_file(
                local_path, remote_path, compression, task_id=task_id)
            return

        # Original logic for other cases (single files, non-compressed lists/dirs)
        paths = local_path if isinstance(local_path, list) else [local_path]
        print(f"Paths Len : {len(paths)}")
        for p in paths:
            # For non-compressed dirs, we don't create items here.
            # They will be created dynamically on first progress/finished signal.
            if not (os.path.isdir(p) and not compression):
                self._add_transfer_item_if_not_exists(
                    widget_key, p, 'upload')
            file_manager.upload_file(p, remote_path, compression)

    def _add_transfer_item_if_not_exists(self, widget_key, path, transfer_type, task_id=None):
        """Helper to add a transfer item to the UI if it doesn't exist."""
        print(f"{type(path)} {path}")
        session_widget = self.session_widgets[widget_key]
        if not session_widget:
            return

        # The unique identifier for a task is now the full path for single files,
        # or the string representation of the list for compressed batches.
        task_identifier = task_id if task_id else (
            str(path) if isinstance(path, list) else path)

        if task_identifier in self.active_transfers:
            return  # Avoid creating duplicate entries

        # Create a truly unique ID for the UI widget
        file_id = f"{widget_key}_{task_identifier}_{time.time()}"

        if isinstance(path, list) and transfer_type == 'upload':
            # Special handling for compressed list uploads
            file_name = "Compressing..."
        elif isinstance(path, list):
            count = len(path)
            if count == 0:
                return
            file_name = f"{os.path.basename(path[0][0])}"
            if count > 1:
                file_name += f" and {count - 1} others"
        else:
            file_name = os.path.basename(path)

        data = {
            "id": file_id,  # The unique ID for the widget
            "type": transfer_type,
            "filename": file_name,
            "progress": 0
        }

        # Use the task_identifier as the key in our tracking dictionary
        self.active_transfers[task_identifier] = data
        session_widget.transfer_progress.add_transfer_item(file_id, data)

    def _handle_transfer_cancellation(self, file_id, widget_key):
        # import inspect
        # caller_frame = inspect.stack()[1]
        # caller_filename = caller_frame.filename
        # caller_line_no = caller_frame.lineno
        # caller_func_name = caller_frame.function
        # print(
        #     f"Called from {caller_func_name} in {caller_filename}:{caller_line_no}")

        file_manager = self.file_tree_object.get(widget_key)
        if not file_manager:
            return

        # Find the original identifier for the task
        task_identifier = None
        for identifier, data in self.active_transfers.items():
            if data.get("id") == file_id:
                task_identifier = identifier
                break

        if task_identifier:
            # Tell the file manager to cancel the backend worker
            file_manager.cancel_transfer(task_identifier)

            # Remove from UI and tracking dictionary
            session_widget = self.session_widgets[widget_key]
            if session_widget:
                session_widget.transfer_progress.remove_transfer_item(file_id)

            self.active_transfers.pop(task_identifier, None)

    def remove_nav_edge(self):
        self.navigationInterface.setStyleSheet("""
            NavigationInterface {
                background-color: transparent;
                border: none;
            }
            NavigationInterface > QWidget {
                background-color: transparent;
            }
        """)

    def _update_transfer_item_name(self, identifier, new_name, widget_key):
        session_widget = self.session_widgets[widget_key]
        if not session_widget:
            return

        if identifier in self.active_transfers:
            file_id = self.active_transfers[identifier]["id"]
            self.active_transfers[identifier]["filename"] = new_name
            data = self.active_transfers[identifier]
            session_widget.transfer_progress.update_transfer_item(
                file_id, data)

    def set_ssh_session_text_color(self, color: str):
        try:
            for _, value_ in self.session_widgets.items():
                for key, value_1 in value_.items():
                    if key != "widget":
                        print(value_1)
                        if not value_1.parent_state:
                            value_1.ssh_widget.set_colors(text_color=color)
                            value_1.task.set_text_color(color)
        except Exception as e:
            print(f"Setting font color failed:{e}")

    def _on_theme_changed(self, value):
        if value == "Light":
            setTheme(Theme.LIGHT)
        elif value == "Dark":
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.AUTO)

        self.setQss()

        for i in range(self.stackWidget.count()):
            w = self.stackWidget.widget(i)
            if hasattr(w, 'widget') and isinstance(w.widget, QWidget):
                w.widget.update()
            else:
                w.update()

    def clear_global_background(self):
        self._bg_pixmap = None
        self._bg_opacity = 1.0
        self.update()

        self.navigationInterface.setStyleSheet("")

    def set_global_background(self, image_path: str):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"Invalid image path: {image_path}")
            return
        self._bg_pixmap = pixmap
        self._bg_ratio = pixmap.width() / pixmap.height()
        self._bg_opacity = 1.0
        self.update()
        self.remove_nav_edge()

    def paintEvent(self, event):
        if self._bg_pixmap:
            painter = QPainter(self)
            painter.setOpacity(self._bg_opacity)
            painter.drawPixmap(self.rect(), self._bg_pixmap)
        super().paintEvent(event)

    def _set_language(self, lang_code: str):
        translator = QTranslator()
        if lang_code == "system":
            system_locale = QLocale.system().name()
            if translator.load(f"resource/i18n/pssh_{system_locale}.qm"):
                QApplication.instance().installTranslator(translator)
            else:
                print("Translation file loading failed")
        else:
            if translator.load(f"resource/i18n/pssh_{lang_code}.qm"):
                QApplication.instance().installTranslator(translator)
            else:
                print("Translation file loading failed")
        self.settingInterface.retranslateUi()
        self.MainInterface.retranslateUi()
        for _, value_ in self.session_widgets.items():
            for key, value_1 in value_.items():
                if key != "widget":
                    value_1.retranslateUi()

    def changeEvent(self, event):
        # Get the maximized and minimized state
        if event.type() == QEvent.WindowStateChange:
            if self.isMaximized():
                setting_.revise_config("maximized", True)
            else:
                setting_.revise_config("maximized", False)
        super().changeEvent(event)


def language_code_to_locale(code: str) -> str:
    """
    EN -> en_US
    CN -> zh_CN
    JP -> ja_JP
    RU -> ru_RU
    system -> 
    """
    mapping = {
        "EN": "en_US",
        "CN": "zh_CN",
        "JP": "ja_JP",
        "RU": "ru_RU",
    }

    code = code.upper().strip()

    if code == "SYSTEM":
        return QLocale.system().name()

    return mapping.get(code, "en_US")


def enable_hardware_acceleration():

    try:
        from PyQt5.QtGui import QOpenGLContext, QSurfaceFormat
        format = QSurfaceFormat.defaultFormat()
        print(f"默认 OpenGL 格式: {format.version()}, Profile: {format.profile()}")

        # 强制启用 OpenGL 2.0+
        if format.majorVersion() < 2:
            format.setVersion(2, 0)
            format.setProfile(QSurfaceFormat.CoreProfile)
            QSurfaceFormat.setDefaultFormat(format)
            print("🔧 强制设置 OpenGL 2.0+")

    except Exception as gl_error:
        print(f"⚠️  OpenGL 配置警告: {gl_error}")

    # 3. 打印硬件信息
    print(f"🖥️  系统平台: {sys.platform}")
    print(f"💻  Python 版本: {sys.version}")
    # print(
    #     f"🖼️  Qt 版本: {QLibraryInfo.libraryLocation(QLibraryInfo.LibraryLocation.PrefixPath)}")

    # 4. 检测 GPU 驱动
    try:
        import platform
        if platform.system() == "Windows":
            # Windows GPU 信息
            import subprocess
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=name',
                        '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    print(f"🎮  NVIDIA GPU: {result.stdout.strip()}")
                else:
                    print("📱  使用集成显卡或无 NVIDIA GPU")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print("📱  无 NVIDIA GPU 或驱动未安装")
    except ImportError:
        pass


if __name__ == '__main__':
    try:
        print("🚀 启动硬件加速配置...")
        enable_hardware_acceleration()

        # 1. 配置管理器
        configer = SCM()

        # 2. 设置日志
        setup_global_logging()
        main_logger.info("Application Startup with Hardware Acceleration")

        # 3. Qt 高 DPI 和硬件加速属性（在 QApplication 之前设置）
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

        # 硬件加速相关属性
        # 禁用 OpenGLES，优先使用 OpenGL
        QApplication.setAttribute(Qt.AA_UseOpenGLES, False)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseDesktopOpenGL, True)  # 使用桌面 OpenGL
        # QApplication.setAttribute(
        #     Qt.AA_CompositingBackgroundEnabled, True)  # 合成背景
        QApplication.setAttribute(
            Qt.AA_DontCreateNativeWidgetSiblings, True)  # 优化窗口管理

        # 4. 创建 QApplication
        app = QApplication(sys.argv)

        # 5. 设置应用图标和 ID
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "su8aru.remmotessh.1.0.0")
            main_logger.info("✅ Windows 应用 ID 设置成功")
        except Exception as icon_error:
            main_logger.warning(f"⚠️  应用 ID 设置失败: {icon_error}")

        # 6. 读取配置
        config = configer.read_config()
        lang = language_code_to_locale(config.get("language", "system"))
        main_logger.info(f"🌐  语言设置: {lang}")

        # 7. 加载翻译
        translator = QTranslator()
        translator_1 = FluentTranslator()

        if lang == "en_US":
            main_logger.info("使用英语界面")
        elif translator.load(resource_path(f"resource/i18n/pssh_{lang}.qm")):
            app.installTranslator(translator)
            main_logger.info(f"✅ 翻译文件加载成功: {lang}")
        else:
            main_logger.warning(f"⚠️  翻译文件加载失败: {lang}")
            print("Translation file loading failed")

        app.installTranslator(translator_1)

        # 8. 剪贴板初始化
        clipboard = app.clipboard()
        main_logger.info("📋 剪贴板初始化完成")

        # 9. 创建并显示主窗口
        w = Window()
        w.show()
        main_logger.info("🖥️  主窗口显示成功")

        # 10. 启动应用
        main_logger.info("🎯 应用启动成功，进入事件循环")
        app.exec_()
    except Exception as e:
        main_logger.critical("Application startup failure", exc_info=True)
