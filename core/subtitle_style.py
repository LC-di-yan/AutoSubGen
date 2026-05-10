"""字幕样式定义"""

import dataclasses
from dataclasses import dataclass, asdict
from typing import Optional


# ── 预设字体列表 ──────────────────────────────────────────────────────────────

FONT_PRESETS = [
    # Windows 中文
    {"label": "微软雅黑",    "value": "Microsoft YaHei"},
    {"label": "黑体",       "value": "SimHei"},
    {"label": "宋体",       "value": "SimSun"},
    {"label": "新宋体",     "value": "NSimSun"},
    {"label": "楷体",       "value": "KaiTi"},
    {"label": "仿宋",       "value": "FangSong"},
    {"label": "华文细黑",   "value": "STXihei"},
    # macOS / 跨平台
    {"label": "苹方",       "value": "PingFang SC"},
    {"label": "思源黑体",   "value": "Source Han Sans CN"},
    {"label": "思源宋体",   "value": "Source Han Serif CN"},
    {"label": "Noto Sans CJK",  "value": "Noto Sans CJK SC"},
    # 英文字体
    {"label": "Arial",           "value": "Arial"},
    {"label": "Helvetica",       "value": "Helvetica"},
    {"label": "Verdana",         "value": "Verdana"},
    {"label": "Times New Roman", "value": "Times New Roman"},
    {"label": "Impact",          "value": "Impact"},
    {"label": "Courier New",     "value": "Courier New"},
]


# ── 数据模型 ──────────────────────────────────────────────────────────────────

@dataclass
class SubtitleStyle:
    """字幕样式配置"""
    # 字体
    font_name: str = "Microsoft YaHei"
    # 字号相对视频高度的比例 (0.025 ≈ 18px 在 720p 下)
    font_size_ratio: float = 0.025
    # 颜色 (hex, 如 #FFFFFF)
    primary_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    # 描边宽度
    outline_width: int = 2
    # 字形
    bold: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "SubtitleStyle":
        valid_keys = {f.name for f in dataclasses.fields(SubtitleStyle)}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return SubtitleStyle(**filtered)


# ── 颜色工具 ──────────────────────────────────────────────────────────────────

def hex_to_ass(hex_color: str) -> str:
    """#RRGGBB → &H00BBGGRR  (ASS 颜色格式)"""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return "&H00FFFFFF"
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H00{b}{g}{r}"
