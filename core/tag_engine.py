import os
import io
import sys
import stat
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from PIL import Image

import mutagen
from mutagen.flac import FLAC, Picture, FLACNoHeaderError
from mutagen.mp3 import MP3, HeaderNotFoundError
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

    def _save_audio(self):
        """安全保存音频文件，自动处理只读属性，并在被锁定时精准定位占用进程"""
        # 1. 尝试自动解除文件的只读属性
        try:
            import stat
            if os.path.exists(self.file_path):
                mode = os.stat(self.file_path).st_mode
                if not (mode & stat.S_IWRITE):
                    os.chmod(self.file_path, stat.S_IWRITE)
        except Exception:
            pass

        try:
            self.audio.save()
        except Exception as e:
            # 判断是否为权限不足 / 文件被占用锁定的错误（全面兼容 mutagen 包装后的各类异常）
            is_perm = False
            if isinstance(e, (PermissionError, OSError)) and getattr(e, "errno", None) == 13:
                is_perm = True
            elif "Permission denied" in str(e) or "Errno 13" in str(e):
                is_perm = True

            if is_perm:
                # 再次尝试通过 chmod 修复只读并重试一次保存
                try:
                    import stat
                    os.chmod(self.file_path, stat.S_IWRITE)
                    self.audio.save()
                    return
                except Exception:
                    pass

                # 精准诊断：是否被外部进程（音乐播放器、系统预览等）独占占用
                locking_procs = get_processes_locking_file(self.file_path)
                if locking_procs:
                    proc_str = "、".join(locking_procs)
                    raise PermissionError(
                        f"无法保存文件，该音频正被其他软件占用锁定！\n\n"
                        f"【正在占用的程序】: {proc_str}\n"
                        f"【文件路径】: {self.file_path}\n\n"
                        f"【解决方法】请在【{proc_str}】中暂停播放或关闭该文件，然后再进行清洗或保存。"
                    ) from e
                else:
                    raise PermissionError(
                        f"无法保存文件，操作被系统拒绝（文件被占用或无写入权限）。\n\n"
                        f"【文件路径】: {self.file_path}\n\n"
                        f"【排查建议】\n"
                        f"1. 请检查该音乐是否正在其他播放器（如网易云、QQ音乐、Foobar2000、PotPlayer等）中播放，若正在播放请先暂停；\n"
                        f"2. 请检查该文件所在目录的修改权限；\n"
                        f"3. 右键该文件查看“属性”，确认未勾选“只读”。"
                    ) from e
            raise


