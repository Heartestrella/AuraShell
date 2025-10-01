## [中文文档](README_zh.md)

# PSSH — Win11 Style SSH Terminal

A cross-platform SSH client developed with **[PyQt](https://riverbankcomputing.com/software/pyqt/intro)** and **[QFluentWidgets](https://qfluentwidgets.com/)**, featuring an interface inspired by **Windows 11 Fluent Design**.  
Includes a **remote file manager** and **integrated terminal**, providing a modern, elegant, and efficient remote management experience.  

---
## ✨ Features

- 🎨 **Win11 Style UI**  
  Uses QFluentWidgets to implement Fluent Design, supports light/dark theme switching.

- 🖥 **SSH Terminal**  
  Based on `xterm.js` and `QWebEngineView`, supports:  
  - Command-line interaction  
  - Command history reuse  
  - Integrated AI-enhanced command input (Currently only supports deepseek)  
  - Adjustable font and color scheme  

- 📂 **Remote File Manager**  
  - File upload / download  
  - Rename / delete / modify permissions  
  - Windows Explorer-like interaction experience  
  - Icon/list views for different user preferences  

- ⚡ **Multi-Session Management**  
  - Supports simultaneous connections to multiple remote hosts  
  - Easy session switching  
  - Supports copy/close session directly  

- 🛜 **Network & Process Monitoring**  
  - View network and system processes
  - File upload/download progress display and termination  
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

### Running from Precompiled Version (Really Not recommended)
1. Download the latest packaged version from the Releases page.
2. Extract the compressed package.
3. Run the executable file directly.System requirements: Windows 10 or higher.
---



## 📷 Screenshots
<img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/c4fb44cf-910c-412b-b4a8-0e8d32c465b6" />

<img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/2c99f305-65ef-4af2-affe-5b7d0d902d55" />

<img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/e386c2b1-8283-4362-bd28-207b613cb15f" />

<img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/94ed1648-f667-4434-b891-80018a70e618" />

---


## 🌐 Internationalization (i18n)

Currently, multilingual support is not yet available. (Chinese and English only.)
This feature is planned for official release, which will include full internationalization support so that users around the world can use PSSH.

## 📝 Source Code

The source code of PSSH is still under development.  
It has not been fully organized, standardized, or refactored, and inline comments are incomplete.  
It is undeniable that part of the code has been generated with the help of AI tools.

## ⚠️ Known Issues & Usage Notes

- Some pages may not display the custom font correctly.  
- Certain UI elements may not fully match the main window's style.  
- Regarding font selection, the font that has been installed in the system is called instead of the character path.

> ⚠️ **Beta Version Notice:**  
> This is a beta release. If you encounter any bugs, please submit the runtime logs along with a brief description of how to reproduce the issue to the [GitHub Issues](https://github.com/Heartestrella/P-SSH/issues).
> Unimplemented Features
- Monitor open text file saves and automatically upload them
- Built-in notepad

## 🔮 Future Development Directions

- ✅ **More Complete Python Implementation**
The current terminal relies on `xterm.js`. While fully functional, it incurs additional memory usage and front-end dependencies.
