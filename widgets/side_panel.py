# coding:utf-8
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt5.QtCore import Qt
from tools.atool import resource_path


class SidePanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SidePanelWidget")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.tabWidget = QTabWidget(self)
        self.tabWidget.setTabPosition(QTabWidget.North)
        self.tabWidget.setMovable(True)
        self.tabWidget.setTabsClosable(True)

        # Add example tabs
        self.tabWidget.addTab(QLabel("AI Chat (Placeholder)"), "AI Chat")
        self.tabWidget.addTab(QLabel("Web Browser (Placeholder)"), "Browser")
        self.tabWidget.addTab(QLabel("Code Editor (Placeholder)"), "Editor")

        self.layout.addWidget(self.tabWidget)

        close_icon_path = resource_path("resource/icons/close.svg").replace("\\", "/")
        self.setStyleSheet(f"""
            QTabWidget::pane {{
                border-top: 1px solid #3c3c3c;
                background: #252526;
            }}
            QTabWidget QTabBar::tab {{
                background: #2d2d2d;
                color: #f0f0f0;
                border: none;
                padding: 8px 24px 8px 12px;
                margin-left: 1px;
            }}
            QTabWidget QTabBar::tab:selected {{
                background: #252526;
                color: #ffffff;
            }}
            QTabWidget QTabBar::tab:!selected:hover {{
                background: #3c3c3c;
            }}
            QTabBar::close-button {{
                image: url("{close_icon_path}");
                subcontrol-position: right;
                subcontrol-origin: padding;
                right: 4px;
            }}
            QTabBar::close-button:hover {{
                background: #555555;
                border-radius: 2px;
            }}
        """)
