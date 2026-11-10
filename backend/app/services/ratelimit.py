# 每位用戶的呼叫頻率限制（僅記憶體，backend 重啟後歸零，可接受）：
# 每一次會打到 LLM 的請求都算一次，避免有人狂刷訊息把 API 額度燒光
from __future__ import annotations
import time
from collections import deque
from app.config import settings as env
from app.errors import RateLimited

MINUTE = 60
DAY = 24 * 60 * 60
MAX_TRACKED_USERS = 50_000

# user_key -> 最近一天內每次請求的時間戳記（由舊到新）
_hits: dict[str, deque[float]] = {}


def check(user_key: str) -> None:
    # 沒超過上限就記一筆並放行，超過就丟 RateLimited
    per_minute, per_day = env.rate_limit_per_minute, env.rate_limit_per_day
    if per_minute <= 0 and per_day <= 0:
        return

    now = time.time()
    if len(_hits) > MAX_TRACKED_USERS:
        for key in [k for k, h in _hits.items() if not h or now - h[-1] >= DAY]:
            _hits.pop(key, None)

    hits = _hits.setdefault(user_key, deque())
    while hits and now - hits[0] >= DAY:
        hits.popleft()

    if per_day > 0 and len(hits) >= per_day:
        raise RateLimited("Daily limit reached")
    if per_minute > 0 and sum(1 for t in hits if now - t < MINUTE) >= per_minute:
        raise RateLimited("Too many requests, slow down")

    hits.append(now)
