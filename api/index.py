"""Vercel 入口 — 最小 FastAPI 测试。"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/api/healthz")
def api_healthz():
    return {"status": "ok"}
