# coding:utf-8
import ast
import sys
import ctypes
from PyQt5.QtCore import Qt, QTranslator, QTimer, QLocale, QUrl
from PyQt5.QtGui import QPixmap, QPainter, QDesktopServices, QIcon
from PyQt5.QtWidgets import QApplication, QStackedWidget, QHBoxLayout, QWidget

from qfluentwidgets import (NavigationInterface, NavigationItemPosition, InfoBar,
                            isDarkTheme, setTheme, Theme, InfoBarPosition, FluentIcon as FIF, FluentTranslator, NavigationAvatarWidget)
from qframelesswindow import FramelessWindow, StandardTitleBar
from widgets.setting_page import SettingPage
from widgets.home_interface import MainInterface
from tools.font_config import font_config
from tools.session_manager import SessionManager
from tools.logger import setup_global_logging, main_logger
from widgets.ssh_widget import Widget
from tools.ssh import SSHWorker
from tools.icons import My_Icons
from tools.remote_file_manage import RemoteFileManager
from tools.setting_config import SCM
from widgets.sync_widget import SycnWidget
import os
import subprocess
from tools.atool import resource_path
from widgets.transfer_progress_widget import TransferProgressWidget
font_ = font_config()


class Window(FramelessWindow):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.active_transfers = {}
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.apply_locked_ratio)
        self.icons = My_Icons()
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
        self.sessions = Widget(
            self.tr('No conversation selected yet'), True, self)

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

    def _set_usage(self, child_key, usage):
        try:
            result = dict(usage)
            parent_key = child_key.split("-", 1)[0].strip()
            # print(self.session_widgets)
            # print(parent_key)
            widget = self.session_widgets[parent_key][child_key]
            if widget:
                cpu_percent = result["cpu_percent"]
                mem_percent = result["mem_percent"]
                widget.sys_resources.set_progress("cpu", cpu_percent)
                widget.sys_resources.set_progress("ram", mem_percent)
                for processes in result["top_processes"]:
                    processes_cpu_percent = processes["cpu"]
                    processes_name = processes["name"]
                    processes_mem = processes["mem"]
                    widget.task.add_row(
                        f"{processes_mem:.1f}",
                        f"{processes_cpu_percent:.1f}",
                        processes_name
                    )

                    # print(processes_cpu_percent, processes_name, processes_mem)
            else:
                print("Failed to obtain the SSH Widget")
        except Exception as e:
            print(e)

    def _show_info(self, path: str = None, status: bool = None, msg: str = None, type_: str = None, child_key: str = None, local_path: str = None, open_it: bool = False):
        no_refresh_types = ["download", "start_upload", "start_download", "info"]

        parent_key = child_key.split("-")[0].strip()
        session_widget = self.session_widgets.get(parent_key, {}).get(child_key)
        if not session_widget:
            return

        if type_ == "upload":
            paths = path if isinstance(path, list) else [path]
            for p in paths:
                file_id = f"{child_key}_{os.path.basename(p)}"
                if status:
                    self.active_transfers[file_id] = {
                        "type": "completed",
                        "filename": os.path.basename(p),
                        "progress": 100
                    }
                else:
                    if file_id in self.active_transfers:
                        del self.active_transfers[file_id]
            session_widget.transfer_progress.update_transfers(self.active_transfers)

        elif type_ == "start_upload":
            paths = local_path if isinstance(local_path, list) else [local_path]
            for p in paths:
                file_id = f"{child_key}_{os.path.basename(p)}"
                self.active_transfers[file_id] = {
                    "type": "upload",
                    "filename": os.path.basename(p),
                    "progress": 0
                }
            session_widget.transfer_progress.update_transfers(self.active_transfers)

        elif type_ == "start_download":
            paths = path if isinstance(path, list) else [path]
            for p in paths:
                file_id = f"{child_key}_{os.path.basename(p)}"
                self.active_transfers[file_id] = {
                    "type": "download",
                    "filename": os.path.basename(p),
                    "progress": 0
                }
            session_widget.transfer_progress.update_transfers(self.active_transfers)

        elif type_ == "download":
            paths = path if isinstance(path, list) else [path]
            for p in paths:
                file_id = f"{child_key}_{os.path.basename(p)}"
                if status:
                    self.active_transfers[file_id] = {
                        "type": "completed",
                        "filename": os.path.basename(p),
                        "progress": 100
                    }
                    if open_it:
                        if sys.platform.startswith('darwin'):
                            subprocess.call(('open', local_path), start_new_session=True)
                        elif os.name == 'nt':
                            os.startfile(local_path)
                        elif os.name == 'posix':
                            subprocess.call(('xdg-open', local_path))
                else:
                    if file_id in self.active_transfers:
                        del self.active_transfers[file_id]
            session_widget.transfer_progress.update_transfers(self.active_transfers)

        else:
            duration = 5000
            title = ""
            if type_ in ("compression", "uncompression"):
                title = self.tr(f"Start to {type_} : {path}")
                msg = ""
            elif type_ == "delete":
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
                    title = self.tr(f"Failed to create directory {path}\n{msg}")
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

        if type_ not in no_refresh_types and child_key:
            self._refresh_paths(child_key)

    def _show_progresses(self, paths, percentage, child_key):
        try:
            lst = ast.literal_eval(paths)
            if not isinstance(lst, list):
                lst = [lst]
        except (ValueError, SyntaxError):
            lst = [paths]

        parent_key = child_key.split("-")[0].strip()
        session_widget = self.session_widgets.get(parent_key, {}).get(child_key)
        if not session_widget:
            return

        for path in lst:
            file_name = os.path.basename(path)
            file_id = f"{child_key}_{file_name}"
            if file_id in self.active_transfers:
                self.active_transfers[file_id]["progress"] = percentage
        
        session_widget.transfer_progress.update_transfers(self.active_transfers)

    def _start_ssh_connect(self, session, child_key):

        parent_key = child_key.split("-")[0].strip()
        session_widget = self.session_widgets[parent_key][child_key]
        processes = SSHWorker(session, for_resources=True)
        self.ssh_session[f'{child_key}-processes'] = processes
        processes.sys_resource.connect(
            lambda usage, key=child_key: self._set_usage(key, usage))
        processes.start()

        file_manager = RemoteFileManager(session)
        file_manager.file_tree_updated.connect(
            lambda file_tree, path, sw=session_widget: self.on_file_tree_updated(
                file_tree, sw, path)
        )

        file_manager.error_occurred.connect(
            self.on_file_manager_error)
        file_manager.delete_finished.connect(lambda path, status, msg:
                                             self._show_info(path, status, msg, "delete", child_key))
        file_manager.upload_finished.connect(lambda path, status, msg:
                                             self._show_info(path, status, msg, "upload", child_key))
        file_manager.download_finished.connect(lambda remote_path, local_path, status, error_msg, open_it:
                                               self._show_info(remote_path, status, error_msg, "download", child_key, local_path=local_path, open_it=open_it))
        file_manager.copy_finished.connect(lambda source_path, target_path, status, error_msg:
                                           self._show_info(source_path, status, error_msg, "paste", child_key, target_path))
        file_manager.rename_finished.connect(lambda source_path, new_path, status, error_msg: self._show_info(
            path=source_path, status=status, msg=error_msg, local_path=new_path, type_="rename", child_key=child_key
        ))
        file_manager.file_type_ready.connect(
            lambda path, type_: self._open_server_files(path, type_, child_key))
        file_manager.file_info_ready.connect(
            lambda path, info, status, error_msg: self._show_info(path=path, status=status, child_key=child_key, msg=error_msg, type_="info", local_path=info))
        file_manager.mkdir_finished.connect(lambda path, status, msg: self._show_info(
            path=path, status=status, msg=msg, type_="mkdir", child_key=child_key
        ))
        file_manager.start_to_compression.connect(
            lambda path: self._show_info(path=path, type_="compression"))
        file_manager.start_to_compression.connect(
            lambda path: self._show_info(path=path, type_="uncompression"))
        file_manager.upload_progress.connect(
            lambda path, percentage: self._show_progresses(path, percentage, child_key=child_key))
        session_widget.file_explorer.upload_file.connect(
            lambda path, target_path, compression: self._show_info(type_="start_upload", child_key=child_key, local_path=path, path=target_path)
        )
        session_widget.file_explorer.upload_file.connect(
            file_manager.upload_file)

        def on_sftp_ready():
            global home_path
            home_path = file_manager.get_default_path()
            path_list = self.parse_linux_path(home_path)
            # print(f"home_path : {home_path}\npath_list : {path_list}")
            _count = 0
            session_widget.file_bar.send_signal = False
            for path in path_list:
                _count += 1
                if _count == len(path_list):
                    session_widget.file_bar.send_signal = True
                session_widget.file_bar.breadcrumbBar.addItem(
                    path, path)

                # session_widget.ssh_widget.bridge.home_path = home_path
            session_widget.file_explorer.path = home_path
            file_manager.add_path(home_path)
            file_manager.path_check_result.connect(
                lambda path, result: self._update_file_tree_branch_when_cd(path, child_key), Qt.QueuedConnection)
        file_manager.sftp_ready.connect(on_sftp_ready)
        file_manager.start()
        self.file_tree_object[child_key] = file_manager

        worker = SSHWorker(session, for_resources=False)
        self.ssh_session[child_key] = worker

        worker.connected.connect(
            lambda success, msg: self._on_ssh_connected(success, msg))
        worker.error_occurred.connect(lambda e: self._on_ssh_error(e))

        try:

            child_widget = self.session_widgets[parent_key][child_key]
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
            lambda checked, ck=child_key: self._refresh_paths(ck)
        )

    def _open_server_files(self, path: str, type_: str, child_key: str):
        file_manager: RemoteFileManager = self.file_tree_object[child_key]
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

    def _handle_files(self, action_type, full_path, copy_to, cut, child_key):
        file_manager: RemoteFileManager = self.file_tree_object[child_key]
        if action_type == "delete":
            file_manager.delete_path(full_path)
        elif action_type == "copy_path":
            paths_to_copy = full_path if isinstance(
                full_path, list) else [full_path]
            clipboard.setText('\n'.join(paths_to_copy))
        elif action_type == "download":
            paths_to_download = full_path if isinstance(
                full_path, list) else [full_path]
            if not cut:
                for path in paths_to_download:
                    self._show_info(path=path, child_key=child_key,
                                    type_="start_download")
                    file_manager.download_path_async(path, compression=cut)
                    print("执行非压缩下载")
            else:
                self._show_info(path=paths_to_download, child_key=child_key,
                                type_="start_download")
                file_manager.download_path_async(
                    paths_to_download, compression=cut)
                print("执行压缩下载")
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

    def _refresh_paths(self, child_key: str):
        print("Refresh the page")
        parent_key = child_key.split("-")[0].strip()
        session_widget: Widget = self.session_widgets[parent_key][child_key]
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

    def _update_file_tree_branch_when_cd(self, path: str, child_key: str):
        file_manager: RemoteFileManager = self.file_tree_object[child_key]
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

    def _on_session_selected(self, session_id=None, parent_key=None):
        """Handling session selection"""
        # self.MainInterface.card_dict[session_id].set_connect_status(True)
        if session_id:
            session = self.sessionmanager.get_session(session_id=session_id)
        elif parent_key:
            session = self.sessionmanager.get_session_by_name(parent_key)
        if not parent_key:
            parent_key = session.name
        if parent_key not in self.session_widgets:
            # Create a parent widget
            print(f"partent_key: {parent_key}")
            parent_widget = Widget(parent_key, True, self,)
            parent_widget.setObjectName(parent_key)
            self.addSubInterface(
                parent_widget, FIF.ALBUM, parent_key, parent=self.sessions
            )
            self.session_widgets[parent_key] = {}
            self.session_widgets[parent_key]["widget"] = parent_widget
        else:
            parent_widget = self.session_widgets[parent_key]["widget"]

        child_number = 1
        for key in self.session_widgets[parent_key].keys():
            if key.startswith(f"{parent_key} - "):
                try:
                    existing_num = int(key.split(" - ")[-1])
                    child_number = max(child_number, existing_num + 1)
                except ValueError:
                    continue

        child_key = f"{parent_key} - {child_number}"
        font_name, font_size = font_.read_font()
        child_widget = Widget(child_key, False, self,
                              font_name=font_name, user_name=session.username)
        # Add to parent
        child_widget.file_explorer.file_action.connect(
            lambda action_type, full_path, copy_to, cut: self._handle_files(action_type, full_path, copy_to, cut, child_key))
        child_widget.disk_storage.directory_selected.connect(
            lambda path: self._update_file_tree_branch_when_cd(path, child_key))
        self.addSubInterface(
            child_widget, FIF.ALBUM, child_key, parent=parent_widget,
        )

        self.session_widgets[parent_key][child_key] = child_widget
        self.switchTo(widget=child_widget, window_tittle=child_key)
        print(f"Creating a Child Session: {child_key} (Parent: {parent_key})")
        print(session, child_key)
        self._start_ssh_connect(session, child_key)

    def apply_locked_ratio(self, event=None):
        new_width, new_height = 0, 0
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

        self.addSubInterface(self.sessions, FIF.ALBUM,
                             self.tr("SSH session"), NavigationItemPosition.SCROLL)

        self.addSubInterface(self.sycn_widget, FIF.SYNC, self.tr(
            "Sync"), NavigationItemPosition.BOTTOM)

        self.navigationInterface.addWidget(
            routeKey='about',
            widget=NavigationAvatarWidget(
                'su8aru', resource_path('resource/icons/avatar.jpg')),
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

    # I cant del the widget's parent widget on remove_sub_interface!!!

    def remove_sub_interface(self, widget=None, close_sub_all: bool = False, parent_id: str = None):

        # Only for main interface.SSHCARD close all sub interface
        # close_sub_all Must be true!!!
        remove_keys = []
        try:
            if parent_id:
                parent = parent_id
            else:
                widget_name = widget.objectName()
                parent = widget_name.split("-")[0].strip()
            if close_sub_all == True:
                # remove and close widget
                for widget_name in self.session_widgets[parent].keys():
                    if widget_name != "widget":
                        self.navigationInterface.removeWidget(
                            routeKey=widget_name)
                        remove_keys.append(widget_name)
                for widget_name in remove_keys:
                    ssh_widget = self.session_widgets[parent].pop(
                        widget_name, None)
                    if ssh_widget:
                        ssh_widget._cleanup()
                # remove and close ssh
                keys_to_remove = [
                    key for key in self.ssh_session if key.startswith(parent)]

                for key in keys_to_remove:
                    worker = self.ssh_session.pop(key, None)
                    if worker:
                        worker.close()

                keys_to_remove_files = [
                    key for key, value in self.file_tree_object.items() if key.startswith(parent)]
                for key in keys_to_remove_files:
                    file_manager = self.file_tree_object.pop(key, None)
                    if file_manager:
                        file_manager._cleanup()
                # for key, ssh_session in self.ssh_session.items():
                #     if key.startswith(parent):
                #         remove_ssh_sessions[key] = ssh_session
                # for key, ssh_session in remove_ssh_sessions.items():
                #     self.ssh_session.pop(key, None)
                #     ssh_session.close()

            else:
                self.navigationInterface.removeWidget(routeKey=widget_name)
                ssh_widget = self.session_widgets[parent].pop(
                    widget_name, None)
                if ssh_widget:
                    ssh_widget._cleanup()
                worker = self.ssh_session.pop(widget_name, None)
                worker_processes = self.ssh_session.pop(
                    f'{widget_name}-processes', None)
                if worker:
                    worker.close()
                if worker_processes:
                    worker_processes.close()
                file_manager = self.file_tree_object.pop(widget_name, None)
                if file_manager:
                    file_manager._cleanup()
            print(f"After close {self.ssh_session} {self.file_tree_object}")
            if not parent_id:
                self.switchTo(self.session_widgets[parent]["widget"])
            close_count = 1 if len(remove_keys) == 0 else len(remove_keys)
            InfoBar.success(
                title=self.tr('Session closed successfully!'),
                content=self.tr(
                    f'Closed {close_count} sessions under "{parent}"'),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
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


if __name__ == '__main__':
    try:
        configer = SCM()

        setup_global_logging()
        main_logger.info("Application Startup")
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

        QApplication.setAttribute(Qt.AA_UseOpenGLES)
        app = QApplication(sys.argv)

        # set icon
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "su8aru.remmotessh.1.0.0")

        config = configer.read_config()
        lang = language_code_to_locale(config.get("language", "system"))

        # print(f"Language setting: {lang}")
        translator = QTranslator()
        translator_1 = FluentTranslator()
        if lang == "en_US":
            pass
        elif translator.load(resource_path(f"resource/i18n/pssh_{lang}.qm")):
            app.installTranslator(translator)
        else:
            print("Translation file loading failed")
        app.installTranslator(translator_1)
        clipboard = app.clipboard()
        w = Window()
        w.show()
        app.exec_()
    except Exception as e:
        main_logger.critical("Application startup failure", exc_info=True)
