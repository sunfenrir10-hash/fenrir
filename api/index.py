"""Vercel Serverless 入口 — 暴露 FastAPI app 给 @vercel/python。

Vercel FastAPI preset 自动检测 api/index.py 中名为 app 的 FastAPI 实例。
"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，使 src.* 可被 import
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# api/ 目录加入，使同目录 main.py 可被 import
_api_dir = str(Path(__file__).resolve().parent)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from main import app  # noqa: E402
