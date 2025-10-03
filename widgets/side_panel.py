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
        # self.tabWidget.setDocumentMode(True)
        self.tabWidget.setTabPosition(QTabWidget.North)
        self.tabWidget.setMovable(True)
        self.tabWidget.setTabsClosable(False)
        self.tabWidget.tabBar().tabBarDoubleClicked.connect(self._close_tab)

        self.tabWidget.addTab(QLabel("正在开发"), "AI Chat")
        self.tabWidget.addTab(QLabel("正在开发"), "Editor")

        self.layout.addWidget(self.tabWidget)

        self.setStyleSheet(f"""
            QTabWidget::tab-bar {{
                alignment: left;
                border-bottom: 1px solid #3c3c3c;
            }}
            QTabWidget::pane {{
                border: none;
                background: #252526;
            }}
            QTabBar::tab {{
                background: #2d2d2d;
                color: #f0f0f0;
                border: 1px solid #3c3c3c;
                border-bottom: none;
                padding: 6px 10px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: #252526;
                color: #ffffff;
                margin-bottom: -1px;
            }}
            QTabBar::tab:!selected:hover {{
                background: #3c3c3c;
            }}
        """)

    def _close_tab(self, index):
        if index == 0:
            return
        self.tabWidget.removeTab(index)
