"""Vercel Serverless 入口 — 暴露 FastAPI app 给 @vercel/python。"""
import sys
import os
from pathlib import Path

# 项目根目录加入 sys.path（使 src.* 可 import）
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# api/ 目录也加入（使同目录的 main.py 可直接 import）
_api_dir = str(Path(__file__).resolve().parent)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from main import app  # noqa: E402
