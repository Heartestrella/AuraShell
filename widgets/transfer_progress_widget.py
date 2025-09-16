from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QEvent
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from qfluentwidgets import FluentIcon as FIF, IconWidget

class TransferProgressWidget(QWidget):
    """ File Transfer Progress Widget """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("transferProgressWidget")

        self.is_expanded = False
        self._animations = []

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
        self.content_area = QFrame(self)
        self.content_area.setObjectName("contentArea")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 5, 10, 10)
        self.content_layout.setSpacing(5)


        # Initial state: collapsed
        self.content_area.setVisible(False)
        self.content_area.setMaximumHeight(0)

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_area)
        
        self._apply_stylesheet()

    def update_transfers(self, transfers: dict):
        # Clear existing items
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not transfers:
            self.setVisible(False)
            return
        
        self.setVisible(True)

        # Add updated items
        for file_id, data in transfers.items():
            transfer_type = data.get("type", "upload")
            filename = data.get("filename", "Unknown File")
            progress = data.get("progress", 0)
            
            item_widget = QFrame()
            item_widget.setObjectName("itemWidget")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(8, 5, 8, 5)

            # --- Left Icon ---
            if transfer_type == "upload":
                icon = FIF.UP
                color = QColor("#0078D4")
            elif transfer_type == "download":
                icon = FIF.DOWN
                color = QColor("#D83B01")
            else:  # completed
                icon = FIF.ACCEPT
                color = QColor("#107C10")

            status_icon = IconWidget(icon, item_widget)
            status_icon.setFixedSize(16, 16)
            status_icon.setStyleSheet(f"color: {color.name()}; background-color: transparent;")

            # --- Filename ---
            filename_label = QLabel(filename)
            filename_label.setWordWrap(True)

            item_layout.addWidget(status_icon)
            item_layout.addSpacing(10)
            item_layout.addWidget(filename_label)
            item_layout.addStretch(1)

            # --- Right Percentage Label (if not completed) ---
            if transfer_type != "completed":
                progress_label = QLabel(f"{progress}%")
                progress_label.setObjectName("progressLabel")
                item_layout.addWidget(progress_label)

            # --- Dynamic Background Style ---
            stop_pos = progress / 100.0
            base_bg = "#3C3C3C"

            if stop_pos <= 0:
                bg_style = f"background-color: {base_bg};"
            elif stop_pos >= 1:
                bg_style = f"background-color: {color.name()};"
            else:
                # The small increment (0.001) creates a sharp dividing line
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
                #itemWidget > QLabel {{
                    background-color: transparent;
                }}
            """)

            self.content_layout.addWidget(item_widget)

    def toggle_view(self):
        self.is_expanded = not self.is_expanded
        
        start_height = self.content_area.height()
        end_height = self.content_area.sizeHint().height() if self.is_expanded else 0

        self.content_area.setVisible(True)

        animation = QPropertyAnimation(self.content_area, b"maximumHeight", self)
        animation.setDuration(300)
        animation.setStartValue(start_height)
        animation.setEndValue(end_height)
        animation.setEasingCurve(QEasingCurve.InOutQuart)
        
        def on_animation_finished():
            if not self.is_expanded:
                self.content_area.setVisible(False)
            self._animations.clear()

        animation.finished.connect(on_animation_finished)
        self._animations.append(animation)
        animation.start(QPropertyAnimation.DeleteWhenStopped)

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
