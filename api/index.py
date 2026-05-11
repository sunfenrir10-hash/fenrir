"""Vercel Serverless Function 入口。

Vercel 自动识别 api/index.py 的 `app` 变量为 ASGI 应用并路由所有 /api/* 流量。
"""
import sys
import os

# 确保项目根目录在 Python path 中，让 src.* 和 api.* 都能正常 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app  # noqa: F401

# 允许 `python api/index.py` 本地直跑做冒烟
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
