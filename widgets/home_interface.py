from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QDialog, QListWidgetItem, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (PrimaryPushButton, ListWidget, TitleLabel,
                            BodyLabel, FluentIcon as FIF, CardWidget, RoundMenu, CaptionLabel, Action, TransparentToolButton, InfoBar, InfoBarPosition)
from PyQt5.QtGui import QFont
# from widgets.session_manager import SessionManager
from widgets.session_dialog import SessionDialog
from tools.font_config import font_config
from tools import valid_ip


class SSH_CARD(CardWidget):

    def __init__(self, title, content, session_id, parent=None):
        super().__init__(parent)
        self.parent_interface = self.parent()
        font = getattr(parent, "fonts", None)
        self.title = title
        self.session_id = session_id
        self.titleLabel = BodyLabel(self.title, self)
        self.contentLabel = CaptionLabel(content, self)

        # # 添加状态指示灯
        # self.statusIndicator = QLabel(self)
        # self.statusIndicator.setFixedSize(8, 8)
        # self.statusIndicator.setStyleSheet(
        #     "background-color: gray; border-radius: 4px;")
        # self.set_connect_status(False)
        self.moreButton = TransparentToolButton(FIF.MORE, self)

        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        self.setFixedHeight(73)
        self.contentLabel.setTextColor("#606060", "#d2d2d2")

        self.hBoxLayout.setContentsMargins(20, 11, 11, 11)
        self.hBoxLayout.setSpacing(15)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        # 标题行布局（状态指示灯 + 标题）
        self.titleLayout = QHBoxLayout()
        # self.titleLayout.addWidget(self.statusIndicator)
        self.titleLayout.addWidget(self.titleLabel)
        self.titleLayout.setSpacing(5)
        self.titleLayout.setContentsMargins(0, 0, 0, 0)

        self.vBoxLayout.addLayout(self.titleLayout, 0)
        self.vBoxLayout.addWidget(self.contentLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)
        self.hBoxLayout.addLayout(self.vBoxLayout)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.moreButton, 0, Qt.AlignRight)

        self.moreButton.setFixedSize(32, 32)

        self.menu = RoundMenu(parent=self)

        self.action_open = Action(FIF.FOLDER, "打开新会话")
        self.action_edit = Action(FIF.EDIT, "编辑")
        self.action_delete = Action(FIF.DELETE, "删除")
        self.close_action = Action(FIF.CLOSE, '关闭所有子会话')
        self.menu.addActions([self.action_open, self.action_edit,])
        self.menu.addSeparator()
        self.menu.addActions([self.action_delete, self.close_action])

        self.moreButton.clicked.connect(self.showMenu)
        self.close_action.triggered.connect(self._close_sub_interface)
        self.action_open.triggered.connect(lambda: getattr(
            parent, "sessionClicked", None).emit(session_id))
        self.action_edit.triggered.connect(self._edit)
        self.action_delete.triggered.connect(self._on_delete)

        if font:
            for w in [self.titleLabel, self.contentLabel, self.moreButton,
                      self.action_open, self.action_edit, self.action_delete]:
                w.setFont(font)

    def _close_sub_interface(self,):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'remove_sub_interface'):
                # 传递正确的参数：route_key，而不是parent
                parent.remove_sub_interface(
                    self, close_sub_all=True, parent_id=self.title)
                return
            parent = parent.parent()

    # def set_connect_status(self, status: bool):
    #     print(f"连接状态：{status}")
    #     """设置连接状态指示器"""
    #     color = "#00FF00" if status else "#FF0000"  # 绿色表示连接，红色表示断开
    #     self.statusIndicator.setStyleSheet(f"""
    #         background-color: {color};
    #         border-radius: 4px;
    #     """)
    #     # 可选：添加工具提示
    #     self.statusIndicator.setToolTip("已连接" if status else "已断开")

    #     # 强制刷新
    #     self.statusIndicator.style().unpolish(self.statusIndicator)
    #     self.statusIndicator.style().polish(self.statusIndicator)
    #     self.statusIndicator.update()

    # def _open_card(self):
    #     if self.parent_interface and hasattr(self.parent_interface, "sessionClicked"):
    #         self.parent_interface.sessionClicked.emit(session_id)

    def set_card_font(self, font: QFont = None):
        """设置卡片字体"""
        # 设置所有文本部件的字体
        self.titleLabel.setFont(font)
        self.contentLabel.setFont(font)
        self.moreButton.setFont(font)
        self.action_delete.setFont(font)
        self.action_edit.setFont(font)
        self.action_open.setFont(font)
        self.setFont(font)

    def _edit(self):
        if hasattr(self.parent_interface, '_create_edit_new_session'):
            self.parent_interface._create_edit_new_session(
                "edit", self.session_id)

    def _on_delete(self):
        """删除会话"""
        # 通过 parent() 获取父部件（MainInterface）
        if hasattr(self.parent_interface, 'session_manager'):
            self.parent_interface.session_manager.delete_session(
                self.session_id)
            self.parent_interface.refresh_sessions()  # 刷新列表

    def showMenu(self):
        """ 在按钮正下方显示菜单 """
        pos = self.moreButton.mapToGlobal(self.moreButton.rect().bottomRight())
        self.menu.exec(pos)


