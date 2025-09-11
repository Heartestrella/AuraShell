# coding:utf-8
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtWidgets import QApplication, QStackedWidget, QHBoxLayout

from qfluentwidgets import (NavigationInterface, NavigationItemPosition, InfoBar, FluentTranslator,
                            isDarkTheme, setTheme, Theme, InfoBarPosition, FluentIcon as FIF)
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
import os
font_ = font_config()


def resource_path(relative_path):
    """获取资源文件的绝对路径（兼容 PyInstaller）"""
    if hasattr(sys, "_MEIPASS"):
        # 打包后
        base_path = sys._MEIPASS
    else:
        # 源码运行
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class Window(FramelessWindow):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.icons = My_Icons()
        self.setMinimumSize(800, 600)
        self.setTitleBar(StandardTitleBar(self))
        self._bg_ratio = None
        self.setWindowTitle("RemmoteSSH Beta @su8aru")
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

        self.sessions = Widget('暂无选择的会话', True, self)

        self.navigationInterface.setStyleSheet("background: transparent;")
        self.navigationInterface.setCollapsible(True)
        self.stackWidget.setStyleSheet("background: transparent;")

        self.settingInterface = SettingPage(self,)
        self.settingInterface.themeChanged.connect(self._on_theme_changed)
        self.settingInterface.lock_ratio_card.checkedChanged.connect(
            self.apply_locked_ratio)
        self.settingInterface.opacityEdit.valueChanged.connect(
            self.set_background_opacity)
        # 连接透明度设置信号
        # self.settingInterface.bgOpacityChanged.connect(
        #     self.set_background_opacity)
        self._on_theme_changed(
            self.settingInterface.cfg.background_color.value)

        # initialize layout
        self.initLayout()

        # add items to navigation interface
        self.initNavigation()

        self.initWindow()
        # self.set_background_opacity(0.5)

    def set_background_opacity(self, opacity: float):
        """
        设置背景图片透明度

        参数:
            opacity: 透明度值 (0.0 - 1.0)，0.0为完全透明，1.0为完全不透明
        """
        if not self._bg_pixmap:
            return

        # int情况下 只会是setting传入
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
            title="连接失败",
            content=f"错误:\n{msg}\n请关闭此会话",
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
                print("获取SSH Widget失败")
        except Exception as e:
            print(e)

    def _show_info(self, path: str = None, status: bool = None, msg: str = None, type_: str = None, child_key: str = None, local_path: str = None):
        # print(f"_show_info type : {type_}")
        if type_ == "upload":
            duration = 10000
            if status:
                status_msg = "上传成功"
            else:
                status_msg = "上传失败"
                duration = -1
            title = f'文件：{path} 状态：{status_msg}\n'

        elif type_ == "start_upload":
            duration = 2000
            title = f"开始上传 {local_path} 到 {path}"
            msg = ""

        elif type_ == "delete":
            duration = 2000
            if status:
                title = f"删除 {path} 成功\n"
            else:
                title = f"删除 {path} 失败\n{msg}"
                duration = -1

        elif type_ == "start_download":
            duration = 2000
            title = f"开始下载 {path}"
            msg = ""

        elif type_ == "download":
            duration = 2000
            if status:
                title = f"下载 {path} 成功"
                msg = f"成功下载到 {local_path}"
            else:
                title = f"下载 {path} 失败\n"
                duration = -1

        elif type_ == "paste":
            duration = 2000
            if status:
                title = f"粘贴成功"
                msg = f"粘贴 {path} 到 {local_path}"
            else:
                title = f"粘贴失败"
                duration = -1
        InfoBar.info(
            title=title,
            content=msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=duration,
            parent=self.window()
        )
        self._refresh_paths(child_key)

    def _start_ssh_connect(self, session, child_key):

        # 系统资源显示相关
        parent_key = child_key.split("-")[0].strip()
        session_widget = self.session_widgets[parent_key][child_key]
        processes = SSHWorker(session, for_resources=True)
        self.ssh_session[f'{child_key}-processes'] = processes
        processes.sys_resource.connect(
            lambda usage, key=child_key: self._set_usage(key, usage))
        processes.start()

        # 处理路径相关
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
        file_manager.download_finished.connect(lambda remote_path, local_path, status, error_msg:
                                               self._show_info(remote_path, status, error_msg, "download", child_key, local_path=local_path))
        file_manager.copy_finished.connect(lambda source_path, target_path, status, error_msg:
                                           self._show_info(source_path, status, error_msg, "paste", child_key, target_path))
        session_widget.file_explorer.upload_file.connect(
            lambda path, target_path: self._show_info(type_="start_upload", child_key=child_key, local_path=path, path=target_path))
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

        # 主SSH窗口
        worker = SSHWorker(session, for_resources=False)
        self.ssh_session[child_key] = worker

        worker.connected.connect(
            lambda success, msg: self._on_ssh_connected(success, msg))
        worker.error_occurred.connect(lambda e: self._on_ssh_error(e))

        # 注入 worker 到 UI 的终端 widget
        try:

            child_widget = self.session_widgets[parent_key][child_key]
            # 假设 child_widget 在构造时已经把 self.ssh_widget = WebTerminal(...) 放好
            if hasattr(child_widget, 'ssh_widget'):
                child_widget.ssh_widget.set_worker(worker)
            else:
                print("child_widget 没有 ssh_widget 属性")
        except Exception as e:
            print("注入 worker 失败:", e)

        worker.start()
        session_widget.ssh_widget.directoryChanged.connect(
            lambda path: file_manager.check_path_async(path)
        )
        session_widget.disk_storage.refresh.triggered.connect(
            lambda checked, ck=child_key: self._refresh_paths(ck)
        )

    def _handle_files(self, action_type, full_path, copy_to, cut, child_key):
        file_manager: RemoteFileManager = self.file_tree_object[child_key]
        if action_type == "delete":
            file_manager.delete_path(full_path)
        elif action_type == "copy_path":
            clipboard.setText(full_path)
        elif action_type == "download":
            self._show_info(path=full_path, child_key=child_key,
                            type_="start_download")
            file_manager.download_path_async(full_path)
        elif action_type == "paste":
            if full_path and copy_to:
                print(f"Copy {full_path} to {copy_to} Cut status : {cut}")
                file_manager.copy_to(full_path, copy_to, cut)

    def _refresh_paths(self, child_key: str):
        print("刷新页面")
        parent_key = child_key.split("-")[0].strip()
        session_widget: Widget = self.session_widgets[parent_key][child_key]
        session_widget._update_file_explorer()

    def parse_linux_path(self, path: str) -> list:
        """
        将 Linux 路径解析为路径列表，每一层作为一个元素。

        示例：
            '/home/bee' -> ['/', 'home', 'bee']
            '/' -> ['/']

        参数：
            path: str，Linux 风格路径

        返回：
            list[str]，从根到最深目录的列表
        """
        if not path:
            return []

        path_list = []

        # 确保以 '/' 开头
        if path.startswith('/'):
            path_list.append('/')  # 根目录

        # 分割路径，去掉空字符串
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
        """处理文件树更新"""
        sw.disk_storage.refresh_tree(file_tree)
        if path:
            sw.disk_storage.switch_to(path)

    def on_file_manager_error(self, error_msg):
        """处理文件管理器错误"""
        InfoBar.error(
            title='文件管理错误',
            content=f'''错误详情:\n{error_msg}''',
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
            print(f"partent_key:{parent_key}")
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
        print(f"创建子级会话: {child_key} (父级: {parent_key})")
        print(session, child_key)
        self._start_ssh_connect(session, child_key)

    def apply_locked_ratio(self, event=None):
        new_width, new_height = 0, 0
        """Apply background image proportionally to window size"""
        if self.settingInterface._lock_ratio and self._bg_pixmap and self._bg_ratio:
            if event is not None and not isinstance(event, bool):
                # resizeEvent 调用
                new_width = event.size().width()
                new_height = event.size().height()
            else:
                # 手动调用，直接用当前窗口大小
                new_width = self.width()
                new_height = self.height()

            target_ratio = self._bg_ratio

            if abs(new_width / new_height - target_ratio) > 0.01:
                new_height = int(new_width / target_ratio)
                self.resize(new_width, new_height)
        if self.settingInterface.init_window_size and new_width and new_height:
            self.settingInterface.save_window_size((new_width, new_height))

    def resizeEvent(self, event):
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
        # enable acrylic effect
        # self.navigationInterface.setAcrylicEnabled(True)

        self.addSubInterface(self.MainInterface, FIF.HOME, '主页')

        self.navigationInterface.addSeparator()

        self.addSubInterface(self.sessions, FIF.ALBUM,
                             'SSH会话', NavigationItemPosition.SCROLL)

        self.addSubInterface(self.settingInterface, FIF.SETTING,
                             '设置', NavigationItemPosition.BOTTOM)

        #!IMPORTANT: don't forget to set the default route key if you enable the return button
        # qrouter.setDefaultRouteKey(self.stackWidget, self.musicInterface.objectName())

        # set the maximum width
        # self.navigationInterface.setExpandWidth(300)

        self.stackWidget.currentChanged.connect(self.onCurrentInterfaceChanged)
        self.stackWidget.setCurrentIndex(0)

        # always expand
        # self.navigationInterface.setCollapsible(False)

    def initWindow(self):
        # self.resize(900, 700)
      #  self.setWindowIcon(QIcon('resource/logo.png'))
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

                for widget_name in self.session_widgets[parent].keys():
                    if widget_name != "widget":
                        self.navigationInterface.removeWidget(
                            routeKey=widget_name)
                        remove_keys.append(widget_name)
                for widget_name in remove_keys:
                    self.session_widgets[parent].pop(widget_name, None)
            else:
                self.navigationInterface.removeWidget(routeKey=widget_name)
                self.session_widgets[parent].pop(widget_name, None)
            if not parent_id:
                self.switchTo(self.session_widgets[parent]["widget"])
            close_count = 1 if len(remove_keys) == 0 else len(remove_keys)
            InfoBar.success(
                title='关闭会话成功',
                content=f'''关闭了 “{parent}” 下 {close_count} 个会话''',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='关闭会话出现错误！',
                content=f'''错误详情:\n{e}''',
                orient=Qt.Vertical,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=-1,
                parent=self
            )

    def addSubInterface(self, interface, icon, text: str, position=NavigationItemPosition.TOP, parent=None):
        """ 添加页面 """
        tittle = None
        if text == "主页":
            tittle = "RemmoteSSH Beta @su8aru"
        else:
            tittle == text
        self.stackWidget.addWidget(interface)
        self.navigationInterface.addItem(
            routeKey=interface.objectName(),
            icon=icon,
            text=text,
            onClick=lambda: self.switchTo(interface, tittle),
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

        #!IMPORTANT: This line of code needs to be uncommented if the return button is enabled
        # qrouter.push(self.stackWidget, widget.objectName())

    def remove_nav_edge(self):
        # Set the NavigationInterface background to be transparent
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
            print(f"设置字体颜色失败：{e}")

    def _on_theme_changed(self, value):
        if value == "浅色":
            setTheme(Theme.LIGHT)
        elif value == "暗色":
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.DARK if isDarkTheme() else Theme.LIGHT)

        self.setQss()

        for i in range(self.stackWidget.count()):
            w = self.stackWidget.widget(i)
            if hasattr(w, 'widget'):
                w.widget().update()
            else:
                w.update()

    def clear_global_background(self):
        """
        清除全局背景图片，并恢复 NavigationInterface 样式
        """
        self._bg_pixmap = None
        self._bg_opacity = 1.0  # 重置透明度
        self.update()  # 触发重绘

        # 恢复导航栏默认样式
        self.navigationInterface.setStyleSheet("")

    def set_global_background(self, image_path: str):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"无效图片路径: {image_path}")
            return
        self._bg_pixmap = pixmap
        self._bg_ratio = pixmap.width() / pixmap.height()
        self._bg_opacity = 1.0  # 设置新背景时重置透明度
        self.update()
        self.remove_nav_edge()

    def paintEvent(self, event):
        if self._bg_pixmap:
            painter = QPainter(self)
            # 设置透明度
            painter.setOpacity(self._bg_opacity)
            painter.drawPixmap(self.rect(), self._bg_pixmap)
        super().paintEvent(event)


if __name__ == '__main__':
    try:

        setup_global_logging()
        main_logger.info("应用程序启动")
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        QApplication.setAttribute(Qt.AA_UseOpenGLES)
        app = QApplication(sys.argv)
        # translator = FluentTranslator(
        #     QLocale(QLocale.English, QLocale.UnitedStates))
        # app.installTranslator(translator)
        translator = FluentTranslator()
        QApplication.instance().installTranslator(translator)
        clipboard = app.clipboard()
        w = Window()
        w.show()
        app.exec_()
    except Exception as e:
        main_logger.critical("应用程序启动失败", exc_info=True)
