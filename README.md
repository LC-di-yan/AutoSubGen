# 视频字幕生成系统

自动识别视频语音，输出带字幕的视频文件。支持 **本地 Whisper 模型**（离线免费）和 **云端 API**（OpenAI 兼容）两种模式。

字幕显示在画面**正下方**，简体中文，黑色描边清晰可读。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 FFmpeg
# Windows: https://ffmpeg.org/download.html 下载后加入 PATH
# macOS:   brew install ffmpeg
# Linux:   sudo apt install ffmpeg

# 3. 选择使用方式
```

### 方式一：Web 界面（推荐）

```bash
python -m web.app
```

浏览器打开 `http://localhost:8000`，拖入视频即可。

### 方式二：命令行

```bash
python main.py video.mp4
```

首次运行会自动下载 Whisper 模型（默认 small ~460MB），后续离线可用。

## 项目结构

```
AutoSubGen/
├── core/                  # 核心模块
│   ├── video_processor.py    # 视频解析
│   ├── audio_extractor.py    # 音频提取
│   ├── speech_recognizer.py  # 本地 Whisper 语音识别
│   ├── api_recognizer.py     # API 语音识别
│   ├── translator.py         # AI 字幕翻译
│   ├── subtitle_generator.py # 字幕生成
│   ├── subtitle_burner.py    # 字幕烧录
│   └── subtitle_style.py     # 字幕样式
├── web/                   # Web 界面
│   ├── app.py
│   ├── templates/
│   └── static/
├── utils/                 # 工具函数
├── main.py                # 命令行入口
├── config.py              # 配置文件（已 gitignore）
├── config.example.py      # 配置模板
├── requirements.txt       # Python 依赖
└── .gitignore
```

## 下载模型自动下载

本项目的 Whisper 模型**不会打包在仓库中**，用户首次运行时会自动下载到 `~/.cache/whisper/`：

| 模型 | 大小 | 下载时机 |
|------|------|----------|
| tiny | ~150MB | 指定 `--model tiny` 时 |
| base | ~290MB | 指定 `--model base` 时 |
| **small（默认）** | **~460MB** | **首次运行自动下载** |
| medium | ~1.5GB | 指定 `--model medium` 时 |
| large-v3 | ~6GB | 指定 `--model large-v3` 时 |

> 所有依赖（torch ~483MB、whisper 等）通过 `pip install -r requirements.txt` 安装，无需手动下载。

## 运行模式

### 本地模式（默认，免费离线）

基于 OpenAI Whisper 本地运行，无需联网，无需 API Key。

```bash
python main.py video.mp4
python main.py video.mp4 --model medium      # 更高精度
python main.py video.mp4 --model large-v3 --device cuda  # GPU 最高精度
```

### API 模式（需 API Key）

调用 OpenAI 兼容的语音识别 API（默认使用 DeepSeek）：

```bash
set ASR_MODE=api
set OPENAI_API_KEY=sk-xxx
python main.py video.mp4
```

## Web 界面功能

- 拖拽 / 点击上传视频
- 选择模型大小和语言
- 实时进度显示
- 内嵌视频播放器预览结果
- 一键下载带字幕的视频

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `input` | 必填 | 视频文件或目录路径 |
| `--model` | small | tiny/base/small/medium/large-v3 |
| `--language` | 自动检测 | zh(中)/en(英)/ja(日) 等 |
| `--device` | cpu | cpu 或 cuda（需 NVIDIA 显卡） |
| `--keep-subs` | 不保留 | 同时输出 SRT/VTT 字幕文件 |

### 命令行示例

```bash
python main.py video.mp4                     # 默认
python main.py video.mp4 --language zh       # 指定中文
python main.py video.mp4 --keep-subs         # 保留字幕文件
python main.py ./videos/                     # 批量处理目录
```

## 输出文件

```
output/
├── videos/
│   └── xxx_subtitled.mp4    ← 带字幕的视频
└── subtitles/               （使用 --keep-subs 时生成）
    └── xxx.srt
```

## 常见问题

**下载模型慢？**
- 设置 Hugging Face 镜像：`set HF_ENDPOINT=https://hf-mirror.com`
- 或用代理：`set HTTP_PROXY=http://127.0.0.1:7890`
- 或改用 `--model tiny`（仅 150MB）

**提示 "ffmpeg 未找到"？**
下载 FFmpeg 并加入系统 PATH。

**支持哪些格式？**
mp4、avi、mkv、mov、wmv、flv、webm。