class MainInterface(QWidget):
    sessionClicked = pyqtSignal(str)  # 发射会话ID

    def __init__(self, parent=None):
        super().__init__(parent)
        font_ = font_config()
        self.fonts = font_.get_font()
        if parent and hasattr(parent, "sessionmanager"):
            self.session_manager = parent.sessionmanager
        self.setObjectName("MainInterface")
        self._build_ui()
        self._load_sessions()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        # 标题区域
        title_layout = QHBoxLayout()
        self.title_label = TitleLabel("SSH 会话管理")
        self.new_session_btn = PrimaryPushButton("新建会话", self, FIF.ADD)
        self.new_session_btn.clicked.connect(self._create_edit_new_session)

        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.new_session_btn)

        layout.addLayout(title_layout)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        # separator.setStyleSheet("background-color: rgba(255, 255, 255, 50);")
        layout.addWidget(separator)

        # 说明文字
        info_label = BodyLabel("选择已有的会话或创建新的SSH连接")
        info_label.setStyleSheet("color: #888888;")
        layout.addWidget(info_label)

        # 会话列表
        self.session_list = ListWidget()
        self.session_list.setSpacing(10)
        self.session_list.setStyleSheet("""
        /* ListWidget 容器 */
        ListWidget {
            background-color: transparent;
            border: 1px solid rgba(255, 255, 255, 30);
            border-radius: 8px;
            outline: none;
            padding: 5px;  /* 容器内边距，让第一/最后一个卡片有呼吸空间 */
        }

        /* 每个 item 使用透明背景，实际圆角由 item_widget 控制 */
        ListWidget::item {
            background-color: transparent;
            border: none;
            padding: 0px;  /* 内部布局控制卡片内边距 */
        }

        /* 移除焦点虚线 */
        ListWidget::item:focus {
            outline: none;
        }
        """)

        self.session_list.itemDoubleClicked.connect(self._on_session_clicked)
        layout.addWidget(self.session_list)

        # 空状态提示
        self.empty_label = BodyLabel("暂无会话，点击右上角按钮创建新会话")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #666666; padding: 40px;")
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

    def _load_sessions(self):
        """加载会话列表"""
        self.session_list.clear()
        sessions = self.session_manager.sessions_cache

        if not sessions:
            self.empty_label.show()
            self.session_list.hide()
        else:
            self.empty_label.hide()
            self.session_list.show()

            for session in sessions:
                self._add_session_item(session)

    def _add_session_item(self, session):
        """添加会话项到列表"""
        card = SSH_CARD(
            title=session.name,
            content=f"{session.username}@{session.host}:{session.port}",
            session_id=session.id,
            parent=self
        )
        list_item = QListWidgetItem(self.session_list)
        card.setBorderRadius(8)
        list_item.setSizeHint(card.sizeHint())
        # card.set_card_font(self.fonts)
        self.session_list.addItem(list_item)
        list_item.setData(Qt.UserRole, session.id)
        self.session_list.setItemWidget(list_item, card)

    def _on_session_clicked(self, item):
        """会话项点击事件"""
        session_id = item.data(Qt.UserRole)
        self.sessionClicked.emit(session_id)

    def _create_edit_new_session(self, mode: str = "create", session_id: str = None):
        """创建新会话"""
        dialog = SessionDialog(self)
        if mode == "create":
            pass
        elif mode == "edit":
            session = next(
                (s for s in self.session_manager.sessions_cache if s.id == session_id), None)

            if not session:
                print(f"未找到会话 ID: {session_id}")
                return
            print("编辑的会话ID:", session.id)
            dialog.session_name.setText(session.name)
            dialog.username.setText(session.username)
            dialog.host.setText(session.host)
            dialog.port.setText(str(session.port))
            if session.auth_type == "password":
                dialog._on_auth_changed(0)
                dialog.password.setText(session.password)
            elif session.auth_type == "key":
                dialog.auth_combo.setCurrentIndex(1)
                dialog._on_auth_changed(1)
                dialog.key_path.setText(session.key_path)
        if dialog.exec():
            try:
                port = int(dialog.port.text()
                           ) if dialog.port.text().isdigit() else 22
            except:
                port = 0
            host_ip = dialog.host.text()
            if valid_ip.is_valid_address(host_ip) and 10 < port < 65535:
                session_data = {
                    'name': dialog.session_name.text().strip(),
                    'host': host_ip,
                    'port': port,
                    'username': dialog.username.text().strip(),
                    'auth_type': 'password' if dialog.auth_combo.currentIndex() == 0 else 'key',
                    'password': dialog.password.text() if dialog.auth_combo.currentIndex() == 0 else '',
                    'key_path': dialog.key_path.text() if dialog.auth_combo.currentIndex() != 0 else ''
                }

                # 打印信息
                print("会话名:", session_data['name'])
                print("用户名:", session_data['username'])
                print("主机地址:", session_data['host'])
                print("端口:", session_data['port'])
                print("认证方式:", session_data['auth_type'])
                print("密码:", session_data['password'])
                print("密钥路径:", session_data['key_path'])

                try:
                    content_mode = "新建"
                    # 编辑模式删除再重建
                    if mode == "edit":
                        self.session_manager.delete_session(
                            session_id=session_id)
                        content_mode = "编辑"
                    new_session = self.session_manager.create_session(
                        name=session_data['name'],
                        host=session_data['host'],
                        username=session_data['username'],
                        port=session_data['port'],
                        auth_type=session_data['auth_type'],
                        password=session_data['password'],
                        key_path=session_data['key_path']
                    )
                    self._load_sessions()
                    # self.sessionClicked.emit(new_session.id)

                    InfoBar.success(
                        title='成功',
                        content=f"{content_mode}会话 [ {session_data['name']} ] 成功",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP_RIGHT,
                        duration=2000,
                        parent=self
                    )

                except ValueError as e:
                    InfoBar.error(
                        title='错误！！！',
                        content=f"尝试会话失败 原因：{e}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP_RIGHT,
                        duration=10000,
                        parent=self
                    )

            else:
                InfoBar.warning(
                    title='创建失败',
                    content="IP/域名/端口不合法",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=5000,    # 永不消失
                    parent=self
                )

    def refresh_sessions(self):
        """刷新会话列表"""
        self.session_manager.sessions_cache = self.session_manager.load_sessions()
        self._load_sessions()

    def showEvent(self, event):
        """显示事件 - 每次显示时刷新会话列表"""
        super().showEvent(event)
        self.refresh_sessions()
