# ssh_webterm.py
"""
Web-based terminal widget using xterm.js embedded in a QWebEngineView,
communicating via QWebChannel.

Features:
- Transparent/web-background-supporting terminal (best-effort; some Qt/Chromium builds
  may not support page transparency; a bg_color fallback is available).
- text_color parameter (foreground color).
- bg_color parameter (fallback background color when transparency isn't desirable).
- text_shadow parameter (boolean) to add subtle text shadow for readability.
- Dynamic theme update via set_colors().
- Bridge (TerminalBridge) relays bytes <-> base64 across the QWebChannel.

Usage:
    widget = WebTerminal(parent, cols=120, rows=30,
                         text_color="white", bg_color="#00000080", text_shadow=True)
    widget.set_worker(ssh_worker)
    # To update colors later:
    widget.set_colors(text_color="#00ffcc",
                      bg_color="rgba(0,0,0,0.6)", text_shadow=False)
"""
import base64
import json
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QHBoxLayout, QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
import PyQt5.QtCore as qc
from tools.setting_config import SCM
import re
import os
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence
print("QT_VERSION:", qc.QT_VERSION_STR, "PYQT:", qc.PYQT_VERSION_STR)

configer = SCM()
_ansi_csi_re = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]')
_ansi_esc_re = re.compile(r'\x1b.[@-~]?')


def _strip_ansi_sequences(s: str) -> str:
    """移除常见的 ESC/CSI 控制序列（方向键、功能键等）"""
    s = _ansi_csi_re.sub('', s)
    s = _ansi_esc_re.sub('', s)
    return s


class TerminalBridge(QObject):
    """
    Bridge object exposed to JavaScript via QWebChannel.

    Signals:
        output(str) : emits base64-encoded bytes from SSHWorker to JS.
        ready() : emits when frontend is ready.
        scrollPositionChanged(int) : emits scroll position from JS to Python.
        directoryChanged(str) : emits directory change events.
    """
    output = pyqtSignal(str)
    ready = pyqtSignal()
    directoryChanged = pyqtSignal(str)

    def __init__(self, parent=None, user_name=None, home_path=None):
        super().__init__(parent)
        self.worker = None
        self.current_directory = "/"
        self._input_buffer = ""  # 用户输入缓冲
        self.username = user_name
        # self.home_path = home_path
        # print(home_path)

    def set_worker(self, worker):
        """Attach an SSHWorker. The worker must emit bytes via result_ready signal."""
        if self.worker is not None:
            try:
                self.worker.result_ready.disconnect(self._on_worker_output)
            except Exception:
                pass
        self.worker = worker
        if worker:
            worker.result_ready.connect(self._on_worker_output)

    def _process_user_input(self, data: bytes):
        """
        处理用户输入：
         - 识别退格、Ctrl+U、Ctrl+W
         - 忽略常见 ESC/CSI 序列
         - 遇到回车时提交命令
        """
        try:
            text = data.decode('utf-8', errors='ignore')
            text = _strip_ansi_sequences(text)

            buf_chars = list(self._input_buffer)
            i = 0
            L = len(text)
            while i < L:
                ch = text[i]

                # 退格
                if ch == '\x08' or ch == '\x7f':
                    if buf_chars:
                        buf_chars.pop()
                    i += 1
                    continue

                # Ctrl+U 清行
                if ch == '\x15':
                    buf_chars = []
                    i += 1
                    continue

                # Ctrl+W 删除上一个单词
                if ch == '\x17':
                    while buf_chars and buf_chars[-1].isspace():
                        buf_chars.pop()
                    while buf_chars and not buf_chars[-1].isspace():
                        buf_chars.pop()
                    i += 1
                    continue

                # 回车或换行
                if ch == '\r' or ch == '\n':
                    cmd = ''.join(buf_chars).strip()
                    if cmd:
                        self._process_command(cmd)
                    buf_chars = []
                    while i < L and (text[i] == '\r' or text[i] == '\n'):
                        i += 1
                    continue

                # 普通字符追加
                buf_chars.append(ch)
                i += 1

            self._input_buffer = ''.join(buf_chars)

        except Exception as e:
            print(f"处理用户输入时出错: {e}")
            self._input_buffer = ""

    def _process_command(self, command: str):
        """
        只在完整命令提交（按回车）时调用。
        支持 cd <dir>、cd、cd ~、cd ~/subdir 等。
        """
        try:
            parts = command.split()
            if not parts:
                return

            if parts[0] == 'cd':
                target_dir = '~' if len(parts) == 1 else parts[1]
                username = self.username
                # 波浪符展开
                if target_dir == '~':
                    if username == 'root':
                        target_dir = '/root'
                    else:
                        target_dir = f'/home/{username}' if username else '/home/user'
                elif target_dir.startswith('~/'):
                    if username == 'root':
                        target_dir = target_dir.replace('~', '/root', 1)
                    else:
                        target_dir = target_dir.replace(
                            '~', f'/home/{username}' if username else '/home/user', 1)
                # 相对路径处理
                if not target_dir.startswith('/'):
                    base = self.current_directory.rstrip('/')
                    base = '/' if base == '' else base
                    candidate = base + '/' + \
                        target_dir if not base.endswith(
                            '/') else base + target_dir
                else:
                    candidate = target_dir

                # 规范化路径
                candidate = os.path.normpath(candidate).replace('\\', '/')

                if candidate != self.current_directory:
                    self.current_directory = candidate
                    self.directoryChanged.emit(candidate)

        except Exception as e:
            print(f"_process_command error: {e}")

    def _on_worker_output(self, chunk: bytes):
        """Encode bytes -> base64 and emit to JS."""
        try:
            b64 = base64.b64encode(chunk).decode("ascii")
            self.output.emit(b64)
        except Exception as e:
            print(f"处理输出时出错: {e}")

    @pyqtSlot(str)
    def sendInput(self, b64: str):
        """JS -> Python: base64-encoded user input"""
        if not self.worker:
            return
        try:
            data = base64.b64decode(b64)
            # print("接收到:", data.decode("utf-8", errors="ignore"))
            self._process_user_input(data)
            self.worker.run_command(data, add_newline=False)
        except Exception as e:
            print("TerminalBridge.sendInput error:", e)

    @pyqtSlot(int, int)
    def resize(self, cols: int, rows: int):
        """JS -> Python: terminal size change"""
        if not self.worker:
            return
        try:
            self.worker.resize_pty(cols, rows)
        except Exception as e:
            print("TerminalBridge.resize error:", e)

    @pyqtSlot()
    def notifyReady(self):
        self.ready.emit()

    @pyqtSlot(str)
    def copyToClipboard(self, text):
        QApplication.clipboard().setText(text)


