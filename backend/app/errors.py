# 會被轉成 HTTP 錯誤回應的應用層例外（main.py 有統一的 exception handler）


class AppError(Exception):
    status_code = 400
    detail = "Bad request"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class SessionNotFound(AppError):
    status_code = 404
    detail = "Session not found"


class NotYourSession(AppError):
    status_code = 403
    detail = "This session belongs to another user"


class AlreadyMaxed(AppError):
    status_code = 400
    detail = "Already at max level"


class EscalationConflict(AppError):
    # 同一個 session 同時被升級兩次（連點按鈕），後到的那次放棄
    status_code = 409
    detail = "Session is being escalated by another request"


class RateLimited(AppError):
    status_code = 429
    detail = "Too many requests"


class LLMError(AppError):
    status_code = 502
    detail = "LLM request failed"
