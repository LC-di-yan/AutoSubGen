"""数据模型"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SubtitleSegment:
    """单条字幕片段"""
    index: int
    start_time: float       # 开始时间（秒）
    end_time: float         # 结束时间（秒）
    text: str               # 原始字幕文本
    translated_text: str = ""  # 翻译后的文本（可选）

    def to_srt_block(self) -> str:
        return (
            f"{self.index}\n"
            f"{_seconds_to_srt_time(self.start_time)} --> {_seconds_to_srt_time(self.end_time)}\n"
            f"{self.text}\n"
        )

    def to_vtt_block(self) -> str:
        return (
            f"{_seconds_to_vtt_time(self.start_time)} --> {_seconds_to_vtt_time(self.end_time)}\n"
            f"{self.text}\n"
        )


@dataclass
class SubtitleResult:
    """完整的字幕结果"""
    video_path: Path
    segments: list[SubtitleSegment] = field(default_factory=list)
    language: str = ""
    duration: float = 0.0
    model_used: str = ""
    processing_time: float = 0.0

    @property
    def full_text(self) -> str:
        return "\n".join(seg.text for seg in self.segments)

    def to_srt(self) -> str:
        return "\n".join(seg.to_srt_block() for seg in self.segments)

    def to_vtt(self) -> str:
        return "WEBVTT\n\n" + "\n".join(seg.to_vtt_block() for seg in self.segments)

    def to_simplified_chinese(self):
        """将所有字幕文本转换为简体中文"""
        import opencc
        converter = opencc.OpenCC("t2s")
        for seg in self.segments:
            seg.text = converter.convert(seg.text)

    def translate(self, target_lang: str, source_lang: str = "",
                  api_key: str = "", base_url: str = "") -> str:
        """翻译所有字幕到目标语言，返回目标语言名称"""
        from core.translator import Translator, LANG_NAMES
        t = Translator(api_key=api_key, base_url=base_url)
        texts = [seg.text for seg in self.segments]
        translated = t.translate(texts, target_lang, source_lang)
        for seg, trans in zip(self.segments, translated):
            seg.translated_text = trans
        return LANG_NAMES.get(target_lang, target_lang)

    def save(self, output_path: Path, fmt: str = "srt") -> Path:
        output_path = output_path.with_suffix(f".{fmt}")
        if fmt == "srt":
            content = self.to_srt()
        elif fmt == "vtt":
            content = self.to_vtt()
        elif fmt == "ass":
            content = _generate_ass(self.segments)
        else:
            raise ValueError(f"不支持的字幕格式: {fmt}")
        output_path.write_text(content, encoding="utf-8")
        return output_path


@dataclass
class ProcessingTask:
    """处理任务"""
    video_path: Path
    mode: str = "local"                      # "api" or "local"
    language: Optional[str] = None
    model_size: str = "small"                # 仅 local 模式
    device: str = "cpu"                     # 仅 local 模式
    compute_type: str = "int8"              # 仅 local 模式
    keep_subtitles: bool = False            # 是否保留字幕文件
    output_dir: Optional[Path] = None


# ── 辅助函数 ──────────────────────────────────────────────────────────────


def _seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _seconds_to_vtt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _generate_ass(segments: list[SubtitleSegment]) -> str:
    lines = [
        "[Script Info]",
        "Title: Generated Subtitle",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,0,0,2,20,20,30,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for seg in segments:
        start = _seconds_to_ass_time(seg.start_time)
        end = _seconds_to_ass_time(seg.end_time)
        text = seg.text.replace("{", "\\{").replace("}", "\\}")
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    return "\n".join(lines)


def _seconds_to_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