class WebTerminal(QWidget):
    """
    Web terminal widget embedding xterm.js in a QWebEngineView.

    Parameters:
      parent: parent widget
      cols, rows: initial terminal size (cols, rows)
      text_color: CSS color for foreground text (e.g., "white" or "#fff")
      bg_color: CSS color fallback for background (e.g., "#000000" or "rgba(0,0,0,0.6)")
      text_shadow: boolean, whether to add a subtle text shadow for improve readability
    """
    directoryChanged = pyqtSignal(str)

    def __init__(self, parent=None, cols=120, rows=30, text_color="white", bg_color="transparent", text_shadow=False, font_name=None, user_name=None):
        super().__init__(parent)
        self._rows = int(rows)
        self._cols = cols
        # Means not set color
        if text_color == "white":
            pass
            # config = configer.read_config()
            # self._text_color = config["ssh_widget_text_color"]
            # print(self._text_color)
        else:
            self._text_color = text_color
        # self._text_color = text_color or "white"
        self._bg_color = bg_color or "transparent"
        self._text_shadow = bool(text_shadow)
        self._scroll_position = 0
        self._max_scroll = 1000
        print(font_name)
        self._font_family = font_name or "monospace"

        # 确保整个 widget 透明
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 创建水平布局用于放置终端和自定义滚动条
        self.terminal_layout = QHBoxLayout()
        self.terminal_layout.setContentsMargins(0, 0, 0, 0)
        self.terminal_layout.setSpacing(0)

        # QWebEngineView setup
        self.view = QWebEngineView(self)

        self.view.setAttribute(Qt.WA_TranslucentBackground, True)
        self.view.setStyleSheet("""
            QWebEngineView {
                background: transparent;
                border: none;
            }
            QWebEngineView::scroll-bar:vertical {
                width: 0px;
            }
            QWebEngineView::scroll-bar:horizontal {
                height: 0px;
            }
        """)

        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.terminal_layout.addWidget(self.view, 1)
        self.main_layout.addLayout(self.terminal_layout)

        try:
            self.view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        except Exception as e:
            print("Warning: could not set page background transparent:", e)

        # WebChannel + Bridge
        self.channel = QWebChannel(self.view.page())
        print(f"User name {user_name}")
        self.bridge = TerminalBridge(self, user_name=user_name)
        self.bridge.directoryChanged.connect(self._on_directory_changed)
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
        # DevTools 调试窗口
        # 独立 DevTools 窗口（没有 parent）
        self.devtools = QWebEngineView()
        self.devtools.setWindowTitle("DevTools")
        self.devtools.resize(900, 700)
        self.view.page().setDevToolsPage(self.devtools.page())

        shortcut = QShortcut(QKeySequence("Ctrl+Shift+I"), self)
        shortcut.activated.connect(self._toggle_devtools)

        # 隐藏原生滚动条的 JavaScript 代码
        self.hide_scrollbars_js = """
        // 隐藏所有滚动条
        const style = document.createElement('style');
        style.innerHTML = `
            ::-webkit-scrollbar {
                display: none !important;
                width: 0 !important;
                height: 0 !important;
            }
            * {
                scrollbar-width: none !important;
                -ms-overflow-style: none !important;
            }
        `;
        document.head.appendChild(style);
        """

        # Load HTML
        html = self._build_html()
        self.view.setHtml(html, QUrl("qrc:///"))

        # 添加透明度调试输出
        print(f"WebTerminal transparency check:")
        print(
            f"  Widget transparent: {self.testAttribute(Qt.WA_TranslucentBackground)}")
        print(
            f"  View transparent: {self.view.testAttribute(Qt.WA_TranslucentBackground)}")

        # 在页面加载完成后检查背景色和隐藏滚动条
        self.view.page().loadFinished.connect(self._on_page_loaded)

    def _toggle_devtools(self):
        if self.devtools.isVisible():
            self.devtools.hide()
        else:
            self.devtools.show()
            self.devtools.raise_()
            self.devtools.activateWindow()

    def _on_directory_changed(self, new_dir):
        """处理目录变更"""
        config = configer.read_config()
        if config["follow_cd"]:
            self.directoryChanged.emit(new_dir)
            print(f"目录已变更: {new_dir}")

    def _set_font(self, font_name):
        """
        设置终端内显示的字体

        Args:
            font_name: 系统已安装的字体名称
        """

        self._font_family = font_name or "monospace"
        self._update_font_in_html()
        self._force_rerender()

    def _force_rerender(self):
        """强制终端重新渲染"""
        rerender_js = """
        const term = window.term;
        if (term) {
            const text = term.getSelection() || term.getText();
            term.clear();
            term.write(text);
        }
        """
        self.view.page().runJavaScript(rerender_js)

    def _update_font_in_html(self):
        """更新 HTML 中的字体设置"""
        font_js = f"""
      // 更新终端字体
      const terminal = document.getElementById('terminal');
      if (terminal) {{
          terminal.style.fontFamily = '{self._font_family}, monospace !important';
          terminal.style.letterSpacing = 'normal !important';
      }}
      
      // 更新 xterm 字体
      const xtermElements = document.querySelectorAll('.xterm, .xterm *');
      xtermElements.forEach(element => {{
          element.style.fontFamily = '{self._font_family}, monospace !important';
          element.style.letterSpacing = 'normal !important';
      }});
      """
        self.view.page().runJavaScript(font_js)

    def _on_page_loaded(self):
        """页面加载完成后的回调函数，用于调试透明度和隐藏滚动条"""
        def check_bg_color(color):
            print(f"Page background color: {color}")

        def check_body_bg(color):
            print(f"Body background color: {color}")

        def check_terminal_bg(color):
            print(f"Terminal div background color: {color}")

        # 检查各种元素的背景色
        self.view.page().runJavaScript(
            "window.getComputedStyle(document.body).backgroundColor",
            check_body_bg
        )

        self.view.page().runJavaScript(
            "window.getComputedStyle(document.getElementById('terminal')).backgroundColor",
            check_terminal_bg
        )

        # 检查页面背景色
        bg_color = self.view.page().backgroundColor()
        print(
            f"QWebEnginePage background color: {bg_color.name(QColor.HexArgb)}")

        # 隐藏原生滚动条
        self.view.page().runJavaScript(self.hide_scrollbars_js)

    def _html_escape(self, s: str) -> str:
        return json.dumps(s)

    def _build_html(self) -> str:
        """
        Return the HTML string used as the web page for the terminal.
        """
        # JSON-encoded strings for safe embedding in JS
        fg_js = self._html_escape(self._text_color)
        bg_js = self._html_escape(self._bg_color)
        shadow_bool = "true" if self._text_shadow else "false"

        # Template with doubled braces for literal '{' '}' inside .format
        tpl = r"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <title>xterm.js via QWebChannel</title>

      <!-- Polyfill: replaceChildren for older embedded Chromium -->
      <script>
      (function () {{
        function makeReplaceChildrenFor(proto) {{
          if (proto && typeof proto.replaceChildren !== 'function') {{
            Object.defineProperty(proto, 'replaceChildren', {{
              configurable: true,
              writable: true,
              value: function() {{
                while (this.firstChild) {{
                  this.removeChild(this.firstChild);
                }}
                for (var i = 0; i < arguments.length; i++) {{
                  var arg = arguments[i];
                  if (typeof arg === 'string') {{
                    this.appendChild(document.createTextNode(arg));
                  }} else if (arg instanceof Node) {{
                    this.appendChild(arg);
                  }}
                }}
              }}
            }});
          }}
        }}
        try {{
          makeReplaceChildrenFor(Element && Element.prototype);
          makeReplaceChildrenFor(Document && Document.prototype);
          makeReplaceChildrenFor(DocumentFragment && DocumentFragment.prototype);
          if (typeof ShadowRoot !== 'undefined') {{
            makeReplaceChildrenFor(ShadowRoot.prototype);
          }}
          console.debug('replaceChildren polyfill installed (if needed)');
        }} catch (e) {{
          console.warn('replaceChildren polyfill error', e);
        }}
      }})();
      </script>

      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.2.0/css/xterm.css" />
      <style>
        html, body {{
            height:100%;
            margin:0;
            background: transparent !important;
            background-color: transparent !important;
            /* 允许文本选择 */
            user-select: text !important;
            -webkit-user-select: text !important;
        }}
        #terminal {{
            height:100%;
            width:100%;
            background: transparent !important;
            background-color: transparent !important;
            /* fallback background color variable; used when transparency is not desired */
            --bg-fallback: {bg_css};
            /* 允许文本选择 */
            user-select: text !important;
            -webkit-user-select: text !important;
            font-family: {font_family}, monospace !important;
        }}

        /* Force xterm rendering layers to be transparent so the page/window background shows */
        .xterm,
        .xterm * {{
            background: transparent !important;
            background-color: transparent !important;
            font-family: {font_family}, monospace !important;
            user-select: text !important;
            -webkit-user-select: text !important;
        }}


        .xterm .xterm-screen,
        .xterm .xterm-text-layer,
        .xterm .xterm-rows,
        .xterm .xterm-cursor-layer {{
            background: transparent !important;
            background-color: transparent !important;
            font-family: {font_family}, monospace !important;
            user-select: text !important;
            -webkit-user-select: text !important;
        }}
        
        .xterm-scrollbar {{
            display: none !important;
        }}

        .xterm .xterm-decoration-top {{
            background: rgba(100, 150, 250, 0.5) !important;
            box-shadow: 0 0 5px rgba(100, 150, 250, 0.7);
            border-radius: 3px;
        }}

        /* optional text shadow applied conditionally via JS */
        .xterm .xterm-text-layer {{
            /* default no shadow; JS may set style on .xterm-text-layer to add shadow */
        }}
      </style>
    </head>
    <body>
      <div id="terminal"></div>

      <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/xterm@5.2.0/lib/xterm.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.7.0/lib/xterm-addon-fit.js"></script>

      <script>
      document.addEventListener('contextmenu', function(e) {{
    e.preventDefault();
}});
    // Prevent all drag operations
    document.addEventListener('dragenter', e => e.preventDefault());
    document.addEventListener('dragover', e => e.preventDefault());
    document.addEventListener('drop', e => e.preventDefault());

      (function() {{
        function safeDecodeB64ToBinary(b64) {{ return atob(b64); }}
        function safeEncodeBinaryToB64(bin) {{ return btoa(bin); }}

        new QWebChannel(qt.webChannelTransport, function(channel) {{
          var bridge = channel.objects.bridge;

          // create terminal with initial theme (transparent background; fg from Python)
          var term = new window.Terminal({{
            convertEol: true,
            cursorBlink: true,
            rows: {rows},
            cols: {cols},
            theme: {{
              background: "transparent",
              foreground: {fg}
            }},
            scrollback: 1000,  // 增加滚动缓冲区
            fontFamily: '{font_family}, monospace'  // 设置终端字体
          }});
          term.attachCustomKeyEventHandler(function(e) {{
    if (e.ctrlKey && e.shiftKey && e.code === 'KeyC') {{
        const selection = term.getSelection();
        if (selection && bridge && bridge.copyToClipboard) {{
            bridge.copyToClipboard(selection); // 调用 Python
        }}
        return false; // 阻止默认行为
    }}
    return true;
}});


          // fit addon creation (robust to various UMD exports)
          var fitAddon = null;
          try {{
            if (typeof window.FitAddon === 'function') {{
              fitAddon = new window.FitAddon();
            }} else if (window.FitAddon && typeof window.FitAddon.FitAddon === 'function') {{
              fitAddon = new window.FitAddon.FitAddon();
            }} else if (window.FitAddon && typeof window.FitAddon.default === 'function') {{
              fitAddon = new window.FitAddon.default();
            }} else if (typeof FitAddon === 'function') {{
              fitAddon = new FitAddon();
            }}
          }} catch(e) {{
            console.warn('FitAddon init failed', e);
            fitAddon = null;
          }}

          if (fitAddon && typeof term.loadAddon === 'function') {{
            try {{ term.loadAddon(fitAddon); }} catch(e) {{ console.warn('loadAddon failed', e); }}
          }}

          term.open(document.getElementById('terminal'));
          window.term = term; // Expose term globally for Python calls
          
          // Expose a helper to update theme at runtime (called from Python via runJavaScript)
          window.setTerminalTheme = function(fg, bgFallback, shadow) {{
            try {{
              // update CSS variable for fallback background
              document.getElementById('terminal').style.setProperty('--bg-fallback', bgFallback || 'transparent');
              // set xterm theme (background remains transparent; we rely on fallback if necessary)
              term.options.theme = {{
                foreground: fg || {fg},
                background: "transparent"
              }};

              var textLayer = document.querySelector('.xterm .xterm-text-layer');
              if (textLayer) {{
                if (shadow) {{
                  textLayer.style.textShadow = '0 0 4px rgba(0,0,0,0.9)';
                }} else {{
                  textLayer.style.textShadow = '';
                }}
              }}
            }} catch (e) {{
              console.error('setTerminalTheme error', e);
            }}
          }};

          // Bridge -> JS: receive base64 data and write into terminal
          if (bridge && bridge.output) {{
            bridge.output.connect(function(b64) {{
              try {{
                var text = base64ToUtf8(b64);
                term.write(text);
              }} catch (e) {{
                console.error('bridge.output write error', e);
              }}
            }});
          }}
            function base64ToUtf8(b64) {{
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
}}
            function utf8ToBase64(str) {{
    const bytes = new TextEncoder().encode(str);
    let binary = '';
    bytes.forEach(b => binary += String.fromCharCode(b));
    return btoa(binary);
}}

          // JS -> Bridge: user typed data
          term.onData(function(data) {{
            try {{
              var b64 = utf8ToBase64(data);
              bridge.sendInput(b64);
            }} catch (e) {{
              console.error('term.onData sendInput error', e);
            }}
          }});

          // 添加选择监听
          term.onSelectionChange(function() {{
            const selection = term.getSelection();
            if (selection) {{
                console.log('Selected text:', selection);
                // 可以在这里处理选中的文本
            }}
          }});

          // sizing: fit + notify backend of cols/rows
          window.notifySize = function() {{
           console.log('notifySize triggered from Python.');
            try {{
              if (fitAddon && typeof fitAddon.fit === 'function') {{
                try {{ fitAddon.fit(); }} catch(e) {{ /* ignore */ }}
              }}
              var cols = term.cols || 80;
              var rows = term.rows || 24;
              if (bridge && bridge.resize) {{
                bridge.resize(cols, rows);
              }}
            }} catch (e) {{
              console.error('notifySize error', e);
            }}
          }}


          // initial sizing & apply initial fallback bg & shadow
          setTimeout(function() {{
            // apply initial bg fallback variable and shadow: Python provided values used below by calling setTerminalTheme
            window.notifySize();
            try {{
              // call setTerminalTheme with initial values
              window.setTerminalTheme({fg}, {bg}, {shadow});
            }} catch(e) {{
              console.warn('initial setTerminalTheme failed', e);
            }}
          }}, 200);

          if (bridge && bridge.notifyReady) {{
            bridge.notifyReady();
          }}

        }});
      }})();
      </script>
    </body>
    </html>
    """
        # Format with safe JSON-encoded values inserted into the template.
        final = tpl.format(
            rows=self._rows,
            cols=self._cols,
            fg=fg_js,
            bg=bg_js,
            shadow=shadow_bool,
            bg_css=self._bg_color,  # 直接插入 CSS 值
            font_family=self._font_family  # 插入字体名称
        )
        return final

    def set_worker(self, worker):
        """Attach SSHWorker to the bridge and notify it of current pty size."""
        self.bridge.set_worker(worker)
        try:
            worker.resize_pty(self._cols, self._rows)
        except Exception:
            pass

    def set_colors(self, text_color=None, bg_color=None, text_shadow=None):
        """
        Dynamically update terminal colors.
        Parameters accept CSS color strings:
          text_color: e.g. "white" or "#00ffcc"
          bg_color: fallback background (used as CSS variable), e.g. "rgba(0,0,0,0.6)"
          text_shadow: boolean
        """
        if text_color is not None:
            self._text_color = text_color
        if bg_color is not None:
            self._bg_color = bg_color
        if text_shadow is not None:
            self._text_shadow = bool(text_shadow)

        # Call JS function to update theme; serialize strings safely via json.dumps
        fg_js = json.dumps(self._text_color)
        bg_js = json.dumps(self._bg_color)
        shadow_js = "true" if self._text_shadow else "false"
        js = f"if (window.setTerminalTheme) window.setTerminalTheme({fg_js}, {bg_js}, {shadow_js});"
        try:
            self.view.page().runJavaScript(js)
        except Exception as e:
            print("set_colors runJavaScript error:", e)

    def resizeEvent(self, event):
        """
        Optionally, we rely on the front-end's window.resize event and fitAddon to call
        bridge.resize. Still, we keep this hook in case additional Python-side logic is desired.
        """
        super().resizeEvent(event)
        # No explicit action here; JS side handles sizing via fitAddon and window resize listener.

    # Prevent all drag operations

    def dragEnterEvent(self, event):
        event.ignore()

    def dropEvent(self, event):
        event.ignore()

    def clear_screen(self):
        """Clears the terminal screen."""
        js = "if (window.term) window.term.clear();"
        try:
            self.view.page().runJavaScript(js)
        except Exception as e:
            print("clear_screen runJavaScript error:", e)

    def send_command(self, command: str):
        """Sends a string command to the terminal."""
        try:
            # The bridge's sendInput expects base64
            b64 = base64.b64encode(command.encode('utf-8')).decode('ascii')
            self.bridge.sendInput(b64)
        except Exception as e:
            print("send_command error:", e)

    def fit_terminal(self):
        """Triggers the fit addon in the browser to resize the terminal."""
        js = "if (typeof notifySize === 'function') notifySize();"
        try:
            self.view.page().runJavaScript(js)
        except Exception as e:
            print("fit_terminal runJavaScript error:", e)
