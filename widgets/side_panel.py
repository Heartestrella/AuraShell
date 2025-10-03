from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QStackedWidget, QLabel,
                             QPushButton, QScrollArea, QHBoxLayout)
from PyQt5.QtCore import Qt, QEvent
from tools.atool import resource_path


class TabButton(QPushButton):
    """ Custom Tab Button """
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setMinimumHeight(30)


class CustomTabBar(QScrollArea):
    """ Custom Scrollable Tab Bar """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(self.NoFrame)

        self.scroll_widget = QWidget()
        self.setWidget(self.scroll_widget)

        self.layout = QHBoxLayout(self.scroll_widget)
        self.layout.setContentsMargins(5, 0, 5, 0)
        self.layout.setSpacing(5)
        self.layout.setAlignment(Qt.AlignLeft)

    def wheelEvent(self, event):
        """ Scroll horizontally with the mouse wheel """
        delta = event.angleDelta().y()
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() - delta)
        event.accept()


class SidePanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SidePanelWidget")
        self.setMinimumWidth(150)

        self.buttons = []
        self.pages = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.tab_bar_container = QWidget()
        self.tab_bar_container.setObjectName("TabBarContainer")
        container_layout = QHBoxLayout(self.tab_bar_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.tab_bar = CustomTabBar(self)
        container_layout.addWidget(self.tab_bar)
        self.main_layout.addWidget(self.tab_bar_container)

        self.page_stack = QStackedWidget(self)
        self.main_layout.addWidget(self.page_stack)

        self.add_new_tab(QLabel("正在开发"), "AI Chat")
        for i in range(13):
            self.add_new_tab(QLabel("正在开发"), "AI Chat")

        self._update_tab_bar_visibility()
        self.setStyleSheet(self._get_style_sheet())

    def add_new_tab(self, widget, title: str):
        """Adds a new tab and its corresponding page."""
        button = TabButton(title)
        button.clicked.connect(lambda _, b=button: self._on_tab_clicked(b))
        button.installEventFilter(self)
        self.tab_bar.layout.addWidget(button)
        self.page_stack.addWidget(widget)
        self.buttons.append(button)
        self.pages.append(widget)
        button.click()
        self._update_tab_bar_visibility()

    def _on_tab_clicked(self, clicked_button: TabButton):
        """Handles tab selection."""
        for i, button in enumerate(self.buttons):
            is_checked = (button == clicked_button)
            button.setChecked(is_checked)
            if is_checked:
                self.page_stack.setCurrentIndex(i)

    def eventFilter(self, obj, event):
        """Event filter to catch double-clicks on tab buttons."""
        if event.type() == QEvent.MouseButtonDblClick and isinstance(obj, TabButton):
            self._close_tab(obj)
            return True
        return super().eventFilter(obj, event)

    def _close_tab(self, button_to_close: TabButton):
        """Closes a tab."""
        try:
            index = self.buttons.index(button_to_close)
        except ValueError:
            return

        if index == 0:
            return

        self.buttons.pop(index)
        self.tab_bar.layout.removeWidget(button_to_close)
        button_to_close.deleteLater()

        page = self.pages.pop(index)
        self.page_stack.removeWidget(page)
        page.deleteLater()

        if not any(b.isChecked() for b in self.buttons) and self.buttons:
            new_index = max(0, index - 1)
            self.buttons[new_index].click()

        self._update_tab_bar_visibility()

    def _update_tab_bar_visibility(self):
        """Hides the tab bar if there's only one tab."""
        is_visible = len(self.buttons) > 1
        self.tab_bar_container.setVisible(is_visible)

    def _get_style_sheet(self):
        return """
            #TabBarContainer {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3c3c3c;
                max-height: 40px;
            }
            CustomTabBar, CustomTabBar QWidget {
                background-color: transparent;
                border: none;
            }
            QStackedWidget {
                border: none;
                background: #252526;
            }
            TabButton {
                background: #2d2d2d;
                color: #aaaaaa;
                border: none;
                padding: 6px 10px;
                margin-right: 2px;
            }
            TabButton:hover {
                background: #3c3c3c;
                color: #ffffff;
            }
            TabButton:checked {
                background-color: #252526;
                color: #ffffff;
            }
        """
