"""时间测量工具"""

import time
from contextlib import contextmanager
from typing import Generator


@contextmanager
def timer(label: str = "") -> Generator[None, None, None]:
    """计时器上下文管理器"""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    if label:
        print(f"  ⏱ {label}: {elapsed:.1f}s")
