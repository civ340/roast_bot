# 後臺登入路由：帳密驗證、session cookie 簽發與登出
from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel, Field
from app.db.database import get_pool
from app.services import auth

router = APIRouter()


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


def _is_https(request: Request) -> bool:
    # nginx (frontend/nginx.conf) 會帶 X-Forwarded-Proto：前面還有一層終結 TLS 的反向代理時
    # 沿用那一層帶來的值，否則用 nginx 自己看到的 scheme。本機直連 backend 沒有這個 header 時
    # 退回 request.url.scheme。
    # 這個值只用來決定 cookie 要不要加 Secure，client 自己偽造也只會影響到自己的 cookie。
    forwarded = request.headers.get("x-forwarded-proto")
    scheme = forwarded.split(",")[0].strip() if forwarded else request.url.scheme
    return scheme == "https"


def _client_ip(request: Request) -> str:
    # nginx 會用 X-Real-IP 帶真正的來源 IP；本機直連 backend 時退回連線本身的位址
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


@router.post("/login")
async def login(payload: LoginPayload, request: Request, response: Response):
    pool = await get_pool()
    try:
        ok = await auth.authenticate(pool, payload.username, payload.password, _client_ip(request))
    except auth.TooManyAttempts:
        raise HTTPException(status_code=429, detail="登入失敗次數過多，請 15 分鐘後再試")
    if not ok:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = await auth.create_session(pool, payload.username)
    response.set_cookie(
        auth.SESSION_COOKIE, token,
        httponly=True, samesite="lax", max_age=auth.SESSION_TTL_SECONDS,
        secure=_is_https(request),
    )
    return {"username": payload.username}


@router.post("/logout")
async def logout(request: Request, response: Response):
    pool = await get_pool()
    await auth.revoke_session(pool, request.cookies.get(auth.SESSION_COOKIE))
    response.delete_cookie(auth.SESSION_COOKIE)
    return {"ok": True}


@router.get("/me")
async def me(request: Request):
    pool = await get_pool()
    username = await auth.get_session_username(pool, request.cookies.get(auth.SESSION_COOKIE))
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"username": username}
