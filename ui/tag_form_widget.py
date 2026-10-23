import os
import re
from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QGroupBox,
    QFileDialog,
)
from PySide6.QtCore import Qt, Signal

from core.models import StandardTags, CoverData
from core.tag_engine import load_audio


class TagFormWidget(QWidget):
    """常规元数据编辑表单"""

    save_requested = Signal(StandardTags)
    reset_requested = Signal()
    reference_imported = Signal(StandardTags, object)  # (StandardTags, Optional[CoverData])

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filename = ""
        self.original_tags = StandardTags()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 顶部快捷操作栏
        top_bar = QHBoxLayout()
        self.lbl_filename = QLabel("未载入文件")
        self.lbl_filename.setStyleSheet("font-weight: bold; color: #1e293b;")
        top_bar.addWidget(self.lbl_filename)

        top_bar.addStretch()

        # 快捷工具按钮
        self.btn_smart_guess = QPushButton("从文件名推导")
        self.btn_smart_guess.setObjectName("secondaryBtn")
        self.btn_smart_guess.setToolTip("从文件名智能解析 '歌手 - 歌名' 等格式")
        self.btn_smart_guess.clicked.connect(self._on_smart_guess)
        top_bar.addWidget(self.btn_smart_guess)

        self.btn_import_ref = QPushButton("从参考音频导入")
        self.btn_import_ref.setObjectName("secondaryBtn")
        self.btn_import_ref.setToolTip("选择另一个已含有正确元数据的音频，直接拷贝其标签与封面")
        self.btn_import_ref.clicked.connect(self._on_import_from_audio)
        top_bar.addWidget(self.btn_import_ref)

        layout.addLayout(top_bar)

        # 常规标签分组
        form_group = QGroupBox("标准元数据")
        form_layout = QFormLayout(form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setSpacing(8)

        self.edit_title = QLineEdit()
        self.edit_artist = QLineEdit()
        self.edit_album = QLineEdit()
        self.edit_album_artist = QLineEdit()

        # 音轨组合: 当前音轨 / 总音轨
        track_layout = QHBoxLayout()
        self.edit_track_num = QLineEdit()
        self.edit_track_num.setPlaceholderText("序号 (如 1)")
        self.edit_track_total = QLineEdit()
        self.edit_track_total.setPlaceholderText("总数 (如 12)")
        track_layout.addWidget(self.edit_track_num)
        track_layout.addWidget(QLabel("/"))
        track_layout.addWidget(self.edit_track_total)

        # 碟片组合: 当前碟 / 总碟数
        disc_layout = QHBoxLayout()
        self.edit_disc_num = QLineEdit()
        self.edit_disc_num.setPlaceholderText("序号 (如 1)")
        self.edit_disc_total = QLineEdit()
        self.edit_disc_total.setPlaceholderText("总数 (如 2)")
        disc_layout.addWidget(self.edit_disc_num)
        disc_layout.addWidget(QLabel("/"))
        disc_layout.addWidget(self.edit_disc_total)

        self.edit_date = QLineEdit()
        self.edit_date.setPlaceholderText("如 2024 或 2024-05-01")

        self.edit_genre = QLineEdit()
        self.edit_genre.setPlaceholderText("如 Pop, Electronic, Anime")

        self.edit_comment = QLineEdit()

        form_layout.addRow("歌曲标题:", self.edit_title)
        form_layout.addRow("艺术家:", self.edit_artist)
        form_layout.addRow("专辑名称:", self.edit_album)
        form_layout.addRow("专辑艺术家:", self.edit_album_artist)
        form_layout.addRow("音轨编号:", track_layout)
        form_layout.addRow("碟片编号:", disc_layout)
        form_layout.addRow("发行年份:", self.edit_date)
        form_layout.addRow("流派分类:", self.edit_genre)
        form_layout.addRow("备注信息:", self.edit_comment)

        layout.addWidget(form_group)

        # 内嵌歌词分组
        lyrics_group = QGroupBox("内嵌歌词 (LRC / 纯文本)")
        lyrics_layout = QVBoxLayout(lyrics_group)

        lyrics_btn_layout = QHBoxLayout()
        lyrics_btn_layout.addStretch()
        self.btn_import_lrc = QPushButton("📜 导入歌词文件 (.lrc/.txt)")
        self.btn_import_lrc.setObjectName("secondaryBtn")
        self.btn_import_lrc.clicked.connect(self._on_import_lrc)
        lyrics_btn_layout.addWidget(self.btn_import_lrc)
        lyrics_layout.addLayout(lyrics_btn_layout)

        self.edit_lyrics = QTextEdit()
        self.edit_lyrics.setPlaceholderText("支持粘贴 LRC 带有时间戳的歌词或纯文本歌词...")
        self.edit_lyrics.setMaximumHeight(130)
        lyrics_layout.addWidget(self.edit_lyrics)
        layout.addWidget(lyrics_group)

        # 底部保存按钮组
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_save = QPushButton("💾 保存修改 (Ctrl+S)")
        self.btn_save.setObjectName("successBtn")
        self.btn_save.clicked.connect(self._on_save)

        self.btn_reset = QPushButton("↺ 还原未保存")
        self.btn_reset.setObjectName("secondaryBtn")
        self.btn_reset.clicked.connect(self._on_reset)

        self.btn_clear = QPushButton("清空表单")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.clicked.connect(self._on_clear_form)

        bottom_bar.addWidget(self.btn_save)
        bottom_bar.addWidget(self.btn_reset)
        bottom_bar.addWidget(self.btn_clear)

        layout.addLayout(bottom_bar)

    def set_data(self, filename: str, tags: StandardTags):
        """设置界面当前展示的标签"""
        self.current_filename = filename
        self.original_tags = tags
        self.lbl_filename.setText(f"当前文件: {filename}")

        self.edit_title.setText(tags.title)
        self.edit_artist.setText(tags.artist)
        self.edit_album.setText(tags.album)
        self.edit_album_artist.setText(tags.album_artist)
        self.edit_track_num.setText(tags.track_number)
        self.edit_track_total.setText(tags.track_total)
        self.edit_disc_num.setText(tags.disc_number)
        self.edit_disc_total.setText(tags.disc_total)
        self.edit_date.setText(tags.date)
        self.edit_genre.setText(tags.genre)
        self.edit_comment.setText(tags.comment)
        self.edit_lyrics.setPlainText(tags.lyrics)

    def get_current_tags(self) -> StandardTags:
        """从界面输入框收集当前填写的标签"""
        return StandardTags(
            title=self.edit_title.text().strip(),
            artist=self.edit_artist.text().strip(),
            album=self.edit_album.text().strip(),
            album_artist=self.edit_album_artist.text().strip(),
            track_number=self.edit_track_num.text().strip(),
            track_total=self.edit_track_total.text().strip(),
            disc_number=self.edit_disc_num.text().strip(),
            disc_total=self.edit_disc_total.text().strip(),
            date=self.edit_date.text().strip(),
            genre=self.edit_genre.text().strip(),
            comment=self.edit_comment.text().strip(),
            lyrics=self.edit_lyrics.toPlainText().strip(),
        )

    def _on_save(self):
        tags = self.get_current_tags()
        self.save_requested.emit(tags)

    def _on_reset(self):
        self.set_data(self.current_filename, self.original_tags)
        self.reset_requested.emit()

    def _on_clear_form(self):
        reply = QMessageBox.question(
            self,
            "清空确认",
            "确定要清空当前所有标准标签输入框吗？（点击保存后才会真正写入文件）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            empty = StandardTags()
            self.set_data(self.current_filename, empty)

    def _on_smart_guess(self):
        """智能从文件名解析音轨、歌手、歌名"""
        if not self.current_filename:
            QMessageBox.information(self, "提示", "请先从左侧列表选择一个音频文件！")
            return

        base = os.path.splitext(self.current_filename)[0].strip()
        track_num = ""

        # 匹配前缀音轨序号，例如: "01. ", "01 - ", "[01] "
        m = re.match(r"^(?:\[?(\d{1,3})\]?[\s._\-]+)(.+)$", base)
        if m:
            track_num = m.group(1).lstrip("0") or "0"
            base = m.group(2).strip()

        # 按常见分隔符切分（优先有空格的 ' - ', ' – ', ' — ', ' － '）
        artist, title = "", base
        for delim in [" - ", " – ", " — ", " － ", " _ ", "-", "_"]:
            if delim in base:
                parts = base.split(delim, 1)
                a = parts[0].strip()
                t = parts[1].strip()
                if a and t:
                    artist, title = a, t
                    break

        if track_num:
            self.edit_track_num.setText(track_num)
        if artist:
            self.edit_artist.setText(artist)
        if title:
            self.edit_title.setText(title)

        QMessageBox.information(
            self,
            "解析结果",
            f"已从文件名推导：\n"
            f"• 艺术家: {artist or '(未提取)'}\n"
            f"• 标题: {title}\n"
            f"• 音轨: {track_num or '(无)'}\n\n"
            f"确认无误后请点击下方【💾 保存修改 (Ctrl+S)】写入文件。",
        )

    def _on_import_from_audio(self):
        """从参考音频文件导入标签与封面"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择已具备完整元数据的参考音频",
            "",
            "音频文件 (*.flac *.mp3);;所有文件 (*.*)",
        )
        if not file_path:
            return

        try:
            handler = load_audio(file_path)
            ref_tags = handler.get_standard_tags()
            ref_cover = handler.get_cover()

            # 将标签填入表单
            if ref_tags.title:
                self.edit_title.setText(ref_tags.title)
            if ref_tags.artist:
                self.edit_artist.setText(ref_tags.artist)
            if ref_tags.album:
                self.edit_album.setText(ref_tags.album)
            if ref_tags.album_artist:
                self.edit_album_artist.setText(ref_tags.album_artist)
            if ref_tags.track_number:
                self.edit_track_num.setText(ref_tags.track_number)
            if ref_tags.track_total:
                self.edit_track_total.setText(ref_tags.track_total)
            if ref_tags.disc_number:
                self.edit_disc_num.setText(ref_tags.disc_number)
            if ref_tags.disc_total:
                self.edit_disc_total.setText(ref_tags.disc_total)
            if ref_tags.date:
                self.edit_date.setText(ref_tags.date)
            if ref_tags.genre:
                self.edit_genre.setText(ref_tags.genre)
            if ref_tags.comment:
                self.edit_comment.setText(ref_tags.comment)
            if ref_tags.lyrics:
                self.edit_lyrics.setPlainText(ref_tags.lyrics)

            # 触发给主窗口同步封面
            self.reference_imported.emit(ref_tags, ref_cover)

            cover_info = (
                f"包含封面 ({ref_cover.width}×{ref_cover.height})"
                if ref_cover
                else "无封面"
            )
            QMessageBox.information(
                self,
                "导入成功",
                f"已从参考音频导入元数据！\n"
                f"来源: {os.path.basename(file_path)}\n"
                f"封面: {cover_info}\n\n"
                f"确认后请点击【💾 保存修改】写入目标文件。",
            )
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"无法读取参考音频元数据:\n{str(e)}")

    def _on_import_lrc(self):
        """导入外部歌词文本"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择歌词文件", "", "歌词文件 (*.lrc *.txt);;所有文件 (*.*)"
        )
        if not file_path:
            return

        content = ""
        for encoding in ["utf-8", "gbk", "utf-16"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except Exception:
                continue

        if content:
            self.edit_lyrics.setPlainText(content)
            QMessageBox.information(self, "歌词导入成功", f"已成功载入歌词文件:\n{file_path}")
        else:
            QMessageBox.critical(self, "读取歌词失败", "无法解析该歌词文件（编码可能不支持）。")
