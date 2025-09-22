from PyQt5.QtWidgets import (
    QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QSizePolicy, QSplitter
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QPainterPath

from qfluentwidgets import SegmentedWidget, RoundMenu, Action, FluentIcon as FIF, ToolButton

from tools.setting_config import SCM
from tools.ssh_webterm import WebTerminal
from widgets.network_detaile import NetProcessMonitor
from widgets.system_resources_widget import ProcessTable
from widgets.task_widget import Tasks
from widgets.file_tree_widget import File_Navigation_Bar, FileTreeWidget
from widgets.files_widgets import FileExplorer
from widgets.transfer_progress_widget import TransferProgressWidget
from widgets.command_input import CommandInput
from tools.session_manager import SessionManager

CONFIGER = SCM()
session_manager = SessionManager()


class SSHPage(QWidget):
    # 定义信号：action 名称, session 名称
    menuActionTriggered = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(10, 10, 10, 10)
        self.vbox.setSpacing(5)

        # 上半部分：SSH 导航栏
        self.pivot = SegmentedWidget(self)
        self.vbox.addWidget(self.pivot, 0)

        # 下半部分：SSH 主窗口
        self.sshStack = QStackedWidget(self)
        self.vbox.addWidget(self.sshStack, 1)

        # 切换逻辑
        self.pivot.currentItemChanged.connect(
            lambda k: self.sshStack.setCurrentWidget(
                self.findChild(QWidget, k))
        )

        # 设置右键菜单策略
        self.pivot.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pivot.customContextMenuRequested.connect(self.show_context_menu)

    def add_session(self, object_name: str, text: str, widget: QWidget):
        widget.setObjectName(object_name)
        if isinstance(widget, QLabel):
            widget.setAlignment(Qt.AlignCenter)

        self.sshStack.addWidget(widget)
        self.pivot.addItem(routeKey=object_name, text=text)
        QTimer.singleShot(0, lambda: self.pivot.setCurrentItem(object_name))
        self.sshStack.setCurrentWidget(widget)

    def get_current_route_key(self):
        """返回当前选中 tab 的 routeKey"""
        current_item = self.pivot.currentItem()
        if not current_item:
            return None
        for key, item in self.pivot.items.items():
            if item == current_item:
                return key
        return None

    def remove_session(self, routeKey: str):
        """删除指定的 session"""
        if routeKey not in self.pivot.items:
            return

        # 1. 如果删除的是当前选中的 tab，先切换到其他 tab
        if self.pivot.currentItem() == self.pivot.items[routeKey]:
            remaining_keys = [k for k in self.pivot.items if k != routeKey]
            if remaining_keys:
                self.pivot.setCurrentItem(remaining_keys[0])
                self.sshStack.setCurrentWidget(
                    self.findChild(QWidget, remaining_keys[0])
                )
            else:
                # 没有剩余 tab，清空当前 routeKey
                self.pivot._currentRouteKey = None

        # 2. 从 pivot 上移除 tab
        item = self.pivot.items.pop(routeKey)
        item.setParent(None)
        item.deleteLater()

        # 3. 从 stacked widget 中移除对应页面
        widget_to_remove = self.findChild(QWidget, routeKey)
        if widget_to_remove:
            self.sshStack.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)
            widget_to_remove.deleteLater()

    def show_context_menu(self, pos: QPoint):
        """在 pivot 上显示右键菜单，同时切换到鼠标所在的 tab"""
        # 找到鼠标点击的子控件
        child = self.pivot.childAt(pos)
        if not child:
            return

        route_key = None
        for key, item in self.pivot.items.items():  # items 是字典
            if item == child or item.isAncestorOf(child):
                route_key = key
                break

        # Switch to the tab where the right-click is located
        self.pivot.setCurrentItem(route_key)
        session_name = self.pivot.currentItem().text()
        # print(session_name)

        menu = RoundMenu(title="", parent=self)
        close_action = Action(self.tr("Close Session"))
        duplicate_action = Action(self.tr("Duplicate Session"))

        close_action.triggered.connect(
            lambda: self.menuActionTriggered.emit(
                "close", session_name)
        )
        duplicate_action.triggered.connect(
            lambda: self.menuActionTriggered.emit(
                "copy", session_name)
        )

        menu.addAction(close_action)
        menu.addAction(duplicate_action)

        global_pos = self.pivot.mapToGlobal(pos)
        menu.exec(global_pos)


