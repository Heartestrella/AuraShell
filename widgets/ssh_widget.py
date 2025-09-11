from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame,  QHBoxLayout, QLabel, QWidget, QVBoxLayout, QSizePolicy, QSplitter
from qfluentwidgets import RoundMenu, Action, FluentIcon as FIF
from widgets.system_resources_widget import ProcessTable
from widgets.task_widget import Tasks
from tools.ssh_webterm import WebTerminal
from widgets.file_tree_widget import File_Navigation_Bar, FileTreeWidget
from widgets.files_widgets import FileExplorer
from tools.setting_config import SCM
configer = SCM()


class Widget(QWidget):
    refresh_file_explorer = pyqtSignal(str)

    def __init__(self, text: str, parent_state: bool = False, parent=None, font_name=None, user_name=None):
        super().__init__(parent=parent)
        self.setObjectName(text)
        self.child_key = text
        self.parent_state = parent_state
        # 保证这个页面在 QStackedWidget 中能正确撑满区域
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 主水平布局：左 30% (index 0)、右 70% (index 1)
        self.mainLayout = QHBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(8)

        if parent_state:
            label = QLabel(text, self)
            label.setAlignment(Qt.AlignCenter)
            self.mainLayout.addWidget(label)
        else:
            config = configer.read_config()
            self.file_manager = None
            # --------- 左列：sys_resources + disk_storage（垂直堆叠） ---------
            leftContainer = QFrame(self)
            leftContainer.setObjectName("leftContainer")
            leftContainer.setSizePolicy(
                QSizePolicy.Preferred, QSizePolicy.Expanding)

            leftLayout = QVBoxLayout(leftContainer)
            leftLayout.setContentsMargins(0, 0, 0, 0)
            leftLayout.setSpacing(0)

            # sys_resources（上）
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
            # Task (中)
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
            # disk_storage（下）
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

            leftLayout.addWidget(self.sys_resources, 2)   # 上下比例可调（这里是 3:2）
            leftLayout.addWidget(self.task, 3)
            leftLayout.addWidget(self.disk_storage, 5)

            # --------- 右列：ssh_widget + file_manage（可拉伸，垂直分割） ---------
            rightContainer = QFrame(self)
            rightContainer.setObjectName("rightContainer")
            rightContainer.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
            rightLayout = QVBoxLayout(rightContainer)
            rightLayout.setContentsMargins(0, 0, 0, 0)
            rightLayout.setSpacing(0)

            # 使用 QSplitter 让上/下两区域可拖拽改变高度
            splitter = QSplitter(Qt.Vertical, rightContainer)
            splitter.setChildrenCollapsible(False)  # 防止折叠成 0 高
            splitter.setHandleWidth(6)
            splitter.setStyleSheet("""
    QSplitter::handle:vertical {
        background-color: #cccccc;
        height: 1px;
        margin: 2px 0px;
    }
    QSplitter::handle:vertical:hover {
        background-color: #999999;
    }
""")
            # ssh_widget（上）
            self.ssh_widget = WebTerminal(
                splitter, font_name=font_name, user_name=user_name, text_color=config["ssh_widget_text_color"])
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
            self.ssh_widget.view.page().runJavaScript(
                "window.getComputedStyle(document.body).backgroundColor", print)
            col = self.ssh_widget.view.page().backgroundColor()
            print("page.bg alpha:", col.alpha())
            # file_manage（下）
            self.file_manage = QWidget(splitter)
            self.file_manage.setObjectName("file_manage")
            self.file_manage.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)

            # 创建垂直布局来分割上下两部分
            file_manage_layout = QVBoxLayout(self.file_manage)
            file_manage_layout.setContentsMargins(0, 0, 0, 0)
            file_manage_layout.setSpacing(0)

            # 上半部分：导航栏（固定50px）
            self.file_bar = File_Navigation_Bar(self.file_manage)
            self.file_bar.bar_path_changed.connect(self._update_file_explorer)
            self.file_bar.setObjectName("file_bar")
            self.file_bar.setFixedHeight(50)
            self.file_bar.setStyleSheet("""
                QFrame#file_bar {
                    background-color: rgba(240, 240, 240, 0.8);
                    border-bottom: 1px solid rgba(0,0,0,0.1);
                    border-radius: 6px 6px 0 0;
                }
            """)

            # 下半部分：文件树（占据剩余空间）

            self.file_explorer = FileExplorer(
                self.file_manage, icons=self._get_icons())
            self.file_explorer.selected.connect(self._process_selected_path)
            self.file_explorer.refresh_action.connect(
                self._update_file_explorer)
            self.file_explorer.setObjectName("file_tree")
            self.file_explorer.setStyleSheet("""
                QFrame#file_tree {
                    background-color: rgba(255, 255, 255, 0.01);
                    border: 1px solid rgba(0,0,0,0.03);
                    border-radius: 0 0 6px 6px;
                }
            """)

            # 添加到布局
            file_manage_layout.addWidget(self.file_bar)
            file_manage_layout.addWidget(self.file_explorer, 1)  # 1表示占据剩余空间

            # 把 splitter 放到右布局
            rightLayout.addWidget(splitter)

            # --------- 把左右两列加入 mainLayout，并设置 stretch 实现 30/70 比例 ---------
            self.mainLayout.addWidget(leftContainer, 20)   # 30%
            self.mainLayout.addWidget(rightContainer, 80)  # 70%

            # 设置 splitter 初始比例（例如 60% 上，40% 下）
            total_h = max(200, self.height())
            splitter.setSizes([int(total_h * 0.6), int(total_h * 0.4)])

    def _get_icons(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'icons'):
                return parent.icons
            parent = parent.parent()

    def _process_selected_path(self, path_dict: dict):
        # print(f"选中了: {path_dict}")
        name = next(iter(path_dict.keys()))
        is_dir = next(iter(path_dict.values()))

        if is_dir:
            new_path = self.file_explorer.path + "/" + name
            self._set_file_bar(new_path)

    def _update_file_explorer(self, path: str = None):
        if path:
            self.file_explorer.path = path
        else:
            path = self.file_explorer.path  # 刷新原有目录

        if not self.file_manager:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'file_tree_object'):
                    # 传递正确的参数：route_key，而不是parent
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

        # 更新 UI（add_files 是主线程函数）
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

        self.file_bar.breadcrumbBar.clear()
        for p in path_list:
            self.file_bar.breadcrumbBar.addItem(p, p)

        try:
            self.file_bar.breadcrumbBar.blockSignals(False)
        except Exception:
            pass

        # ensure explorer.path updated and only refresh once
        self.file_explorer.path = path
        # explicitly request one refresh
        self._update_file_explorer(path)

    def contextMenuEvent(self, e) -> None:
        menu = RoundMenu(parent=self)
        if not self.parent_state:
            copy_action = Action(FIF.COPY, '复制会话')
            delete_action = Action(FIF.DELETE, '删除会话')
            copy_action.triggered.connect(self._on_copy)
            delete_action.triggered.connect(self._on_delete)

            menu.addActions([copy_action, delete_action])
            menu.addSeparator()
            menu.exec(e.globalPos())
        elif self.parent_state:
            close_action = Action(FIF.CLOSE, '关闭所有子会话')
            close_action.triggered.connect(self._on_close)
            menu.addAction(close_action)
            menu.exec(e.globalPos())

    def _on_close(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'remove_sub_interface'):
                # 传递正确的参数：route_key，而不是parent
                parent.remove_sub_interface(self, close_sub_all=True)
                return
            parent = parent.parent()
        print("无法找到父级窗口或删除方法")

    def _on_copy(self):
        """复制会话"""
        parent = self.parent()
        parent_key = self.child_key.split("-")[0].strip()
        while parent:
            if hasattr(parent, '_on_session_selected'):

                parent._on_session_selected(parent_key=parent_key)
                return
            parent = parent.parent()
        print("无法找到父级窗口或删除方法")

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
        print("无法找到父级窗口或删除方法")
