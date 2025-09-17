from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QEvent, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
from qfluentwidgets import FluentIcon as FIF, IconWidget

class TransferProgressWidget(QWidget):
    """ File Transfer Progress Widget """
    expansionChanged = pyqtSignal(bool)
    cancelRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("transferProgressWidget")

        self.is_expanded = False
        self._animations = []
        self.transfer_items = {}
        self.completed_count = 0
        self.total_count = 0

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

        self.count_label = QLabel("", self.header)
        self.count_label.setObjectName("countLabel")

        self.header_layout.addWidget(self.title_label, 0, Qt.AlignLeft)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.count_label, 0, Qt.AlignRight)

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
        self.content_layout.addStretch(1)

        self.scroll_area.setWidget(self.scroll_content)
        self.content_area_layout.addWidget(self.scroll_area)


        # Initial state: collapsed
        self.content_area.setVisible(False)
        self.content_area.setMaximumHeight(0)

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_area)
        
        self._apply_stylesheet()
        self._update_title()

    def add_transfer_item(self, file_id: str, data: dict):
        if not self.isVisible():
            self.setVisible(True)

        if file_id in self.transfer_items:
            # If item already exists, just update it
            self.update_transfer_item(file_id, data)
            return

        self.total_count += 1
        self._update_title()

        transfer_type = data.get("type", "upload")
        filename = data.get("filename", "Unknown File")
        progress = data.get("progress", 0)

        item_widget = QFrame()
        item_widget.setObjectName("itemWidget")
        item_widget.setFixedHeight(40)
        item_widget.setCursor(Qt.PointingHandCursor)
        item_widget.installEventFilter(self)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(8, 5, 8, 5)

        # --- Icon ---
        if transfer_type == "upload":
            icon, color = FIF.UP, QColor("#0078D4")
        else:
            icon, color = FIF.DOWN, QColor("#D83B01")

        status_icon = IconWidget(icon, item_widget)
        status_icon.setObjectName("statusIcon")
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

        # --- Waiting Icon ---
        waiting_icon = IconWidget(FIF.HISTORY, item_widget)
        waiting_icon.setObjectName("waitingIcon")
        waiting_icon.setFixedSize(16, 16)
        waiting_icon.hide()
        item_layout.addWidget(waiting_icon)
        
        # --- Completed Icon ---
        completed_icon = IconWidget(FIF.ACCEPT, item_widget)
        completed_icon.setObjectName("completedIcon")
        completed_icon.setFixedSize(16, 16)
        completed_icon.setStyleSheet(
            f"color: {QColor('#107C10').name()}; background-color: transparent;")
        completed_icon.hide()
        item_layout.addWidget(completed_icon)

        # --- Cancel Icon (for hover) ---
        cancel_icon = IconWidget(FIF.DELETE, item_widget)
        cancel_icon.setObjectName("cancelIcon")
        cancel_icon.setFixedSize(16, 16)
        cancel_icon.setStyleSheet("color: #E81123;")
        cancel_icon.hide()
        item_layout.addWidget(cancel_icon)

        # --- Store and add to layout ---
        item_widget.setProperty("transfer_type", transfer_type)
        # Add a property to track completion status to avoid double counting
        item_widget.setProperty("is_completed", False)
        self.transfer_items[file_id] = item_widget
        self.content_layout.insertWidget(0, item_widget)
        
        self.update_transfer_item(file_id, data)


    def update_transfer_item(self, file_id: str, data: dict):
        item_widget = self.transfer_items.get(file_id)
        if not item_widget:
            return

        item_widget.setProperty("last_data", data) # Store data for hover state restoration
        transfer_type = data.get("type", "upload")
        progress = data.get("progress", 0)
        status_icon = item_widget.findChild(IconWidget, "statusIcon")
        progress_label = item_widget.findChild(QLabel, "progressLabel")
        completed_icon = item_widget.findChild(IconWidget, "completedIcon")
        waiting_icon = item_widget.findChild(IconWidget, "waitingIcon")
        cancel_icon = item_widget.findChild(IconWidget, "cancelIcon")
        
        if not all([status_icon, progress_label, completed_icon, waiting_icon, cancel_icon]):
            return

        # Hide cancel icon unless it's being hovered
        if not item_widget.underMouse():
            cancel_icon.hide()

        # --- Update widgets based on transfer type ---
        if transfer_type == "completed":
            if not item_widget.property("is_completed"):
                item_widget.setProperty("is_completed", True)
                self.completed_count += 1
                self._update_title()

            color = QColor("#107C10")  # Green for completed
            progress_label.hide()
            waiting_icon.hide()
            completed_icon.show()

            # Keep original icon but update color to green
            original_type = item_widget.property("transfer_type")
            if original_type == "upload":
                status_icon.setIcon(FIF.UP)
            elif original_type == "download":
                status_icon.setIcon(FIF.DOWN)
            status_icon.setStyleSheet(
                f"color: {color.name()}; background-color: transparent;")
        
        elif progress == -1:  # Waiting state
            progress_label.hide()
            completed_icon.hide()
            waiting_icon.show()

            if transfer_type == "upload":
                color = QColor("#0078D4")
            else: # download
                color = QColor("#D83B01")
            
            status_icon.setStyleSheet(f"color: {color.name()}; background-color: transparent;")
            waiting_icon.setStyleSheet(f"color: {color.name()}; background-color: transparent;")

        else:  # In-progress upload or download
            progress_label.show()
            completed_icon.hide()
            waiting_icon.hide()
            progress_label.setText(f"{progress}%")

            if transfer_type == "upload":
                color = QColor("#0078D4")
                if status_icon.icon != FIF.UP: status_icon.setIcon(FIF.UP)
            elif transfer_type == "download":
                color = QColor("#D83B01")
                if status_icon.icon != FIF.DOWN: status_icon.setIcon(FIF.DOWN)
            
            status_icon.setStyleSheet(f"color: {color.name()}; background-color: transparent;")

        # --- Update background style ---
        stop_pos = progress / 100.0
        base_bg = "#3C3C3C"
        hover_bg = "#5A5A5A"  # A brighter background for hover

        # Define styles for normal and hover states
        bg_style = ""
        hover_style = ""

        if progress < 0:  # Waiting state
            bg_style = f"background-color: {base_bg};"
            hover_style = f"background-color: {hover_bg};"
        elif stop_pos >= 1:  # Completed or 100%
            hover_color = QColor(color).lighter(120).name()
            bg_style = f"background-color: {color.name()};"
            hover_style = f"background-color: {hover_color};"
        else:  # In-progress
            bg_style = f"""
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:{stop_pos} {color.name()}, stop:{stop_pos + 0.001} {base_bg}
                );
            """
            hover_style = f"""
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:{stop_pos} {color.name()}, stop:{stop_pos + 0.001} {hover_bg}
                );
            """
        
        item_widget.setStyleSheet(f"""
            #itemWidget {{
                {bg_style}
                border-radius: 6px;
            }}
            #itemWidget:hover {{
                {hover_style}
            }}
            #itemWidget > QLabel, #itemWidget > IconWidget {{
                background-color: transparent;
            }}
        """)


    def remove_transfer_item(self, file_id: str):
        item_widget = self.transfer_items.pop(file_id, None)
        if item_widget:
            if item_widget.property("is_completed"):
                self.completed_count -= 1
            self.total_count -= 1
            self._update_title()
            item_widget.deleteLater()

        # Keep the widget visible even when the list is empty
        # if not self.transfer_items:
        #     self.setVisible(False)

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
        
        if "itemWidget" in str(obj.objectName()):
            # Find all relevant child widgets
            progress_label = obj.findChild(QLabel, "progressLabel")
            completed_icon = obj.findChild(IconWidget, "completedIcon")
            waiting_icon = obj.findChild(IconWidget, "waitingIcon")
            cancel_icon = obj.findChild(IconWidget, "cancelIcon")

            if event.type() == QEvent.Enter:
                if progress_label: progress_label.hide()
                if completed_icon: completed_icon.hide()
                if waiting_icon: waiting_icon.hide()
                if cancel_icon: cancel_icon.show()
                return True
            
            elif event.type() == QEvent.Leave:
                if cancel_icon: cancel_icon.hide()
                # Restore the original state by re-calling update
                file_id = next((fid for fid, widget in self.transfer_items.items() if widget == obj), None)
                last_data = obj.property("last_data")
                if file_id and last_data:
                    self.update_transfer_item(file_id, last_data)
                return True

            elif event.type() == QEvent.MouseButtonPress:
                file_id = next((fid for fid, widget in self.transfer_items.items() if widget == obj), None)
                if file_id:
                    self.cancelRequested.emit(file_id)
                return True

        return super().eventFilter(obj, event)

    def _update_title(self):
        """Updates the title label with the current transfer counts."""
        self.count_label.setText(f"({self.completed_count}/{self.total_count})")

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            #transferProgressWidget {
                background-color: #2C2C2C;
                border-top: 1px solid #444444;
            }
            #header {
                background-color: transparent;
            }
            #titleLabel, #countLabel {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
                background-color: transparent;
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
