"""语音识别 - 基于 OpenAI Whisper 的本地语音转文字"""

import os
from pathlib import Path
from typing import Optional

import whisper

from core.models import SubtitleResult, SubtitleSegment

# Whisper 模型缓存目录
WHISPER_CACHE_DIR = Path(os.path.expanduser("~")) / ".cache" / "whisper"

# 国内镜像下载命令（下载慢时可用）
_MODEL_DOWNLOAD_HELP = """
下载慢时可使用以下方式手动下载模型:

  方式 1 - 使用 Hugging Face 镜像（推荐）:
     pip install huggingface-hub
     set HF_ENDPOINT=https://hf-mirror.com
     huggingface-cli download openai/whisper-{model} --local-dir {cache_dir}

  方式 2 - 直接下载后放到缓存目录:
     将 whisper-{model}.pt 文件放到 {cache_dir}

  方式 3 - 使用代理（如 clash/v2ray）:
     在终端中设置 set HTTP_PROXY=http://127.0.0.1:7890
"""


class SpeechRecognizer:
    """
    Whisper 语音识别器

    支持本地离线运行，默认使用 small 模型（~460MB）。
    下载慢时参考 _MODEL_DOWNLOAD_HELP。
    """

    _model_cache: dict[str, whisper.Whisper] = {}

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

        # 模型缓存路径（供提示用）
        self._cache_path = WHISPER_CACHE_DIR / f"{model_size}.pt"

    def _load_model(self) -> whisper.Whisper:
        key = f"{self.model_size}_{self.device}"
        if key in self._model_cache:
            return self._model_cache[key]

        if self.model_size not in whisper.available_models():
            raise ValueError(
                f"未知模型: {self.model_size}。可用: {whisper.available_models()}"
            )

        # 清理小于 1MB 的损坏缓存
        if self._cache_path.exists() and self._cache_path.stat().st_size < 1024 * 1024:
            print(f"  ⚠️  检测到损坏的缓存文件，正在删除...")
            self._cache_path.unlink()

        print(f"  📦 加载 Whisper 模型 '{self.model_size}' (~{self._model_size_mb()}MB)...")
        try:
            model = whisper.load_model(self.model_size, device=self.device)
        except Exception as e:
            raise RuntimeError(
                f"模型下载/加载失败: {e}\n"
                + _MODEL_DOWNLOAD_HELP.format(
                    model=self.model_size, cache_dir=WHISPER_CACHE_DIR
                )
            )

        self._model_cache[key] = model
        return self._model_cache[key]

    def _model_size_mb(self) -> int:
        return {"tiny": 150, "base": 290, "small": 460, "medium": 1500, "large-v3": 6000}.get(
            self.model_size, 0
        )

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        verbose: bool = False,
    ) -> SubtitleResult:
        """
        转录音频文件为字幕

        Args:
            audio_path: 音频文件路径 (WAV 16kHz mono)
            language:   语言代码 (None=自动检测, "zh"=中文, "en"=英文)
            verbose:    是否显示 Whisper 详细输出

        Returns:
            SubtitleResult 包含所有识别结果

        Raises:
            RuntimeError: 识别过程出错
        """
        import time
        start_time = time.perf_counter()

        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        model = self._load_model()

        # 转录参数
        transcribe_opts = {
            "verbose": verbose,
        }
        if language:
            transcribe_opts["language"] = language

        print(f"  🎤 开始语音识别...")
        result = model.transcribe(str(audio_path), **transcribe_opts)

        elapsed = time.perf_counter() - start_time

        # 构建结果
        segments = []
        for seg in result.get("segments", []):
            segments.append(SubtitleSegment(
                index=seg["id"] + 1,
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"].strip(),
            ))

        detected_lang = result.get("language", language or "")

        subtitle_result = SubtitleResult(
            video_path=audio_path,
            segments=segments,
            language=detected_lang,
            duration=result.get("segments", [{}])[-1].get("end", 0) if segments else 0,
            model_used=self.model_size,
            processing_time=elapsed,
        )

        # 显示识别统计
        audio_duration = result.get("segments", [{}])[-1].get("end", 0) if segments else 0
        speed_ratio = audio_duration / elapsed if elapsed > 0 else 0
        print(f"  ✅ 识别完成 | 语言: {detected_lang} | "
              f"耗时: {elapsed:.1f}s | "
              f"实时率: {speed_ratio:.1f}x | "
              f"字幕条数: {len(segments)}")

        return subtitle_result

    @staticmethod
    def available_models() -> list[str]:
        """获取可用模型列表"""
        return whisper.available_models()
