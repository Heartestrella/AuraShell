from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem, QFrame)
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

        # Add status indicator

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

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        self.menu = RoundMenu(parent=self)

        self.action_open = Action(FIF.FOLDER, self.tr("Open a new session"))
        self.action_edit = Action(FIF.EDIT, self.tr("Edit"))
        self.action_delete = Action(FIF.DELETE, self.tr("Delete"))
        self.close_action = Action(FIF.CLOSE, self.tr('Close all subsessions'))
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
        if hasattr(self.parent_interface, 'session_manager'):
            self.parent_interface.session_manager.delete_session(
                self.session_id)
            self.parent_interface.refresh_sessions()  # Refresh list

    def showMenu(self):
        pos = self.moreButton.mapToGlobal(self.moreButton.rect().bottomRight())
        self.menu.exec(pos)

    def showContextMenu(self, pos):
        """Shows the context menu at the given position."""
        global_pos = self.mapToGlobal(pos)
        self.menu.exec(global_pos)


class MainInterface(QWidget):
    sessionClicked = pyqtSignal(str)

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

        title_layout = QHBoxLayout()
        self.title_label = TitleLabel(self.tr("SSH session management"))
        self.new_session_btn = PrimaryPushButton(
            self.tr("New Session"), self, FIF.ADD)
        self.new_session_btn.clicked.connect(self._create_edit_new_session)

        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.new_session_btn)

        layout.addLayout(title_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        # separator.setStyleSheet("background-color: rgba(255, 255, 255, 50);")
        layout.addWidget(separator)

        info_label = BodyLabel(
            self.tr("Select an existing session or create a new SSH connection"))
        info_label.setStyleSheet("color: #888888;")
        layout.addWidget(info_label)

        self.session_list = ListWidget()
        self.session_list.setSpacing(10)
        self.session_list.setStyleSheet("""

        ListWidget {
            background-color: transparent;
            border: 1px solid rgba(255, 255, 255, 30);
            border-radius: 8px;
            outline: none;
            padding: 5px; 
        }

        ListWidget::item {
            background-color: transparent;
            border: none;
            padding: 0px;
        }

        ListWidget::item:focus {
            outline: none;
        }
        """)

        self.session_list.itemDoubleClicked.connect(self._on_session_clicked)
        layout.addWidget(self.session_list)

        self.empty_label = BodyLabel(self.tr(
            "There is no session yet. Click the button in the upper right corner to create a new session."))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #666666; padding: 40px;")
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

    def _load_sessions(self):
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
        session_id = item.data(Qt.UserRole)
        self.sessionClicked.emit(session_id)

    def _create_edit_new_session(self, mode: str = "create", session_id: str = None):
        dialog = SessionDialog(self)
        sessions = self.session_manager.sessions_cache
        s_name = []
        for s in sessions:
            s_name.append(s.name)
            # dialog.jump_server_combo.addItem(s.name)
        dialog.jump_server_combo.addItems(s_name)
        if mode == "create":
            other_data = {
                'history': [],
                'host_key': "",
                'processes_md5': "",
            }
        elif mode == "edit":
            session = next(
                (s for s in self.session_manager.sessions_cache if s.id == session_id), None)

            if not session:
                print(f"Session ID not found: {session_id}")
                return

            dialog.session_name.setText(session.name)
            dialog.username.setText(session.username)
            dialog.host.setText(session.host)
            dialog.port.setText(str(session.port))
            dialog.ssh_default_path.setText(session.ssh_default_path)
            dialog.file_manager_default_path.setText(
                session.file_manager_default_path)

            other_data = {
                'history': session.history,
                'host_key': session.host_key,
                'processes_md5': session.processes_md5,
            }
            try:
                dialog.jump_server_combo.setCurrentText(session.jump_server)
            except:
                pass

            if session.auth_type == "password":
                dialog._on_auth_changed(0)
                dialog.password.setText(session.password)
            elif session.auth_type == "key":
                dialog.auth_combo.setCurrentIndex(1)
                dialog._on_auth_changed(1)
                dialog.key_path.setText(session.key_path)

            # Populate proxy fields
            proxy_type = getattr(session, 'proxy_type', 'None')
            proxy_index = dialog.proxy_type_combo.findText(proxy_type)
            if proxy_index != -1:
                dialog.proxy_type_combo.setCurrentIndex(proxy_index)
            dialog.proxy_host.setText(getattr(session, 'proxy_host', ''))
            dialog.proxy_port.setText(str(getattr(session, 'proxy_port', '')))
            dialog.proxy_username.setText(
                getattr(session, 'proxy_username', ''))
            dialog.proxy_password.setText(
                getattr(session, 'proxy_password', ''))
            dialog._on_proxy_type_changed(
                proxy_index if proxy_index != -1 else 0)

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
                    'key_path': dialog.key_path.text() if dialog.auth_combo.currentIndex() != 0 else '',
                    'proxy_type': dialog.proxy_type_combo.currentText(),
                    'proxy_host': dialog.proxy_host.text().strip(),
                    'proxy_port': int(dialog.proxy_port.text()) if dialog.proxy_port.text().isdigit() else 0,
                    'proxy_username': dialog.proxy_username.text().strip(),
                    'proxy_password': dialog.proxy_password.text(),
                    "ssh_default_path": dialog.ssh_default_path.text(),
                    "file_manager_default_path": dialog.file_manager_default_path.text(),
                }
                session_data.update(other_data)
                try:
                    content_mode = self.tr("New")
                    if mode == "edit":
                        self.session_manager.delete_session(
                            session_id=session_id)
                        content_mode = self.tr("Edit")
                    new_session = self.session_manager.create_session(
                        name=session_data['name'],
                        host=session_data['host'],
                        username=session_data['username'],
                        port=session_data['port'],
                        auth_type=session_data['auth_type'],
                        password=session_data['password'],
                        key_path=session_data['key_path'],
                        proxy_type=session_data['proxy_type'],
                        proxy_host=session_data['proxy_host'],
                        proxy_port=session_data['proxy_port'],
                        proxy_username=session_data['proxy_username'],
                        proxy_password=session_data['proxy_password'],
                        ssh_default_path=session_data["ssh_default_path"],
                        file_manager_default_path=session_data["file_manager_default_path"],
                        history=session_data["history"],
                        host_key=session_data["host_key"],
                        processes_md5=session_data["processes_md5"],
                        jump_server=dialog.jump_server_combo.currentText()
                    )
                    self._load_sessions()
                    # self.sessionClicked.emit(new_session.id)

                    InfoBar.success(
                        title=self.tr('Success'),
                        content=self.tr(
                            f"{content_mode}session [ {session_data['name']} ] success"),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP_RIGHT,
                        duration=2000,
                        parent=self
                    )

                except ValueError as e:
                    InfoBar.error(
                        title=self.tr('Error！！！'),
                        content=self.tr(f"Session attempt failed Reason：{e}"),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP_RIGHT,
                        duration=10000,
                        parent=self
                    )

            else:
                InfoBar.warning(
                    title=self.tr('Creation failed'),
                    content=self.tr(
                        "The IP/domain name/port is illegal, please re-enter"),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=5000,
                    parent=self
                )

    def refresh_sessions(self):
        self.session_manager.sessions_cache = self.session_manager.load_sessions()
        self._load_sessions()

    # def showEvent(self, event):
    #     super().showEvent(event)
    #     self.refresh_sessions()
