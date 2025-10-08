<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>xterm.js via QWebChannel</title>

  <!-- Polyfill: replaceChildren for older embedded Chromium -->
  <script>
  (function () {
    function makeReplaceChildrenFor(proto) {
      if (proto && typeof proto.replaceChildren !== 'function') {
        Object.defineProperty(proto, 'replaceChildren', {
          configurable: true,
          writable: true,
          value: function() {
            while (this.firstChild) {
              this.removeChild(this.firstChild);
            }
            for (var i = 0; i < arguments.length; i++) {
              var arg = arguments[i];
              if (typeof arg === 'string') {
                this.appendChild(document.createTextNode(arg));
              } else if (arg instanceof Node) {
                this.appendChild(arg);
              }
            }
          }
        });
      }
    }
    try {
      makeReplaceChildrenFor(Element && Element.prototype);
      makeReplaceChildrenFor(Document && Document.prototype);
      makeReplaceChildrenFor(DocumentFragment && DocumentFragment.prototype);
      if (typeof ShadowRoot !== 'undefined') {
        makeReplaceChildrenFor(ShadowRoot.prototype);
      }
      console.debug('replaceChildren polyfill installed (if needed)');
    } catch (e) {
      console.warn('replaceChildren polyfill error', e);
    }
  })();
  </script>

  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.2.0/css/xterm.css" />
  <style>
    html, body {
        height:100%;
        margin:0;
        background: transparent !important;
        background-color: transparent !important;
        /* 允许文本选择 */
        user-select: text !important;
        -webkit-user-select: text !important;
    }
    #terminal {
        height:100%;
        width:100%;
        background: transparent !important;
        background-color: transparent !important;
        /* fallback background color variable; used when transparency is not desired */
        --bg-fallback: {{bg_css}};
        /* 允许文本选择 */
        user-select: text !important;
        -webkit-user-select: text !important;
        font-family: {{font_family}}, monospace !important;
    }

    /* Force xterm rendering layers to be transparent so the page/window background shows */
    .xterm,
    .xterm * {
        background: transparent !important;
        background-color: transparent !important;
        font-family: {{font_family}}, monospace !important;
        user-select: text !important;
        -webkit-user-select: text !important;
    }


    .xterm .xterm-screen,
    .xterm .xterm-text-layer,
    .xterm .xterm-rows,
    .xterm .xterm-cursor-layer {
        background: transparent !important;
        background-color: transparent !important;
        font-family: {{font_family}}, monospace !important;
        user-select: text !important;
        -webkit-user-select: text !important;
    }
    
    .xterm-scrollbar {
        display: none !important;
    }

    .xterm .xterm-decoration-top {
        background: rgba(100, 150, 250, 0.5) !important;
        box-shadow: 0 0 5px rgba(100, 150, 250, 0.7);
        border-radius: 3px;
    }

    /* optional text shadow applied conditionally via JS */
    .xterm .xterm-text-layer {
        /* default no shadow; JS may set style on .xterm-text-layer to add shadow */
    }
    #context-menu {
        display: none;
        position: absolute;
        z-index: 1000;
        background-color: #2b2b2b;
        border: 1px solid #444;
        border-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.5);
        min-width: 150px;
        padding: 5px 0;
    }
    .menu-item {
        padding: 8px 15px;
        color: #d0d0d0;
        cursor: pointer;
        font-family: sans-serif;
        font-size: 14px;
    }
    .menu-item:hover {
        background-color: #3c3c3c;
    }
    .menu-item.disabled {
        color: #666;
        cursor: default;
        background-color: transparent;
    }
  </style>
</head>
<body>
  <div id="terminal"></div>
  <div id="context-menu">
    <div class="menu-item" id="menu-copy">复制</div>
    <div class="menu-item" id="menu-paste">粘贴</div>
  </div>

  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm@5.2.0/lib/xterm.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.7.0/lib/xterm-addon-fit.js"></script>

  <script>
