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
  - Integrated AI-enhanced command input (AI-generated commands will be supported in the future)  
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
  - View network and system processes (operation support coming soon)  
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

### Running from Precompiled Version
1. Download the latest packaged version from the Releases page.
2. Extract the compressed package.
3. Run the executable file directly.System requirements: Windows 10 or higher.
---



## 📷 Screenshots
<img width="1920" height="1040" alt="46d1914a-129b-464b-b08c-ac13bc94f14c" src="https://github.com/user-attachments/assets/4853b2a5-c0a0-404f-a295-9e5c93aead41" />
<img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/b27f0d00-a65f-4a6c-8fd2-9a8ff6e6d521" />
<img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/9a34ce06-4ba1-4853-997c-d7e2a71679b7" />
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