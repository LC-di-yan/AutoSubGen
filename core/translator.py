"""字幕翻译 - 基于 AI Chat API 的文本翻译"""

import os
import re
from typing import Optional

from openai import OpenAI

# 语言代码 → 中文名称映射
LANG_NAMES = {
    "en": "英文", "zh": "中文", "ja": "日文", "ko": "韩文",
    "fr": "法文", "de": "德文", "es": "西班牙文", "pt": "葡萄牙文",
    "ru": "俄文", "ar": "阿拉伯文", "th": "泰文", "vi": "越南文",
    "it": "意大利文", "nl": "荷兰文", "pl": "波兰文", "tr": "土耳其文",
}


class Translator:
    """
    基于 AI Chat API 的字幕翻译

    使用 OpenAI 兼容的 Chat 接口（默认 DeepSeek）批量翻译字幕文本。
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = "deepseek-chat"

    def translate(
        self,
        texts: list[str],
        target_lang: str,
        source_lang: str = "",
    ) -> list[str]:
        """
        批量翻译字幕文本

        Args:
            texts:       待翻译的文本列表
            target_lang: 目标语言代码 (如 "en", "zh", "ja")
            source_lang: 源语言代码 (可选，帮助提升质量)

        Returns:
            翻译后的文本列表，顺序与输入一致
        """
        if not texts:
            return []

        target_name = LANG_NAMES.get(target_lang, target_lang)
        source_hint = f"从{source_lang} " if source_lang else ""

        # 将文本编号后拼成一条消息
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        system_prompt = (
            f"你是一个专业的字幕翻译助手。请将以下字幕文本{source_hint}"
            f"翻译成{target_name}。\n"
            "要求：\n"
            "- 保持每条字幕的编号不变\n"
            "- 只返回翻译结果，不要额外解释\n"
            "- 每条结果一行，格式为: 编号. 翻译\n"
            "- 保持口语化、自然流畅"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": numbered},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
        except Exception as e:
            raise RuntimeError(f"翻译 API 调用失败: {e}")

        raw = resp.choices[0].message.content.strip()
        return self._parse_response(raw, len(texts))

    def _parse_response(self, raw: str, expected_count: int) -> list[str]:
        """解析 API 返回的编号文本为列表"""
        results = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 去掉编号前缀 "1. " 或 "1、"
            cleaned = re.sub(r"^\d+[.、)\s]+", "", line).strip()
            if cleaned:
                results.append(cleaned)

        # 如果行数不匹配，尝试用空字符串补齐
        while len(results) < expected_count:
            results.append("")
        return results[:expected_count]
