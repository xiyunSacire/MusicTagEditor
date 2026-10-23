import re
from typing import List, Tuple, Optional
from .models import AnomalyItem

# 标准 Vorbis 标签白名单（统一小写判断）
STANDARD_VORBIS_KEYS = {
    "title",
    "artist",
    "album",
    "albumartist",
    "tracknumber",
    "tracktotal",
    "totaltracks",
    "discnumber",
    "disctotal",
    "totaldiscs",
    "date",
    "year",
    "genre",
    "lyrics",
    "unsyncedlyrics",
    "comment",
    "description",
    "composer",
    "performer",
    "arranger",
    "copyright",
    "organization",
    "isrc",
    "bpm",
    "replaygain_track_gain",
    "replaygain_track_peak",
    "replaygain_album_gain",
    "replaygain_album_peak",
}

# 常见的容器残留关键词
CONTAINER_RESIDUE_KEYS = {
    "major_brand",
    "minor_version",
    "compatible_brands",
    "media_type",
    "hd_video",
}

# 常见的编码器/工具关键词
ENCODER_KEYS = {
    "encoder",
    "encoded_by",
    "writing_application",
    "tool",
    "tsse",
    "tenc",
}

# 广告/平台残留文本特征正则
JUNK_TEXT_PATTERNS = [
    re.compile(r"bilibili", re.IGNORECASE),
    re.compile(r"xcoder", re.IGNORECASE),
    re.compile(r"lavf[0-9.]*", re.IGNORECASE),
    re.compile(r"lavc[0-9.]*", re.IGNORECASE),
    re.compile(r"ffmpeg", re.IGNORECASE),
]


class AnomalyDetector:
    """元数据异常与冗余标签检测器"""

    @staticmethod
    def inspect_vorbis_tag(raw_key: str, raw_values: List[str]) -> Optional[AnomalyItem]:
        """检测单个 Vorbis 标签（用于 FLAC / OGG）"""
        k_lower = raw_key.lower().strip()
        val_str = " / ".join(str(v).strip() for v in raw_values if str(v).strip())

        # 1. 检测空值
        if not val_str:
            return AnomalyItem(
                raw_key=raw_key,
                display_name=raw_key,
                value="(空值)",
                category="空标签",
                reason="该标签键存在，但对应的值为空白字符",
            )

        # 2. 检测视频/音频容器转换残留（如 m4s, mp4）
        if k_lower in CONTAINER_RESIDUE_KEYS:
            return AnomalyItem(
                raw_key=raw_key,
                display_name=raw_key,
                value=val_str,
                category="容器残留",
                reason=f"来自视频或m4s容器封装的残留字段 ({raw_key})，音乐播放器不需要",
            )

        # 3. 检测编码器签名
        if k_lower in ENCODER_KEYS:
            return AnomalyItem(
                raw_key=raw_key,
                display_name=raw_key,
                value=val_str,
                category="编码器签名",
                reason=f"转码工具写入的签名字段 ({raw_key})，非歌曲本质元数据",
            )

        # 4. 检测字段内容中是否包含平台/转码工具特征（如 Bilibili XCoder）
        for pat in JUNK_TEXT_PATTERNS:
            if pat.search(val_str):
                return AnomalyItem(
                    raw_key=raw_key,
                    display_name=raw_key,
                    value=val_str,
                    category="转码/平台残留",
                    reason=f"标签内容包含转码工具或平台残留标记: '{val_str}'",
                )

        # 5. 白名单以外的非标字段
        if k_lower not in STANDARD_VORBIS_KEYS:
            return AnomalyItem(
                raw_key=raw_key,
                display_name=raw_key,
                value=val_str,
                category="非标字段",
                reason="未在标准音乐标签白名单中定义，可能为私有或废弃字段",
            )

        return None

    @staticmethod
    def inspect_id3_frame(frame_id: str, frame_obj) -> Optional[AnomalyItem]:
        """检测单个 ID3 帧（用于 MP3）"""
        frame_id_upper = frame_id.upper()

        # 提取值
        val_str = str(frame_obj).strip()
        if not val_str:
            return AnomalyItem(
                raw_key=frame_id,
                display_name=frame_id,
                value="(空值)",
                category="空标签",
                reason="该ID3帧存在，但内容为空",
            )

        # 1. 检测 TXXX (用户自定义文本帧)
        if frame_id_upper.startswith("TXXX"):
            desc = getattr(frame_obj, "desc", "").strip()
            desc_lower = desc.lower()

            if desc_lower in CONTAINER_RESIDUE_KEYS:
                return AnomalyItem(
                    raw_key=frame_id,
                    display_name=f"TXXX:{desc}" if desc else "TXXX",
                    value=val_str,
                    category="容器残留",
                    reason=f"m4s/mp4转换生成的自定义TXXX容器残留字段 ({desc})",
                )

            if desc_lower in ENCODER_KEYS:
                return AnomalyItem(
                    raw_key=frame_id,
                    display_name=f"TXXX:{desc}" if desc else "TXXX",
                    value=val_str,
                    category="编码器签名",
                    reason="转码工具写入的自定义编码器标记",
                )

            for pat in JUNK_TEXT_PATTERNS:
                if pat.search(val_str) or (desc and pat.search(desc)):
                    return AnomalyItem(
                        raw_key=frame_id,
                        display_name=f"TXXX:{desc}" if desc else "TXXX",
                        value=val_str,
                        category="转码/平台残留",
                        reason=f"自定义标签内容匹配平台/工具残留标记: '{val_str}'",
                    )

            # 普通 TXXX 标记为自定义
            return AnomalyItem(
                raw_key=frame_id,
                display_name=f"TXXX:{desc}" if desc else "TXXX",
                value=val_str,
                category="非标字段",
                reason=f"用户自定义文本帧 ({desc})，非标准ID3主字段",
            )

        # 2. 编码工具标识帧
        if frame_id_upper in ("TSSE", "TENC"):
            return AnomalyItem(
                raw_key=frame_id,
                display_name=frame_id,
                value=val_str,
                category="编码器签名",
                reason=f"ID3编码器/软件信息帧 ({frame_id_upper})，可清理",
            )

        # 3. 隐私私有帧 (PRIV)
        if frame_id_upper.startswith("PRIV"):
            owner = getattr(frame_obj, "owner", "")
            return AnomalyItem(
                raw_key=frame_id,
                display_name=f"PRIV:{owner}" if owner else "PRIV",
                value=f"<{len(getattr(frame_obj, 'data', b''))} 字节二进制数据>",
                category="私有数据块",
                reason="播放器或系统留下的私有数据帧 (PRIV)，对播放无益",
            )

        # 4. COMM 注释帧中是否包含平台广告/残留
        if frame_id_upper.startswith("COMM"):
            for pat in JUNK_TEXT_PATTERNS:
                if pat.search(val_str):
                    return AnomalyItem(
                        raw_key=frame_id,
                        display_name=frame_id,
                        value=val_str,
                        category="转码/平台残留",
                        reason="注释帧中包含转码/平台特征字符串",
                    )

        # 5. 二进制封装对象 (GEOB)
        if frame_id_upper.startswith("GEOB"):
            return AnomalyItem(
                raw_key=frame_id,
                display_name=frame_id,
                value=val_str,
                category="非标数据块",
                reason="通用封装二进制对象 (GEOB)，非音乐常规标签",
            )

        return None
