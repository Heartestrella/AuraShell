## [中文文档](README_zh.md)

# PSSH — Win11 Style SSH Terminal

A cross-platform SSH client developed with **[PyQt](https://riverbankcomputing.com/software/pyqt/intro)** and **[QFluentWidgets](https://qfluentwidgets.com/)**, featuring an interface inspired by **Windows 11 Fluent Design**.  
Includes a **remote file manager** and **integrated terminal**, providing a modern, elegant, and efficient remote management experience.  

---

## ✨ Features

- 🎨 **Win11 Style UI**  
  Uses QFluentWidgets to implement Fluent Design style, supporting light/dark theme switching.  

- 🖥 **SSH Terminal**  
  Built with `xterm.js` and `QWebEngineView`, supporting:  
  - Command-line interaction  
  - Text copy & paste (shortcut keys supported)  
  - Adjustable fonts and color schemes  

- 📂 **Remote File Manager**  
  - File upload / download  
  - File renaming / deletion / permission modification  
  - Interaction similar to Windows Explorer  

- ⚡ **Multi-Session Management**  
  - Supports multiple simultaneous remote connections  
  - Easy switching between different sessions  

---
---
## 🚀 How to Run

### Running from Source Code
1. Make sure Python 3.8 is installed.
2. Install the dependencies:
```
bash pip install -r requirements.txt
```
4. Run the main program:
```
bash python main_window.py
```

### Running from Precompiled Version
1. Download the latest packaged version from the Releases page.
2. Extract the compressed package.
3. Run the executable file directly.System requirements: Windows 10 or higher.
---



## 📷 Screenshots

<img width="1557" height="780" alt="2fd06349e71c266d6e154124fb468eea" src="https://github.com/user-attachments/assets/8d5fa40d-7783-4cf2-9467-36c6f76c735b" />
<img width="1557" height="780" alt="07eaa1154efbc5ac496323983e92fe7e" src="https://github.com/user-attachments/assets/41c15ef4-b3bb-4cb8-b08b-454b0aa32ced" />
<img width="1557" height="780" alt="99804f59c816008c0647800ac79a0f8e" src="https://github.com/user-attachments/assets/115abcc7-c140-484a-bc67-38e82f2636a8" />


---


## 🌐 Internationalization (i18n)

Currently, multi-language support is not yet implemented.  
This feature is planned for the official release, which will include full internationalization support to make PSSH accessible to users worldwide.

## 📝 Source Code

The source code of PSSH is still under development.  
It has not been fully organized, standardized, or refactored, and inline comments are incomplete.  
It is undeniable that part of the code has been generated with the help of AI tools.

## ⚠️ Known Issues & Usage Notes

- In the SSH terminal, text selection does not display a visible cursor,  
  but the text is actually selected and can be copied with `Ctrl+Shift+C` and pasted with `Ctrl+Shift+V`.  
- Some pages may not display the custom font correctly.  
- Certain UI elements may not fully match the main window's style.  

> ⚠️ **Beta Version Notice:**  
> This is a beta release. If you encounter any bugs, please submit the runtime logs along with a brief description of how to reproduce the issue to the [GitHub Issues](https://github.com/Heartestrella/P-SSH/issues).


