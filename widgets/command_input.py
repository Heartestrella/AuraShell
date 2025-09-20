from PyQt5.QtCore import Qt, pyqtSignal, QStringListModel, QPoint, QEvent, QTimer
from PyQt5.QtWidgets import QApplication, QPushButton
from qfluentwidgets import TextEdit, ListView


class CommandInput(TextEdit):
    executeCommand = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        # Check if Enter key is pressed
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Check if Shift modifier is also pressed
            if not (event.modifiers() & Qt.ShiftModifier):
                # If only Enter is pressed, emit the signal and ignore the event
                command = self.toPlainText()
                self.executeCommand.emit(command)
                self.clear()
                return  # Consume the event to prevent a newline
            else:
                # If Shift+Enter is pressed, let the base class handle it (inserts a newline)
                super().keyPressEvent(event)
        else:
            # For any other key, let the base class handle it
            super().keyPressEvent(event)
