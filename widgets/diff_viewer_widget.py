from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPlainTextEdit,
                             QSplitter, QLabel, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QSize
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor, QFont, QPainter, QTextBlock
import difflib

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    def lineNumberAreaWidth(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 10 + self.fontMetrics().width('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#282828"))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#888888"))
                painter.drawText(0, int(top), self.lineNumberArea.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(60, 60, 60)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)


class DiffViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.left_content = ""
        self.right_content = ""
        self._init_ui()
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        self.left_label = QLabel(self.tr("Original"))
        self.left_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 5px 10px;
                background-color: rgba(100, 100, 255, 0.1);
                border-radius: 4px;
            }
        """)
        self.right_label = QLabel(self.tr("Modified"))
        self.right_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 5px 10px;
                background-color: rgba(100, 255, 100, 0.1);
                border-radius: 4px;
            }
        """)
        self.compare_button = QPushButton(self.tr("Compare"))
        self.compare_button.setStyleSheet("""
            QPushButton {
                padding: 5px 20px;
                background-color: #007ACC;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
        """)
        self.compare_button.clicked.connect(self.compare_diff)
        header_layout.addWidget(self.left_label)
        header_layout.addStretch()
        header_layout.addWidget(self.compare_button)
        header_layout.addStretch()
        header_layout.addWidget(self.right_label)
        main_layout.addLayout(header_layout)
        self.splitter = QSplitter(Qt.Horizontal)
        self.left_editor = CodeEditor()
        self.left_editor.setPlaceholderText(self.tr("Enter or paste original text here..."))
        self._setup_editor_style(self.left_editor)
        self.right_editor = CodeEditor()
        self.right_editor.setPlaceholderText(self.tr("Enter or paste modified text here..."))
        self._setup_editor_style(self.right_editor)
        self._sync_scroll_enabled = True
        self.left_editor.verticalScrollBar().valueChanged.connect(
            lambda value: self._sync_scroll(self.left_editor, self.right_editor, value)
        )
        self.right_editor.verticalScrollBar().valueChanged.connect(
            lambda value: self._sync_scroll(self.right_editor, self.left_editor, value)
        )
        self.splitter.addWidget(self.left_editor)
        self.splitter.addWidget(self.right_editor)
        self.splitter.setSizes([500, 500])
        main_layout.addWidget(self.splitter, 1)
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("""
            QLabel {
                padding: 5px 10px;
                background-color: rgba(128, 128, 128, 0.1);
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        self.stats_label.hide()
        main_layout.addWidget(self.stats_label)
    def _setup_editor_style(self, editor):
        editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                padding: 5px;
            }
        """)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        editor.setFont(font)
    def set_left_content(self, content: str):
        self.left_content = content
        self.left_editor.setPlainText(content)
    def set_right_content(self, content: str):
        self.right_content = content
        self.right_editor.setPlainText(content)
    def compare_diff(self):
        left_text = self.left_editor.toPlainText()
        right_text = self.right_editor.toPlainText()
        self._clear_highlights()
        left_lines = left_text.splitlines()
        right_lines = right_text.splitlines()
        differ = difflib.SequenceMatcher(None, left_lines, right_lines)
        added = 0
        deleted = 0
        modified = 0
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'delete':
                deleted += (i2 - i1)
                self._highlight_lines(self.left_editor, i1, i2, QColor(255, 100, 100, 80))
            elif tag == 'insert':
                added += (j2 - j1)
                self._highlight_lines(self.right_editor, j1, j2, QColor(100, 255, 100, 80))
            elif tag == 'replace':
                modified += max(i2 - i1, j2 - j1)
                self._highlight_lines(self.left_editor, i1, i2, QColor(255, 200, 100, 80))
                self._highlight_lines(self.right_editor, j1, j2, QColor(255, 200, 100, 80))
        self._show_stats(added, deleted, modified)
    def _highlight_lines(self, editor, start_line, end_line, color):
        cursor = editor.textCursor()
        cursor.setPosition(0)
        for _ in range(start_line):
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor)
        cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
        start_pos = cursor.position()
        for _ in range(end_line - start_line - 1):
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor)
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.MoveAnchor)
        end_pos = cursor.position()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        cursor.mergeCharFormat(fmt)
        cursor.clearSelection()
    def _clear_highlights(self):
        left_cursor = self.left_editor.textCursor()
        left_cursor.select(QTextCursor.Document)
        fmt = QTextCharFormat()
        left_cursor.setCharFormat(fmt)
        left_cursor.clearSelection()
        right_cursor = self.right_editor.textCursor()
        right_cursor.select(QTextCursor.Document)
        fmt = QTextCharFormat()
        right_cursor.setCharFormat(fmt)
        right_cursor.clearSelection()
        self.stats_label.hide()
    def _show_stats(self, added, deleted, modified):
        if added == 0 and deleted == 0 and modified == 0:
            self.stats_label.setText(self.tr("✓ No differences found"))
            self.stats_label.setStyleSheet("""
                QLabel {
                    padding: 5px 10px;
                    background-color: rgba(100, 255, 100, 0.2);
                    border-radius: 4px;
                    font-size: 12px;
                    color: #4CAF50;
                }
            """)
        else:
            stats_text = self.tr(f"Differences: {added} added, {deleted} deleted, {modified} modified")
            self.stats_label.setText(stats_text)
            self.stats_label.setStyleSheet("""
                QLabel {
                    padding: 5px 10px;
                    background-color: rgba(255, 200, 100, 0.2);
                    border-radius: 4px;
                    font-size: 12px;
                    color: #FF9800;
                }
            """)
        self.stats_label.show()
    def get_left_content(self):
        return self.left_editor.toPlainText()
    def get_right_content(self):
        return self.right_editor.toPlainText()
    def _sync_scroll(self, source_editor, target_editor, value):
        if not self._sync_scroll_enabled:
            return
        self._sync_scroll_enabled = False
        target_editor.verticalScrollBar().setValue(value)
        self._sync_scroll_enabled = True
    def clear_all(self):
        self.left_editor.clear()
        self.right_editor.clear()
        self.stats_label.hide()