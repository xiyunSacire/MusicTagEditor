import os
from typing import List, Dict, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor

from core.tag_engine import load_audio
from core.models import AudioStreamInfo


class FileListWidget(QWidget):
    """文件列表管理组件（支持拖拽与异常状态标识）"""

    file_selected = Signal(str)  # 选中某个文件，通知主窗口载入
    files_added = Signal(list)
    batch_clean_requested = Signal(list)  # 批量清理异常标签请求
    batch_guess_requested = Signal(list)  # 批量推导标签请求

    SUPPORTED_EXTS = {".flac", ".mp3"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.file_data_map: Dict[str, dict] = {}  # path -> {info, anomaly_count}
        self.ordered_paths: List[str] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 顶部按钮条
        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)

        self.btn_add_files = QPushButton("＋ 添加文件")
        self.btn_add_files.setObjectName("secondaryBtn")
        self.btn_add_files.clicked.connect(self._on_add_files)

        self.btn_add_dir = QPushButton("📁 添加目录")
        self.btn_add_dir.setObjectName("secondaryBtn")
        self.btn_add_dir.clicked.connect(self._on_add_dir)

        self.btn_batch_guess = QPushButton("批量推导")
        self.btn_batch_guess.setObjectName("secondaryBtn")
        self.btn_batch_guess.setToolTip("根据文件名格式批量自动提取并保存所有文件的歌手和歌名")
        self.btn_batch_guess.clicked.connect(self._on_batch_guess)

        self.btn_batch_clean = QPushButton("批量清洗")
        self.btn_batch_clean.setObjectName("cleanupBtn")
        self.btn_batch_clean.setToolTip("对列表中所有存在异常标签的文件执行一键清理")
        self.btn_batch_clean.clicked.connect(self._on_batch_clean)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.clicked.connect(self.clear_all)

        top_bar.addWidget(self.btn_add_files)
        top_bar.addWidget(self.btn_add_dir)
        top_bar.addWidget(self.btn_batch_guess)
        top_bar.addWidget(self.btn_batch_clean)
        top_bar.addWidget(self.btn_clear)
        layout.addLayout(top_bar)

        # 搜索过滤条
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 快速过滤文件名...")
        self.search_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_edit)

        # 文件列表表格
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["状态", "文件名", "格式", "时长", "码率", "大小"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if os.path.exists(u.toLocalFile())]
        self.add_paths(paths)
        event.acceptProposedAction()

    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.flac *.mp3);;FLAC 音频 (*.flac);;MP3 音频 (*.mp3);;所有文件 (*.*)",
        )
        if files:
            self.add_paths(files)

    def _on_add_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择包含音频的文件夹")
        if folder:
            self.add_paths([folder])

    def add_paths(self, paths: List[str]):
        """收集路径中的音频文件并加入列表"""
        collected = []
        for p in paths:
            if os.path.isfile(p):
                ext = os.path.splitext(p)[1].lower()
                if ext in self.SUPPORTED_EXTS:
                    collected.append(os.path.abspath(p))
            elif os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in self.SUPPORTED_EXTS:
                            collected.append(os.path.abspath(os.path.join(root, f)))

        new_added = []
        for p in collected:
            if p not in self.file_data_map:
                try:
                    handler = load_audio(p)
                    info = handler.get_stream_info()
                    anomalies = handler.get_anomalies()
                    self.file_data_map[p] = {
                        "info": info,
                        "anomaly_count": len(anomalies),
                    }
                    self.ordered_paths.append(p)
                    new_added.append(p)
                except Exception as e:
                    print(f"载入音频失败 {p}: {e}")

        if new_added:
            self._refresh_table()
            self.files_added.emit(new_added)
            # 默认选中第一个
            if self.table.rowCount() > 0 and not self.table.selectedItems():
                self.table.selectRow(0)

    def update_file_status(self, file_path: str, anomaly_count: int):
        """刷新单个文件的异常状态与表格行"""
        if file_path in self.file_data_map:
            self.file_data_map[file_path]["anomaly_count"] = anomaly_count
            for row in range(self.table.rowCount()):
                p = self.table.item(row, 1).data(Qt.UserRole)
                if p == file_path:
                    self._set_status_item(row, anomaly_count)
                    break

    def _set_status_item(self, row: int, count: int):
        if count > 0:
            status_item = QTableWidgetItem(f"⚠️ {count}项异常")
            status_item.setForeground(QColor("#d97706"))
            status_item.setToolTip(f"检测到 {count} 项非标准/残留标签")
        else:
            status_item = QTableWidgetItem("✔ 规范")
            status_item.setForeground(QColor("#059669"))
            status_item.setToolTip("元数据规范，无残留标签")
        status_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, status_item)

    def _refresh_table(self):
        filter_text = self.search_edit.text().strip().lower()
        self.table.setRowCount(0)

        for p in self.ordered_paths:
            data = self.file_data_map.get(p)
            if not data:
                continue
            info: AudioStreamInfo = data["info"]
            count: int = data["anomaly_count"]

            if filter_text and filter_text not in info.file_name.lower():
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            # 状态列
            self._set_status_item(row, count)

            # 文件名列
            name_item = QTableWidgetItem(info.file_name)
            name_item.setData(Qt.UserRole, p)
            name_item.setToolTip(p)

            # 格式
            fmt_item = QTableWidgetItem(info.format)
            fmt_item.setTextAlignment(Qt.AlignCenter)

            # 时长
            dur_item = QTableWidgetItem(info.duration_formatted)
            dur_item.setTextAlignment(Qt.AlignCenter)

            # 码率
            br_item = QTableWidgetItem(f"{info.bitrate_kbps} kbps")
            br_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # 大小
            sz_item = QTableWidgetItem(info.file_size_formatted)
            sz_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, fmt_item)
            self.table.setItem(row, 3, dur_item)
            self.table.setItem(row, 4, br_item)
            self.table.setItem(row, 5, sz_item)

    def _apply_filter(self):
        self._refresh_table()

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = self.table.currentRow()
        item = self.table.item(row, 1)
        if item:
            path = item.data(Qt.UserRole)
            self.file_selected.emit(path)

    def _on_batch_guess(self):
        paths = list(self.ordered_paths)
        if not paths:
            QMessageBox.information(self, "提示", "列表中暂无文件！")
            return
        reply = QMessageBox.question(
            self,
            "批量推导确认",
            f"确定要对当前列表中的 {len(paths)} 个文件执行【按文件名推导标签并保存】吗？\n"
            "（将根据 '歌手 - 歌名' 等格式自动解析并直接写入音频文件的艺术家与标题）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self.batch_guess_requested.emit(paths)

    def _on_batch_clean(self):
        # 找出当前列表所有带异常的文件
        dirty_paths = [
            p for p, data in self.file_data_map.items() if data["anomaly_count"] > 0
        ]
        if not dirty_paths:
            QMessageBox.information(
                self, "提示", "列表中所有文件均为规范状态，没有需要清理的残留数据！"
            )
            return

        reply = QMessageBox.question(
            self,
            "批量清理确认",
            f"共检测到 {len(dirty_paths)} 个文件存在异常或残留标签。\n"
            "确定要对这些文件执行批量一键清洗吗？\n"
            "（所有标准音乐信息与封面将完整保留）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self.batch_clean_requested.emit(dirty_paths)

    def clear_all(self):
        self.file_data_map.clear()
        self.ordered_paths.clear()
        self.table.setRowCount(0)
