#!/usr/bin/env python3
"""
视频字幕生成系统

基于本地 Whisper 的离线字幕生成工具，直接输出带字幕的视频。
无需联网，无需 API Key。

用法:
    python main.py video.mp4                       # 本地模式（默认 small 模型）
    python main.py video.mp4 --model medium         # 使用 medium 模型（更准）
    python main.py video.mp4 --language zh          # 指定中文
    python main.py ./videos/                        # 批量处理
    python main.py video.mp4 --keep-subs            # 同时保留字幕文件
"""

import argparse
import sys
from pathlib import Path

from config import Config
from core.audio_extractor import AudioExtractor
from core.models import ProcessingTask
from core.subtitle_burner import SubtitleBurner
from core.subtitle_generator import SubtitleGenerator
from core.video_processor import VideoInfo
from utils.file_utils import (
    find_video_files,
    get_audio_tmp_path,
    get_output_video_path,
    get_file_size,
    format_duration,
)
from utils.time_utils import timer


def process_video(task: ProcessingTask) -> None:
    """处理单个视频文件"""
    video_path = task.video_path
    print(f"\n{'='*60}")
    print(f"  处理视频: {video_path.name}")
    print(f"{'='*60}")

    # 1. 读取视频信息
    with timer("读取视频信息"):
        try:
            info = VideoInfo(video_path)
            print(f"  ℹ️  时长: {format_duration(info.duration)} | "
                  f"分辨率: {info.width}x{info.height} | "
                  f"编码: {info.codec}")
        except RuntimeError as e:
            print(f"  ❌ 无法读取视频信息: {e}")
            return

    # 2. 提取音频
    audio_path = get_audio_tmp_path(video_path)
    with timer("音频提取"):
        try:
            AudioExtractor.extract(video_path, audio_path)
            print(f"  🔊 音频: {audio_path.name} ({get_file_size(audio_path)})")
        except RuntimeError as e:
            print(f"  ❌ 音频提取失败: {e}")
            return

    # 3. 语音识别
    result = None
    try:
        if task.mode == "api":
            from core.api_recognizer import ApiRecognizer
            recognizer = ApiRecognizer(
                api_key=Config.API_KEY, base_url=Config.API_BASE_URL
            )
        else:
            from core.speech_recognizer import SpeechRecognizer
            recognizer = SpeechRecognizer(
                model_size=task.model_size,
                device=task.device,
                compute_type=task.compute_type,
            )

        result = recognizer.transcribe(audio_path, language=task.language)
        result.video_path = video_path
    except Exception as e:
        print(f"  ❌ 语音识别失败: {e}")
        return
    finally:
        if audio_path.exists():
            audio_path.unlink()

    if not result or not result.segments:
        print(f"  ❌ 未识别到有效字幕")
        return

    # 3.5 繁体转简体
    result.to_simplified_chinese()

    # 4. 烧录字幕到视频（默认行为）
    output_video = get_output_video_path(video_path)
    with timer("字幕烧录"):
        try:
            SubtitleBurner.burn(
                video_path,
                result.segments,
                output_video,
                video_width=info.width,
                video_height=info.height,
            )
        except RuntimeError as e:
            print(f"  ❌ 字幕烧录失败: {e}")
            return

    output_size = get_file_size(output_video)
    print(f"  🎬 输出视频: {output_video.name} ({output_size})")

    # 5. 可选: 保留字幕文件
    if task.keep_subtitles:
        output_base = (task.output_dir or Config.SUBTITLE_DIR) / video_path.stem
        saved = SubtitleGenerator.save(result, output_base, {"srt", "vtt"})
        SubtitleGenerator.print_summary(saved)

    # 6. 打印摘要
    print(f"\n  📊 处理摘要:")
    print(f"     来源: {video_path.name}")
    print(f"     输出: {output_video.name}")
    print(f"     时长: {format_duration(info.duration)}")
    print(f"     语言: {result.language}")
    print(f"     模式: {result.model_used}")
    print(f"     耗时: {result.processing_time:.1f}s")
    print(f"     字幕: {len(result.segments)} 条")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="视频字幕生成系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py video.mp4                        # 默认 local + small 模型
  python main.py video.mp4 --model medium          # 换 medium 模型
  python main.py video.mp4 --model large-v3        # 最高精度
  python main.py video.mp4 --device cuda           # GPU 加速
  python main.py video.mp4 --language zh           # 指定中文
  python main.py video.mp4 --keep-subs             # 同时保留字幕文件
  python main.py ./videos/                         # 批量处理
        """,
    )

    parser.add_argument("input", nargs="?",
                        help="视频文件或包含视频的目录路径")
    parser.add_argument("--mode", choices=["api", "local"],
                        default=Config.MODE,
                        help=f"识别模式 (默认: {Config.MODE})")
    parser.add_argument("--language",
                        default=Config.DEFAULT_LANGUAGE,
                        help="语言代码 (默认自动检测; 如: zh, en, ja)")
    parser.add_argument("--model",
                        default=Config.WHISPER_MODEL_SIZE,
                        help=f"本地模型大小 (默认: {Config.WHISPER_MODEL_SIZE}, 仅 local 模式)")
    parser.add_argument("--device",
                        choices=["cpu", "cuda"],
                        default=Config.DEVICE,
                        help=f"运行设备 (默认: {Config.DEVICE}, 仅 local 模式)")
    parser.add_argument("--keep-subs", action="store_true",
                        help="同时保留 SRT/VTT 字幕文件")

    args = parser.parse_args()

    # 检查输入
    if not args.input:
        parser.print_help()
        print("\n⚡ 需要指定视频文件或目录")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 路径不存在: {input_path}")
        sys.exit(1)

    # 确保输出目录
    Config.ensure_dirs()

    # 查找视频文件
    try:
        video_files = find_video_files(str(input_path))
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    if not video_files:
        print(f"❌ 未找到支持的视频文件 (mp4/avi/mkv/mov/wmv/flv/webm)")
        sys.exit(1)

    print(f"\n🔍 找到 {len(video_files)} 个视频文件  |  模式: {args.mode}")

    # 批量处理
    success = 0
    fail = 0

    for video_file in video_files:
        task = ProcessingTask(
            video_path=video_file,
            mode=args.mode,
            language=args.language,
            model_size=args.model,
            device=args.device,
            compute_type="float16" if args.device == "cuda" else "int8",
            keep_subtitles=args.keep_subs,
        )
        try:
            process_video(task)
            success += 1
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            fail += 1

    if len(video_files) > 1:
        print(f"\n{'='*60}")
        print(f"  全部完成 | 成功: {success} | 失败: {fail}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
