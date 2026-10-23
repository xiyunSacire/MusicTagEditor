import os
import sys
import ctypes

# 将项目根目录加入模块搜索路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from ui.main_window import MainWindow
from ui.style import MODERN_STYLE


def get_resource_path(relative_path: str) -> str:
    """获取程序运行时的真实资源路径（兼容直接运行、单文件模式与单目录模式）"""
    # 1. 优先检查 PyInstaller 的 _MEIPASS 目录（单文件解压临时目录或单目录 _internal）
    if hasattr(sys, "_MEIPASS"):
        mei_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(mei_path):
            return mei_path

    # 2. 检查可执行文件所在目录（单目录模式下 exe 旁边）
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        exe_path = os.path.join(exe_dir, relative_path)
        if os.path.exists(exe_path):
            return exe_path

    # 3. 源码开发环境运行
    return os.path.join(PROJECT_ROOT, relative_path)


def set_windows_taskbar_icon(window, icon_path: str):
    """通过 Win32 API 向原生窗口 HWND 显式发送 WM_SETICON，确保 Windows 任务栏强制渲染图标"""
    try:
        if sys.platform != "win32" or not os.path.exists(icon_path):
            return
        hwnd = int(window.winId())
        user32 = ctypes.windll.user32
        WM_SETICON = 0x0080
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        # 加载 32x32（任务栏大图标）与 16x16（标题栏小图标）
        hicon_big = user32.LoadImageW(0, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        hicon_small = user32.LoadImageW(0, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        if hicon_big:
            user32.SendMessageW(hwnd, WM_SETICON, 1, hicon_big)
        if hicon_small:
            user32.SendMessageW(hwnd, WM_SETICON, 0, hicon_small)
    except Exception:
        pass


def main():
    # 解决 Windows 任务栏无法独立显示程序图标的暗坑
    # 必须显式声明唯一的 AppUserModelID，Windows 才会将此窗口作为独立程序分组显示，而不是归入 python.exe
    try:
        myappid = "musictageditor.desktop.player.v1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass
    
    # 启用高分屏支持与抗锯齿
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("MusicTagEditor")
    app.setApplicationDisplayName("MusicTagEditor - 音乐元数据与异常标签清洗工具")

    # 获取图标路径并加载多尺寸图标
    icon_path = get_resource_path("app.ico")
    app_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

    # 设置程序全局图标
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # 应用现代样式表
    app.setStyleSheet(MODERN_STYLE)

    # 设置默认字体
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    window = MainWindow(icon=app_icon)

    # 显式为主窗口设置窗口图标（确保任务栏预览、Alt+Tab与左上角精准显示定制图标）
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)

    # 如果启动时传递了文件/目录参数，自动载入
    if len(sys.argv) > 1:
        initial_paths = [p for p in sys.argv[1:] if os.path.exists(p)]
        if initial_paths:
            window.file_list_widget.add_paths(initial_paths)

    window.show()

    # 窗口显示后，向原生 Win32 HWND 投递底层 WM_SETICON 消息（击穿 Qt 抽象层直接给任务栏注入图标）
    set_windows_taskbar_icon(window, icon_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
