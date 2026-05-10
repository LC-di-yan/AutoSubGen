"""API 语音识别 - 基于 OpenAI Whisper API（兼容任何 OpenAI 接口服务）"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI

from core.models import SubtitleResult, SubtitleSegment


class ApiRecognizer:
    """
    基于 API 的语音识别

    使用 OpenAI Whisper API 或任何兼容接口（如 API 代理、国产模型服务）。
    环境变量:
      OPENAI_API_KEY   - API 密钥（必填）
      OPENAI_BASE_URL  - 自定义接口地址（可选，默认 https://api.openai.com/v1）
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")

        if not self.api_key:
            raise ValueError(
                "未设置 API Key\n"
                "  方式: export OPENAI_API_KEY=sk-xxx  (或 set OPENAI_API_KEY=sk-xxx)"
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> SubtitleResult:
        """
        通过 API 转录音频

        Args:
            audio_path: 音频文件路径
            language:   语言代码 (None=自动检测, "zh", "en" 等)
            prompt:     提示词，帮助模型识别特定术语

        Returns:
            SubtitleResult
        """
        start = time.perf_counter()

        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        # 确保文件不超过 API 限制 (25MB)
        upload_path = self._ensure_file_size(audio_path)

        print(f"  🌐 发送到 API 进行识别...")
        try:
            with open(upload_path, "rb") as f:
                kwargs = {
                    "model": "whisper-1",
                    "file": f,
                    "response_format": "verbose_json",
                }
                if language:
                    kwargs["language"] = language
                if prompt:
                    kwargs["prompt"] = prompt

                response = self.client.audio.transcriptions.create(**kwargs)
        finally:
            # 清理压缩后的临时文件
            if upload_path != audio_path and upload_path.exists():
                upload_path.unlink()

        elapsed = time.perf_counter() - start

        # 解析结果
        segments = []
        for seg in response.segments:
            text = seg.text.strip()
            if text:
                segments.append(SubtitleSegment(
                    index=seg.id + 1,
                    start_time=seg.start,
                    end_time=seg.end,
                    text=text,
                ))

        detected_lang = language or response.language or ""
        audio_duration = segments[-1].end_time if segments else 0
        speed_ratio = audio_duration / elapsed if elapsed > 0 else 0

        print(f"  ✅ 识别完成 | 语言: {detected_lang} | "
              f"耗时: {elapsed:.1f}s | "
              f"实时率: {speed_ratio:.1f}x | "
              f"字幕条数: {len(segments)}")

        return SubtitleResult(
            video_path=audio_path,
            segments=segments,
            language=detected_lang,
            duration=audio_duration,
            model_used="whisper-1 (API)",
            processing_time=elapsed,
        )

    def _ensure_file_size(self, audio_path: Path) -> Path:
        """确保文件不超过 API 限制 (25MB)，过大则压缩"""
        size_mb = audio_path.stat().st_size / (1024 * 1024)
        if size_mb <= 24:
            return audio_path

        print(f"  ⚡ 音频文件 {size_mb:.0f}MB 超过 API 限制 (25MB)，正在压缩...")
        compressed = audio_path.with_suffix(".mp3")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            str(compressed),
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        compressed_mb = compressed.stat().st_size / (1024 * 1024)
        print(f"  ✅ 压缩完成: {size_mb:.0f}MB → {compressed_mb:.0f}MB")
        return compressed
