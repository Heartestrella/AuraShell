## [English Documentation](README.md)


# 🖥️ PSSH — Win11 Style SSH Terminal

A cross-platform SSH client built with **[PyQt](https://riverbankcomputing.com/software/pyqt/intro)** and **[QFluentWidgets](https://qfluentwidgets.com/)**,  
featuring a **Windows 11 Fluent Design** interface.

Includes a **remote file manager** and an **integrated terminal**, providing a modern, elegant, and efficient remote management experience.

> 💡 Please read this file carefully — most common issues are already covered here.

---

## ✨ Features

### 🎨 Win11 Fluent Design UI  
- Built with QFluentWidgets  
- Supports light/dark theme switching  

---

### 🖥 SSH Terminal  
Based on `xterm.js` and `QWebEngineView`, supporting:
- Full command-line interaction  
- Command history reuse  
- AI-assisted command input (currently supports **DeepSeek**)  
- Adjustable font size and color scheme  

---

### 📂 Remote File Manager  
- Upload / Download  
- Rename / Delete / Change permissions  
- Windows Explorer–like interface  
- Icon view and list view supported  
- Real-time progress display  

![File Manager Example](https://github.com/user-attachments/assets/e386c2b1-8283-4362-bd28-207b613cb15f)
![Detailed View Example](https://github.com/user-attachments/assets/86af85be-661f-4a03-8bde-5687ea4a61b4)

---

### ⚡ Multi-Session Management  
- Connect to multiple hosts simultaneously  
- Quickly switch between sessions  
- Duplicate or close sessions easily  

---

### 🛜 Network & Process Monitor  
- View and manage network/system processes  
- Monitor upload/download progress with cancel option  

![Process Management Example](https://github.com/user-attachments/assets/c4fb44cf-910c-412b-b4a8-0e8d32c465b6)

---

### 🤖 AI Integration

#### ✨ Quick Input Mode  
After enabling and configuring your AI key in settings:
- Type a natural-language instruction in the input box  
- Press **Ctrl + O** to call the AI assistant  
- Press **Tab** to accept the generated command  

![AI Quick Mode](https://github.com/user-attachments/assets/ab2aeb36-76cf-4bf5-b626-fdaf9121a717)

#### 📋 Sidebar Advanced Mode  
Provides more powerful shell assistance and context-aware suggestions.

![AI Sidebar](https://github.com/user-attachments/assets/777c658b-1ac4-4742-9e65-6832b76157cd)

---

## 🚀 How to Run

### Run from Source
1. Make sure you have **Python 3.8+**
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the main program:
   ```bash
   python main_window.py
   ```

---

### Run Precompiled Version
1. Download the latest release from the **[Releases Page](https://github.com/Heartestrella/P-SSH/releases)**  
2. Extract the archive  
3. Run the executable directly  

> ✅ **System Requirement:** Windows 10 or later

---

## 📷 Screenshots

![Main Window](https://github.com/user-attachments/assets/2c99f305-65ef-4af2-affe-5b7d0d902d55)
![Connection Panel](https://github.com/user-attachments/assets/94ed1648-f667-4434-b891-80018a70e618)

---

## 🌐 Internationalization (i18n)

Currently supports **English** and **Chinese** only.  
A complete multilingual system will be introduced in future releases.

> ⚠️ **About Translation**
> - Most UI text is marked with `tr()` for localization  
> - A few tooltips remain untranslated  
> - This will be refined in future updates  

---

## 📝 Source Code Notes

PSSH is still under active development:
- Code structure is being refactored and cleaned  
- Some components were AI-assisted  
- Documentation and comments are being improved  

---

## ⚠️ Known Issues & Tips

### 🧭 Usage Tips
- After enabling AI, type a natural language command in the input box  
  → Press **Ctrl + O** to generate commands  
  → Press **Tab** to accept the suggestion  
- To close a tab in the built-in editor, **double-click** the tab title.  

---

### 🧩 Dependencies
If the **left sidebar** information is missing, make sure these commands are installed on your remote system:
```bash
sudo apt install -y ss lsblk iostat
```
(Use your package manager if not on Debian/Ubuntu)

---

### 🪟 Other Notes
- If fonts display incorrectly, ensure the font is installed on your system  
- Some minor style mismatches may appear in specific themes  

---

## 🔮 Future Development

- ✅ Full Python-based terminal rendering (remove xterm.js dependency)  
- 🧠 Enhanced AI-assisted Shell operations  
- 🌍 Extended multi-language and theming support  
- 🧱 Plugin-based extensibility  

---

> ⚠️ **Beta Notice:**  
> If you encounter bugs, please submit an issue with logs and reproduction steps to [GitHub Issues](https://github.com/Heartestrella/P-SSH/issues).  
> Pull requests are welcome — all submissions will be reviewed within **3 days**.

---

**💙 PSSH — A Fluent, Elegant SSH Experience**
