# Telegram / Discord bot 共用：呼叫 backend 的內部端點（/api/roast、/api/excuse）
import httpx
from app.config import settings

API_BASE = f"{settings.api_base_url}/api"
INTERNAL_HEADERS = {"X-Internal-Secret": settings.api_secret_key}
# backend 最多等 LLM llm_timeout_seconds 秒，這裡多留一點讓它有時間回錯誤
API_TIMEOUT = settings.llm_timeout_seconds + 10

# bot 為獨立行程，需定期從 DB 重新載入設定才能反映後台的開關變更
SETTINGS_TTL = 15


class ApiError(Exception):
    def __init__(self, message: str, retryable: bool):
        super().__init__(message)
        self.message = message      # 可以直接顯示給用戶看的訊息
        self.retryable = retryable  # 重試有沒有意義（暫時性錯誤才有）


_ERROR_MESSAGES = {
    400: "這場對話已經到頂了，換一個吧。",
    403: "這不是你的對話。",
    404: "找不到這場對話，請重新開始。",
    409: "上一個還在處理，等一下。",
    422: "這個內容我處理不了，換一個試試。",
    429: "慢一點，你太快了。等一下再來。",
}


async def post(path: str, payload: dict) -> dict:
    # 成功回傳 backend 的 JSON；失敗一律丟 ApiError
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            resp = await client.post(f"{API_BASE}{path}", json=payload, headers=INTERNAL_HEADERS)
    except httpx.HTTPError as exc:
        raise ApiError("出了點問題，稍後再試。", retryable=True) from exc

    if resp.status_code in _ERROR_MESSAGES:
        raise ApiError(_ERROR_MESSAGES[resp.status_code], retryable=False)
    if resp.status_code >= 400:
        raise ApiError("出了點問題，稍後再試。", retryable=True)
    return resp.json()
