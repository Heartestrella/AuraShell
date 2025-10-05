## [English Documentation](README_en.md)

# 🖥️ PSSH — Win11 风格 SSH 终端

一个基于 **[PyQt](https://riverbankcomputing.com/software/pyqt/intro)** 与 **[QFluentWidgets](https://qfluentwidgets.com/)** 开发的跨平台 SSH 客户端，  
界面风格贴近 **Windows 11 Fluent Design**。

内置 **远程文件管理器** 与 **集成终端**，提供现代化、优雅且高效的远程管理体验。

> 💡 请先阅读本文件，大部分常见问题都能在这里找到答案。

---

## ✨ 功能特点

### 🎨 Win11 风格 UI  
- 使用 QFluentWidgets 实现 Fluent Design 风格  
- 支持亮/暗主题自动切换  (傻逼亮色 迟早删了)

---

### 🖥 SSH 终端  
基于 `xterm.js` 与 `QWebEngineView` 实现，支持：
- 命令行交互  
- 历史指令复用  
- 集成 AI 智能命令输入栏（目前支持 DeepSeek）  
- 可调整字体与配色方案  

---

### 📂 远程文件管理器  
- 文件上传 / 下载  
- 文件重命名 / 删除 / 权限修改  
- 类似 Windows 资源管理器的交互体验  
- 图标 / 列表两种文件视图  
- 实时进度与状态反馈  

![文件管理器示例](https://github.com/user-attachments/assets/e386c2b1-8283-4362-bd28-207b613cb15f)
![详细视图示例](https://github.com/user-attachments/assets/86af85be-661f-4a03-8bde-5687ea4a61b4)

---

### ⚡ 多会话管理  
- 支持同时连接多个远程主机  
- 快速切换不同会话  
- 支持直接复制 / 关闭会话  

---

### 🛜 网络与系统进程管理  
- 支持查看并操作网络与系统进程  
- 显示文件上传/下载进度，可中止操作  

![进程管理示例](https://github.com/user-attachments/assets/c4fb44cf-910c-412b-b4a8-0e8d32c465b6)

---

### 🤖 AI 智能体接入

#### ✨ 输入框快捷模式
在设置中启用并正确配置后：
- 在输入框输入自然语言  
- 按下 `Ctrl + O` 调用 AI 自动生成命令  
- 按下 `Tab` 接纳建议

![AI 快捷模式](https://github.com/user-attachments/assets/ab2aeb36-76cf-4bf5-b626-fdaf9121a717)

#### 📋 侧边栏高级模式
提供更强大的 Shell 辅助功能：

![AI 侧边栏](https://github.com/user-attachments/assets/777c658b-1ac4-4742-9e65-6832b76157cd)

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

---

### 从预编译版本运行
1. 从 **[Releases 页面](https://github.com/Heartestrella/P-SSH/releases)** 下载最新版本  
2. 解压缩包  
3. 运行可执行文件即可  

> ✅ 系统要求：Windows 10 或更高版本

---

## 📷 界面截图

![主界面](https://github.com/user-attachments/assets/2c99f305-65ef-4af2-affe-5b7d0d902d55)
![连接面板](https://github.com/user-attachments/assets/94ed1648-f667-4434-b891-80018a70e618)

---

## 🌐 多语言国际化（i18n）

目前仅支持 **中 / 英** 两种语言。  
计划在未来版本中引入完整的国际化系统，使 PSSH 可面向全球用户。

> ⚠️ **关于中文汉化**
> - 主要 UI 采用 `tr()` 标记实现  
> - 极少部分提示文字（Tips）未完全翻译  
> - 后续版本会进一步优化语言一致性

---

## 📝 源代码说明

PSSH 仍在持续开发中：
- 代码结构尚在整理与重构中  
- 部分模块由 AI 工具辅助生成  
- 注释正在补充完善  

---

## ⚠️ 已知问题与使用须知

### 🧭 使用技巧
- 启用 AI 功能后，在命令输入框输入自然语言 → 按下 **Ctrl + O**  
  AI 会生成命令建议，按 **Tab** 接纳。
- 内置编辑器的标签页关闭方式为 **双击标签标题**。

---

### 🧩 依赖提示
若左侧栏功能无法使用，请在远程主机安装以下命令：
```bash
sudo apt install -y ss lsblk iostat
```
（不同发行版请使用对应包管理器）

---

### 🪟 其他问题
- 由于Webengine的问题 导致软件在拖拽的时候存在卡顿现象
- 若字体显示异常，请确认系统中存在相应字体  
- 部分界面元素的样式在特定主题下可能略有偏差  

---

## 🔮 未来发展方向

- ✅ 完全 Python 实现终端渲染  
  当前终端依赖 `xterm.js`，未来计划使用纯 PyQt 渲染方案  
- 🧠 更深入的 AI Shell 辅助模式  
- 🌍 多语言与主题自定义支持  
- 🧱 插件式扩展架构  

---

> ⚠️ **Beta 测试版本说明**  
> 若遇到任何 bug，请附带运行日志与复现步骤提交到 [GitHub Issues](https://github.com/Heartestrella/P-SSH/issues)  
> 欢迎提交 PR，我们将在 **3 日内** 审核。

---

**💙 PSSH — A Fluent, Elegant SSH Experience**
