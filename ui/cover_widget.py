import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent

from core.models import CoverData


class CoverDropLabel(QLabel):
    """支持拖拽图片的封面预览框"""

    image_dropped = Signal(str)  # 传递图片文件本地路径
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(180, 180)
        self.setMaximumSize(300, 300)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #cbd5e1;
                border-radius: 8px;
                background-color: #f8fafc;
                color: #94a3b8;
            }
            QLabel:hover {
                border-color: #3b82f6;
                background-color: #eff6ff;
            }
        """)
        self.setText("暂无封面\n点击或拖拽图片至此处添加")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                ext = os.path.splitext(urls[0].toLocalFile())[1].lower()
                if ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.image_dropped.emit(file_path)
            event.acceptProposedAction()


class CoverWidget(QWidget):
    """专辑封面展示与管理组件"""

    cover_changed = Signal(bytes, str)  # (image_bytes, mime_type)
    cover_removed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_cover: Optional[CoverData] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 封面预览区域
        self.preview_label = CoverDropLabel()
        self.preview_label.clicked.connect(self._on_choose_image)
        self.preview_label.image_dropped.connect(self._load_image_from_path)
        layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)

        # 封面参数信息
        self.info_label = QLabel("无内嵌封面")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.info_label)

        # 操作按钮条
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.btn_replace = QPushButton("替换封面")
        self.btn_replace.setObjectName("secondaryBtn")
        self.btn_replace.clicked.connect(self._on_choose_image)

        self.btn_export = QPushButton("导出封面")
        self.btn_export.setObjectName("secondaryBtn")
        self.btn_export.clicked.connect(self._on_export_cover)

        self.btn_delete = QPushButton("删除封面")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self._on_delete_cover)

        btn_layout.addWidget(self.btn_replace)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

    def set_cover_data(self, cover: Optional[CoverData]):
        """设置当前封面数据并刷新界面"""
        self.current_cover = cover
        if cover and cover.data:
            pixmap = QPixmap()
            pixmap.loadFromData(cover.data)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
                mime_short = "PNG" if "png" in cover.mime_type.lower() else "JPEG"
                kb = cover.size_bytes / 1024
                self.info_label.setText(
                    f"{mime_short} · {cover.width}×{cover.height} · {kb:.1f} KB"
                )
                self.btn_export.setEnabled(True)
                self.btn_delete.setEnabled(True)
                return

        # 无封面时
        self.preview_label.clear()
        self.preview_label.setText("暂无封面\n点击或拖拽图片至此处添加")
        self.info_label.setText("无内嵌封面")
        self.btn_export.setEnabled(False)
        self.btn_delete.setEnabled(False)

    def _on_choose_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择专辑封面图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.webp);;所有文件 (*.*)",
        )
        if file_path:
            self._load_image_from_path(file_path)

    def _load_image_from_path(self, file_path: str):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            ext = os.path.splitext(file_path)[1].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            self.cover_changed.emit(data, mime)
        except Exception as e:
            QMessageBox.critical(self, "读取封面错误", f"无法读取图片文件:\n{str(e)}")

    def _on_export_cover(self):
        if not self.current_cover or not self.current_cover.data:
            return
        ext = ".png" if "png" in self.current_cover.mime_type.lower() else ".jpg"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出封面图片", f"cover{ext}", f"图片文件 (*{ext})"
        )
        if save_path:
            try:
                with open(save_path, "wb") as f:
                    f.write(self.current_cover.data)
                QMessageBox.information(self, "导出成功", f"封面图片已成功保存至:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"无法导出图片:\n{str(e)}")

    def _on_delete_cover(self):
        if not self.current_cover:
            return
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要从当前文件中移除内嵌封面吗？（保存后生效）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.set_cover_data(None)
            self.cover_removed.emit()
