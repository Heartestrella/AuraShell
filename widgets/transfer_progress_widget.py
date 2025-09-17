from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QEvent, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
from qfluentwidgets import FluentIcon as FIF, IconWidget

class TransferProgressWidget(QWidget):
    """ File Transfer Progress Widget """
    expansionChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("transferProgressWidget")

        self.is_expanded = False
        self._animations = []
        self.transfer_items = {}

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header
        self.header = QWidget(self)
        self.header.setObjectName("header")
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(10, 5, 10, 5)
        self.header.setCursor(Qt.PointingHandCursor)

        self.title_label = QLabel("File Transfers", self.header)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setWordWrap(True)

        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch(1)

        self.header.installEventFilter(self)

        # Content area (collapsible)
        # Content area (collapsible) with ScrollArea
        self.content_area = QFrame(self)
        self.content_area.setObjectName("contentArea")
        self.content_area_layout = QVBoxLayout(self.content_area)
        self.content_area_layout.setContentsMargins(0, 0, 0, 0)
        self.content_area_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self.content_area)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2A2A2A;
                width: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        self.scroll_content = QWidget()
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(10, 5, 10, 10)
        self.content_layout.setSpacing(5)

        self.scroll_area.setWidget(self.scroll_content)
        self.content_area_layout.addWidget(self.scroll_area)


        # Initial state: collapsed
        self.content_area.setVisible(False)
        self.content_area.setMaximumHeight(0)

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_area)
        
        self._apply_stylesheet()

    def add_transfer_item(self, file_id: str, data: dict):
        if not self.isVisible():
            self.setVisible(True)

        transfer_type = data.get("type", "upload")
        filename = data.get("filename", "Unknown File")
        progress = data.get("progress", 0)

        item_widget = QFrame()
        item_widget.setObjectName("itemWidget")
        item_widget.setFixedHeight(40)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(8, 5, 8, 5)

        # --- Icon ---
        if transfer_type == "upload":
            icon, color = FIF.UP, QColor("#0078D4")
        else:
            icon, color = FIF.DOWN, QColor("#D83B01")

        status_icon = IconWidget(icon, item_widget)
        status_icon.setFixedSize(16, 16)

        # --- Filename ---
        filename_label = QLabel(filename, item_widget)
        filename_label.setWordWrap(True)

        item_layout.addWidget(status_icon)
        item_layout.addSpacing(10)
        item_layout.addWidget(filename_label)
        item_layout.addStretch(1)

        # --- Progress Label ---
        progress_label = QLabel(f"{progress}%", item_widget)
        progress_label.setObjectName("progressLabel")
        item_layout.addWidget(progress_label)

        # --- Store and add to layout ---
        self.transfer_items[file_id] = item_widget
        self.content_layout.insertWidget(0, item_widget)
        
        self.update_transfer_item(file_id, data)


    def update_transfer_item(self, file_id: str, data: dict):
        item_widget = self.transfer_items.get(file_id)
        if not item_widget:
            return

        transfer_type = data.get("type", "upload")
        progress = data.get("progress", 0)
        status_icon = item_widget.findChild(IconWidget)
        progress_label = item_widget.findChild(QLabel, "progressLabel")

        # --- Update color and icon based on type ---
        if transfer_type == "upload":
            color = QColor("#0078D4")
            if status_icon.icon != FIF.UP: status_icon.setIcon(FIF.UP)
        elif transfer_type == "download":
            color = QColor("#D83B01")
            if status_icon.icon != FIF.DOWN: status_icon.setIcon(FIF.DOWN)
        else: # completed
            color = QColor("#107C10")
            if status_icon.icon != FIF.ACCEPT: status_icon.setIcon(FIF.ACCEPT)

        status_icon.setStyleSheet(f"color: {color.name()}; background-color: transparent;")
        
        # --- Update progress label ---
        if progress_label:
            if transfer_type == "completed":
                progress_label.hide()
            else:
                progress_label.setText(f"{progress}%")
                if not progress_label.isVisible():
                    progress_label.show()

        # --- Update background style ---
        stop_pos = progress / 100.0
        base_bg = "#3C3C3C"
        if stop_pos <= 0:
            bg_style = f"background-color: {base_bg};"
        elif stop_pos >= 1:
            bg_style = f"background-color: {color.name()};"
        else:
            bg_style = f"""
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:{stop_pos} {color.name()}, stop:{stop_pos + 0.001} {base_bg}
                );
            """
        
        item_widget.setStyleSheet(f"""
            #itemWidget {{
                {bg_style}
                border-radius: 6px;
            }}
            #itemWidget > QLabel, #itemWidget > IconWidget {{
                background-color: transparent;
            }}
        """)


    def remove_transfer_item(self, file_id: str):
        item_widget = self.transfer_items.pop(file_id, None)
        if item_widget:
            item_widget.deleteLater()

        if not self.transfer_items:
            self.setVisible(False)

    def toggle_view(self):
        self.is_expanded = not self.is_expanded
        self.expansionChanged.emit(self.is_expanded)

        if self.is_expanded:
            self.content_area.setMaximumHeight(1000)
            self.content_area.setVisible(True)
        else:
            self.content_area.setVisible(False)
            self.content_area.setMaximumHeight(0)

    def eventFilter(self, obj, event):
        if obj is self.header and event.type() == QEvent.MouseButtonPress:
            self.toggle_view()
            return True
        return super().eventFilter(obj, event)

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            #transferProgressWidget {
                background-color: #2C2C2C;
                border-top: 1px solid #444444;
            }
            #header {
                background-color: transparent;
            }
            #titleLabel {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
            }
            #contentArea {
                background-color: transparent;
                border: none;
            }
            QLabel {
                color: #E0E0E0;
                background-color: transparent;
            }
        """)
