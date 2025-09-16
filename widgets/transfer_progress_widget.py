from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar
from qfluentwidgets import PushButton, FluentIcon as FIF

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

        self.title_label = QLabel("File Transfers", self.header)
        self.title_label.setObjectName("titleLabel")

        self.toggle_button = PushButton(self.header)
        self.toggle_button.setIcon(FIF.UP)
        self.toggle_button.setFixedSize(30, 30)
        self.toggle_button.clicked.connect(self.toggle_view)
        
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.toggle_button)

        # Content area (collapsible)
        self.content_area = QFrame(self)
        self.content_area.setObjectName("contentArea")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 5, 10, 10)
        self.content_layout.setSpacing(8)

        # Add dummy data for testing
        self._add_transfer_item("upload", "Uploading (3/5)", 60)
        self._add_file_item("important_document_final_v2.docx", 65)
        self._add_file_item("summer_vacation_photos.zip", 20)
        self._add_transfer_item("download", "Downloading (1/2)", 50)
        self._add_file_item("project_presentation_video.mp4", 85)

        # Initial state: collapsed
        self.content_area.setVisible(False)
        self.content_area.setMaximumHeight(0)

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_area)
        
        self._apply_stylesheet()


    def _add_transfer_item(self, type_, text, value):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(2)

        label = QLabel(text)
        progress_bar = QProgressBar()
        progress_bar.setValue(value)
        
        if type_ == "upload":
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #0078D4; }")
        else:
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #107C10; }")

        layout.addWidget(label)
        layout.addWidget(progress_bar)
        self.content_layout.addWidget(container)


    def _add_file_item(self, filename, progress):
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(15, 0, 0, 0)

        # Here you could add a file type icon
        # icon_label = QLabel() 
        # item_layout.addWidget(icon_label)

        filename_label = QLabel(filename)
        progress_label = QLabel(f"{progress}%")
        
        item_layout.addWidget(filename_label)
        item_layout.addStretch(1)
        item_layout.addWidget(progress_label)
        self.content_layout.addWidget(item_widget)


    def toggle_view(self):
        self.is_expanded = not self.is_expanded
        
        self.toggle_button.setIcon(FIF.DOWN if self.is_expanded else FIF.UP)
        
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
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                height: 8px;
            }
            QProgressBar::chunk {
                border-radius: 3px;
            }
        """)
