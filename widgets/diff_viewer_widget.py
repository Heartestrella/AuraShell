from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPlainTextEdit,
                             QSplitter, QLabel, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QSize
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor, QFont, QPainter, QTextBlock
import difflib
import diff_match_patch as dmp_module

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
        pass


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
        self.left_editor.textChanged.connect(self._on_left_text_changed)
        self.right_editor.textChanged.connect(self._on_right_text_changed)
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
    def _on_left_text_changed(self):
        if hasattr(self, '_comparing'):
            return
        self.left_content = ""
    def _on_right_text_changed(self):
        if hasattr(self, '_comparing'):
            return
        self.right_content = ""
    def compare_diff(self):
        self._comparing = True
        if not self.left_content:
            self.left_content = self.left_editor.toPlainText()
        else:
            self.left_editor.setPlainText(self.left_content)
        if not self.right_content:
            self.right_content = self.right_editor.toPlainText()
        else:
            self.right_editor.setPlainText(self.right_content)
        left_text = self.left_content
        right_text = self.right_content
        self._clear_highlights()
        left_lines = left_text.splitlines()
        right_lines = right_text.splitlines()
        differ = difflib.SequenceMatcher(None, left_lines, right_lines)
        dmp = dmp_module.diff_match_patch()
        added = 0
        deleted = 0
        modified = 0
        left_display = []
        right_display = []
        left_highlights = []
        right_highlights = []
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'equal':
                for i in range(i1, i2):
                    left_display.append(left_lines[i])
                    right_display.append(right_lines[j1 + (i - i1)])
            elif tag == 'delete':
                deleted += (i2 - i1)
                for i in range(i1, i2):
                    line_idx = len(left_display)
                    left_display.append(left_lines[i])
                    right_display.append('')
                    left_highlights.append((line_idx, None, QColor(255, 100, 100, 80)))
            elif tag == 'insert':
                added += (j2 - j1)
                for j in range(j1, j2):
                    line_idx = len(right_display)
                    left_display.append('')
                    right_display.append(right_lines[j])
                    right_highlights.append((line_idx, None, QColor(100, 255, 100, 80)))
            elif tag == 'replace':
                num_deleted = i2 - i1
                num_added = j2 - j1
                if num_deleted == 1 and num_added == 1:
                    line_idx = len(left_display)
                    left_line = left_lines[i1]
                    right_line = right_lines[j1]
                    left_display.append(left_line)
                    right_display.append(right_line)
                    diffs = dmp.diff_main(left_line, right_line)
                    dmp.diff_cleanupSemantic(diffs)
                    left_pos = 0
                    right_pos = 0
                    left_char_ranges = []
                    right_char_ranges = []
                    for op, text in diffs:
                        text_len = len(text)
                        if op == -1:
                            left_char_ranges.append((left_pos, left_pos + text_len))
                            left_pos += text_len
                        elif op == 1:
                            right_char_ranges.append((right_pos, right_pos + text_len))
                            right_pos += text_len
                        else:
                            left_pos += text_len
                            right_pos += text_len
                    if left_char_ranges and right_char_ranges:
                        modified += 1
                        left_highlights.append((line_idx, left_char_ranges, QColor(255, 100, 100, 120)))
                        right_highlights.append((line_idx, right_char_ranges, QColor(100, 255, 100, 120)))
                    else:
                        deleted += 1
                        added += 1
                        left_highlights.append((line_idx, None, QColor(255, 100, 100, 80)))
                        right_highlights.append((line_idx, None, QColor(100, 255, 100, 80)))
                else:
                    deleted += num_deleted
                    added += num_added
                    for i in range(i1, i2):
                        line_idx = len(left_display)
                        left_display.append(left_lines[i])
                        right_display.append('')
                        left_highlights.append((line_idx, None, QColor(255, 100, 100, 80)))
                    for j in range(j1, j2):
                        line_idx = len(left_display)
                        left_display.append('')
                        right_display.append(right_lines[j])
                        right_highlights.append((line_idx, None, QColor(100, 255, 100, 80)))
        self.left_editor.setPlainText('\n'.join(left_display))
        self.right_editor.setPlainText('\n'.join(right_display))
        for line_idx, char_ranges, color in left_highlights:
            if char_ranges is None:
                self._highlight_full_line(self.left_editor, line_idx, color)
            else:
                self._highlight_char_ranges(self.left_editor, line_idx, char_ranges, color)
        for line_idx, char_ranges, color in right_highlights:
            if char_ranges is None:
                self._highlight_full_line(self.right_editor, line_idx, color)
            else:
                self._highlight_char_ranges(self.right_editor, line_idx, char_ranges, color)
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
    def _highlight_char_diff(self, editor, line_num, old_line, new_line, color, is_left):
        s = difflib.SequenceMatcher(None, old_line, new_line, autojunk=False)
        block = editor.document().findBlockByNumber(line_num)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag == 'equal':
                continue
            if is_left:
                start_col, end_col = i1, i2
            else:
                start_col, end_col = j1, j2
            if start_col >= end_col:
                continue
            cursor.setPosition(block.position() + start_col)
            cursor.setPosition(block.position() + end_col, QTextCursor.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            cursor.mergeCharFormat(fmt)
    def _highlight_full_line(self, editor, line_num, color):
        block = editor.document().findBlockByNumber(line_num)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        cursor.mergeCharFormat(fmt)
    def _highlight_char_ranges(self, editor, line_num, char_ranges, color):
        block = editor.document().findBlockByNumber(line_num)
        if not block.isValid():
            return
        for start_col, end_col in char_ranges:
            cursor = QTextCursor(block)
            cursor.setPosition(block.position() + start_col)
            cursor.setPosition(block.position() + end_col, QTextCursor.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            cursor.mergeCharFormat(fmt)
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
            parts = []
            if added > 0:
                parts.append(self.tr(f"{added} added"))
            if deleted > 0:
                parts.append(self.tr(f"{deleted} deleted"))
            if modified > 0:
                parts.append(self.tr(f"{modified} modified"))
            stats_text = self.tr("Differences: ") + ", ".join(parts)
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
        self.left_content = ""
        self.right_content = ""
        self.left_editor.clear()
        self.right_editor.clear()
        self.stats_label.hide()