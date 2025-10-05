import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QMessageBox, QFileDialog,
                             QHBoxLayout, QLabel, QStatusBar, QScrollBar, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QFocusEvent, QTextCursor
from tools.setting_config import SCM
from qfluentwidgets import BodyLabel, LineEdit, ScrollBar, FluentIcon, TransparentToolButton

from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QTextDocument
from PyQt5.QtWidgets import QPlainTextEdit
import re

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython, QsciLexerCPP, QsciLexerJava, \
        QsciLexerJavaScript, QsciLexerHTML, QsciLexerCSS, QsciLexerXML, QsciLexerSQL, \
        QsciLexerBash, QsciLexerBatch, QsciLexerJSON, QsciLexerYAML, QsciLexerMarkdown, \
        QsciLexerCSharp, QsciLexerRuby, QsciLexerPerl, QsciLexerLua, QsciLexerPascal, \
        QsciLexerFortran, QsciLexerMakefile, QsciLexerCMake, QsciLexerDiff
    QSCINTILLA_AVAILABLE = True
except ImportError:
    QSCINTILLA_AVAILABLE = False

from qfluentwidgets import isDarkTheme


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(86, 156, 214))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
            'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True',
            'try', 'while', 'with', 'yield'
        ]
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            self.highlighting_rules.append(
                (re.compile(pattern), keyword_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(214, 157, 133))
        self.highlighting_rules.append(
            (re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append(
            (re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(106, 153, 85))
        self.highlighting_rules.append(
            (re.compile(r'#[^\n]*'), comment_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(181, 206, 168))
        self.highlighting_rules.append(
            (re.compile(r'\b[0-9]+\b'), number_format))
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(220, 220, 170))
        self.highlighting_rules.append(
            (re.compile(r'\b[A-Za-z0-9_]+(?=\()'), function_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() -
                               match.start(), format)


class EditorWidget(QWidget):
    file_modified = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
    QWidget {
        background: transparent;
        border: none;
    }
""")
        self.tab_id = None
        self._side_panel = None
        self.file_path = None
        self.original_content = ""
        self.is_modified = False
        self.scm = SCM()
        self.last_search_text = ""
        self.search_bar_visible = False
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)
        self.setLayout(self.layout_)
        self._setup_search_bar()
        if QSCINTILLA_AVAILABLE:
            self.editor = QsciScintilla()
            self._setup_qscintilla()
        else:
            self.editor = QPlainTextEdit()
            self._setup_plain_text_edit()

        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        v_scroll = ScrollBar(Qt.Vertical, self.editor)
        # h_scroll = ScrollBar(Qt.Horizontal, self.editor)

        self.layout_.addWidget(self.editor)
        self._setup_status_bar()
        self._setup_shortcuts()
        self._apply_theme()

    def _setup_shortcuts(self):
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self.editor)
        save_shortcut.activated.connect(self.save_file)
        reload_shortcut = QShortcut(QKeySequence("F5"), self.editor)
        reload_shortcut.activated.connect(self.reload_file)
        find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self.editor)
        find_shortcut.activated.connect(self.toggle_search_bar)
        replace_shortcut = QShortcut(QKeySequence("Ctrl+H"), self.editor)
        replace_shortcut.activated.connect(
            lambda: self.toggle_search_bar(show_replace=True))
        esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        esc_shortcut.activated.connect(self.hide_search_bar)
        find_next_shortcut = QShortcut(QKeySequence("F3"), self.editor)
        find_next_shortcut.activated.connect(self.find_next)
        find_prev_shortcut = QShortcut(QKeySequence("Shift+F3"), self.editor)
        find_prev_shortcut.activated.connect(self.find_previous)
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self.editor)
        undo_shortcut.activated.connect(self.undo)
        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self.editor)
        redo_shortcut.activated.connect(self.redo)
        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self.editor)
        select_all_shortcut.activated.connect(self.select_all)
        copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self.editor)
        copy_shortcut.activated.connect(self.copy)
        cut_shortcut = QShortcut(QKeySequence("Ctrl+X"), self.editor)
        cut_shortcut.activated.connect(self.cut)
        paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self.editor)
        paste_shortcut.activated.connect(self.paste)

    def _setup_qscintilla(self):
        font = QFont('Consolas' if sys.platform ==
                     'win32' else 'Monaco' if sys.platform == 'darwin' else 'Monospace')
        font.setPointSize(10)
        self.editor.setFont(font)
        self.editor.setMarginType(0, QsciScintilla.NumberMargin)
        self.editor.setMarginWidth(0, "0000")
        self.editor.setMarginLineNumbers(0, True)
        self.editor.linesChanged.connect(self._update_line_number_width)
        self.editor.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.editor.setCaretLineVisible(True)
        self.editor.setCaretLineBackgroundColor(QColor("#3c3c3c"))
        self.editor.setIndentationsUseTabs(False)
        self.editor.setIndentationWidth(4)
        self.editor.setAutoIndent(True)
        self.editor.setSelectionBackgroundColor(QColor("#264f78"))
        self.editor.setSelectionForegroundColor(QColor("#ffffff"))
        self.editor.setWrapMode(QsciScintilla.WrapWord)
        self.editor.setWrapVisualFlags(QsciScintilla.WrapFlagByText)
        self.editor.setWrapIndentMode(QsciScintilla.WrapIndentIndented)
        self.editor.setAutoCompletionSource(QsciScintilla.AcsAll)
        self.editor.setAutoCompletionThreshold(2)
        self.editor.setAutoCompletionCaseSensitivity(False)
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.modificationChanged.connect(self._on_modification_changed)
        self.editor.cursorPositionChanged.connect(self._update_cursor_position)
        self.editor.selectionChanged.connect(self._update_cursor_position)
        self._setup_focus_handler()

    def _update_line_number_width(self):
        if not QSCINTILLA_AVAILABLE:
            return
        lines = self.editor.lines()
        if lines == 0:
            lines = 1
        width = self.editor.fontMetrics().width(str(lines)) + 15
        self.editor.setMarginWidth(0, width)

    def _setup_plain_text_edit(self):
        font = QFont('Consolas' if sys.platform ==
                     'win32' else 'Monaco' if sys.platform == 'darwin' else 'Monospace')
        font.setPointSize(10)
        self.editor.setFont(font)
        self.editor.setTabStopWidth(40)
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._update_cursor_position)
        self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self._setup_focus_handler()

    def _apply_theme(self):
        if QSCINTILLA_AVAILABLE:
            if isDarkTheme():
                self.editor.setCaretForegroundColor(QColor("#ffffff"))
                self.editor.setMarginsBackgroundColor(QColor("#1e1e1e"))
                self.editor.setMarginsForegroundColor(QColor("#858585"))
                self.editor.setFoldMarginColors(
                    QColor("#1e1e1e"), QColor("#1e1e1e"))
                self.editor.setPaper(QColor("#1e1e1e"))
                self.editor.setColor(QColor("#d4d4d4"))
                if hasattr(self.editor, 'lexer') and self.editor.lexer():
                    self._apply_dark_theme_to_lexer(self.editor.lexer())
            else:
                self.editor.setCaretForegroundColor(QColor("#000000"))
                self.editor.setMarginsBackgroundColor(QColor("#ffffff"))
                self.editor.setMarginsForegroundColor(QColor("#666666"))
                self.editor.setFoldMarginColors(
                    QColor("#f0f0f0"), QColor("#f0f0f0"))
                self.editor.setPaper(QColor("#ffffff"))
                self.editor.setColor(QColor("#000000"))
                if hasattr(self.editor, 'lexer') and self.editor.lexer():
                    self._apply_light_theme_to_lexer(self.editor.lexer())
        else:
            if isDarkTheme():
                self.editor.setStyleSheet("""
                    QPlainTextEdit {
                        background-color: #1e1e1e;
                        color: #d4d4d4;
                        border: none;
                        selection-background-color: #264f78;
                        selection-color: #ffffff;
                    }
                """)
            else:
                self.editor.setStyleSheet("""
                    QPlainTextEdit {
                        background-color: #ffffff;
                        color: #000000;
                        border: none;
                        selection-background-color: #3399ff;
                        selection-color: #ffffff;
                    }
                """)

    def _apply_dark_theme_to_lexer(self, lexer):
        lexer.setDefaultPaper(QColor("#1e1e1e"))
        lexer.setDefaultColor(QColor("#d4d4d4"))
        lexer.setColor(QColor("#608b4e"), lexer.Comment)
        lexer.setColor(QColor("#ce9178"), lexer.DoubleQuotedString)
        lexer.setColor(QColor("#ce9178"), lexer.SingleQuotedString)
        lexer.setColor(QColor("#569cd6"), lexer.Keyword)
        lexer.setColor(QColor("#b5cea8"), lexer.Number)
        if hasattr(lexer, 'ClassName'):
            lexer.setColor(QColor("#dcdcaa"), lexer.ClassName)
        if hasattr(lexer, 'FunctionMethodName'):
            lexer.setColor(QColor("#dcdcaa"), lexer.FunctionMethodName)
        lexer.setColor(QColor("#9cdcfe"), lexer.Identifier)
        lexer.setColor(QColor("#c586c0"), lexer.Operator)

    def _apply_light_theme_to_lexer(self, lexer):
        lexer.setDefaultPaper(QColor("#ffffff"))
        lexer.setDefaultColor(QColor("#000000"))
        lexer.setColor(QColor("#008000"), lexer.Comment)
        lexer.setColor(QColor("#a31515"), lexer.DoubleQuotedString)
        lexer.setColor(QColor("#a31515"), lexer.SingleQuotedString)
        lexer.setColor(QColor("#0000ff"), lexer.Keyword)
        lexer.setColor(QColor("#098658"), lexer.Number)
        if hasattr(lexer, 'ClassName'):
            lexer.setColor(QColor("#267f99"), lexer.ClassName)
        if hasattr(lexer, 'FunctionMethodName'):
            lexer.setColor(QColor("#795e26"), lexer.FunctionMethodName)
        lexer.setColor(QColor("#001080"), lexer.Identifier)
        lexer.setColor(QColor("#000000"), lexer.Operator)

    def set_tab_id(self, tab_id):
        self.tab_id = tab_id
        print(f"Editor initialized with tab ID: {self.tab_id}")
        QTimer.singleShot(100, self.load_file_from_tab_data)

    def _find_side_panel(self):
        if self._side_panel:
            return self._side_panel
        parent = self.parent()
        while parent is not None:
            if parent.metaObject().className() == "SidePanelWidget":
                print("Found and cached SidePanelWidget.")
                self._side_panel = parent
                return self._side_panel
            parent = parent.parent()
        return None

    def get_tab_data(self):
        side_panel = self._find_side_panel()
        if side_panel:
            tab_data = side_panel.get_tab_data_by_uuid(self.tab_id)
            print(f"Retrieved tab data: {tab_data}")
            return tab_data
        return None

    def load_file_from_tab_data(self):
        tab_data = self.get_tab_data()
        if tab_data and isinstance(tab_data, dict):
            file_path = tab_data.get('file_path') or tab_data.get(
                'path') or tab_data.get('filepath')
            if file_path:
                self.load_file(file_path)
            else:
                print(f"No file path found in tab data: {tab_data}")

    def load_file(self, file_path):
        try:
            self.file_path = file_path
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.original_content = content
            self.editor.setText(content)
            self.is_modified = False
            self._set_syntax_highlighter(file_path)
            self._update_file_type(file_path)
            self._update_cursor_position()
            self._update_tab_title()
        except Exception as e:
            print(f"Failed to load file: {str(e)}")

    def reload_file(self):
        if self.file_path:
            if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
                vertical_pos = self.editor.firstVisibleLine()
                horizontal_pos = self.editor.horizontalScrollBar().value()
            else:
                vertical_pos = self.editor.verticalScrollBar().value()
                horizontal_pos = self.editor.horizontalScrollBar().value()
            self.load_file(self.file_path)
            if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
                self.editor.setFirstVisibleLine(vertical_pos)
                self.editor.horizontalScrollBar().setValue(horizontal_pos)
            else:
                self.editor.verticalScrollBar().setValue(vertical_pos)
                self.editor.horizontalScrollBar().setValue(horizontal_pos)

    def _set_syntax_highlighter(self, file_path):
        if not QSCINTILLA_AVAILABLE:
            if file_path.endswith('.py'):
                self.highlighter = PythonHighlighter(self.editor.document())
            return
        ext = os.path.splitext(file_path)[1].lower()
        lexer_map = {
            '.py': QsciLexerPython,
            '.pyw': QsciLexerPython,
            '.c': QsciLexerCPP,
            '.cpp': QsciLexerCPP,
            '.cc': QsciLexerCPP,
            '.cxx': QsciLexerCPP,
            '.h': QsciLexerCPP,
            '.hpp': QsciLexerCPP,
            '.java': QsciLexerJava,
            '.js': QsciLexerJavaScript,
            '.jsx': QsciLexerJavaScript,
            '.ts': QsciLexerJavaScript,
            '.tsx': QsciLexerJavaScript,
            '.html': QsciLexerHTML,
            '.htm': QsciLexerHTML,
            '.css': QsciLexerCSS,
            '.xml': QsciLexerXML,
            '.sql': QsciLexerSQL,
            '.sh': QsciLexerBash,
            '.bash': QsciLexerBash,
            '.bat': QsciLexerBatch,
            '.cmd': QsciLexerBatch,
            '.json': QsciLexerJSON,
            '.yaml': QsciLexerYAML,
            '.yml': QsciLexerYAML,
            '.md': QsciLexerMarkdown,
            '.markdown': QsciLexerMarkdown,
            '.cs': QsciLexerCSharp,
            '.rb': QsciLexerRuby,
            '.pl': QsciLexerPerl,
            '.lua': QsciLexerLua,
            '.pas': QsciLexerPascal,
            '.f': QsciLexerFortran,
            '.f90': QsciLexerFortran,
            '.makefile': QsciLexerMakefile,
            '.mk': QsciLexerMakefile,
            '.cmake': QsciLexerCMake,
            '.diff': QsciLexerDiff,
            '.patch': QsciLexerDiff,
        }
        lexer_class = lexer_map.get(ext)
        if lexer_class:
            lexer = lexer_class()
            font = QFont('Consolas' if sys.platform ==
                         'win32' else 'Monaco' if sys.platform == 'darwin' else 'Monospace')
            font.setPointSize(10)
            lexer.setDefaultFont(font)
            if isDarkTheme():
                self._apply_dark_theme_to_lexer(lexer)
            else:
                self._apply_light_theme_to_lexer(lexer)
            self.editor.setLexer(lexer)
            self._apply_theme()

    def save_file(self):
        if not self.file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                "",
                "All Files (*.*)"
            )
            if not file_path:
                return False
            self.file_path = file_path
        try:
            content = self.editor.text()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.original_content = content
            self.is_modified = False
            self.file_modified.emit(False)
            self._update_tab_title()
            print(f"File saved: {self.file_path}")
            return True
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save file: {str(e)}")
            return False

    def _on_text_changed(self):
        if self.file_path:
            current_content = self.editor.text()
            self.is_modified = (current_content != self.original_content)
            self.file_modified.emit(self.is_modified)
            self._update_tab_title()

    def _on_modification_changed(self, modified):
        self.is_modified = modified
        self.file_modified.emit(modified)
        self._update_tab_title()

    def _update_tab_title(self):
        if self.file_path:
            side_panel = self._find_side_panel()
            if side_panel and self.tab_id in side_panel.tabs:
                file_name = os.path.basename(self.file_path)
                title = f"{'*' if self.is_modified else ''}{file_name}"
                side_panel.tabs[self.tab_id]['button'].setText(title)

    def closeEvent(self, event):
        if self.is_modified:
            reply = QMessageBox.question(
                self, 'Save Changes',
                'The file has been modified. Do you want to save changes?',
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            if reply == QMessageBox.Save:
                if not self.save_file():
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        event.accept()

    def _setup_focus_handler(self):
        self._original_focus_out = self.editor.focusOutEvent

        def focus_out_handler(event):
            if self.scm.read_config().get("editor_auto_save_on_focus_lost", False):
                if self.is_modified and self.file_path:
                    self.save_file()
                    print(f"Auto-saved on focus out: {self.file_path}")
            self._original_focus_out(event)
        self.editor.focusOutEvent = focus_out_handler

    def _setup_search_bar(self):
        self.search_widget = QWidget()
        self.search_widget.setMaximumHeight(40)
        self.search_widget.setVisible(False)
        search_layout = QHBoxLayout(self.search_widget)
        search_layout.setContentsMargins(10, 5, 10, 5)
        search_layout.setSpacing(5)
        self.search_input = LineEdit()
        self.search_input.setPlaceholderText("查找...")
        self.search_input.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.search_input.returnPressed.connect(self.find_next)
        self.replace_input = LineEdit()
        self.replace_input.setPlaceholderText("替换为...")
        self.replace_input.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.replace_input.setVisible(False)
        self.find_prev_btn = TransparentToolButton(FluentIcon.UP)
        self.find_prev_btn.setToolTip("查找上一个 (Shift+F3)")
        self.find_prev_btn.setFixedSize(30, 30)
        self.find_prev_btn.clicked.connect(self.find_previous)
        self.find_next_btn = TransparentToolButton(FluentIcon.DOWN)
        self.find_next_btn.setToolTip("查找下一个 (F3)")
        self.find_next_btn.setFixedSize(30, 30)
        self.find_next_btn.clicked.connect(self.find_next)
        self.replace_btn = TransparentToolButton(FluentIcon.SYNC)
        self.replace_btn.setToolTip("替换")
        self.replace_btn.setFixedSize(30, 30)
        self.replace_btn.clicked.connect(self.replace_current)
        self.replace_btn.setVisible(False)
        self.replace_all_btn = TransparentToolButton(FluentIcon.ACCEPT)
        self.replace_all_btn.setToolTip("全部替换")
        self.replace_all_btn.setFixedSize(30, 30)
        self.replace_all_btn.clicked.connect(self.replace_all)
        self.replace_all_btn.setVisible(False)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.replace_input)
        search_layout.addStretch()
        search_layout.addWidget(self.find_prev_btn)
        search_layout.addWidget(self.find_next_btn)
        search_layout.addWidget(self.replace_btn)
        search_layout.addWidget(self.replace_all_btn)
        self.layout_.addWidget(self.search_widget)

    def toggle_search_bar(self, show_replace=False):
        if not self.search_bar_visible:
            self.show_search_bar(show_replace)
        else:
            if show_replace and not self.replace_input.isVisible():
                self.show_replace_options(True)
            else:
                self.hide_search_bar()

    def show_search_bar(self, show_replace=False):
        self.search_widget.setVisible(True)
        self.search_bar_visible = True
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            if self.editor.hasSelectedText():
                self.search_input.setText(self.editor.selectedText())
        else:
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                self.search_input.setText(cursor.selectedText())
        self.show_replace_options(show_replace)
        self.search_input.setFocus()
        self.search_input.selectAll()

    def hide_search_bar(self):
        self.search_widget.setVisible(False)
        self.search_bar_visible = False
        self.editor.setFocus()

    def show_replace_options(self, show):
        self.replace_input.setVisible(show)
        self.replace_btn.setVisible(show)
        self.replace_all_btn.setVisible(show)

    def find_next(self):
        text = self.search_input.text()
        if text:
            self.last_search_text = text
            self._do_find(text, False)

    def find_previous(self):
        text = self.search_input.text()
        if text:
            self.last_search_text = text
            self._do_find(text, True)

    def replace_current(self):
        find_text = self.search_input.text()
        replace_text = self.replace_input.text()
        if find_text:
            self._do_replace_one(find_text, replace_text)

    def replace_all(self):
        find_text = self.search_input.text()
        replace_text = self.replace_input.text()
        if find_text:
            self._do_replace_all(find_text, replace_text)

    def _do_find(self, text, backward=False):
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            if backward:
                line, index = self.editor.getCursorPosition()
                if self.editor.hasSelectedText():
                    line_from, index_from, line_to, index_to = self.editor.getSelection()
                    line, index = line_from, index_from
                found = self.editor.findFirst(text, False, False, False,
                                              False, False, line, index, False)
                if not found:
                    last_line = self.editor.lines() - 1
                    last_index = self.editor.lineLength(last_line)
                    found = self.editor.findFirst(text, False, False, False,
                                                  False, False, last_line, last_index, False)
            else:
                line, index = self.editor.getCursorPosition()
                if self.editor.hasSelectedText():
                    _, _, line_to, index_to = self.editor.getSelection()
                    line, index = line_to, index_to
                found = self.editor.findFirst(
                    text, False, False, False, True, True, line, index)
        else:
            cursor = self.editor.textCursor()
            options = QTextDocument.FindFlags()
            if backward:
                options |= QTextDocument.FindBackward
            cursor = self.editor.document().find(text, cursor, options)
            if cursor.isNull():
                if backward:
                    cursor = self.editor.textCursor()
                    cursor.movePosition(QTextCursor.End)
                else:
                    cursor = self.editor.textCursor()
                    cursor.movePosition(QTextCursor.Start)
                cursor = self.editor.document().find(text, cursor, options)
            if not cursor.isNull():
                self.editor.setTextCursor(cursor)

    def _do_replace_one(self, find_text, replace_text):
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            if self.editor.hasSelectedText():
                selected = self.editor.selectedText()
                if selected == find_text:
                    self.editor.replaceSelectedText(replace_text)
                    self._do_find(find_text, False)
                else:
                    self._do_find(find_text, False)
            else:
                self._do_find(find_text, False)
        else:
            cursor = self.editor.textCursor()
            if cursor.hasSelection():
                selected = cursor.selectedText()
                if selected == find_text:
                    cursor.insertText(replace_text)
                    self._do_find(find_text, False)
                else:
                    self._do_find(find_text, False)
            else:
                self._do_find(find_text, False)

    def _do_replace_all(self, find_text, replace_text):
        count = 0
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            self.editor.setCursorPosition(0, 0)
            while self.editor.findFirst(find_text, False, False, False,
                                        False, True, -1, -1, False):
                self.editor.replaceSelectedText(replace_text)
                count += 1
        else:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.beginEditBlock()
            while True:
                cursor = self.editor.document().find(find_text, cursor)
                if cursor.isNull():
                    break
                cursor.insertText(replace_text)
                count += 1
            cursor.endEditBlock()

    def undo(self):
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            self.editor.undo()
        else:
            self.editor.undo()

    def redo(self):
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            self.editor.redo()
        else:
            self.editor.redo()

    def select_all(self):
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            self.editor.selectAll()
        else:
            self.editor.selectAll()

    def copy(self):
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            self.editor.copy()
        else:
            self.editor.copy()

    def cut(self):
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            self.editor.cut()
        else:
            self.editor.cut()

    def paste(self):
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            self.editor.paste()
        else:
            self.editor.paste()

    def _setup_status_bar(self):
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(5, 2, 5, 2)
        self.encoding_label = BodyLabel("UTF-8")
        self.encoding_label.setStyleSheet("QLabel { color: #888; }")
        sep1 = BodyLabel("|")
        sep1.setStyleSheet("QLabel { color: #888; }")
        self.position_label = BodyLabel(self.tr("Row 1, Column 1"))
        self.position_label.setStyleSheet("QLabel { color: #888; }")
        sep2 = BodyLabel("|")
        sep2.setStyleSheet("QLabel { color: #888; }")
        self.file_type_label = BodyLabel(self.tr("Plain text"))
        self.file_type_label.setStyleSheet("QLabel { color: #888; }")
        status_layout.addWidget(self.encoding_label)
        status_layout.addWidget(sep1)
        status_layout.addWidget(self.position_label)
        status_layout.addWidget(sep2)
        status_layout.addWidget(self.file_type_label)
        status_layout.addStretch()
        sep3 = BodyLabel("|")
        sep3.setStyleSheet("QLabel { color: #888; }")
        self.selection_label = BodyLabel("")
        self.selection_label.setStyleSheet("QLabel { color: #888; }")
        status_layout.addWidget(sep3)
        status_layout.addWidget(self.selection_label)
        status_widget = QWidget()
        status_widget.setLayout(status_layout)
        status_widget.setMaximumHeight(25)
        status_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.05);
                border-top: 1px solid rgba(0, 0, 0, 0.1);
            }
        """)
        self.layout_.addWidget(status_widget)

    def _update_cursor_position(self):
        if QSCINTILLA_AVAILABLE and isinstance(self.editor, QsciScintilla):
            line, col = self.editor.getCursorPosition()
            self.position_label.setText(
                self.tr(f"row {line + 1}, column {col + 1}"))
            if self.editor.hasSelectedText():
                selected_text = self.editor.selectedText()
                lines = selected_text.count('\n') + 1
                chars = len(selected_text)
                self.selection_label.setText(
                    self.tr(f"{chars} characters selected"))
                if lines > 1:
                    self.selection_label.setText(
                        self.tr(f"{lines} lines, {chars} characters selected"))
            else:
                self.selection_label.setText("")
        else:
            cursor = self.editor.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.position_label.setText(self.tr(f"row {line}, column {col}"))
            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                chars = len(selected_text)
                self.selection_label.setText(
                    self.tr(f"{chars} characters selected"))
            else:
                self.selection_label.setText("")

    def _update_file_type(self, file_path):
        if not file_path:
            self.file_type_label.setText(self.tr("Plain text"))
            return
        ext = os.path.splitext(file_path)[1].lower()
        file_types = {
            '.py': 'Python',
            '.pyw': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript React',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript React',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.cc': 'C++',
            '.cxx': 'C++',
            '.h': 'C/C++ Header',
            '.hpp': 'C++ Header',
            '.cs': 'C#',
            '.html': 'HTML',
            '.htm': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sass': 'Sass',
            '.less': 'Less',
            '.xml': 'XML',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.md': 'Markdown',
            '.markdown': 'Markdown',
            '.sql': 'SQL',
            '.sh': 'Shell Script',
            '.bash': 'Bash Script',
            '.bat': 'Batch',
            '.cmd': 'Command',
            '.ps1': 'PowerShell',
            '.rb': 'Ruby',
            '.pl': 'Perl',
            '.lua': 'Lua',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.r': 'R',
            '.m': 'MATLAB/Objective-C',
            '.vb': 'Visual Basic',
            '.pas': 'Pascal',
            '.f': 'Fortran',
            '.f90': 'Fortran 90',
            '.asm': 'Assembly',
            '.s': 'Assembly',
            '.makefile': 'Makefile',
            '.mk': 'Makefile',
            '.cmake': 'CMake',
            '.dockerfile': 'Dockerfile',
            '.gitignore': 'Git Ignore',
            '.env': 'Environment',
            '.ini': 'INI',
            '.cfg': 'Configuration',
            '.conf': 'Configuration',
            '.toml': 'TOML',
            '.properties': 'Properties',
            '.diff': 'Diff',
            '.patch': 'Patch',
        }
        file_type = file_types.get(ext, self.tr("Plain text"))
        self.file_type_label.setText(file_type)