def get_processes_locking_file(filepath: str) -> List[str]:
    """使用 Windows 原生 Restart Manager API 探测锁定指定文件的进程名称"""
    if sys.platform != "win32" or not os.path.exists(filepath):
        return []
    try:
        import ctypes
        from ctypes import wintypes

        class FILETIME(ctypes.Structure):
            _fields_ = [
                ("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD),
            ]

        class RM_UNIQUE_PROCESS(ctypes.Structure):
            _fields_ = [
                ("dwProcessId", wintypes.DWORD),
                ("ProcessStartTime", FILETIME),
            ]

        class RM_PROCESS_INFO(ctypes.Structure):
            _fields_ = [
                ("Process", RM_UNIQUE_PROCESS),
                ("strAppName", wintypes.WCHAR * 256),
                ("strServiceShortName", wintypes.WCHAR * 64),
                ("ApplicationType", wintypes.DWORD),
                ("AppStatus", wintypes.DWORD),
                ("TSSessionId", wintypes.DWORD),
                ("bRestartable", wintypes.BOOL),
            ]

        rstrtmgr = ctypes.windll.rstrtmgr
        session = wintypes.DWORD()
        key = (wintypes.WCHAR * 65)()
        res = rstrtmgr.RmStartSession(ctypes.byref(session), 0, key)
        if res != 0:
            return []
        try:
            abs_path = os.path.abspath(filepath)
            path_arr = (wintypes.LPCWSTR * 1)(abs_path)
            res = rstrtmgr.RmRegisterResources(session, 1, path_arr, 0, None, 0, None)
            if res != 0:
                return []
            n_proc_info_needed = wintypes.UINT(0)
            n_proc_info = wintypes.UINT(0)
            res = rstrtmgr.RmGetList(
                session,
                ctypes.byref(n_proc_info_needed),
                ctypes.byref(n_proc_info),
                None,
                ctypes.byref(wintypes.DWORD()),
            )
            if res == 234:  # ERROR_MORE_DATA
                n_proc_info = n_proc_info_needed
                proc_info_arr = (RM_PROCESS_INFO * n_proc_info.value)()
                res = rstrtmgr.RmGetList(
                    session,
                    ctypes.byref(n_proc_info_needed),
                    ctypes.byref(n_proc_info),
                    proc_info_arr,
                    ctypes.byref(wintypes.DWORD()),
                )
                if res == 0:
                    names = []
                    for p in proc_info_arr:
                        app_name = p.strAppName.strip()
                        if app_name:
                            names.append(app_name)
                    return list(dict.fromkeys(names))
        finally:
            rstrtmgr.RmEndSession(session)
    except Exception:
        pass
    return []


def detect_audio_format(file_path: str) -> str:
    """根据文件二进制头部特征探测其实际文件格式或特征"""
    if not os.path.exists(file_path):
        return "文件不存在"
    try:
        size = os.path.getsize(file_path)
        if size == 0:
            return "空文件 (0 字节)"
        with open(file_path, "rb") as f:
            header = f.read(64)
    except Exception as e:
        return f"无法读取文件 ({e})"

    if len(header) < 4:
        return "数据过短 (无效文件)"

    # 1. 常见加密音乐格式
    if header.startswith(b"CTENFDAM"):
        return "网易云加密音乐 (NCM 格式)"
    if len(header) >= 4 and header[:4] in (b"\x7c\xd5\x19\xbb", b"\x7b\xd5\x19\xbb"):
        return "酷狗加密音乐 (KGM/VPR 格式)"
    if header.startswith(b"yeelion") or header.startswith(b"kwm"):
        return "酷我加密音乐 (KWM 格式)"
    if header.startswith(b"qmc") or header.startswith(b"QMC"):
        return "QQ音乐加密格式 (QMC 格式)"

    # 2. 常见无损/有损格式
    if header.startswith(b"fLaC"):
        return "FLAC 无损音频"
    if len(header) >= 8 and header[4:8] == b"ftyp":
        brand = header[8:12].decode("latin1", errors="ignore").strip()
        brand_desc = f", brand: {brand}" if brand else ""
        return f"M4A / MP4 容器 (AAC/ALAC 音频{brand_desc})"
    if header.startswith(b"ID3"):
        return "带 ID3v2 标签的音频 (通常为 MP3)"
    if header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
        return "MP3 音频 (MPEG Frame)"
    if header.startswith(b"OggS"):
        return "OGG / Opus / Vorbis 音频"
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WAVE":
        return "WAV 无损音频"
    if header.startswith(b"MAC "):
        return "APE 无损音频"
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return "WebM / MKV 音频容器"
    if header.startswith(b"DSD ") or header.startswith(b"FRM8"):
        return "DSD / DSF 音频"

    return "未知或非标准音频格式"


class FlacHandler(BaseAudioHandler):
    """FLAC 文件处理器"""

    def _load(self):
        try:
            self.audio = FLAC(self.file_path)
        except FLACNoHeaderError as e:
            detected = detect_audio_format(self.file_path)
            if "M4A" in detected or "MP4" in detected:
                raise ValueError(
                    f"文件虽然使用了 .flac 后缀，但实际是【{detected}】。\n"
                    f"【原因】该文件可能是从网页/视频网站导出的 AAC/M4A 音频被直接重命名为了 .flac。\n"
                    f"【建议】请将其后缀名改回 .m4a，或使用转码工具转换为标准 FLAC 无损音频。"
                ) from e
            elif "加密" in detected:
                raise ValueError(
                    f"文件并非标准 FLAC，检测到特征为【{detected}】。\n"
                    f"【原因】这是受版权保护的加密音乐文件，无法直接编辑元数据。\n"
                    f"【建议】请先使用相应的解密工具转换为普通音频格式后再导入。"
                ) from e
            elif "MP3" in detected:
                raise ValueError(
                    f"文件虽然使用了 .flac 后缀，但实际是【{detected}】。\n"
                    f"【建议】请将其文件后缀名修改为 .mp3 后重试。"
                ) from e
            elif "空文件" in detected or "数据过短" in detected:
                raise ValueError(f"文件无效: {detected}") from e
            else:
                raise ValueError(
                    f"不是有效的 FLAC 音频文件（未检测到标准 fLaC 头部，识别特征: {detected}）。\n"
                    f"文件可能已损坏，或由其他不支持的格式修改后缀名而来。"
                ) from e
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"读取 FLAC 文件失败: {str(e)}") from e

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

        self._save_audio()

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

        self._save_audio()

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
        self._save_audio()

    def remove_cover(self):
        self.audio.clear_pictures()
        self._save_audio()


class Mp3Handler(BaseAudioHandler):
    """MP3 文件处理器"""

    def _load(self):
        try:
            self.audio = MP3(self.file_path)
        except (HeaderNotFoundError, mutagen.mp3.error, Exception) as e:
            detected = detect_audio_format(self.file_path)
            if "FLAC" in detected:
                raise ValueError(
                    f"文件虽然使用了 .mp3 后缀，但实际是【{detected}】。\n"
                    f"【建议】请将文件后缀名更改为 .flac 后重新导入。"
                ) from e
            elif "M4A" in detected or "MP4" in detected:
                raise ValueError(
                    f"文件虽然使用了 .mp3 后缀，但实际是【{detected}】。\n"
                    f"【原因】该文件可能是 AAC/M4A 音频被直接重命名为了 .mp3。\n"
                    f"【建议】请将其后缀名改回 .m4a，或使用转码工具转换为标准 MP3 音频。"
                ) from e
            elif "加密" in detected:
                raise ValueError(
                    f"文件并非标准 MP3，检测到特征为【{detected}】。\n"
                    f"【原因】这是受版权保护的加密音乐文件，无法直接编辑元数据。\n"
                    f"【建议】请先使用解密工具解密后再导入。"
                ) from e
            elif "空文件" in detected or "数据过短" in detected:
                raise ValueError(f"文件无效: {detected}") from e
            else:
                raise ValueError(
                    f"不是有效的 MP3 音频文件（未找到有效的 MPEG 帧头，识别特征: {detected}，原错误: {str(e)}）。\n"
                    f"文件可能已损坏，或由其他不支持的格式修改后缀名而来。"
                ) from e

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

        self._save_audio()

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

        self._save_audio()

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
        self._save_audio()

    def remove_cover(self):
        if not self.audio.tags:
            return
        for k in list(self.audio.tags.keys()):
            if k.startswith("APIC"):
                del self.audio.tags[k]
        self._save_audio()


def load_audio(file_path: str) -> BaseAudioHandler:
    """加载音频文件适配器工厂函数"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".flac":
        return FlacHandler(file_path)
    elif ext == ".mp3":
        return Mp3Handler(file_path)
    else:
        detected = detect_audio_format(file_path)
        raise ValueError(
            f"暂不支持的音频后缀: {ext} (实际格式特征: {detected})。\n"
            f"【提示】目前小工具仅支持标准 .flac 与 .mp3 音频文件。"
        )
