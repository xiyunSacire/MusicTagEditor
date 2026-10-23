# MusicTagEditor (音乐元数据与异常标签清洗工具)

<p align="center">
  <b>专为音乐爱好者与本地收藏整理者设计的轻量级桌面元数据查看、编辑与异常标签检测清洗工具</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python Version" />
  <img src="https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-brightgreen.svg" alt="PySide6" />
  <img src="https://img.shields.io/badge/Audio%20Engine-Mutagen-orange.svg" alt="Mutagen" />
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6.svg" alt="Windows" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey.svg" alt="License" />
</p>

---

## 📖 项目简介

在现代本地音乐收藏中，我们常常从各类音视频切片（例如 B站 m4s/MP4 转封装、FFmpeg 粗暴提取）中获取音频文件。这些文件往往残留着大量非标准的容器脏数据（如 `major_brand`、`compatible_brands`、转码签名 `Packed by Bilibili XCoder` 等），导致很多音乐播放器（如 Foobar2000、Walkman、车载中控、网易云等）出现标签乱码、分类混乱或无法读取内嵌封面。

**MusicTagEditor** 提供了直观的可视化诊断与一键清洗引擎：既支持常规音乐标签（歌名、歌手、专辑、年份、音轨、LRC歌词、高清封面）的高效编辑与批量推导，又具备底层的异常标签扫描能力，帮助您快速打造纯净、标准的本地音乐曲库。

---

## ✨ 核心特性

### 1. 异常与残留数据深度检测与清洗
* **容器残留识别**：精准扫描 `major_brand`、`minor_version`、`compatible_brands`、`encoder` 等从 MP4/M4S 继承而来的无用脏数据。
* **转码签名与平台标识**：自动标红识别并清理 `Packed by Bilibili XCoder`、`Lavf...` 等工具签名。
* **空值与未知非标帧**：检测空文本标签、私有二进制帧或格式损坏的废弃字段。
* **一键清洗**：提供单曲一键剔除和全部歌曲**批量一键清洗**，完整保留标准元数据与内嵌封面。

### 2. 标准音乐元数据编辑与智能推导
* **完整元数据覆盖**：歌曲标题、艺术家、专辑名、专辑艺术家、音轨号/总轨数、碟片号/总碟数、发行年份、流派分类、备注。
* **内嵌歌词支持**：支持嵌入式 LRC 歌词与纯文本歌词展示，提供一键导入外部 `.lrc` 文件功能。
* **从文件名智能推导**：支持常见命名模式（如 `歌手 - 歌名`、`序号. 歌手 - 歌名` 等）智能提取，支持**单曲推导**与**全列表批量智能应用**。
* **参考音频标签克隆**：支持从另一个规范音频文件中一键克隆标题、专辑、歌手及内嵌封面。

### 3. 专辑封面可视化管理
* **高清封面预览**：实时展示内嵌封面缩略图，显示分辨率（如 `800×800`）、图片格式与体积。
* **拖拽直接替换**：支持从桌面或文件夹将 JPG/PNG 图片直接拖入封面区域完成替换。
* **封面导出与剥离**：支持一键将内嵌图片提取保存至本地，或一键剥离内嵌图片以大幅精简文件体积。

### 4. 批量处理与优雅交互
* **全量拖拽交互**：支持从资源管理器直接拖拽单个音频文件、多个文件或整个音乐文件夹。
* **状态徽标直观呈现**：左侧文件列表实时展示 `✔ 规范` 与 `⚠️ X项异常` 徽标，规范情况一目了然。
* **实时检索与过滤**：支持通过文件名关键字实时过滤列表。
* **任务栏定制图标与快捷键**：深度适配 Windows 11/10 原生任务栏分组与高分屏缩放，支持 `Ctrl + S` 快速保存。

---

## 🎵 支持音频格式

| 音频格式 | 文件扩展名 | 底层标签规范 | 封面与特殊支持 |
| :--- | :--- | :--- | :--- |
| **FLAC** | `.flac` | Vorbis Comment | 原生 Picture Block (支持多尺寸图片与 MIME 类型) |
| **MP3** | `.mp3` | ID3v2.3 / ID3v2.4 | APIC 封面帧、COMM 备注帧、USLT 内嵌歌词帧 |

---

## 🚀 快速上手与运行

### 方式一：开发环境运行（源码方式）

#### 1. 准备环境与安装依赖
推荐使用 Python 3.10 或更高版本：
```bash
git clone https://github.com/your-username/MusicTagEditor.git
cd MusicTagEditor

# 创建虚拟环境（可选推荐）
python -m venv venv
venv\Scripts\activate

# 安装必要依赖
pip install -r requirements.txt
```

