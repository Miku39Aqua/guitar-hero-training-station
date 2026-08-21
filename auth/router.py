"""认证相关 API 路由。"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from . import db
from .security import (
    create_access_token,
    get_current_user_id,
    get_password_hash,
    require_user,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8)
    email: EmailStr


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    existing = db.get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    password_hash = get_password_hash(req.password)
    user_id = db.create_user(req.username, req.email, password_hash)
    token = create_access_token(user_id, remember_me=False)
    return TokenResponse(
        access_token=token,
        expires_in=2 * 3600,
        user={"id": user_id, "username": req.username, "email": req.email},
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = db.get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    token = create_access_token(user["id"], remember_me=req.remember_me)
    expires_in = 7 * 24 * 3600 if req.remember_me else 2 * 3600
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user={"id": user["id"], "username": user["username"], "email": user["email"]},
    )


@router.get("/me", response_model=UserResponse)
def me(user_id: int = Depends(require_user)):
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"id": user["id"], "username": user["username"], "email": user["email"]}


@router.post("/logout")
def logout():
    return {"ok": True}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


def _send_reset_email(to_email: str, reset_url: str):
    """通过 SMTP 发送密码重置邮件。环境变量未配置时不执行。"""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT") or 587)
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    if not smtp_host or not smtp_user or not smtp_pass:
        return False

    try:
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(
            f"你好，\n\n请点击以下链接重置你的密码（1小时内有效）：\n{reset_url}\n\n"
            "如果你未请求重置密码，请忽略此邮件。",
            "plain",
            "utf-8",
        )
        msg["Subject"] = "吉他英雄训练站 - 密码重置"
        msg["From"] = smtp_user
        msg["To"] = to_email

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        return True
    except Exception:
        return False


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """请求密码重置。无论邮箱是否存在都返回相同提示，防止用户枚举。"""
    user = db.get_user_by_email(req.email)
    if user is None:
        return {"message": "如果该邮箱已注册，重置链接将发送至邮箱"}

    token = db.create_reset_token(user["id"])
    public_url = os.getenv("PUBLIC_URL", "http://localhost:8000")
    reset_url = f"{public_url}/?reset_token={token}"

    sent = _send_reset_email(req.email, reset_url)
    response: dict = {"message": "如果该邮箱已注册，重置链接将发送至邮箱"}
    # 开发环境未配置 SMTP 时，将链接返回给前端以便演示
    if not sent and os.getenv("DEBUG"):
        response["reset_url"] = reset_url
    return response


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    record = db.get_reset_token(req.token)
    if record is None:
        raise HTTPException(status_code=400, detail="无效或已过期的重置令牌")

    if record.get("used_at"):
        raise HTTPException(status_code=400, detail="重置令牌已使用")

    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="重置令牌已过期")

    password_hash = get_password_hash(req.new_password)
    db.update_user_password(record["user_id"], password_hash)
    db.mark_reset_token_used(req.token)
    return {"message": "密码已重置，请使用新密码登录"}
