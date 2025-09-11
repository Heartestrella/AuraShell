from PyQt5.QtWidgets import QHBoxLayout, QLabel
from qfluentwidgets import LineEdit, ComboBox, SubtitleLabel, MessageBoxBase, PushButton, InfoBar, InfoBarPosition, PasswordLineEdit
from PyQt5.QtCore import Qt


class SessionDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._font = getattr(parent, "fonts", None)
        print(self._font)
        self.titleLabel = SubtitleLabel('新的SSH会话')
        if self._font:
            self.titleLabel.setFont(self._font)
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        # 输入控件
        self.session_name = LineEdit()
        self.username = LineEdit()
        self.host = LineEdit()
        self.port = LineEdit()
        self.auth_combo = ComboBox()
        self.password = PasswordLineEdit()
        self.key_path = LineEdit()
        self.key_browse_btn = PushButton("浏览...")
        self.key_browse_btn.clicked.connect(self._browse_ssh_key)
        # for w in [self.session_name, self.username, self.host, self.port,
        #           self.auth_combo, self.password, self.key_path, self.key_browse_btn]:
        #     if self._font:
        #         w.setFont(self._font)

        # 会话名
        self.session_name.setPlaceholderText("输入会话名称")
        session_name_layout = QHBoxLayout()
        session_name_layout.addWidget(QLabel("会话名:"))
        session_name_layout.addWidget(self.session_name)
        session_name_layout.setStretch(1, 1)

        # 用户名
        self.username.setPlaceholderText("输入用户名")
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("用户名:"))
        username_layout.addWidget(self.username)
        username_layout.setStretch(1, 1)

        # 主机
        self.host.setPlaceholderText("例如: 192.168.1.100")
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("主机地址:"))
        host_layout.addWidget(self.host)
        host_layout.setStretch(1, 1)

        # 端口
        self.port.setPlaceholderText("默认: 22")
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        port_layout.addWidget(self.port)
        port_layout.setStretch(1, 1)

        # 认证方式
        self.auth_combo.addItems(["密码", "密钥"])
        self.auth_combo.currentIndexChanged.connect(self._on_auth_changed)
        auth_layout = QHBoxLayout()
        auth_layout.addWidget(QLabel("认证方式:"))
        auth_layout.addWidget(self.auth_combo)
        auth_layout.setStretch(1, 1)

        # 密码
        self.password.setPlaceholderText("输入密码")
        self.password.setEchoMode(LineEdit.Password)
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("密码:"))
        password_layout.addWidget(self.password)
        password_layout.setStretch(1, 1)

        # 密钥文件
        self.key_path.setPlaceholderText("选择私钥文件")
        self.key_path.setReadOnly(True)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("密钥文件:"))
        key_layout.addWidget(self.key_path)
        key_layout.addWidget(self.key_browse_btn)
        key_layout.setStretch(1, 1)

        # 添加所有布局到对话框内容布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addLayout(session_name_layout)
        self.viewLayout.addLayout(username_layout)
        self.viewLayout.addLayout(host_layout)
        self.viewLayout.addLayout(port_layout)
        self.viewLayout.addLayout(auth_layout)
        self.viewLayout.addLayout(password_layout)
        self.viewLayout.addLayout(key_layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.viewLayout.addLayout(button_layout)

        # 设置对话框最小宽度
        self.widget.setMinimumWidth(400)

        # 默认显示密码输入
        self._on_auth_changed(0)

    def _on_auth_changed(self, index):
        """根据认证方式显示密码或密钥输入框"""
        if index == 0:  # 密码
            self.password.setVisible(True)
            self.key_path.setVisible(False)
            self.key_browse_btn.setVisible(False)
        else:  # 密钥
            self.password.setVisible(False)
            self.key_path.setVisible(True)
            self.key_browse_btn.setVisible(True)

    def _browse_ssh_key(self):
        """浏览并选择SSH密钥文件"""
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.QtCore import QDir

        # 设置文件过滤器，只显示常见的SSH密钥格式
        key_filters = (
            "SSH私钥文件 (*.pem *.key ppk id_rsa id_dsa id_ecdsa id_ed25519);;"
            "PEM格式 (*.pem);;"
            "KEY格式 (*.key);;"
            "PuTTY格式 (*.ppk);;"
            "OpenSSH格式 (id_rsa id_dsa id_ecdsa id_ed25519);;"
            "所有文件 (*.*)"
        )

        # 打开文件对话框
        key_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择SSH私钥文件",
            QDir.homePath(),  # 默认从用户主目录开始
            key_filters
        )

        if key_path:
            if self._validate_ssh_key_strict(key_path):
                self.key_path.setText(key_path)
            else:
                InfoBar.error(
                    title='创建失败',
                    content="SSH密钥文件验证失败",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=10000,
                    parent=self
                )

    def _validate_ssh_key_strict(self, key_path):
        """更严格的SSH密钥验证"""
        import os
        import re

        if not os.path.exists(key_path):
            return False

        try:
            with open(key_path, 'r', encoding='utf-8') as f:
                content = f.read(4096)

                # OpenSSH私钥格式
                openssh_pattern = r'-----BEGIN OPENSSH PRIVATE KEY-----'
                if re.search(openssh_pattern, content):
                    return True

                # PEM格式私钥
                pem_pattern = r'-----BEGIN (RSA|DSA|EC) PRIVATE KEY-----'
                if re.search(pem_pattern, content):
                    return True

                # PKCS#8格式
                pkcs8_pattern = r'-----BEGIN PRIVATE KEY-----'
                if re.search(pkcs8_pattern, content):
                    return True

                # PuTTY格式
                putty_pattern = r'PuTTY-User-Key-File'
                if re.search(putty_pattern, content):
                    return True

                # 检查常见的无扩展名密钥文件
                file_name = os.path.basename(key_path).lower()
                common_key_files = [
                    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519']
                if file_name in common_key_files:
                    # 基本内容检查
                    if content.strip() and not content.startswith('#'):
                        return True

        except Exception:
            return False

        return False
