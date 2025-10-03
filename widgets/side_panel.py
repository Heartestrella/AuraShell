from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QStackedWidget, QLabel,
                             QPushButton, QScrollArea, QHBoxLayout)
from PyQt5.QtCore import Qt, QEvent
from qfluentwidgets import RoundMenu, CheckableMenu, Action, FluentIcon as FIF
from tools.atool import resource_path
from tools.setting_config import SCM
from widgets.ai_chat_widget import AiChatWidget
from widgets.editor_widget import EditorWidget
import uuid


class TabButton(QPushButton):
    """ Custom Tab Button """
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setMinimumHeight(30)
        self.setContextMenuPolicy(Qt.CustomContextMenu)


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
        delta = event.angleDelta().y()
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() - delta)
        event.accept()


class SidePanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SidePanelWidget")
        self.setMinimumWidth(150)
        self.tabs = {}
        self.tab_order = []
        self.scm = SCM()  # Setting config manager
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
        self.add_new_tab(AiChatWidget(), "AI Chat", {"test": "test"})
        self.add_new_tab(EditorWidget(), "Editor", {"path": r"C:\Users\Administrator\Desktop\editor_widget1.py"})
        self._update_tab_bar_visibility()
        self.setStyleSheet(self._get_style_sheet())

    def add_new_tab(self, widget, title: str, extra_data: dict = None):
        tab_id = str(uuid.uuid4())
        widget.set_tab_id(tab_id)
        button = TabButton(title)
        button.clicked.connect(lambda _, tid=tab_id: self._on_tab_clicked(tid))
        button.customContextMenuRequested.connect(lambda pos, tid=tab_id: self._show_tab_context_menu(pos, tid))
        button.installEventFilter(self)
        self.tab_bar.layout.addWidget(button)
        self.page_stack.addWidget(widget)
        self.tabs[tab_id] = {
            "button": button,
            "page": widget,
            "data": extra_data
        }
        self.tab_order.append(tab_id)
        button.click()
        self._update_tab_bar_visibility()
        return tab_id

    def _on_tab_clicked(self, clicked_tab_id: str):
        if clicked_tab_id not in self.tabs:
            return
        page_to_show = self.tabs[clicked_tab_id]['page']
        for tab_id, tab_info in self.tabs.items():
            is_checked = (tab_id == clicked_tab_id)
            tab_info['button'].setChecked(is_checked)
        self.page_stack.setCurrentWidget(page_to_show)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonDblClick and isinstance(obj, TabButton):
            self._close_tab(obj)
            return True
        return super().eventFilter(obj, event)

    def _close_tab(self, button_to_close: TabButton):
        tab_id_to_close = None
        for tab_id, tab_info in self.tabs.items():
            if tab_info['button'] == button_to_close:
                tab_id_to_close = tab_id
                break
        if not tab_id_to_close:
            return
        try:
            index = self.tab_order.index(tab_id_to_close)
        except ValueError:
            return
        if index == 0:
            return
        was_checked = button_to_close.isChecked()
        self.tab_order.pop(index)
        tab_info = self.tabs.pop(tab_id_to_close)
        page = tab_info['page']
        
        self.tab_bar.layout.removeWidget(button_to_close)
        button_to_close.deleteLater()
        self.page_stack.removeWidget(page)
        page.deleteLater()
        if was_checked and self.tab_order:
            new_index = max(0, index - 1)
            new_tab_id_to_select = self.tab_order[new_index]
            self.tabs[new_tab_id_to_select]['button'].click()
        self._update_tab_bar_visibility()

    def _update_tab_bar_visibility(self):
        is_visible = len(self.tabs) > 1
        self.tab_bar_container.setVisible(is_visible)

    def switch_to_tab(self, tab_id: str):
        if tab_id in self.tabs:
            self.tabs[tab_id]['button'].click()
            return True
        return False

    def get_tab_data_by_uuid(self, tab_id: str):
        if tab_id in self.tabs:
            return self.tabs[tab_id]['data']
        return None

    def set_tab_data_by_uuid(self, tab_id: str, data: dict):
        if tab_id in self.tabs:
            self.tabs[tab_id]['data'] = data

    def _show_tab_context_menu(self, pos, tab_id):
        """Show context menu for tab"""
        if tab_id not in self.tabs:
            return
            
        widget = self.tabs[tab_id]['page']
        button = self.tabs[tab_id]['button']
        
        # Check widget type and create appropriate menu
        if isinstance(widget, EditorWidget):
            # Create checkable menu for editor
            menu = CheckableMenu(parent=self)
            
            # Auto-save toggle action (global setting)
            auto_save_action = Action(FIF.SAVE, self.tr("Auto-save on focus lost (Global)"))
            auto_save_action.setCheckable(True)
            auto_save_action.setChecked(self.scm.read_config().get("editor_auto_save_on_focus_lost", False))
            auto_save_action.triggered.connect(self._toggle_global_auto_save)
            menu.addAction(auto_save_action)
            
            # Add separator
            menu.addSeparator()
            
            # Close tab action
            close_action = Action(FIF.CLOSE, self.tr("Close Tab"))
            close_action.triggered.connect(lambda: self._close_tab(button))
            menu.addAction(close_action)
            
        elif isinstance(widget, AiChatWidget):
            # Create regular menu for AI chat
            menu = RoundMenu(parent=self)
            
            # For AiChatWidget, just add close action for now
            close_action = Action(FIF.CLOSE, self.tr("Close Tab"))
            close_action.triggered.connect(lambda: self._close_tab(button))
            menu.addAction(close_action)
        else:
            return
        
        # Show menu at cursor position
        menu.exec_(button.mapToGlobal(pos))
    
    def _toggle_global_auto_save(self, enabled):
        """Toggle global auto-save setting"""
        # Save to config only
        self.scm.revise_config("editor_auto_save_on_focus_lost", enabled)

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
