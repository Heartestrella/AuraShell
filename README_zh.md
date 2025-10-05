## [English Documentation](README.md)

# PSSH — Win11 风格 SSH 终端

一个基于 **[PyQt](https://riverbankcomputing.com/software/pyqt/intro)** 与 **[QFluentWidgets](https://qfluentwidgets.com/)** 开发的跨平台 SSH 客户端，界面风格贴近 **Windows 11 Fluent Design**  
内置 **远程文件管理器** 与 **集成终端**，提供现代化、优雅且高效的远程管理体验  

请看完MD文件 大部分问题都可以解决
---

## ✨ 功能特点

- 🎨 **Win11 风格 UI**  
  使用 QFluentWidgets 实现 Fluent Design 风格，支持亮/暗主题切换  

- 🖥 **SSH 终端**  
  基于 `xterm.js` 与 `QWebEngineView` 实现，支持：  
  - 命令行交互  
  - 历史指令复用
  - 集成Ai 多功能的命令输入栏 (目前只做了Deepseek的支持)
  - 可调整字体与配色方案  

- 📂 **远程文件管理器**  
  - 文件上传 / 下载  
  - 文件重命名 / 删除 / 权限修改 等等
  - 类似 Windows 资源管理器的交互体验  
  - 图标/列表显示文件信息 满足不同人群喜好
  - <img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/e386c2b1-8283-4362-bd28-207b613cb15f" />
  - <img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/86af85be-661f-4a03-8bde-5687ea4a61b4" />

- ⚡ **多会话管理**  
  - 支持同时连接多个远程主机  
  - 方便切换不同会话  
  - 支持直接复制/关闭会话

- 🛜 **网络进程/详细应用进程查看**
  - 支持查看 并且操作网络与系统进程
  - 文件上传下载进度显示与终止
  - <img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/c4fb44cf-910c-412b-b4a8-0e8d32c465b6" />
  
- **AI智能体接入**
  - 输入框快捷模式
    - 当在设置页面中启用并正确配置后 在输入框输入自然语言 并按下Ctrl + O 快捷键 可调用Ai生成指令或辅助定位报错问题
    - <img width="1570" height="788" alt="image" src="https://github.com/user-attachments/assets/ab2aeb36-76cf-4bf5-b626-fdaf9121a717" />
  - 侧边栏高级模式
    - 在拉起后 可以进行更高级对Shell的辅助
    - <img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/777c658b-1ac4-4742-9e65-6832b76157cd" />

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


<img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/2c99f305-65ef-4af2-affe-5b7d0d902d55" />

<img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/94ed1648-f667-4434-b891-80018a70e618" />

---


---
## 🌐 多语言国际化（i18n）

目前多语言支持尚未实现  (仅限于中英有翻译)
计划在正式版本中加入完整的国际化支持，使 PSSH 面向全球用户可用
# ⚠️关于中文汉化
代码全部UI都默认为英文 用tr标记翻译了尽可能多的UI内容
但是仍然有极少部分TIPS的汉化出现问题 但都是些常见的单词 也许会在后续修复该非致命问题

~~我真傻逼 从英文翻译到中文 不从中文做对其他语言的~~
---


## 📝 源代码说明

PSSH 的源代码仍在开发中  
代码尚未完全整理、规范化或重构，且部分注释尚不完整  
不可否认的是，部分代码由 AI 工具辅助生成

## ⚠️ 已知问题与使用须知

# 使用技巧
- AI辅助功能 在正确配置KEY和MODEL后 在命令输入框输入自然语言 然后按Ctrl + O 即可开始生成 按Tab接纳AI建议填充到输入框
- 若需要关闭内置编辑器的tab 请双击(我要不说 估计没人能知道了)

# 部分小问题
- 若需要左侧栏的功能 请手动安装 ss lsblk iostat 这几个包(apt yum等包管理器) 脚本虽然内置安装 但不一定管用 若不显示左侧边栏信息 多半是这几个包的问题
- 部分页面可能未正确显示自定义字体
- 部分界面元素可能与主窗口风格不完全一致
- 关于选择字体调用的是已经安装到系统中的字体 而非选择字符路径



> ⚠️ **Beta 版本说明：**  
> 这是一个测试版本如果遇到任何 bug，请将运行日志以及大致复现方法提交到 [GitHub Issues](https://github.com/Heartestrella/P-SSH/issues)
> 若您愿意参与到项目的开发中来 向我们提交Pr 我们将在3日内审核

## 🔮 未来发展方向

- ✅ **更完全的 Python 实现**  
  当前终端依赖 `xterm.js`，虽然功能完整，但会带来额外的内存与前端依赖
