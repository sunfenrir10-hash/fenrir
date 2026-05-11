"""人生 K 线图 · 核心算法模块。

Pipeline: bazi -> score -> sanitize -> kline
"""
from .bazi import compute_bazi
from .score import compute_year_score
from .sanitize import sanitize
from .kline import build_kline
from .pipeline import pipeline

__all__ = [
    "compute_bazi",
    "compute_year_score",
    "sanitize",
    "build_kline",
    "pipeline",
]
