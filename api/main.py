"""FastAPI 入口（Phase 3）。

接口:
    POST /api/chart   生成 100 年 K 线 + 命运叙事
    GET  /api/cities  当前支持的城市列表
    GET  /healthz     健康检查

Phase 5 改造：
- 加 slowapi IP 速率限制（防恶意刷 LLM）
- Vercel 部署入口在 api/index.py，本文件保留供本地 uvicorn 使用
"""
from __future__ import annotations

import os
import statistics
import traceback
from datetime import date, time as dtime
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.pipeline import pipeline
from src.cities import CITIES, resolve_city
from src.llm import call_llm, is_mock_mode
from src.personality import detect_personality, extract_highlight_years, PERSONALITIES


# ============================================================
# Pydantic models
# ============================================================

class ChartRequest(BaseModel):
    birth_date: str = Field(..., description="生日 YYYY-MM-DD", examples=["1991-05-12"])
    birth_time: str = Field(..., description="出生钟表时间 HH:MM", examples=["08:00"])
    city: str = Field(..., description="出生城市（中文名）", examples=["北京"])
    gender: Literal[0, 1] = Field(1, description="0=女 1=男")
    title: str | None = Field(None, description="可选自定义标题")

    @field_validator("birth_date")
    @classmethod
    def _check_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"birth_date 格式错误，应为 YYYY-MM-DD: {v}") from e
        return v

    @field_validator("birth_time")
    @classmethod
    def _check_time(cls, v: str) -> str:
        try:
            dtime.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"birth_time 格式错误，应为 HH:MM: {v}") from e
        return v


class KlineCandle(BaseModel):
    year: int
    age: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    color: str


class ChartSummary(BaseModel):
    start_close: float
    end_close: float
    max_year: int
    min_year: int
    avg_close: float
    red_count: int
    green_count: int


class ChartMeta(BaseModel):
    bazi: list[str]
    strength: str
    day_master: str
    city: str
    true_solar_time: str
    personality: dict  # {id, name, emoji, tagline}
    city_input: str = ""             # 用户原始输入
    city_used: str = ""              # 实际用于排盘的城市名
    city_match_type: str = "exact"   # exact | alias | fuzzy | fallback


class ChartResponse(BaseModel):
    title: str
    kline: list[KlineCandle]
    narrative: str
    summary: ChartSummary
    meta: ChartMeta
    mock: bool  # 是否用 mock LLM 生成


# ============================================================
# App
# ============================================================

app = FastAPI(
    title="mingk · 人生命运 K 线图",
    description="输入生日 + 出生地，输出 100 年 K 线 + 命运叙事",
    version="0.5.0",
)

# ---- 速率限制（slowapi）：防恶意刷 LLM 烧钱 ----
# 测试环境（pytest）默认禁用限流，避免污染既有测试
_RATELIMIT_ENABLED = os.environ.get("MINGK_RATELIMIT", "1") != "0"
limiter = Limiter(
    key_func=get_remote_address,
    enabled=_RATELIMIT_ENABLED,
    default_limits=[],
)
app.state.limiter = limiter


def _friendly_429(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": "请求太频繁了，等 1 分钟再试",
            "retry_after_seconds": 60,
        },
    )


app.add_exception_handler(RateLimitExceeded, _friendly_429)
app.add_middleware(SlowAPIMiddleware)

# 本地联调允许跨域；上线时再收紧 allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "mock_llm": is_mock_mode()}


@app.get("/api/cities")
@limiter.limit("60/minute")
def list_cities(request: Request) -> dict:
    return {"cities": sorted(CITIES.keys())}


@app.get("/api/personalities")
@limiter.limit("60/minute")
def list_personalities(request: Request) -> list[dict]:
    """返回 12 种 K 线人格（id/name/emoji/tagline），供 Landing 渲染。"""
    return [
        {"id": p["id"], "name": p["name"], "emoji": p["emoji"], "tagline": p["tagline"]}
        for p in PERSONALITIES
    ]


@app.post("/api/chart", response_model=ChartResponse)
@limiter.limit("5/minute")
def create_chart(request: Request, req: ChartRequest) -> ChartResponse:
    # 1. 解析输入
    try:
        d = date.fromisoformat(req.birth_date)
        t = dtime.fromisoformat(req.birth_time)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. 解析城市（容忍自由输入：精确 → 模糊 → 北京兜底，永不 4xx）
    city_input = (req.city or "").strip()
    resolved = resolve_city(city_input)
    if resolved is None:
        city_used = "北京"
        city_match_type = "fallback"
    else:
        city_used = resolved["name"]
        city_match_type = resolved["matched"]

    # 3. 跑 pipeline
    try:
        result = pipeline(
            d.year, d.month, d.day, t.hour, t.minute, city_used, gender=req.gender
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"排盘失败: {e}")

    # 3. 计算人格标签 + 高光年份（在 LLM 之前）
    personality = detect_personality(result["kline"])
    highlights = extract_highlight_years(result["kline"])

    # 4. 调用 LLM 生成叙事（无 Key 自动 mock）
    try:
        narrative = call_llm(
            result["chart"],
            result["kline"],
            personality=personality,
            highlights=highlights,
            yearly_raw=result.get("yearly_raw"),
        )
    except Exception as e:
        traceback.print_exc()
        # 兜底：用标签构造一个最简短卡
        narrative = (
            f"{personality['emoji']} {personality['name']}：命主八字稳健，"
            f"30 岁起放量突破，50 岁震荡调整，70 岁回踩支撑后再起。"
            f"建议长期持有，别频繁交易。"
        )

    # 5. 组装响应
    closes = [k["close"] for k in result["kline"]]
    years = [k["year"] for k in result["kline"]]
    max_idx = max(range(len(closes)), key=lambda i: closes[i])
    min_idx = min(range(len(closes)), key=lambda i: closes[i])

    summary = ChartSummary(
        start_close=round(closes[0], 2),
        end_close=round(closes[-1], 2),
        max_year=years[max_idx],
        min_year=years[min_idx],
        avg_close=round(statistics.mean(closes), 2),
        red_count=sum(1 for k in result["kline"] if k["color"] == "red"),
        green_count=sum(1 for k in result["kline"] if k["color"] == "green"),
    )

    fp = result["chart"]["four_pillars"]
    meta = ChartMeta(
        bazi=[fp["year"], fp["month"], fp["day"], fp["hour"]],
        strength=result["chart"]["strength"],
        day_master=result["chart"]["day_master"],
        city=result["chart"]["city"],
        true_solar_time=result["chart"]["true_solar_time"],
        personality=personality,
        city_input=city_input,
        city_used=city_used,
        city_match_type=city_match_type,
    )

    title = req.title or f"{req.birth_date} {req.birth_time} {city_used}"

    return ChartResponse(
        title=title,
        kline=[KlineCandle(**k) for k in result["kline"]],
        narrative=narrative,
        summary=summary,
        meta=meta,
        mock=is_mock_mode(),
    )
