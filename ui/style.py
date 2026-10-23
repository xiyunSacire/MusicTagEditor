"""
现代轻量音乐标签编辑器 QSS 样式表
"""

MODERN_STYLE = """
/* 全局基础设置 */
QWidget {
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    color: #2c3e50;
    background-color: #f8fafc;
}

/* 标题栏与分组框 */
QGroupBox {
    font-weight: bold;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #3b82f6;
    background-color: #ffffff;
}

/* 输入框 */
QLineEdit, QTextEdit, QPlainTextEdit {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    background-color: #ffffff;
    selection-background-color: #3b82f6;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #ffffff;
}

QLineEdit:read-only {
    background-color: #f1f5f9;
    color: #64748b;
}

/* 按钮通用 */
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: 500;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #2563eb;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

QPushButton:disabled {
    background-color: #cbd5e1;
    color: #94a3b8;
}

/* 特殊危险/警告按钮 */
QPushButton#dangerBtn {
    background-color: #ef4444;
}
QPushButton#dangerBtn:hover {
    background-color: #dc2626;
}
QPushButton#dangerBtn:pressed {
    background-color: #b91c1c;
}

/* 次要/功能按钮 */
QPushButton#secondaryBtn {
    background-color: #f1f5f9;
    color: #334155;
    border: 1px solid #cbd5e1;
}
QPushButton#secondaryBtn:hover {
    background-color: #e2e8f0;
}
QPushButton#secondaryBtn:pressed {
    background-color: #cbd5e1;
}

/* 绿色成功按钮 */
QPushButton#successBtn {
    background-color: #10b981;
    color: #ffffff;
}
QPushButton#successBtn:hover {
    background-color: #059669;
}
QPushButton#successBtn:pressed {
    background-color: #047857;
}

/* 橙色清理按钮 */
QPushButton#cleanupBtn {
    background-color: #f59e0b;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#cleanupBtn:hover {
    background-color: #d97706;
}
QPushButton#cleanupBtn:pressed {
    background-color: #b45309;
}

/* 表格控件 */
QTableWidget, QTableView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #f1f5f9;
    selection-background-color: #e0f2fe;
    selection-color: #0f172a;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    font-weight: 600;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    padding: 6px 8px;
}

/* 滚动条 */
QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

/* 状态栏 */
QStatusBar {
    background-color: #f1f5f9;
    border-top: 1px solid #e2e8f0;
    color: #64748b;
    font-size: 12px;
}

/* 分割条 */
QSplitter::handle {
    background-color: #e2e8f0;
}
QSplitter::handle:horizontal {
    width: 4px;
}
QSplitter::handle:vertical {
    height: 4px;
}
"""
