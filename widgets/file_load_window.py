import sys
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QScrollArea
from qfluentwidgets import CardWidget, BodyLabel, CaptionLabel, PushButton, IconWidget, ProgressRing, ScrollArea, FluentIcon, setTheme, Theme
from PyQt5.QtWidgets import QHBoxLayout
from qframelesswindow import FramelessWindow


class DownloadCard(CardWidget):
    file_stop = pyqtSignal(object)

    def __init__(self, title, content, file_id, action_type, parent=None):
        super().__init__(parent)
        self.file_id = file_id

        if action_type == "upload":
            icon = FluentIcon.UP
        elif action_type == "download":
            icon = FluentIcon.DOWNLOAD

        self.iconWidget = IconWidget(icon)
        self.titleLabel = BodyLabel(self)
        self.titleLabel.setText(title)
        self.contentLabel = CaptionLabel(self)  # 不直接设置文本
        self.contentLabel.setText(content)
        self.stopButton = PushButton(self.tr("Stop"), self)
        self.progressRing = ProgressRing(self)
        self.progressRing.setFixedSize(48, 48)
        self.progressRing.setValue(0)
        self.progressRing.setTextVisible(True)

        # 设置标签的样式 - 关键修复
        self.titleLabel.setStyleSheet("""
            BodyLabel {
                color: rgb(220, 220, 220);
                background-color: transparent;
            }
        """)

        self.contentLabel.setStyleSheet("""
            CaptionLabel {
                color: rgb(160, 160, 160);
                background-color: transparent;
            }
        """)

        # 设置卡片样式
        self.setStyleSheet("""
            DownloadCard {
                background-color: rgb(49, 49, 49);
                border: 1px solid rgb(59, 59, 59);
                border-radius: 6px;
            }
            PushButton {
                background-color: rgb(69, 69, 69);
                color: rgb(220, 220, 220);
                border: 1px solid rgb(89, 89, 89);
                border-radius: 4px;
                padding: 6px 12px;
            }
            PushButton:hover {
                background-color: rgb(79, 79, 79);
            }
        """)

        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        self.setFixedHeight(73)
        self.iconWidget.setFixedSize(32, 32)
        self.stopButton.setFixedWidth(120)

        self.hBoxLayout.setContentsMargins(20, 11, 11, 11)
        self.hBoxLayout.setSpacing(15)
        self.hBoxLayout.addWidget(self.iconWidget)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.addWidget(self.contentLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)
        self.hBoxLayout.addLayout(self.vBoxLayout)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.stopButton, 0, Qt.AlignRight)
        self.hBoxLayout.addWidget(self.progressRing, 0, Qt.AlignRight)

        self.stopButton.clicked.connect(self.send_emit)

    def send_emit(self):
        print(self.file_id)
        self.file_stop.emit(self.file_id)


class FileWindow(FramelessWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(600, 400)
        self.cards = {}
        self.titleBar.maxBtn.hide()
        self.titleBar.minBtn.hide()
        self.setWindowFlag(Qt.Tool, True)

        # 设置窗口圆角和背景
        self.setObjectName("fileWindow")
        self.setStyleSheet("""
            #fileWindow {
                background-color: rgb(39, 39, 39);
                border: 1px solid rgb(29, 29, 29);
                border-radius: 10px;
            }
        """)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 设置标题栏样式（顶部圆角）
        self.titleBar.setStyleSheet("""
            StandardTitleBar {
                background-color: rgb(49, 49, 49);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid rgb(29, 29, 29);
            }
            StandardTitleBar QLabel {
                color: rgb(220, 220, 220);
                font-weight: 500;
                font-size: 11px;
            }
        """)

        # 滚动区域
        scroll_area = ScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        # 容器，用来放卡片
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: rgb(39, 39, 39);
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        scroll_area.setWidget(container)

        # 布局
        self.mainlayout = QVBoxLayout(container)
        self.mainlayout.setContentsMargins(20, 20, 20, 20)
        self.mainlayout.setSpacing(10)

        main_layout.addWidget(self.titleBar)
        main_layout.addWidget(scroll_area)

    def add_card(self, title, content, file_id, action_type):
        card = DownloadCard(title, content, file_id, action_type, self)
        self.mainlayout.addWidget(card)
        self.cards[file_id] = card
        card.file_stop.connect(self.handle_stop)

    def handle_stop(self, file_id):
        pass

    def set_processes(self, value, file_id):
        card: DownloadCard = self.cards.get(file_id)
        if card:
            card.progressRing.setValue(value)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