class SSHWidget(QWidget):

    def __init__(self, name: str,  parent=None, font_name=None, user_name=None):
        super().__init__(parent=parent)
        self.file_manager = None
        self.setObjectName(name)
        self.router = name
        self.parentkey = name.split('-')[0].strip()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        config = CONFIGER.read_config()

        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        # --- Left Widget ---
        leftContainer = QFrame(self)
        leftContainer.setObjectName("leftContainer")
        leftContainer.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Expanding)

        leftLayout = QVBoxLayout(leftContainer)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setSpacing(0)

        # sys_resources
        self.sys_resources = ProcessTable(leftContainer)
        self.sys_resources.setObjectName("sys_resources")
        self.sys_resources.setMinimumHeight(80)
        self.sys_resources.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.sys_resources.setStyleSheet("""
            QFrame#sys_resources {
                background-color: rgba(200, 200, 200, 0.12);
                border: 1px solid rgba(0,0,0,0.12);
                border-radius: 6px;
            }
        """)

        # Task
        self.task = Tasks(leftContainer)
        self.task.set_text_color(config["ssh_widget_text_color"])
        self.task.setObjectName("task")
        self.task.setMinimumHeight(80)
        self.task.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.task.setStyleSheet("""
            QFrame#task {
                background-color: rgba(220, 220, 220, 0.06);
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 6px;
            }
        """)

        # disk_storage
        self.disk_storage = FileTreeWidget(leftContainer)
        self.disk_storage.directory_selected.connect(self._set_file_bar)
        self.disk_storage.setObjectName("disk_storage")
        self.disk_storage.setMinimumHeight(80)
        self.disk_storage.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)
        # self.disk_storage.directory_selected.connect(self._set_file_bar)
        self.disk_storage.setStyleSheet("""
            QFrame#disk_storage {
                background-color: rgba(220, 220, 220, 0.06);
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 6px;
            }
        """)
        # Transfer Progress Widget
        self.transfer_progress = TransferProgressWidget(leftContainer)
        self.transfer_progress.setObjectName("transfer_progress")
        self.transfer_progress.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)

        leftLayout.addWidget(self.sys_resources, 15)
        leftLayout.addWidget(self.task, 40)
        leftLayout.addWidget(self.disk_storage, 45)

        # Initially, no stretch
        leftLayout.addWidget(self.transfer_progress, 0)

        # --- Right Widgets
        rightContainer = QFrame(self)
        rightContainer.setObjectName("rightContainer")
        rightContainer.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        rightLayout = QVBoxLayout(rightContainer)
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.setSpacing(0)
        rsplitter = QSplitter(Qt.Vertical, rightContainer)
        rsplitter.setChildrenCollapsible(False)
        rsplitter.setHandleWidth(2)
        rsplitter.setStyleSheet("""
                QSplitter::handle:vertical {
                    background-color: #cccccc;
                    height: 1px;
                    margin: 0px;
                }
                QSplitter::handle:vertical:hover {
                    background-color: #999999;
                }
            """)
        # Top container for ssh_widget and command_bar
        top_container = QFrame(rsplitter)
        top_container_layout = QVBoxLayout(top_container)
        top_container_layout.setContentsMargins(0, 0, 0, 0)
        top_container_layout.setSpacing(0)

        # ssh_widget
        self.ssh_widget = WebTerminal(
            top_container,
            font_name=font_name,
            user_name=user_name,
            text_color=config["ssh_widget_text_color"]
        )
        self.ssh_widget.directoryChanged.connect(self._set_file_bar)
        self.ssh_widget.setObjectName("ssh_widget")
        self.ssh_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ssh_widget.setStyleSheet("""
            QFrame#ssh_widget {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(0,0,0,0.04);
                border-radius: 6px;
            }
        """)

        # command input bar
        self.command_bar = QFrame(top_container)
        self.command_bar.setObjectName("command_bar")
        # self.command_bar.setFixedHeight(42) # Remove fixed height

        self.command_bar.setStyleSheet("""
            QFrame#command_bar {
                background-color: rgba(30, 30, 30, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QFrame#command_bar:focus-within {
                border: 1px solid rgba(0, 122, 255, 0.7);
            }
            ToolButton {
                background-color: transparent;
                border-radius: 4px;
            }
            ToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            ToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        command_bar_layout = QHBoxLayout(self.command_bar)
        command_bar_layout.setContentsMargins(8, 5, 8, 5)
        command_bar_layout.setSpacing(8)

        self.command_icon = ToolButton(FIF.BROOM, self.command_bar)
        self.history = ToolButton(FIF.HISTORY, self.command_bar)
        # Add bash wrap toggle button
        # Add bash wrap toggle button
        self.bash_wrap_button = ToolButton(
            self.command_bar)  # Icon will be set manually
        self.bash_wrap_button.setCheckable(True)
        self.bash_wrap_button.setToolTip(
            self.tr("Toggle `bash -c` wrapper for commands"))
        self.bash_wrap_enabled = False

        # Create and cache icons
        self.icon_bash_disabled = self._create_bash_wrap_icon(
            enabled=False)
        self.icon_bash_enabled = self._create_bash_wrap_icon(enabled=True)
        self.bash_wrap_button.setIcon(self.icon_bash_disabled)

        self.bash_wrap_button.toggled.connect(self._on_bash_wrap_toggled)

        self.command_input = CommandInput(self.command_bar)
        self.command_input.setObjectName("command_input")
        self.command_input.setPlaceholderText(
            self.tr("Enter command here,Shift+Enter for new line,Enter to sendExec,or Enter Alt to show history command"))
        # self.command_input.setFixedHeight(32) # Remove fixed height
        self.command_input.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)
        self.command_input.textChanged.connect(self.adjust_input_height)
        self.command_input.executeCommand.connect(self.send_command_to_ssh)
        self.command_input.clear_history_.connect(self._clear_history)
        self.command_input.setStyleSheet("""
            CommandInput#command_input {
                background-color: transparent;
                border: none;
                color: %s;
                font-size: 14px;
                padding-left: 5px;
            }
        """ % config["ssh_widget_text_color"])
        self.command_input.add_history(
            session_manager.get_session_by_name(self.parentkey).history)
        self.command_icon.clicked.connect(self.ssh_widget.clear_screen)
        self.history.clicked.connect(self.command_input.toggle_history)
        command_bar_layout.addWidget(self.command_icon)
        command_bar_layout.addWidget(self.bash_wrap_button)
        command_bar_layout.addWidget(self.history)
        command_bar_layout.addWidget(self.command_input)

        top_container_layout.addWidget(self.ssh_widget)
        top_container_layout.addWidget(self.command_bar)
        self.adjust_input_height()

        # file_manage
        self.file_manage = QWidget(rsplitter)
        self.file_manage.setObjectName("file_manage")
        self.file_manage.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        file_manage_layout = QVBoxLayout(self.file_manage)
        file_manage_layout.setContentsMargins(0, 0, 0, 0)
        file_manage_layout.setSpacing(0)

        # file_bar
        self.file_bar = File_Navigation_Bar(self.file_manage)
        self.file_bar.bar_path_changed.connect(self._set_file_bar)
        self.file_bar.setObjectName("file_bar")
        self.file_bar.setFixedHeight(45)
        self.file_bar.setStyleSheet("""
            QFrame#file_bar {
                background-color: rgba(240, 240, 240, 0.8);
                border-bottom: 1px solid rgba(0,0,0,0.1);
                border-radius: 6px 6px 0 0;
            }
        """)
        # file_explorer
        self.file_explorer = FileExplorer(
            self.file_manage)

        def connect_file_explorer():
            # self.file_explorer.upload_file.connect(
            #     lambda source_path, _: self.show_file_action("upload", source_path))
            default_view = config.get("default_view", "icon")
            self.file_explorer.switch_view(default_view)
            self.file_explorer.selected.connect(self._process_selected_path)
            self.file_explorer.refresh_action.connect(
                self._update_file_explorer)
            self.file_bar.refresh_clicked.connect(self._update_file_explorer)
            self.file_bar.new_folder_clicked.connect(
                self.file_explorer._handle_mkdir)
            self.file_bar.view_switch_clicked.connect(self._switch_view_mode)

            self.file_bar.upload_mode_toggled.connect(
                self._on_upload_mode_toggled)
            self.file_explorer.upload_mode_switch.toggled.connect(
                self.file_bar.update_upload_mode_button)
            # init button state
            is_compress_upload = CONFIGER.read_config()["compress_upload"]
            self.file_bar.update_upload_mode_button(is_compress_upload)
            self.file_explorer.upload_mode_switch.setChecked(
                is_compress_upload)

            self.file_bar.update_view_switch_button(
                self.file_explorer.view_mode)
            self.file_bar.pivot.currentItemChanged.connect(
                self._change_file_or_net)
        connect_file_explorer()
        self.net_monitor = NetProcessMonitor()
        file_manage_layout.addWidget(self.file_bar)
        self.net_monitor.hide()
        file_manage_layout.addWidget(self.net_monitor)
        self.now_ui = "file_explorer"
        file_manage_layout.addWidget(self.file_explorer, 1)

        rightLayout.addWidget(rsplitter)

        # Left Right splitter
        splitter_lr = QSplitter(Qt.Horizontal, self)
        splitter_lr.addWidget(leftContainer)
        splitter_lr.addWidget(rightContainer)
        self.mainLayout.addWidget(splitter_lr)

        rsplitter.setStretchFactor(0, 3)   # top_container
        rsplitter.setStretchFactor(1, 2)   # file_manage

        splitter_lr.setStretchFactor(0, 25)  # 左侧面板
        splitter_lr.setStretchFactor(1, 75)  # 右侧主区

        # ---- Debounce terminal resize on splitter move ----
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(50)  # 150ms delay
        self.resize_timer.timeout.connect(self.ssh_widget.fit_terminal)
        rsplitter.splitterMoved.connect(self.resize_timer.start)

    def _change_file_or_net(self, router):
        if router == "file_explorer" and self.now_ui != "file_explorer":
            self.net_monitor.hide()
            self.file_explorer.show()
            self.now_ui = "file_explorer"
        elif router == "net" and self.now_ui != "net":
            self.file_explorer.hide()
            self.net_monitor.show()
            self.now_ui = "net"

    def _clear_history(self):
        session_manager.clear_history(self.parentkey)

    def _on_upload_mode_toggled(self, checked):
        CONFIGER.revise_config("compress_upload", checked)
        self.file_explorer.upload_mode_switch.setChecked(checked)

    def adjust_input_height(self):
        doc = self.command_input.document()
        # Get the required height from the document's layout
        content_height = int(doc.size().height())

        # The document margin is the internal padding of the TextEdit
        margin = int(self.command_input.document().documentMargin()) * 2

        # Calculate the total required height
        required_height = content_height + margin

        # Define min/max heights
        font_metrics = self.command_input.fontMetrics()
        line_height = font_metrics.lineSpacing()
        # Min height for at least one line
        min_height = line_height + margin
        # Max height for 5 lines
        max_height = (line_height * 5) + margin + \
            5  # A bit of extra padding for max

        # Clamp the final height
        final_height = min(max(required_height, min_height), max_height)

        # Update the heights of the input and its container
        self.command_input.setFixedHeight(final_height)
        self.command_bar.setFixedHeight(
            final_height + 10)  # 10 for container's padding

    def send_command_to_ssh(self, command):
        if self.ssh_widget and command:
            if self.bash_wrap_enabled:
                # Escape double quotes in the command
                escaped_command = command.replace('"', '\\"')
                final_command = f'bash -c "{escaped_command}"\n'
            else:
                final_command = command + '\n'
            self.ssh_widget.send_command(final_command)
            session_manager.add_command_to_session(
                self.parentkey, final_command)

    def _on_bash_wrap_toggled(self, checked):
        self.bash_wrap_enabled = checked
        if checked:
            self.bash_wrap_button.setIcon(self.icon_bash_enabled)
        else:
            self.bash_wrap_button.setIcon(self.icon_bash_disabled)

    def _create_bash_wrap_icon(self, enabled: bool) -> QIcon:
        """Draws a custom icon with a checkmark overlay if enabled."""
        # Use a fixed size for consistency
        size = QSize(20, 20)

        # Create base icon from FluentIcon
        base_icon = Action(FIF.COMMAND_PROMPT, '', self.command_bar).icon()
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw base icon centered
        base_pixmap = base_icon.pixmap(size)
        painter.drawPixmap(0, 0, base_pixmap)

        if enabled:
            # Draw checkmark in the bottom-right corner
            pen = QPen(QColor("#00E676"), 2.5)  # A vibrant green, thicker
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)

            w, h = size.width(), size.height()
            path = QPainterPath()
            path.moveTo(w * 0.50, h * 0.65)
            path.lineTo(w * 0.70, h * 0.85)
            path.lineTo(w * 1.0, h * 0.55)
            painter.drawPath(path)

        painter.end()
        return QIcon(pixmap)

    def _switch_view_mode(self):
        if self.file_explorer.view_mode == "icon":
            new_mode = "details"
        else:
            new_mode = "icon"
        self.file_explorer.switch_view(new_mode)
        self.file_bar.update_view_switch_button(new_mode)

    def _process_selected_path(self, path_dict: dict):
        # print(f"选中了: {path_dict}")
        name = next(iter(path_dict.keys()))
        is_dir = next(iter(path_dict.values()))
        if name == '..':
            #
            current_path = self.file_explorer.path
            if current_path and current_path != '/':
                new_path = '/'.join(current_path.split('/')[:-1])
                if not new_path:
                    new_path = '/'
                self._set_file_bar(new_path)
            return

        new_path = self.file_explorer.path + "/" + name
        if is_dir:
            self._set_file_bar(new_path)
        else:
            if self.file_manager:
                print(f"get file type for: {new_path}")
                self.file_manager.get_file_type(new_path)

    def _update_file_explorer(self, path: str = None):
        if path:
            self.file_explorer.path = path
        else:
            path = self.file_explorer.path  # Refresh the original directory

        if not self.file_manager:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'file_tree_object'):
                    # Pass the correct parameter: route_key, not parent
                    self.file_manager = parent.file_tree_object[self.router]
                    break
                parent = parent.parent()
            self.file_manager.list_dir_finished.connect(
                self._on_list_dir_finished, type=Qt.QueuedConnection)
        if self.file_manager:
            # print(f"添加：{path} 到任务")
            self.file_manager.list_dir_async(path)

    def _on_list_dir_finished(self, path: str, file_dict: dict):
        # if path != self.file_explorer.path:
        #     return

        try:
            self.file_explorer.add_files(file_dict)
        # self.file_manager._add_path_to_tree(path, False)
        # file_tree = self.file_manager.get_file_tree()
        # self.disk_storage.refresh_tree(file_tree)
        except Exception as e:
            print(f"_on_list_dir_finished error: {e}")

    def _set_file_bar(self, path: str):
        def parse_linux_path(path: str) -> list:
            if not path:
                return []
            path_list = []
            if path.startswith('/'):
                path_list.append('/')
            parts = [p for p in path.strip('/').split('/') if p]
            path_list.extend(parts)
            return path_list

        path_list = parse_linux_path(path)

        # BLOCK signals while rebuilding breadcrumb to avoid multiple refreshes
        try:
            self.file_bar.breadcrumbBar.blockSignals(True)
        except Exception:
            pass

        self.file_bar.set_path(path)
        self.file_bar.breadcrumbBar.clear()
        for p in path_list:
            self.file_bar.breadcrumbBar.addItem(p, p)

        try:
            self.file_bar.breadcrumbBar.blockSignals(False)
        except Exception:
            pass

        self.file_bar._hide_path_edit()

        # ensure explorer.path updated and only refresh once
        self.file_explorer.path = path
        # explicitly request one refresh
        self._update_file_explorer(path)

    def on_main_window_resized(self):
        # A simple way to trigger the debounced resize
        self.resize_timer.start()

    def cleanup(self):
        self.ssh_widget.cleanup()
        try:
            self.ssh_widget.directoryChanged.disconnect()
            self.disk_storage.directory_selected.disconnect()
        except Exception:
            pass
        try:
            self.command_input.textChanged.disconnect()
            self.command_input.executeCommand.disconnect()
        except Exception:
            pass

        for container in [getattr(self, 'ssh_widget', None),
                          getattr(self, 'command_bar', None),
                          getattr(self, 'sys_resources', None),
                          getattr(self, 'task', None),
                          getattr(self, 'disk_storage', None),
                          getattr(self, 'transfer_progress', None),
                          getattr(self, 'file_manage', None),
                          getattr(self, 'file_bar', None),
                          getattr(self, 'file_explorer', None)]:
            if container:
                container.setParent(None)
                container.deleteLater()

        if hasattr(self, 'mainLayout'):
            while self.mainLayout.count():
                item = self.mainLayout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

        parent_layout = self.parentWidget().layout() if self.parentWidget() else None
        if parent_layout:
            parent_layout.removeWidget(self)
        self.setParent(None)
        self.deleteLater()
