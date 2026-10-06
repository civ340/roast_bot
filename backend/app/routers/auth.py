# 後臺登入路由：帳密驗證、session cookie 簽發與登出
from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel
from app.db.database import get_pool
from app.services import auth

router = APIRouter()


class LoginPayload(BaseModel):
    username: str
    password: str


def _is_https(request: Request) -> bool:
    # nginx (frontend/nginx.conf) 用 $scheme 覆蓋這個 header，不是原樣轉發 client 帶的值，
    # 所以可以信任；本機直連 backend 沒有這個 header 時退回 request.url.scheme。
    forwarded = request.headers.get("x-forwarded-proto")
    scheme = forwarded.split(",")[0].strip() if forwarded else request.url.scheme
    return scheme == "https"


@router.post("/login")
async def login(payload: LoginPayload, request: Request, response: Response):
    pool = await get_pool()
    if not await auth.authenticate(pool, payload.username, payload.password):
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
