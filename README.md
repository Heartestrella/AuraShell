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
```bash
 pip install -r requirements.txt
```
4. Run the main program:
```bash
 python main_window.py
```

### Running from Precompiled Version
1. Download the latest packaged version from the Releases page.
2. Extract the compressed package.
3. Run the executable file directly.System requirements: Windows 10 or higher.
---



## 📷 Screenshots

<img width="1456" height="819" alt="image" src="https://github.com/user-attachments/assets/467ac84d-284e-4572-97ea-22109ee92575" />
<img width="1456" height="819" alt="image" src="https://github.com/user-attachments/assets/da427c06-731e-4606-b5f6-1ea3b038301c" />
<img width="1456" height="819" alt="image" src="https://github.com/user-attachments/assets/34e86170-d602-4f6c-8540-358447f2faf9" />





---


## 🌐 Internationalization (i18n)

Currently, multilingual support is not yet available. (Chinese and English only.)
This feature is planned for official release, which will include full internationalization support so that users around the world can use PSSH.

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
> Unimplemented Features
- Display file upload/download progress
- Terminate file upload/download progress
- Monitor open text file saves and automatically upload them
- Built-in notepad

