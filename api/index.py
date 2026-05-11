"""Vercel Serverless Function 入口。

Vercel 自动识别 api/index.py 的 `app` 变量为 ASGI 应用并路由所有 /api/* 流量。
本文件复用 api/main.py 已构建好的 FastAPI app，避免重复定义。
"""
from api.main import app  # noqa: F401  (Vercel 通过 app 名字反射加载)

# 允许 `python api/index.py` 本地直跑做冒烟（与 Vercel 行为对齐）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
