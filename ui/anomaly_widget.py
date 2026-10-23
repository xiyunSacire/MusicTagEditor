from typing import List
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from core.models import AnomalyItem


class AnomalyWidget(QWidget):
    """异常与冗余标签诊断及清洗面板"""

    clean_all_requested = Signal()
    delete_keys_requested = Signal(list)  # 传递待删除的标签键列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_anomalies: List[AnomalyItem] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 诊断状态横幅
        self.status_banner = QLabel("就绪")
        self.status_banner.setWordWrap(True)
        self.status_banner.setStyleSheet("""
            QLabel {
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.status_banner)

        # 异常标签表格
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["标签键", "内容值", "异常分类", "诊断原因"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(1, 160)
        layout.addWidget(self.table)

        # 操作按钮条
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_clean_all = QPushButton("🧹 一键清理全部冗余数据")
        self.btn_clean_all.setObjectName("cleanupBtn")
        self.btn_clean_all.clicked.connect(self._on_clean_all)

        self.btn_delete_selected = QPushButton("删除选中标签")
        self.btn_delete_selected.setObjectName("dangerBtn")
        self.btn_delete_selected.clicked.connect(self._on_delete_selected)

        btn_layout.addWidget(self.btn_clean_all)
        btn_layout.addWidget(self.btn_delete_selected)
        layout.addLayout(btn_layout)

        self.set_anomalies([])

    def set_anomalies(self, items: List[AnomalyItem]):
        """更新异常标签列表展示"""
        self.current_anomalies = items
        count = len(items)

        self.table.setRowCount(count)

        if count == 0:
            self.status_banner.setStyleSheet("""
                QLabel {
                    background-color: #ecfdf5;
                    color: #065f46;
                    border: 1px solid #a7f3d0;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
            """)
            self.status_banner.setText("✔ 未发现异常或冗余残留标签，元数据规范。")
            self.btn_clean_all.setEnabled(False)
            self.btn_delete_selected.setEnabled(False)
        else:
            self.status_banner.setStyleSheet("""
                QLabel {
                    background-color: #fffbeb;
                    color: #92400e;
                    border: 1px solid #fde68a;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
            """)
            self.status_banner.setText(
                f"⚠️ 检测到 {count} 项残留或异常标签 (包含容器残留、转码签名等)"
            )
            self.btn_clean_all.setEnabled(True)
            self.btn_delete_selected.setEnabled(True)

        for row, item in enumerate(items):
            # 标签键
            k_item = QTableWidgetItem(item.display_name)
            k_item.setData(Qt.UserRole, item.raw_key)

            # 内容
            v_item = QTableWidgetItem(item.value)
            v_item.setToolTip(item.value)

            # 分类
            c_item = QTableWidgetItem(item.category)
            if item.category in ("容器残留", "转码/平台残留"):
                c_item.setForeground(QColor("#dc2626"))
            elif item.category == "编码器签名":
                c_item.setForeground(QColor("#d97706"))
            else:
                c_item.setForeground(QColor("#4b5563"))

            # 诊断原因
            r_item = QTableWidgetItem(item.reason)
            r_item.setToolTip(item.reason)

            self.table.setItem(row, 0, k_item)
            self.table.setItem(row, 1, v_item)
            self.table.setItem(row, 2, c_item)
            self.table.setItem(row, 3, r_item)

    def _on_clean_all(self):
        if not self.current_anomalies:
            return
        reply = QMessageBox.question(
            self,
            "清理确认",
            f"确定要清理当前文件中的全部 {len(self.current_anomalies)} 项冗余/异常标签吗？\n"
            "（标准音乐标签如标题、艺术家、专辑及封面将完整保留）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self.clean_all_requested.emit()

    def _on_delete_selected(self):
        selected_rows = sorted(
            list(set(index.row() for index in self.table.selectedIndexes())),
            reverse=True,
        )
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在表格中点击选中需要删除的标签行。")
            return

        keys = []
        for row in selected_rows:
            item = self.table.item(row, 0)
            if item:
                keys.append(item.data(Qt.UserRole))

        reply = QMessageBox.question(
            self,
            "删除确认",
            f"确定删除选中的 {len(keys)} 项标签吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self.delete_keys_requested.emit(keys)
