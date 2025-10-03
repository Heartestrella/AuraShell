import os
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QFocusEvent
from tools.setting_config import SCM

# Import QSyntaxHighlighter first
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
    """Simple Python syntax highlighter for fallback mode"""
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []
        
        # Keywords
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
            self.highlighting_rules.append((re.compile(pattern), keyword_format))
        
        # String
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(214, 157, 133))
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
        
        # Comment
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(106, 153, 85))
        self.highlighting_rules.append((re.compile(r'#[^\n]*'), comment_format))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(181, 206, 168))
        self.highlighting_rules.append((re.compile(r'\b[0-9]+\b'), number_format))
        
        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(220, 220, 170))
        self.highlighting_rules.append((re.compile(r'\b[A-Za-z0-9_]+(?=\()'), function_format))
    
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)


class EditorWidget(QWidget):
    file_modified = pyqtSignal(bool)  # Signal emitted when file is modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_id = None
        self._side_panel = None
        self.file_path = None
        self.original_content = ""
        self.is_modified = False
        self.scm = SCM()  # Setting config manager
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        
        # Create editor
        if QSCINTILLA_AVAILABLE:
            self.editor = QsciScintilla()
            self._setup_qscintilla()
        else:
            self.editor = QPlainTextEdit()
            self._setup_plain_text_edit()
        
        self.layout.addWidget(self.editor)
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
        
        # Apply theme
        self._apply_theme()

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        
        # Create Ctrl+S shortcut
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self.editor)
        save_shortcut.activated.connect(self.save_file)
        
        # You can add more shortcuts here if needed
        # Example: Ctrl+O for open, Ctrl+N for new, etc.
    
    def _setup_qscintilla(self):
        """Setup QsciScintilla editor with features"""
        # Set font
        font = QFont('Consolas' if sys.platform == 'win32' else 'Monaco' if sys.platform == 'darwin' else 'Monospace')
        font.setPointSize(10)
        self.editor.setFont(font)
        
        # Line numbers
        self.editor.setMarginType(0, QsciScintilla.NumberMargin)
        self.editor.setMarginWidth(0, "0000")
        self.editor.setMarginLineNumbers(0, True)
        self.editor.setMarginsBackgroundColor(QColor("#2b2b2b"))
        self.editor.setMarginsForegroundColor(QColor("#888888"))
        
        # Enable brace matching
        self.editor.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        
        # Current line highlighting
        self.editor.setCaretLineVisible(True)
        self.editor.setCaretLineBackgroundColor(QColor("#3c3c3c"))
        
        # Set indentation
        self.editor.setIndentationsUseTabs(False)
        self.editor.setIndentationWidth(4)
        self.editor.setAutoIndent(True)
        
        # Enable code folding
        self.editor.setFolding(QsciScintilla.BoxedTreeFoldStyle)
        
        # Set selection colors
        self.editor.setSelectionBackgroundColor(QColor("#264f78"))
        self.editor.setSelectionForegroundColor(QColor("#ffffff"))
        
        # Enable word wrap (auto line wrap)
        self.editor.setWrapMode(QsciScintilla.WrapWord)
        self.editor.setWrapVisualFlags(QsciScintilla.WrapFlagByText)
        self.editor.setWrapIndentMode(QsciScintilla.WrapIndentIndented)
        
        # Enable auto-completion
        self.editor.setAutoCompletionSource(QsciScintilla.AcsAll)
        self.editor.setAutoCompletionThreshold(2)
        self.editor.setAutoCompletionCaseSensitivity(False)
        
        # Connect signals
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.modificationChanged.connect(self._on_modification_changed)
        
        # Override focusOutEvent
        self._setup_focus_handler()
        
    def _setup_plain_text_edit(self):
        """Setup fallback plain text editor"""
        font = QFont('Consolas' if sys.platform == 'win32' else 'Monaco' if sys.platform == 'darwin' else 'Monospace')
        font.setPointSize(10)
        self.editor.setFont(font)
        self.editor.setTabStopWidth(40)
        self.editor.textChanged.connect(self._on_text_changed)
        
        # Enable word wrap for plain text editor
        self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        
        # Override focusOutEvent for plain text editor
        self._setup_focus_handler()
        
    def _apply_theme(self):
        """Apply dark or light theme"""
        if QSCINTILLA_AVAILABLE:
            if isDarkTheme():
                # Dark theme
                self.editor.setCaretForegroundColor(QColor("#ffffff"))
                self.editor.setMarginsBackgroundColor(QColor("#1e1e1e"))
                self.editor.setMarginsForegroundColor(QColor("#858585"))
                self.editor.setFoldMarginColors(QColor("#1e1e1e"), QColor("#1e1e1e"))
                
                # Set paper (background) color
                self.editor.setPaper(QColor("#1e1e1e"))
                
                # Update lexer colors if set
                if hasattr(self.editor, 'lexer') and self.editor.lexer():
                    self._apply_dark_theme_to_lexer(self.editor.lexer())
            else:
                # Light theme
                self.editor.setCaretForegroundColor(QColor("#000000"))
                self.editor.setMarginsBackgroundColor(QColor("#f0f0f0"))
                self.editor.setMarginsForegroundColor(QColor("#666666"))
                self.editor.setFoldMarginColors(QColor("#f0f0f0"), QColor("#f0f0f0"))
                
                # Set paper (background) color
                self.editor.setPaper(QColor("#ffffff"))
                
                # Update lexer colors if set
                if hasattr(self.editor, 'lexer') and self.editor.lexer():
                    self._apply_light_theme_to_lexer(self.editor.lexer())
        else:
            # Fallback editor theme
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
        """Apply dark theme colors to lexer"""
        lexer.setDefaultPaper(QColor("#1e1e1e"))
        lexer.setDefaultColor(QColor("#d4d4d4"))
        
        # Common color scheme for dark theme
        lexer.setColor(QColor("#608b4e"), lexer.Comment)  # Green for comments
        lexer.setColor(QColor("#ce9178"), lexer.DoubleQuotedString)  # Orange for strings
        lexer.setColor(QColor("#ce9178"), lexer.SingleQuotedString)
        lexer.setColor(QColor("#569cd6"), lexer.Keyword)  # Blue for keywords
        lexer.setColor(QColor("#b5cea8"), lexer.Number)  # Light green for numbers
        lexer.setColor(QColor("#dcdcaa"), lexer.ClassName)  # Yellow for classes
        lexer.setColor(QColor("#dcdcaa"), lexer.FunctionMethodName)  # Yellow for functions
        lexer.setColor(QColor("#9cdcfe"), lexer.Identifier)  # Light blue for identifiers
        lexer.setColor(QColor("#c586c0"), lexer.Operator)  # Purple for operators
        
    def _apply_light_theme_to_lexer(self, lexer):
        """Apply light theme colors to lexer"""
        lexer.setDefaultPaper(QColor("#ffffff"))
        lexer.setDefaultColor(QColor("#000000"))
        
        # Common color scheme for light theme
        lexer.setColor(QColor("#008000"), lexer.Comment)  # Green for comments
        lexer.setColor(QColor("#a31515"), lexer.DoubleQuotedString)  # Red for strings
        lexer.setColor(QColor("#a31515"), lexer.SingleQuotedString)
        lexer.setColor(QColor("#0000ff"), lexer.Keyword)  # Blue for keywords
        lexer.setColor(QColor("#098658"), lexer.Number)  # Dark green for numbers
        lexer.setColor(QColor("#267f99"), lexer.ClassName)  # Teal for classes
        lexer.setColor(QColor("#795e26"), lexer.FunctionMethodName)  # Brown for functions
        lexer.setColor(QColor("#001080"), lexer.Identifier)  # Dark blue for identifiers
        lexer.setColor(QColor("#000000"), lexer.Operator)  # Black for operators

    def set_tab_id(self, tab_id):
        self.tab_id = tab_id
        print(f"Editor initialized with tab ID: {self.tab_id}")
        # Delay loading file to ensure widget is properly added to parent
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
        """Load file from tab data"""
        tab_data = self.get_tab_data()
        if tab_data and isinstance(tab_data, dict):
            # Try different possible keys for file path
            file_path = tab_data.get('file_path') or tab_data.get('path') or tab_data.get('filepath')
            if file_path:
                self.load_file(file_path)
            else:
                print(f"No file path found in tab data: {tab_data}")
    
    def load_file(self, file_path):
        """Load a file into the editor"""
        try:
            self.file_path = file_path
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.original_content = content
            self.editor.setText(content)
            self.is_modified = False
            
            # Set syntax highlighter based on file extension
            self._set_syntax_highlighter(file_path)
            
            # Update tab title if possible
            self._update_tab_title()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
    
    def _set_syntax_highlighter(self, file_path):
        """Set appropriate syntax highlighter based on file extension"""
        if not QSCINTILLA_AVAILABLE:
            # Use simple Python highlighter for .py files in fallback mode
            if file_path.endswith('.py'):
                self.highlighter = PythonHighlighter(self.editor.document())
            return
        
        ext = os.path.splitext(file_path)[1].lower()
        
        # Map file extensions to lexers
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
        
        # Get lexer class
        lexer_class = lexer_map.get(ext)
        if lexer_class:
            lexer = lexer_class()
            
            # Set font for lexer
            font = QFont('Consolas' if sys.platform == 'win32' else 'Monaco' if sys.platform == 'darwin' else 'Monospace')
            font.setPointSize(10)
            lexer.setDefaultFont(font)
            
            # Apply theme to lexer
            if isDarkTheme():
                self._apply_dark_theme_to_lexer(lexer)
            else:
                self._apply_light_theme_to_lexer(lexer)
            
            self.editor.setLexer(lexer)
    
    def save_file(self):
        """Save the current file"""
        if not self.file_path:
            # If no file path, prompt for save location
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
            
            # Show success message (optional)
            print(f"File saved: {self.file_path}")
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
            return False
    
    def _on_text_changed(self):
        """Handle text change event"""
        if self.file_path:
            current_content = self.editor.text()
            self.is_modified = (current_content != self.original_content)
            self.file_modified.emit(self.is_modified)
            self._update_tab_title()
    
    def _on_modification_changed(self, modified):
        """Handle modification change event (QsciScintilla only)"""
        self.is_modified = modified
        self.file_modified.emit(modified)
        self._update_tab_title()
    
    def _update_tab_title(self):
        """Update the tab title to show modification status"""
        if self.file_path:
            side_panel = self._find_side_panel()
            if side_panel and self.tab_id in side_panel.tabs:
                file_name = os.path.basename(self.file_path)
                title = f"{'*' if self.is_modified else ''}{file_name}"
                side_panel.tabs[self.tab_id]['button'].setText(title)
    
    def closeEvent(self, event):
        """Handle close event"""
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
        """Setup focus out event handler for auto-save"""
        # Store original focusOutEvent
        self._original_focus_out = self.editor.focusOutEvent
        
        # Override focusOutEvent
        def focus_out_handler(event):
            # Check if auto-save is enabled
            if self.scm.read_config().get("editor_auto_save_on_focus_lost", False):
                # Save file if modified and has path
                if self.is_modified and self.file_path:
                    self.save_file()
                    print(f"Auto-saved on focus out: {self.file_path}")
            
            # Call original handler
            self._original_focus_out(event)
        
        self.editor.focusOutEvent = focus_out_handler
    