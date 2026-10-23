import os
import io
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from PIL import Image

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3,
    TIT2,
    TPE1,
    TALB,
    TPE2,
    TRCK,
    TPOS,
    TDRC,
    TYER,
    TCON,
    USLT,
    COMM,
    APIC,
    ID3NoHeaderError,
)

from .models import StandardTags, AnomalyItem, CoverData, AudioStreamInfo
from .detector import AnomalyDetector, STANDARD_VORBIS_KEYS


class BaseAudioHandler(ABC):
    """音频元数据处理器基类"""

    def __init__(self, file_path: str):
        self.file_path = os.path.abspath(file_path)
        self.file_name = os.path.basename(file_path)
        self._load()

    @abstractmethod
    def _load(self):
        """载入音频文件"""
        pass

    @abstractmethod
    def get_stream_info(self) -> AudioStreamInfo:
        """获取基础流媒体信息"""
        pass

    @abstractmethod
    def get_standard_tags(self) -> StandardTags:
        """获取标准元数据"""
        pass

    @abstractmethod
    def get_anomalies(self) -> List[AnomalyItem]:
        """获取检测到的异常与冗余标签"""
        pass

    @abstractmethod
    def save_standard_tags(self, tags: StandardTags):
        """保存标准元数据"""
        pass

    @abstractmethod
    def clean_anomalies(self, keys: Optional[List[str]] = None):
        """清除指定或全部异常冗余标签"""
        pass

    @abstractmethod
    def get_cover(self) -> Optional[CoverData]:
        """提取专辑封面"""
        pass

    @abstractmethod
    def set_cover(self, image_bytes: bytes, mime_type: Optional[str] = None):
        """写入/替换封面"""
        pass

    @abstractmethod
    def remove_cover(self):
        """删除封面"""
        pass


