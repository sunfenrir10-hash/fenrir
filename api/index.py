"""Vercel Serverless 入口 — 暴露 FastAPI app 给 @vercel/python。

@vercel/python 会自动将项目根目录加入 sys.path，
因此 src.* 和 api.main 均可直接 import。
"""
import sys
from pathlib import Path

# 双保险：确保项目根在 path 中（Vercel 通常已做，但防万一）
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from api.main import app  # noqa: E402
