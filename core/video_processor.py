"""视频处理 - 获取视频元信息"""

import json
import subprocess
from pathlib import Path
from typing import Optional


class VideoInfo:
    """视频元信息"""

    def __init__(self, path: Path):
        self.path = path
        self.duration: float = 0.0
        self.width: int = 0
        self.height: int = 0
        self.fps: float = 0.0
        self.codec: str = ""
        self.audio_codec: str = ""
        self._load()

    def _load(self):
        """使用 ffprobe 读取视频元信息"""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(self.path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"无法读取视频信息: {e}")

        # 格式信息
        fmt = data.get("format", {})
        self.duration = float(fmt.get("duration", 0))

        # 流信息
        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type")
            if codec_type == "video":
                self.width = stream.get("width", 0)
                self.height = stream.get("height", 0)
                self.codec = stream.get("codec_name", "")
                # FPS 计算
                avg_frame_rate = stream.get("avg_frame_rate", "0/1")
                if "/" in avg_frame_rate:
                    num, den = avg_frame_rate.split("/")
                    self.fps = float(num) / float(den) if float(den) > 0 else 0
            elif codec_type == "audio":
                self.audio_codec = stream.get("codec_name", "")

    def __repr__(self) -> str:
        return (
            f"VideoInfo({self.path.name})\n"
            f"  时长: {self.duration:.1f}s\n"
            f"  分辨率: {self.width}x{self.height}\n"
            f"  FPS: {self.fps:.2f}\n"
            f"  视频编码: {self.codec}\n"
            f"  音频编码: {self.audio_codec}"
        )
