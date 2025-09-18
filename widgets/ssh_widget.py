from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QPainterPath
from PyQt5.QtWidgets import QFrame,  QHBoxLayout, QLabel, QWidget, QVBoxLayout, QSizePolicy, QSplitter
from qfluentwidgets import RoundMenu, Action, FluentIcon as FIF,  ToolButton
from widgets.command_input import CommandInput
from widgets.system_resources_widget import ProcessTable
from widgets.task_widget import Tasks
from tools.ssh_webterm import WebTerminal
from widgets.file_tree_widget import File_Navigation_Bar, FileTreeWidget
from widgets.files_widgets import FileExplorer
from widgets.transfer_progress_widget import TransferProgressWidget
from tools.setting_config import SCM
configer = SCM()


class Widget(QWidget):
    refresh_file_explorer = pyqtSignal(str)

    def __init__(self, text: str, parent_state: bool = False, parent=None, font_name=None, user_name=None):
        super().__init__(parent=parent)
        self.setObjectName(text)
        self.child_key = text
        self.parent_state = parent_state
        # Ensure that this page can correctly fill the area in QStackedWidget
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Main horizontal layout: left 30% (index 0), right 70% (index 1)
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        splitter_lr = QSplitter(Qt.Horizontal, self)
        splitter_lr.setChildrenCollapsible(False)
        splitter_lr.setHandleWidth(6)

        if parent_state:
            label = QLabel(text, self)
            label.setAlignment(Qt.AlignCenter)
            self.mainLayout.addWidget(label)

        else:

            config = configer.read_config()
            self.file_manager = None

            # --------- 左侧容器 ---------
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
            self.disk_storage.setObjectName("disk_storage")
            self.disk_storage.setMinimumHeight(80)
            self.disk_storage.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.disk_storage.directory_selected.connect(self._set_file_bar)
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

            # 左侧竖排布局（比例 2:3:5）
            leftLayout.addWidget(self.sys_resources, 2)
            leftLayout.addWidget(self.task, 3)
            leftLayout.addWidget(self.disk_storage, 5)
            # Initially, no stretch
            leftLayout.addWidget(self.transfer_progress, 0)

            def toggle_transfer_stretch(is_expanded):
                if is_expanded:
                    # transfer_progress index is 3
                    leftLayout.setStretch(3, 10)
                else:
                    leftLayout.setStretch(3, 0)

            self.transfer_progress.expansionChanged.connect(
                toggle_transfer_stretch)

            # --------- 右侧容器 ---------
            rightContainer = QFrame(self)
            rightContainer.setObjectName("rightContainer")
            rightContainer.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)

            rightLayout = QVBoxLayout(rightContainer)
            rightLayout.setContentsMargins(0, 0, 0, 0)
            rightLayout.setSpacing(0)

            # 上下 splitter（右边 ssh_widget / file_manage）
            splitter = QSplitter(Qt.Vertical, rightContainer)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(2)
            splitter.setStyleSheet("""
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
            top_container = QFrame(splitter)
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

            # Add bash wrap toggle button
            # Add bash wrap toggle button
            self.bash_wrap_button = ToolButton(self.command_bar) # Icon will be set manually
            self.bash_wrap_button.setCheckable(True)
            self.bash_wrap_button.setToolTip(self.tr("Toggle `bash -c` wrapper for commands"))
            self.bash_wrap_enabled = False

            # Create and cache icons
            self.icon_bash_disabled = self._create_bash_wrap_icon(enabled=False)
            self.icon_bash_enabled = self._create_bash_wrap_icon(enabled=True)
            self.bash_wrap_button.setIcon(self.icon_bash_disabled)

            self.bash_wrap_button.toggled.connect(self._on_bash_wrap_toggled)


            self.command_input = CommandInput(self.command_bar)
            self.command_input.setObjectName("command_input")
            self.command_input.setPlaceholderText(
                self.tr("Enter command here,Shift+Enter for new line,Enter to sendExec"))
            # self.command_input.setFixedHeight(32) # Remove fixed height
            self.command_input.setVerticalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff)
            self.command_input.textChanged.connect(self.adjust_input_height)
            self.command_input.executeCommand.connect(self.send_command_to_ssh)

            self.command_input.setStyleSheet("""
                CommandInput#command_input {
                    background-color: transparent;
                    border: none;
                    color: %s;
                    font-size: 14px;
                    padding-left: 5px;
                }
            """ % config["ssh_widget_text_color"])
            self.command_icon.clicked.connect(self.ssh_widget.clear_screen)
            command_bar_layout.addWidget(self.command_icon)
            command_bar_layout.addWidget(self.bash_wrap_button)
            command_bar_layout.addWidget(self.command_input)

            top_container_layout.addWidget(self.ssh_widget)
            top_container_layout.addWidget(self.command_bar)
            self.adjust_input_height()

            # file_manage
            self.file_manage = QWidget(splitter)
            self.file_manage.setObjectName("file_manage")
            self.file_manage.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)

            file_manage_layout = QVBoxLayout(self.file_manage)
            file_manage_layout.setContentsMargins(0, 0, 0, 0)
            file_manage_layout.setSpacing(0)

            # file_bar
            self.file_bar = File_Navigation_Bar(self.file_manage)
            self.file_bar.bar_path_changed.connect(self._set_file_bar)
            self.file_bar.bar_path_changed.connect(self._update_file_explorer)
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
                self.file_manage, icons=self._get_icons())
            self.file_explorer.upload_file.connect(
                lambda source_path, _: self.show_file_action("upload", source_path))
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
            is_compress_upload = configer.read_config()["compress_upload"]
            self.file_bar.update_upload_mode_button(is_compress_upload)
            self.file_explorer.upload_mode_switch.setChecked(
                is_compress_upload)

            self.file_bar.update_view_switch_button(
                self.file_explorer.view_mode)
            self.file_explorer.setObjectName("file_tree")
            self.file_explorer.setStyleSheet("""
                QFrame#file_tree {
                    background-color: rgba(255, 255, 255, 0.01);
                    border: 1px solid rgba(0,0,0,0.03);
                    border-radius: 0 0 6px 6px;
                }
            """)

            file_manage_layout.addWidget(self.file_bar)
            file_manage_layout.addWidget(self.file_explorer, 1)

            rightLayout.addWidget(splitter)

            # --------- 左右 splitter ---------
            splitter_lr = QSplitter(Qt.Horizontal, self)
            splitter_lr.addWidget(leftContainer)
            splitter_lr.addWidget(rightContainer)
            self.mainLayout.addWidget(splitter_lr)

            # ---- 上下 splitter 默认比例 ----
            splitter.setStretchFactor(0, 3)   # top_container
            splitter.setStretchFactor(1, 2)   # file_manage

            # ---- 左右 splitter 默认比例 ----
            splitter_lr.setStretchFactor(0, 2)  # 左侧面板
            splitter_lr.setStretchFactor(1, 8)  # 右侧主区

            # ---- 拖动事件绑定，保存比例 ----
            def save_lr_ratio(pos, index):
                sizes = splitter_lr.sizes()
                total = sum(sizes)
                configer.revise_config("splitter_lr_ratio", [
                                       s / total for s in sizes])

            def save_tb_ratio(pos, index):
                sizes = splitter.sizes()
                total = sum(sizes)
                if total > 0:
                    configer.revise_config("splitter_tb_ratio", [
                        s / total for s in sizes])
                # config["splitter_tb_ratio"] = [s / total for s in sizes]
                # configer.save_config(config)

            splitter_lr.splitterMoved.connect(save_lr_ratio)
            # ---- Debounce terminal resize on splitter move ----
            resize_timer = QTimer(self)
            resize_timer.setSingleShot(True)
            resize_timer.setInterval(150)  # 150ms delay
            resize_timer.timeout.connect(self.ssh_widget.fit_terminal)

            splitter.splitterMoved.connect(save_tb_ratio)
            splitter.splitterMoved.connect(resize_timer.start)

            # ---- 恢复上次保存的比例 ----
            if "splitter_lr_ratio" in config:
                total_w = max(400, self.width())
                r = config["splitter_lr_ratio"]
                splitter_lr.setSizes(
                    [int(total_w * r[0]), int(total_w * r[1])])

            if "splitter_tb_ratio" in config:
                total_h = max(200, self.height())
                r = config["splitter_tb_ratio"]
                if len(r) == 2:  # New format
                    splitter.setSizes(
                        [int(total_h * r[0]), int(total_h * r[1])])
                elif len(r) == 3:  # For compatibility with old config
                    top_size_ratio = r[0] + r[1]
                    bottom_size_ratio = r[2]
                    splitter.setSizes([int(total_h * top_size_ratio),
                                      int(total_h * bottom_size_ratio)])

    def _on_upload_mode_toggled(self, checked):
        configer.revise_config("compress_upload", checked)
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

    def _get_icons(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'icons'):
                return parent.icons
            parent = parent.parent()

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
                    self.file_manager = parent.file_tree_object[self.child_key]
                    break
                parent = parent.parent()
            self.file_manager.list_dir_finished.connect(
                self._on_list_dir_finished, type=Qt.QueuedConnection)
        if self.file_manager:
            print(f"添加：{path} 到任务")
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

    def contextMenuEvent(self, e) -> None:
        menu = RoundMenu(parent=self)
        if not self.parent_state:
            copy_action = Action(FIF.COPY, self.tr('Copy session'))
            delete_action = Action(FIF.DELETE, self.tr('Delete session'))
            copy_action.triggered.connect(self._on_copy)
            delete_action.triggered.connect(self._on_delete)

            menu.addActions([copy_action, delete_action])
            menu.addSeparator()
            menu.exec(e.globalPos())
        elif self.parent_state:
            close_action = Action(
                FIF.CLOSE, self.tr('Close all child sessions'))
            close_action.triggered.connect(self._on_close)
            menu.addAction(close_action)
            menu.exec(e.globalPos())

    def _on_close(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'remove_sub_interface'):
                parent.remove_sub_interface(self, close_sub_all=True)
                return
            parent = parent.parent()
        print("Unable to find parent window or delete method")

    def _on_copy(self):
        parent = self.parent()
        parent_key = self.child_key.split("-")[0].strip()
        while parent:
            if hasattr(parent, '_on_session_selected'):

                parent._on_session_selected(parent_key=parent_key)
                return
            parent = parent.parent()
        print("Unable to find parent window or delete method")

    def _on_delete(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, "ssh_session"):
                ssh_session = parent.ssh_session
                ssh_session[self.child_key].close()
                ssh_session[f'{self.child_key}-processes'].close()
            if hasattr(parent, 'remove_sub_interface'):
                parent.remove_sub_interface(self)
                return
            parent = parent.parent()
        print("Unable to find parent window or delete method")

    def _cleanup(self):
        try:
            self.disk_storage.directory_selected.disconnect()
        except Exception:
            pass
        try:
            self.file_bar.bar_path_changed.disconnect()
        except Exception:
            pass
        try:
            self.file_explorer.selected.disconnect()
            self.file_explorer.refresh_action.disconnect()
        except Exception:
            pass
        try:
            self.ssh_widget.directoryChanged.disconnect()
        except Exception:
            pass
        for child in self.findChildren(QWidget):
            child.deleteLater()

    def show_file_action(self, action_type, file_paths):
        pass
