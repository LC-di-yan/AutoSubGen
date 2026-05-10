"""Web 服务 - FastAPI 后端"""

import os
import sys
import time
import uuid
import threading
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# 确保能导入项目根目录的模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import Config
from core.audio_extractor import AudioExtractor
from core.video_processor import VideoInfo
from core.subtitle_burner import SubtitleBurner
from core.subtitle_style import SubtitleStyle

Config.ensure_dirs()

# ── 数据模型 ──────────────────────────────────────────────────────────────

@dataclass
class TaskRecord:
    """后台任务记录"""
    task_id: str
    status: str = "pending"       # pending / processing / completed / failed
    progress: float = 0.0
    step: str = "等待处理"
    input_filename: str = ""
    output_filename: Optional[str] = None
    error: Optional[str] = None
    created_at: float = 0.0
    video_duration: float = 0.0
    video_resolution: str = ""
    language: str = ""
    subtitle_count: int = 0
    model_used: str = ""
    translate_to: str = ""            # 翻译目标语言
    translate_lang: str = ""          # 翻译语言显示名
    style: Optional[dict] = None      # 字幕样式配置

# ── 全局状态 ──────────────────────────────────────────────────────────────

_tasks: dict[str, TaskRecord] = {}
_tasks_lock = threading.Lock()

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 允许的视频扩展名
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}

# ── FastAPI 应用 ──────────────────────────────────────────────────────────

app = FastAPI(title="VideoSubtitle", version="1.0.0")


# ── 后台处理 ──────────────────────────────────────────────────────────────

def update_task(task_id: str, **kwargs):
    """线程安全地更新任务状态"""
    with _tasks_lock:
        for k, v in kwargs.items():
            setattr(_tasks[task_id], k, v)


def run_pipeline(task_id: str, video_path: Path, language: Optional[str],
                 model_size: str, translate_to: str = "",
                 style_dict: Optional[dict] = None):
    """后台运行处理流水线"""
    try:
        # 0. 解析样式配置
        style = SubtitleStyle.from_dict(style_dict) if style_dict else SubtitleStyle()

        # 1. 读取视频信息
        update_task(task_id, status="processing", progress=5, step="读取视频信息")
        info = VideoInfo(video_path)
        update_task(task_id,
                    video_duration=info.duration,
                    video_resolution=f"{info.width}x{info.height}",
                    progress=10)

        # 2. 提取音频
        update_task(task_id, step="提取音频中...", progress=15)
        audio_path = Config.AUDIO_DIR / f"{task_id}.wav"
        AudioExtractor.extract(video_path, audio_path)

        # 3. 语音识别
        from core.speech_recognizer import SpeechRecognizer
        update_task(task_id, step="语音识别中...", progress=25)
        recognizer = SpeechRecognizer(model_size=model_size)
        result = recognizer.transcribe(audio_path, language=language)
        result.video_path = video_path

        # 清理临时音频
        if audio_path.exists():
            audio_path.unlink()

        if not result.segments:
            raise RuntimeError("未识别到有效字幕")

        # 繁体转简体
        result.to_simplified_chinese()

        # 3.5 翻译字幕（可选）
        if translate_to:
            update_task(task_id, step=f"翻译字幕中... ({translate_to})", progress=65)
            lang_name = result.translate(
                target_lang=translate_to,
                source_lang=result.language,
                api_key=Config.API_KEY,
                base_url=Config.API_BASE_URL,
            )
            update_task(task_id, translate_lang=lang_name)
            print(f"  🌍 字幕已翻译为: {lang_name}")

        update_task(task_id,
                    progress=80,
                    step="正在烧录字幕...",
                    language=result.language,
                    subtitle_count=len(result.segments),
                    model_used=f"whisper-{model_size}")

        # 5. 烧录字幕
        output_filename = f"{task_id}_subtitled{video_path.suffix}"
        output_path = Config.OUTPUT_VIDEO_DIR / output_filename
        SubtitleBurner.burn(video_path, result.segments, output_path,
                            video_width=info.width, video_height=info.height,
                            style=style)

        # 完成
        update_task(task_id,
                    status="completed",
                    progress=100,
                    step="处理完成",
                    output_filename=output_filename)

    except Exception as e:
        update_task(task_id, status="failed", error=str(e), progress=0)
    finally:
        # 清理上传的临时视频
        if video_path.exists():
            video_path.unlink()


# ── API 路由 ──────────────────────────────────────────────────────────────

@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    """获取任务状态"""
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "step": task.step,
        "language": task.language,
        "subtitle_count": task.subtitle_count,
        "model_used": task.model_used,
        "video_duration": task.video_duration,
        "video_resolution": task.video_resolution,
        "output_filename": task.output_filename,
        "error": task.error,
        "created_at": task.created_at,
        "translate_to": task.translate_to,
        "translate_lang": task.translate_lang,
        "style": task.style,
    }


@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    model: str = Form("small"),
    translate_to: Optional[str] = Form(None),
    style: Optional[str] = Form(None),
):
    """上传视频并开始处理"""
    # 验证文件扩展名
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式: {ext}")

    # 解析样式 JSON
    style_dict = None
    if style:
        try:
            import json
            style_dict = json.loads(style)
        except json.JSONDecodeError:
            raise HTTPException(400, "样式参数格式错误")

    # 创建任务
    task_id = uuid.uuid4().hex[:12]
    record = TaskRecord(
        task_id=task_id,
        created_at=time.time(),
        input_filename=file.filename,
        style=style_dict,
    )
    if translate_to:
        record.translate_to = translate_to
    with _tasks_lock:
        _tasks[task_id] = record

    # 保存上传文件
    upload_path = UPLOAD_DIR / f"{task_id}{ext}"
    content = await file.read()
    upload_path.write_bytes(content)

    # 启动后台处理
    thread = threading.Thread(
        target=run_pipeline,
        args=(task_id, upload_path, language, model, translate_to or "", style_dict),
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id, "filename": file.filename}


@app.get("/api/download/{filename}")
def download_video(filename: str):
    """下载处理完成的视频"""
    file_path = Config.OUTPUT_VIDEO_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(
        str(file_path),
        media_type="video/mp4",
        filename=filename,
    )


# ── 页面路由 ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/app.js", response_class=HTMLResponse)
def app_js():
    js_path = Path(__file__).parent / "static" / "js" / "app.js"
    return HTMLResponse(js_path.read_text(encoding="utf-8"), media_type="application/javascript")


@app.get("/style.css", response_class=HTMLResponse)
def style_css():
    css_path = Path(__file__).parent / "static" / "css" / "style.css"
    return HTMLResponse(css_path.read_text(encoding="utf-8"), media_type="text/css")


# ── 启动 ──────────────────────────────────────────────────────────────────

def main():
    print(f"\n  🌐 VideoSubtitle Web Service")
    print(f"  {'='*40}")
    print(f"  地址: http://localhost:8000")
    print(f"  上传目录: {UPLOAD_DIR}")
    print(f"  输出目录: {Config.OUTPUT_VIDEO_DIR}")
    print(f"  {'='*40}\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
