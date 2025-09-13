from PyQt5.QtWidgets import QHBoxLayout, QLabel, QFileDialog
from qfluentwidgets import LineEdit, ComboBox, SubtitleLabel, MessageBoxBase, PushButton, InfoBar, InfoBarPosition, PasswordLineEdit
from PyQt5.QtCore import Qt, QDir


class SessionDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._font = getattr(parent, "fonts", None)
        print(self._font)
        self.titleLabel = SubtitleLabel(self.tr('New SSH Session'))
        if self._font:
            self.titleLabel.setFont(self._font)
        self.yesButton.setText(self.tr("Save"))
        self.cancelButton.setText(self.tr("Cancel"))

        self.session_name = LineEdit()
        self.username = LineEdit()
        self.host = LineEdit()
        self.port = LineEdit()
        self.auth_combo = ComboBox()
        self.password = PasswordLineEdit()
        self.key_path = LineEdit()
        self.key_browse_btn = PushButton(self.tr("Browse..."))
        self.key_browse_btn.clicked.connect(self._browse_ssh_key)
        # for w in [self.session_name, self.username, self.host, self.port,
        #           self.auth_combo, self.password, self.key_path, self.key_browse_btn]:
        #     if self._font:
        #         w.setFont(self._font)

        # Session Name
        self.session_name.setPlaceholderText(self.tr("Enter session name"))
        session_name_layout = QHBoxLayout()
        session_name_layout.addWidget(QLabel(self.tr("Session Name:")))
        session_name_layout.addWidget(self.session_name)
        session_name_layout.setStretch(1, 1)

        # Username
        self.username.setPlaceholderText(self.tr("Enter username"))
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel(self.tr("Username:")))
        username_layout.addWidget(self.username)
        username_layout.setStretch(1, 1)

        # Host
        self.host.setPlaceholderText(self.tr("e.g.: 192.168.1.100"))
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel(self.tr("Host Address:")))
        host_layout.addWidget(self.host)
        host_layout.setStretch(1, 1)

        # Port
        self.port.setPlaceholderText(self.tr("Default: 22"))
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel(self.tr("Port:")))
        port_layout.addWidget(self.port)
        port_layout.setStretch(1, 1)

        # Authentication method
        self.auth_combo.addItems(["Password", "Key"])
        self.auth_combo.currentIndexChanged.connect(self._on_auth_changed)
        auth_layout = QHBoxLayout()
        auth_layout.addWidget(QLabel(self.tr("Authentication Method:")))
        auth_layout.addWidget(self.auth_combo)
        auth_layout.setStretch(1, 1)

        # Password
        self.password.setPlaceholderText(self.tr("Enter password"))
        self.password.setEchoMode(LineEdit.Password)
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel(self.tr("Password:")))
        password_layout.addWidget(self.password)
        password_layout.setStretch(1, 1)

        # key file
        self.key_path.setPlaceholderText(self.tr("Select private key file"))
        self.key_path.setReadOnly(True)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel(self.tr("Key File:")))
        key_layout.addWidget(self.key_path)
        key_layout.addWidget(self.key_browse_btn)
        key_layout.setStretch(1, 1)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addLayout(session_name_layout)
        self.viewLayout.addLayout(username_layout)
        self.viewLayout.addLayout(host_layout)
        self.viewLayout.addLayout(port_layout)
        self.viewLayout.addLayout(auth_layout)
        self.viewLayout.addLayout(password_layout)
        self.viewLayout.addLayout(key_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.viewLayout.addLayout(button_layout)

        self.widget.setMinimumWidth(400)
        self._on_auth_changed(0)  # Initialize to password authentication

    def _on_auth_changed(self, index):
        if index == 0:  # Password
            self.password.setVisible(True)
            self.key_path.setVisible(False)
            self.key_browse_btn.setVisible(False)
        else:  # Key
            self.password.setVisible(False)
            self.key_path.setVisible(True)
            self.key_browse_btn.setVisible(True)

    def _browse_ssh_key(self):

        key_filters = (
            self.tr(
                "SSH Private Key Files (*.pem *.key ppk id_rsa id_dsa id_ecdsa id_ed25519);;")
            + self.tr("PEM Format (*.pem);;")
            + self.tr("KEY Format (*.key);;")
            + self.tr("PuTTY Format (*.ppk);;")
            + self.tr("OpenSSH Format (id_rsa id_dsa id_ecdsa id_ed25519);;")
            + self.tr("All Files (*.*)")
        )

        key_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select SSH Private Key File"),
            QDir.homePath(),
            key_filters
        )

        if key_path:
            if self._validate_ssh_key_strict(key_path):
                self.key_path.setText(key_path)
            else:
                InfoBar.error(
                    title=self.tr('Creation Failed'),
                    content=self.tr("SSH private key validation failed"),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=10000,
                    parent=self
                )

    def _validate_ssh_key_strict(self, key_path):
        import os
        import re

        if not os.path.exists(key_path):
            return False

        try:
            with open(key_path, 'r', encoding='utf-8') as f:
                content = f.read(4096)

                # OpenSSH
                openssh_pattern = r'-----BEGIN OPENSSH PRIVATE KEY-----'
                if re.search(openssh_pattern, content):
                    return True

                # PEM
                pem_pattern = r'-----BEGIN (RSA|DSA|EC) PRIVATE KEY-----'
                if re.search(pem_pattern, content):
                    return True

                # PKCS#8
                pkcs8_pattern = r'-----BEGIN PRIVATE KEY-----'
                if re.search(pkcs8_pattern, content):
                    return True

                # PuTTY
                putty_pattern = r'PuTTY-User-Key-File'
                if re.search(putty_pattern, content):
                    return True

                file_name = os.path.basename(key_path).lower()
                common_key_files = [
                    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519']
                if file_name in common_key_files:
                    if content.strip() and not content.startswith('#'):
                        return True

        except Exception:
            return False

        return False
