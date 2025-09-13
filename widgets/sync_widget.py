from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget
from qfluentwidgets import LineEdit, SubtitleLabel, MessageBoxBase,  PasswordLineEdit
from tools.font_config import font_config


class SycnWidget(MessageBoxBase):
    def __init__(self, parent=None,):
        super().__init__(parent)
        font_ = font_config()
        self._font = font_.get_font()

        self.titleLabel = SubtitleLabel(self.tr('Sycn Settings'))
        self.yesButton.setText(self.tr("Sycn"))
        self.cancelButton.setText(self.tr("Cancel"))

        self.username = LineEdit()
        self.password = PasswordLineEdit()

        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel(self.tr("Username:")))
        username_layout.addWidget(self.username)

        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel(self.tr("Password:")))
        password_layout.addWidget(self.password)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addLayout(username_layout)
        self.viewLayout.addLayout(password_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.viewLayout.addLayout(button_layout)

        self.widget.setMinimumWidth(400)

        self.set_font_recursive(self, self._font)

    def set_font_recursive(self, widget: QWidget, font):
        """
        Recursively set the font for a widget and all its children.
        """
        if font is None:
            return
        widget.setFont(font)
        for child in widget.findChildren(QWidget):
            child.setFont(font)
