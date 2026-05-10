"""字幕生成 - 保存字幕文件"""

from pathlib import Path

from core.models import SubtitleResult


class SubtitleGenerator:
    """字幕生成与保存"""

    @staticmethod
    def save(
        result: SubtitleResult,
        output_path: Path,
        formats: set[str] | None = None,
    ) -> dict[str, Path]:
        """
        保存字幕到文件

        Args:
            result:      字幕识别结果
            output_path: 输出文件路径（不含后缀）
            formats:     字幕格式集合，默认 {"srt", "vtt"}

        Returns:
            格式到路径的映射，如 {"srt": Path("output.srt"), "vtt": Path("output.vtt")}
        """
        if formats is None:
            formats = {"srt", "vtt"}

        saved = {}
        for fmt in formats:
            path = result.save(output_path, fmt)
            saved[fmt] = path

        return saved

    @staticmethod
    def print_summary(saved_paths: dict[str, Path]):
        """打印字幕文件摘要"""
        print(f"  📄 已生成字幕文件:")
        for fmt, path in saved_paths.items():
            size = path.stat().st_size
            print(f"     {fmt.upper():>4}: {path} ({size / 1024:.1f} KB)")
