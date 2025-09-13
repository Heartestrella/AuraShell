## [English Documentation](README.md)

# PSSH — Win11 风格 SSH 终端

一个基于 **[PyQt](https://riverbankcomputing.com/software/pyqt/intro)** 与 **[QFluentWidgets](https://qfluentwidgets.com/)** 开发的跨平台 SSH 客户端，界面风格贴近 **Windows 11 Fluent Design**  
内置 **远程文件管理器** 与 **集成终端**，提供现代化、优雅且高效的远程管理体验  

---

## ✨ 功能特点

- 🎨 **Win11 风格 UI**  
  使用 QFluentWidgets 实现 Fluent Design 风格，支持亮/暗主题切换  

- 🖥 **SSH 终端**  
  基于 `xterm.js` 与 `QWebEngineView` 实现，支持：  
  - 命令行交互  
  - 文本复制/粘贴（支持快捷键）  
  - 可调整字体与配色方案  

- 📂 **远程文件管理器**  
  - 文件上传 / 下载  
  - 文件重命名 / 删除 / 权限修改  
  - 类似 Windows 资源管理器的交互体验  

- ⚡ **多会话管理**  
  - 支持同时连接多个远程主机  
  - 方便切换不同会话  

---

---
## 🚀 运行方式

### 从源代码运行

1. 确保已安装 Python 3.8+
2. 安装依赖包：
```bash
pip install -r requirements.txt
```
3. 运行主程序：
```bash
python main_window.py
```

### 从预编译版本运行
1. 从 Releases 页面 下载最新的打包版本

2. 解压压缩包

3. 直接运行可执行文件

系统要求: Windows 10 或更高版本
---

## 📷 界面截图

<img width="1557" height="780" alt="2fd06349e71c266d6e154124fb468eea" src="https://github.com/user-attachments/assets/8d5fa40d-7783-4cf2-9467-36c6f76c735b" />
<img width="1557" height="780" alt="07eaa1154efbc5ac496323983e92fe7e" src="https://github.com/user-attachments/assets/41c15ef4-b3bb-4cb8-b08b-454b0aa32ced" />
<img width="1557" height="780" alt="99804f59c816008c0647800ac79a0f8e" src="https://github.com/user-attachments/assets/115abcc7-c140-484a-bc67-38e82f2636a8" />

---


---
## 🌐 多语言国际化（i18n）

目前多语言支持尚未实现  (仅限于中英有翻译)
计划在正式版本中加入完整的国际化支持，使 PSSH 面向全球用户可用
# ⚠️关于中文汉化
代码全部UI都默认为英文 用tr标记翻译了尽可能多的UI内容
但是仍然有极少部分TIPS的汉化出现问题 但都是些常见的单词 也许会在后续修复该非致命问题

---


## 📝 源代码说明

PSSH 的源代码仍在开发中  
代码尚未完全整理、规范化或重构，且部分注释尚不完整  
不可否认的是，部分代码由 AI 工具辅助生成

## ⚠️ 已知问题与使用须知


- 在 SSH 终端中，选中文本时不会显示光标，  
  但文本实际上已被选中，可使用 `Ctrl+Shift+C` 复制，`Ctrl+Shift+V` 粘贴
- 部分页面可能未正确显示自定义字体
- 部分界面元素可能与主窗口风格不完全一致


> ⚠️ **Beta 版本说明：**  
> 这是一个测试版本如果遇到任何 bug，请将运行日志以及大致复现方法提交到 [GitHub Issues](https://github.com/Heartestrella/P-SSH/issues)

