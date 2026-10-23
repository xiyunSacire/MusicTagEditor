from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class StandardTags:
    """标准音乐标签模型"""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    track_number: str = ""
    track_total: str = ""
    disc_number: str = ""
    disc_total: str = ""
    date: str = ""
    genre: str = ""
    lyrics: str = ""
    comment: str = ""


@dataclass
class AnomalyItem:
    """异常/冗余标签项"""
    raw_key: str
    display_name: str
    value: str
    category: str  # 容器残留, 编码器签名, 空标签, 非标字段
    reason: str
    removable: bool = True


@dataclass
class CoverData:
    """专辑封面信息"""
    data: bytes
    mime_type: str = "image/jpeg"
    width: int = 0
    height: int = 0
    size_bytes: int = 0
    pic_type: int = 3  # 3 = Front Cover (Cover art)


@dataclass
class AudioStreamInfo:
    """音频文件基础流媒体属性"""
    file_path: str
    file_name: str
    format: str  # 'FLAC' | 'MP3'
    duration_seconds: float = 0.0
    bitrate_kbps: int = 0
    sample_rate_hz: int = 0
    channels: int = 2
    file_size_bytes: int = 0

    @property
    def duration_formatted(self) -> str:
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def file_size_formatted(self) -> str:
        mb = self.file_size_bytes / (1024 * 1024)
        return f"{mb:.2f} MB"