#### 2. 启动应用程序
```bash
python main.py
```
*提示：您也可以在启动时传入音乐文件夹路径作为初始参数：*
```bash
python main.py "D:\Music"
```

---

## 📦 Windows 独立软件打包与发布 (Packaging)

本项目已针对 Windows 平台深度优化，彻底解决了常见于 Conda 环境、PySide6 动态链接及 Windows Defender SmartScreen 的打包暗坑：

* **独立 Onedir 架构 (`-D`)**：毫秒级极速冷启动，告别单文件 (`-F`) 解压到 `%TEMP%` 的卡顿与安全软件误杀。
* **Conda 运行时依赖补齐**：自动补齐配套的 `msvcp140*.dll`、`vcruntime140*.dll` 与 `ffi.dll`，彻底杜绝 `WinError 127: 找不到指定的程序` 与 `_ctypes` 丢失。
* **原生任务栏图标适配**：注册独立 `AppUserModelID` 并通过底层 Win32 API 发送 `WM_SETICON` 消息，确保任务栏完美显示定制图标。
* **Authenticode 代码签名**：支持自签名证书并导出受信任颁发机构，解决 SmartScreen “发布者未知” 警告。

### 一键打包方式：
直接在项目根目录下右键以 PowerShell 运行脚本：
```powershell
.\build_release.ps1
```
或者双击运行纯批处理入口：
```cmd
build_release.bat
```
打包成功后，可在 `dist\MusicTagEditor\` 目录下获取即点即用的完整独立绿色版客户端。

> 💡 **详细排坑技术指南**：关于 Windows GUI 工业级打包技术细节、依赖排查与代码签名原理，请参考专门撰写的深度指南：[python-gui-packaging-windows-guide.md](python-gui-packaging-windows-guide.md)。

---

## 📂 项目结构说明

```text
MusicTagEditor/
├── core/                                # 核心业务层（纯 Python，解耦 UI）
│   ├── models.py                        # 数据实体 (StandardTags, AnomalyItem, CoverData)
│   ├── detector.py                      # 异常与冗余标签诊断规则库 (白名单/黑名单正则匹配)
│   └── tag_engine.py                    # 音频标签读写底层驱动适配器 (Mutagen FLAC/MP3)
├── ui/                                  # 界面表现层 (PySide6 / Qt)
│   ├── style.py                         # 现代深色/扁平化 QSS 样式表与调色板
│   ├── file_list_widget.py              # 左侧文件拖拽列表与状态徽标
│   ├── tag_form_widget.py               # 中间标准元数据编辑表单与智能解析
│   ├── cover_widget.py                  # 右上方专辑封面拖拽预览与导出模块
│   ├── anomaly_widget.py                # 右下方异常标签列表与一键清洗面板
│   └── main_window.py                   # 主窗口核心布局与信号调度中枢
├── app.ico                              # 高清多分辨率应用程序图标 (16~256px)
├── build_release.ps1                    # 自动化打包、依赖补齐与自签名流水线
├── build_release.bat                    # 双击运行打包的批处理入口
├── install_cert.bat                     # 本地自签名根证书生成与受信任导入脚本
├── python-gui-packaging-windows-guide.md # Windows Python GUI 打包排坑实战白皮书
├── requirements.txt                     # 生产与运行依赖清单
├── main.py                              # 应用程序主入口 (进程 AppID 与 Win32 消息挂载)
└── README.md                            # 项目技术与使用文档
```

---

## ❓ 常见问题 (FAQ)

### Q: 首次运行打包后的 exe 提示“Windows 已保护你的电脑，阻止了无法识别的应用启动”？
**A**: 这是 Windows Defender SmartScreen 对没有购买商业 EV 证书（本地新生成哈希二进制）的防御性提醒：
1. 点击弹窗上的 **“更多信息” (More info)** 链接；
2. 点击右下角的 **“仍要运行” (Run anyway)**；
3. **只需点击这一次**，Windows 会将该程序签名哈希永久计入本地受信白名单，后续双击再也不会弹窗。

### Q: 任务栏为什么显示了正确的应用图标，而不是通用的 Python 图标？
**A**: 本项目在 `main.py` 中通过 `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID` 为程序指定了唯一的 AppID，使 Windows 桌面管理器将此窗口当成独立的专业软件对待；同时在窗口创建后通过 Win32 API 投递了 `WM_SETICON` 消息强制刷新系统任务栏缓存。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 许可证开源，欢迎自由使用、修改与分发。
