"""文件处理工具"""

import os
from pathlib import Path
from typing import Optional

from config import Config


def find_video_files(path: str) -> list[Path]:
    """查找目录下的所有视频文件"""
    p = Path(path)
    if p.is_file():
        if p.suffix.lower() in Config.SUPPORTED_VIDEO_FORMATS:
            return [p]
        raise ValueError(f"不支持的文件格式: {p.suffix}")

    videos = []
    for f in sorted(p.iterdir()):
        if f.suffix.lower() in Config.SUPPORTED_VIDEO_FORMATS:
            videos.append(f)
    return videos


def get_output_path(video_path: Path, fmt: str = "srt") -> Path:
    """生成字幕输出路径"""
    return Config.SUBTITLE_DIR / f"{video_path.stem}.{fmt}"


def get_audio_tmp_path(video_path: Path) -> Path:
    """生成临时音频文件路径"""
    return Config.AUDIO_DIR / f"{video_path.stem}.wav"


def get_output_video_path(video_path: Path) -> Path:
    """生成烧录字幕后的视频路径"""
    return Config.OUTPUT_VIDEO_DIR / f"{video_path.stem}_subtitled{video_path.suffix}"


def get_file_size(path: Path) -> str:
    """获取文件大小（人类可读）"""
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_duration(seconds: float) -> str:
    """格式化时长"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"
