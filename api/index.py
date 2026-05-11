"""Vercel Serverless Function 入口 — 含完整 FastAPI app。"""
import sys
import os

# 项目根目录加入 Python path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/healthz")
def healthz():
    return {"status": "ok", "debug": "minimal_test", "root": ROOT, "path": sys.path[:3]}

# 尝试导入 src 模块，如果失败返回错误信息
try:
    from src.cities import CITIES, resolve_city
    from src.pipeline import pipeline
    from src.personality import PERSONALITIES
    IMPORT_OK = True
    IMPORT_ERR = None
except Exception as e:
    IMPORT_OK = False
    IMPORT_ERR = str(e)

@app.get("/healthz/imports")
def healthz_imports():
    return {"import_ok": IMPORT_OK, "error": IMPORT_ERR, "cities_count": len(CITIES) if IMPORT_OK else 0}

@app.get("/api/healthz")
def api_healthz():
    return {"status": "ok", "import_ok": IMPORT_OK, "error": IMPORT_ERR}
