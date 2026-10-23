import os
import re
from typing import Optional, List
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QStatusBar,
    QMessageBox,
    QProgressBar,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut, QIcon

from core.tag_engine import load_audio, BaseAudioHandler
from core.models import StandardTags, CoverData
from .file_list_widget import FileListWidget
from .tag_form_widget import TagFormWidget
from .cover_widget import CoverWidget
from .anomaly_widget import AnomalyWidget


class MainWindow(QMainWindow):
    """主窗口控制器"""

    def __init__(self, icon: Optional[QIcon] = None):
        super().__init__()
        self.setWindowTitle("MusicTagEditor - 音乐元数据与异常标签清洗工具")
        self.resize(1200, 760)
        self.setMinimumSize(960, 600)

        if icon and not icon.isNull():
            self.setWindowIcon(icon)

        self.current_handler: Optional[BaseAudioHandler] = None
        self.current_file_path: Optional[str] = None

        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 主水平分割条
        self.main_splitter = QSplitter(Qt.Horizontal)

        # 1. 左侧：文件列表
        self.file_list_widget = FileListWidget()
        self.file_list_widget.file_selected.connect(self._on_file_selected)
        self.file_list_widget.batch_clean_requested.connect(self._on_batch_clean)
        self.file_list_widget.batch_guess_requested.connect(self._on_batch_guess)
        self.main_splitter.addWidget(self.file_list_widget)

        # 2. 中间：标准标签编辑表单
        self.tag_form_widget = TagFormWidget()
        self.tag_form_widget.save_requested.connect(self._on_save_tags)
        self.tag_form_widget.reset_requested.connect(self._on_reset_tags)
        self.tag_form_widget.reference_imported.connect(self._on_reference_imported)
        self.main_splitter.addWidget(self.tag_form_widget)

        # 3. 右侧：垂直分割（上方封面，下方异常检测表格）
        right_splitter = QSplitter(Qt.Vertical)

        self.cover_widget = CoverWidget()
        self.cover_widget.cover_changed.connect(self._on_cover_changed)
        self.cover_widget.cover_removed.connect(self._on_cover_removed)
        right_splitter.addWidget(self.cover_widget)

        self.anomaly_widget = AnomalyWidget()
        self.anomaly_widget.clean_all_requested.connect(self._on_clean_all_anomalies)
        self.anomaly_widget.delete_keys_requested.connect(self._on_delete_specific_anomalies)
        right_splitter.addWidget(self.anomaly_widget)

        # 设置右侧分割初始比例
        right_splitter.setSizes([320, 380])

        self.main_splitter.addWidget(right_splitter)

        # 设置主分割比例 (左 30%, 中 38%, 右 32%)
        self.main_splitter.setSizes([360, 440, 400])

        main_layout.addWidget(self.main_splitter)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 支持拖拽音频文件或文件夹至左侧列表")

    def _setup_shortcuts(self):
        # Ctrl+S 快捷键保存
        save_shortcut = QShortcut(QKeySequence.Save, self)
        save_shortcut.activated.connect(self.tag_form_widget._on_save)

    def _on_file_selected(self, file_path: str):
        """选中某个文件进行载入展示"""
        if not os.path.exists(file_path):
            return

        try:
            self.current_file_path = file_path
            self.current_handler = load_audio(file_path)

            # 1. 刷新基础信息至状态栏
            info = self.current_handler.get_stream_info()
            status_text = (
                f"文件: {info.file_name}  |  "
                f"格式: {info.format}  |  "
                f"时长: {info.duration_formatted}  |  "
                f"码率: {info.bitrate_kbps} kbps  |  "
                f"采样率: {info.sample_rate_hz} Hz  |  "
                f"声道: {info.channels}  |  "
                f"大小: {info.file_size_formatted}"
            )
            self.status_bar.showMessage(status_text)

            # 2. 刷新标准标签表单
            tags = self.current_handler.get_standard_tags()
            self.tag_form_widget.set_data(info.file_name, tags)

            # 3. 刷新封面预览
            cover = self.current_handler.get_cover()
            self.cover_widget.set_cover_data(cover)

            # 4. 刷新异常标签表格
            anomalies = self.current_handler.get_anomalies()
            self.anomaly_widget.set_anomalies(anomalies)

        except Exception as e:
            QMessageBox.critical(self, "读取文件失败", f"无法解析音频文件:\n{str(e)}")

    def _on_save_tags(self, tags: StandardTags):
        """保存标准元数据"""
        if not self.current_handler:
            QMessageBox.warning(self, "提示", "请先从左侧列表选择一个音频文件！")
            return

        try:
            self.current_handler.save_standard_tags(tags)
            self.status_bar.showMessage("✔ 标准元数据已成功保存！", 5000)
            QMessageBox.information(self, "保存成功", "音频元数据已成功写入文件！")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存元数据时出错:\n{str(e)}")

    def _on_reset_tags(self):
        self.status_bar.showMessage("已还原未保存的表单修改", 3000)

    def _on_cover_changed(self, img_bytes: bytes, mime_type: str):
        """用户更新封面"""
        if not self.current_handler:
            return
        try:
            self.current_handler.set_cover(img_bytes, mime_type)
            # 重新拉取以更新尺寸和视图
            cover = self.current_handler.get_cover()
            self.cover_widget.set_cover_data(cover)
            self.status_bar.showMessage("✔ 封面已成功更新并写入文件！", 5000)
            QMessageBox.information(self, "封面已更新", "新专辑封面已成功嵌入音频文件！")
        except Exception as e:
            QMessageBox.critical(self, "写入封面失败", f"更新封面时出错:\n{str(e)}")

    def _on_cover_removed(self):
        """用户移除封面"""
        if not self.current_handler:
            return
        try:
            self.current_handler.remove_cover()
            self.status_bar.showMessage("✔ 封面已从文件中移除！", 5000)
        except Exception as e:
            QMessageBox.critical(self, "删除封面失败", f"删除封面时出错:\n{str(e)}")

    def _on_clean_all_anomalies(self):
        """一键清理当前文件的所有异常标签"""
        if not self.current_handler or not self.current_file_path:
            return
        try:
            self.current_handler.clean_anomalies()
            # 重新获取异常项（此时应为 0）
            anomalies = self.current_handler.get_anomalies()
            self.anomaly_widget.set_anomalies(anomalies)

            # 更新左侧列表状态
            self.file_list_widget.update_file_status(self.current_file_path, len(anomalies))
            self.status_bar.showMessage("✔ 冗余异常标签已全部清除！", 5000)
            QMessageBox.information(self, "清洗完成", "所有检测出的冗余/异常标签已安全移除！")
        except Exception as e:
            QMessageBox.critical(self, "清洗失败", f"清理标签时发生错误:\n{str(e)}")

    def _on_delete_specific_anomalies(self, keys: List[str]):
        """删除选中的指定异常标签"""
        if not self.current_handler or not self.current_file_path:
            return
        try:
            self.current_handler.clean_anomalies(keys)
            anomalies = self.current_handler.get_anomalies()
            self.anomaly_widget.set_anomalies(anomalies)
            self.file_list_widget.update_file_status(self.current_file_path, len(anomalies))
            self.status_bar.showMessage(f"✔ 已删除选中的 {len(keys)} 项标签", 5000)
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除指定标签时发生错误:\n{str(e)}")

    def _on_batch_clean(self, dirty_paths: List[str]):
        """批量清理列表中所有异常文件"""
        success_count = 0
        error_count = 0

        for p in dirty_paths:
            try:
                handler = load_audio(p)
                handler.clean_anomalies()
                anomalies = handler.get_anomalies()
                self.file_list_widget.update_file_status(p, len(anomalies))
                success_count += 1
            except Exception as e:
                print(f"批量清理失败 {p}: {e}")
                error_count += 1

        # 如果当前打开的文件也在清理列表中，重新刷新
        if self.current_file_path and self.current_file_path in dirty_paths:
            self._on_file_selected(self.current_file_path)

        msg = f"批量清理完成！\n成功清理: {success_count} 个文件"
        if error_count > 0:
            msg += f"\n失败: {error_count} 个文件"

        self.status_bar.showMessage(f"✔ 批量清洗完成，处理了 {success_count} 个文件", 5000)
        QMessageBox.information(self, "批量清理结果", msg)

    def _on_reference_imported(self, ref_tags: StandardTags, ref_cover: Optional[CoverData]):
        """从参考音频导入了标签和封面"""
        if ref_cover:
            self.cover_widget.set_cover_data(ref_cover)
            if self.current_handler:
                try:
                    self.current_handler.set_cover(ref_cover.data, ref_cover.mime_type)
                except Exception as e:
                    print(f"写入导入的封面失败: {e}")
        self.status_bar.showMessage("已从参考音频导入标签数据（请核对后点击保存）", 5000)

    def _on_batch_guess(self, paths: List[str]):
        """批量根据文件名推导所有文件的艺术家与歌名并直接保存"""
        success = 0
        error = 0

        for p in paths:
            try:
                base = os.path.splitext(os.path.basename(p))[0].strip()
                track_num = ""
                m = re.match(r"^(?:\[?(\d{1,3})\]?[\s._\-]+)(.+)$", base)
                if m:
                    track_num = m.group(1).lstrip("0") or "0"
                    base = m.group(2).strip()

                artist, title = "", base
                for delim in [" - ", " – ", " — ", " － ", " _ ", "-", "_"]:
                    if delim in base:
                        parts = base.split(delim, 1)
                        a = parts[0].strip()
                        t = parts[1].strip()
                        if a and t:
                            artist, title = a, t
                            break

                handler = load_audio(p)
                tags = handler.get_standard_tags()
                if artist:
                    tags.artist = artist
                if title:
                    tags.title = title
                if track_num:
                    tags.track_number = track_num

                handler.save_standard_tags(tags)
                success += 1
            except Exception as e:
                print(f"批量推导标签失败 {p}: {e}")
                error += 1

        # 若当前选中文件被更改，重新刷新视图
        if self.current_file_path and self.current_file_path in paths:
            self._on_file_selected(self.current_file_path)

        self.status_bar.showMessage(f"✔ 批量推导完成，成功更新了 {success} 个文件！", 5000)
        msg = f"批量推导标签完成！\n成功更新: {success} 个文件"
        if error > 0:
            msg += f"\n失败: {error} 个文件"
        QMessageBox.information(self, "批量推导结果", msg)