class FlacHandler(BaseAudioHandler):
    """FLAC 文件处理器"""

    def _load(self):
        self.audio = FLAC(self.file_path)

    def get_stream_info(self) -> AudioStreamInfo:
        info = self.audio.info
        size_bytes = os.path.getsize(self.file_path)
        bitrate = int(info.bitrate // 1000) if getattr(info, "bitrate", 0) else 0
        if bitrate == 0 and info.length > 0:
            bitrate = int((size_bytes * 8) / (info.length * 1000))

        return AudioStreamInfo(
            file_path=self.file_path,
            file_name=self.file_name,
            format="FLAC",
            duration_seconds=getattr(info, "length", 0.0),
            bitrate_kbps=bitrate,
            sample_rate_hz=getattr(info, "sample_rate", 0),
            channels=getattr(info, "channels", 2),
            file_size_bytes=size_bytes,
        )

    def _get_first(self, *keys) -> str:
        if not self.audio.tags:
            return ""
        for k in keys:
            vals = self.audio.tags.get(k)
            if vals:
                return str(vals[0]).strip()
        return ""

    def get_standard_tags(self) -> StandardTags:
        return StandardTags(
            title=self._get_first("title", "TITLE"),
            artist=self._get_first("artist", "ARTIST"),
            album=self._get_first("album", "ALBUM"),
            album_artist=self._get_first("albumartist", "ALBUMARTIST"),
            track_number=self._get_first("tracknumber", "TRACKNUMBER"),
            track_total=self._get_first("tracktotal", "TRACKTOTAL", "totaltracks", "TOTALTRACKS"),
            disc_number=self._get_first("discnumber", "DISCNUMBER"),
            disc_total=self._get_first("disctotal", "DISCTOTAL", "totaldiscs", "TOTALDISCS"),
            date=self._get_first("date", "DATE", "year", "YEAR"),
            genre=self._get_first("genre", "GENRE"),
            lyrics=self._get_first("lyrics", "LYRICS", "unsyncedlyrics"),
            comment=self._get_first("comment", "COMMENT"),
        )

    def get_anomalies(self) -> List[AnomalyItem]:
        anomalies = []
        if not self.audio.tags:
            return anomalies

        for raw_k, vals in self.audio.tags.items():
            item = AnomalyDetector.inspect_vorbis_tag(raw_k, vals)
            if item:
                anomalies.append(item)
        return anomalies

    def save_standard_tags(self, tags: StandardTags):
        if self.audio.tags is None:
            self.audio.add_tags()

        # 辅助写入函数：若为空字符串则删除该标签，避免产生空标签
        def update_tag(primary_key: str, value: str, alias_keys: List[str] = None):
            val_clean = value.strip()
            # 清理别名键，统一使用小写标准键
            if alias_keys:
                for ak in alias_keys:
                    if ak in self.audio.tags:
                        del self.audio.tags[ak]

            if val_clean:
                self.audio.tags[primary_key] = [val_clean]
            else:
                if primary_key in self.audio.tags:
                    del self.audio.tags[primary_key]

        update_tag("title", tags.title)
        update_tag("artist", tags.artist)
        update_tag("album", tags.album)
        update_tag("albumartist", tags.album_artist)
        update_tag("tracknumber", tags.track_number)
        update_tag("tracktotal", tags.track_total, ["totaltracks"])
        update_tag("discnumber", tags.disc_number)
        update_tag("disctotal", tags.disc_total, ["totaldiscs"])
        update_tag("date", tags.date, ["year"])
        update_tag("genre", tags.genre)
        update_tag("lyrics", tags.lyrics, ["unsyncedlyrics"])
        update_tag("comment", tags.comment)

        self.audio.save()

    def clean_anomalies(self, keys: Optional[List[str]] = None):
        if not self.audio.tags:
            return

        if keys is None:
            # 清理全部检测出的异常项
            detected = self.get_anomalies()
            keys_to_remove = [item.raw_key for item in detected]
        else:
            keys_to_remove = keys

        for k in keys_to_remove:
            if k in self.audio.tags:
                del self.audio.tags[k]

        self.audio.save()

    def get_cover(self) -> Optional[CoverData]:
        if not self.audio.pictures:
            return None

        # 优先寻找封面 (type == 3: Front Cover)
        front_pics = [p for p in self.audio.pictures if p.type == 3]
        pic = front_pics[0] if front_pics else self.audio.pictures[0]

        w, h = pic.width, pic.height
        if (w == 0 or h == 0) and pic.data:
            try:
                with Image.open(io.BytesIO(pic.data)) as img:
                    w, h = img.size
            except Exception:
                pass

        return CoverData(
            data=pic.data,
            mime_type=pic.mime or "image/jpeg",
            width=w,
            height=h,
            size_bytes=len(pic.data),
            pic_type=pic.type,
        )

    def set_cover(self, image_bytes: bytes, mime_type: Optional[str] = None):
        w, h = 0, 0
        real_mime = mime_type
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                w, h = img.size
                if not real_mime:
                    fmt = (img.format or "").upper()
                    real_mime = "image/png" if fmt == "PNG" else "image/jpeg"
        except Exception:
            if not real_mime:
                real_mime = "image/jpeg"

        pic = Picture()
        pic.data = image_bytes
        pic.type = 3  # Cover (front)
        pic.mime = real_mime
        pic.desc = "Cover (front)"
        pic.width = w
        pic.height = h

        # 清除旧的封面，写入新封面
        self.audio.clear_pictures()
        self.audio.add_picture(pic)
        self.audio.save()

    def remove_cover(self):
        self.audio.clear_pictures()
        self.audio.save()


class Mp3Handler(BaseAudioHandler):
    """MP3 文件处理器"""

    def _load(self):
        self.audio = MP3(self.file_path)
        if self.audio.tags is None:
            try:
                self.audio.add_tags()
            except Exception:
                pass

    def get_stream_info(self) -> AudioStreamInfo:
        info = self.audio.info
        size_bytes = os.path.getsize(self.file_path)
        bitrate = int(getattr(info, "bitrate", 0) // 1000)

        return AudioStreamInfo(
            file_path=self.file_path,
            file_name=self.file_name,
            format="MP3",
            duration_seconds=getattr(info, "length", 0.0),
            bitrate_kbps=bitrate,
            sample_rate_hz=getattr(info, "sample_rate", 0),
            channels=getattr(info, "channels", 2),
            file_size_bytes=size_bytes,
        )

    def _get_text_frame(self, frame_id: str) -> str:
        if not self.audio.tags:
            return ""
        frame = self.audio.tags.get(frame_id)
        if frame and hasattr(frame, "text") and frame.text:
            return str(frame.text[0]).strip()
        return ""

    def get_standard_tags(self) -> StandardTags:
        tags = StandardTags()
        if not self.audio.tags:
            return tags

        tags.title = self._get_text_frame("TIT2")
        tags.artist = self._get_text_frame("TPE1")
        tags.album = self._get_text_frame("TALB")
        tags.album_artist = self._get_text_frame("TPE2")

        # 音轨号可能格式为 "1/12"
        trck = self._get_text_frame("TRCK")
        if "/" in trck:
            parts = trck.split("/", 1)
            tags.track_number = parts[0].strip()
            tags.track_total = parts[1].strip()
        else:
            tags.track_number = trck

        # 碟片号可能格式为 "1/2"
        tpos = self._get_text_frame("TPOS")
        if "/" in tpos:
            parts = tpos.split("/", 1)
            tags.disc_number = parts[0].strip()
            tags.disc_total = parts[1].strip()
        else:
            tags.disc_number = tpos

        # 年份: 优先 TDRC (ID3v2.4)，其次 TYER (ID3v2.3)
        tags.date = self._get_text_frame("TDRC") or self._get_text_frame("TYER")
        tags.genre = self._get_text_frame("TCON")

        # 歌词 USLT
        for key in self.audio.tags.keys():
            if key.startswith("USLT"):
                uslt = self.audio.tags[key]
                tags.lyrics = getattr(uslt, "text", "").strip()
                break

        # 备注 COMM
        for key in self.audio.tags.keys():
            if key.startswith("COMM"):
                comm = self.audio.tags[key]
                tags.comment = str(getattr(comm, "text", [""])[0] if getattr(comm, "text", None) else "").strip()
                break

        return tags

    def get_anomalies(self) -> List[AnomalyItem]:
        anomalies = []
        if not self.audio.tags:
            return anomalies

        for frame_id, frame_obj in self.audio.tags.items():
            # 略过标准封面和常规文本帧
            if frame_id.startswith("APIC") or frame_id in (
                "TIT2", "TPE1", "TALB", "TPE2", "TRCK", "TPOS",
                "TDRC", "TYER", "TCON", "TCOM", "TCOP"
            ):
                continue
            item = AnomalyDetector.inspect_id3_frame(frame_id, frame_obj)
            if item:
                anomalies.append(item)
        return anomalies

    def save_standard_tags(self, tags: StandardTags):
        if self.audio.tags is None:
            self.audio.add_tags()

        def set_text(frame_cls, value: str):
            fid = frame_cls.__name__
            val = value.strip()
            if val:
                self.audio.tags.setall(fid, [frame_cls(encoding=3, text=[val])])
            else:
                self.audio.tags.delall(fid)

        set_text(TIT2, tags.title)
        set_text(TPE1, tags.artist)
        set_text(TALB, tags.album)
        set_text(TPE2, tags.album_artist)

        # 组装 TRCK
        trck_val = tags.track_number.strip()
        if tags.track_total.strip():
            trck_val = f"{trck_val}/{tags.track_total.strip()}" if trck_val else f"0/{tags.track_total.strip()}"
        set_text(TRCK, trck_val)

        # 组装 TPOS
        tpos_val = tags.disc_number.strip()
        if tags.disc_total.strip():
            tpos_val = f"{tpos_val}/{tags.disc_total.strip()}" if tpos_val else f"0/{tags.disc_total.strip()}"
        set_text(TPOS, tpos_val)

        # 写入 TDRC / TYER
        date_val = tags.date.strip()
        if date_val:
            self.audio.tags.setall("TDRC", [TDRC(encoding=3, text=[date_val])])
        else:
            self.audio.tags.delall("TDRC")
            self.audio.tags.delall("TYER")

        set_text(TCON, tags.genre)

        # 写入 USLT 歌词
        lyrics_val = tags.lyrics.strip()
        # 清除旧歌词
        for k in list(self.audio.tags.keys()):
            if k.startswith("USLT"):
                del self.audio.tags[k]
        if lyrics_val:
            self.audio.tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics_val))

        # 写入 COMM
        comm_val = tags.comment.strip()
        for k in list(self.audio.tags.keys()):
            if k.startswith("COMM"):
                del self.audio.tags[k]
        if comm_val:
            self.audio.tags.add(COMM(encoding=3, lang="eng", desc="", text=[comm_val]))

        self.audio.save()

    def clean_anomalies(self, keys: Optional[List[str]] = None):
        if not self.audio.tags:
            return

        if keys is None:
            detected = self.get_anomalies()
            keys_to_remove = [item.raw_key for item in detected]
        else:
            keys_to_remove = keys

        for k in keys_to_remove:
            if k in self.audio.tags:
                del self.audio.tags[k]

        self.audio.save()

    def get_cover(self) -> Optional[CoverData]:
        if not self.audio.tags:
            return None

        apic_frames = [f for k, f in self.audio.tags.items() if k.startswith("APIC")]
        if not apic_frames:
            return None

        front_pics = [f for f in apic_frames if getattr(f, "type", None) == 3]
        pic = front_pics[0] if front_pics else apic_frames[0]

        w, h = 0, 0
        if pic.data:
            try:
                with Image.open(io.BytesIO(pic.data)) as img:
                    w, h = img.size
            except Exception:
                pass

        return CoverData(
            data=pic.data,
            mime_type=getattr(pic, "mime", "image/jpeg") or "image/jpeg",
            width=w,
            height=h,
            size_bytes=len(pic.data),
            pic_type=getattr(pic, "type", 3),
        )

    def set_cover(self, image_bytes: bytes, mime_type: Optional[str] = None):
        if self.audio.tags is None:
            self.audio.add_tags()

        real_mime = mime_type
        if not real_mime:
            try:
                with Image.open(io.BytesIO(image_bytes)) as img:
                    fmt = (img.format or "").upper()
                    real_mime = "image/png" if fmt == "PNG" else "image/jpeg"
            except Exception:
                real_mime = "image/jpeg"

        # 清除所有旧 APIC
        for k in list(self.audio.tags.keys()):
            if k.startswith("APIC"):
                del self.audio.tags[k]

        apic = APIC(
            encoding=3,
            mime=real_mime,
            type=3,  # Cover front
            desc="Cover",
            data=image_bytes,
        )
        self.audio.tags.add(apic)
        self.audio.save()

    def remove_cover(self):
        if not self.audio.tags:
            return
        for k in list(self.audio.tags.keys()):
            if k.startswith("APIC"):
                del self.audio.tags[k]
        self.audio.save()


def load_audio(file_path: str) -> BaseAudioHandler:
    """加载音频文件适配器工厂函数"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".flac":
        return FlacHandler(file_path)
    elif ext == ".mp3":
        return Mp3Handler(file_path)
    else:
        raise ValueError(f"暂不支持的音频格式: {ext} (目前仅支持 .flac 与 .mp3)")