// Prevent all drag operations
document.addEventListener('dragenter', e => e.preventDefault());
document.addEventListener('dragover', e => e.preventDefault());
document.addEventListener('drop', e => e.preventDefault());

  (function() {
    function safeDecodeB64ToBinary(b64) { return atob(b64); }
    function safeEncodeBinaryToB64(bin) { return btoa(bin); }

    new QWebChannel(qt.webChannelTransport, function(channel) {
      var bridge = channel.objects.bridge;
      const contextMenu = document.getElementById('context-menu');
      const menuCopy = document.getElementById('menu-copy');
      const menuPaste = document.getElementById('menu-paste');

      // create terminal with initial theme (transparent background; fg from Python)
      var term = new window.Terminal({
        convertEol: true,
        cursorBlink: true,
        rows: {{rows}},
        cols: {{cols}},
        theme: {
          background: "transparent",
          foreground: {{fg}}
        },
        scrollback: 1000,  // 增加滚动缓冲区
        fontFamily: '{{font_family}}, monospace'  // 设置终端字体
      });
      term.attachCustomKeyEventHandler(function(e) {
        if (e.ctrlKey && !e.shiftKey && e.code === 'KeyC') {
            const selection = term.getSelection();
            if (selection) {
                if (bridge && bridge.copyToClipboard) {
                    bridge.copyToClipboard(selection);
                }
                return false;
            }
            return true;
        }
        if (e.ctrlKey && !e.shiftKey && e.code === 'KeyV') {
            if (bridge && bridge.pasteFromClipboard) {
                bridge.pasteFromClipboard();
            }
            return false;
        }
        if (e.ctrlKey && e.shiftKey && (e.code === 'KeyV' || e.code === 'KeyC')) {
            return false;
        }
        return true;
      });


      // fit addon creation (robust to various UMD exports)
      var fitAddon = null;
      try {
        if (typeof window.FitAddon === 'function') {
          fitAddon = new window.FitAddon();
        } else if (window.FitAddon && typeof window.FitAddon.FitAddon === 'function') {
          fitAddon = new window.FitAddon.FitAddon();
        } else if (window.FitAddon && typeof window.FitAddon.default === 'function') {
          fitAddon = new window.FitAddon.default();
        } else if (typeof FitAddon === 'function') {
          fitAddon = new FitAddon();
        }
      } catch(e) {
        console.warn('FitAddon init failed', e);
        fitAddon = null;
      }

      if (fitAddon && typeof term.loadAddon === 'function') {
        try { term.loadAddon(fitAddon); } catch(e) { console.warn('loadAddon failed', e); }
      }

      term.open(document.getElementById('terminal'));
      window.term = term; // Expose term globally for Python calls
      
      // Expose a helper to update theme at runtime (called from Python via runJavaScript)
      window.setTerminalTheme = function(fg, bgFallback, shadow) {
        try {
          // update CSS variable for fallback background
          document.getElementById('terminal').style.setProperty('--bg-fallback', bgFallback || 'transparent');
          // set xterm theme (background remains transparent; we rely on fallback if necessary)
          term.options.theme = {
            foreground: fg || {{fg}},
            background: "transparent"
          };

          var textLayer = document.querySelector('.xterm .xterm-text-layer');
          if (textLayer) {
            if (shadow) {
              textLayer.style.textShadow = '0 0 4px rgba(0,0,0,0.9)';
            } else {
              textLayer.style.textShadow = '';
            }
          }
        } catch (e) {
          console.error('setTerminalTheme error', e);
        }
      };

      // Bridge -> JS: receive base64 data and write into terminal
      if (bridge && bridge.output) {
        bridge.output.connect(function(b64) {
          try {
            var text = base64ToUtf8(b64);
            term.write(text);
          } catch (e) {
            console.error('bridge.output write error', e);
          }
        });
      }
        function base64ToUtf8(b64) {
const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
return new TextDecoder("utf-8").decode(bytes);
}
        function utf8ToBase64(str) {
const bytes = new TextEncoder().encode(str);
let binary = '';
bytes.forEach(b => binary += String.fromCharCode(b));
return btoa(binary);
}

      // JS -> Bridge: user typed data
      term.onData(function(data) {
        try {
          var b64 = utf8ToBase64(data);
          bridge.sendInput(b64);
        } catch (e) {
          console.error('term.onData sendInput error', e);
        }
      });

      document.addEventListener('contextmenu', function(e) {
          e.preventDefault();
          const selection = term.getSelection();
          if (selection) {
              menuCopy.classList.remove('disabled');
          } else {
              menuCopy.classList.add('disabled');
          }
          contextMenu.style.top = `${e.clientY}px`;
          contextMenu.style.left = `${e.clientX}px`;
          contextMenu.style.display = 'block';
      });

      document.addEventListener('click', function(e) {
          if (contextMenu.style.display === 'block') {
              contextMenu.style.display = 'none';
          }
      });

      menuCopy.addEventListener('click', function() {
          const selection = term.getSelection();
          if (selection && bridge && bridge.copyToClipboard) {
              bridge.copyToClipboard(selection);
          }
      });

      menuPaste.addEventListener('click', function() {
          if (bridge && bridge.pasteFromClipboard) {
              bridge.pasteFromClipboard();
          }
      });


      // sizing: fit + notify backend of cols/rows
      window.notifySize = function() {
       console.log('notifySize triggered from Python.');
        try {
          if (fitAddon && typeof fitAddon.fit === 'function') {
            try { fitAddon.fit(); } catch(e) { /* ignore */ }
          }
          var cols = term.cols || 80;
          var rows = term.rows || 24;
          if (bridge && bridge.resize) {
            bridge.resize(cols, rows);
          }
        } catch (e) {
          console.error('notifySize error', e);
        }
      }


      // initial sizing & apply initial fallback bg & shadow
      setTimeout(function() {
        // apply initial bg fallback variable and shadow: Python provided values used below by calling setTerminalTheme
        window.notifySize();
        try {
          // call setTerminalTheme with initial values
          window.setTerminalTheme({{fg}}, {{bg}}, {{shadow}});
        } catch(e) {
          console.warn('initial setTerminalTheme failed', e);
        }
      }, 200);

      if (bridge && bridge.notifyReady) {
        bridge.notifyReady();
      }

    });
  })();
  </script>
</body>
</html>