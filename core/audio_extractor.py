"""音频提取 - 从视频中提取音频"""

import subprocess
from pathlib import Path

from config import Config


class AudioExtractor:
    """从视频文件中提取音频（WAV 格式, 16kHz 单声道）"""

    @staticmethod
    def extract(video_path: Path, output_path: Path) -> Path:
        """
        提取音频并保存为 WAV 文件

        Args:
            video_path:  输入视频路径
            output_path: 输出 WAV 路径

        Returns:
            输出 WAV 文件路径

        Raises:
            RuntimeError: FFmpeg 执行失败
        """
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",                        # 不处理视频
            "-acodec", "pcm_s16le",       # PCM 16-bit 编码
            "-ar", str(Config.SAMPLE_RATE),  # 采样率 16kHz
            "-ac", "1",                   # 单声道
            str(output_path),
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() or str(e)
            raise RuntimeError(f"音频提取失败: {error_msg}")

        if not output_path.exists():
            raise RuntimeError("音频提取失败: 输出文件未生成")

        return output_path

    @staticmethod
    def get_audio_duration(audio_path: Path) -> float:
        """获取音频文件时长（秒）"""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
