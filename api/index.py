"""Vercel Python Function — 极简测试，零外部依赖。"""

def handler(request):
    """Vercel Python handler format."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"status":"alive","msg":"hello from vercel python"}'
    }

# 同时暴露 ASGI app（Vercel 可能用这个）
try:
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "mode": "fastapi"}

    @app.get("/api/healthz")
    def api_healthz():
        return {"status": "ok", "mode": "fastapi"}
except ImportError:
    app = None
