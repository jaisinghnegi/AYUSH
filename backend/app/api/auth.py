from typing import Literal, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from app.auth.jwt_utils import create_access_token
from app.db import otp, users
from app.email.resend_client import send_otp_email

router = APIRouter(prefix="/auth")

Purpose = Literal["login", "register"]


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OtpRequestRequest(BaseModel):
    email: EmailStr
    purpose: Purpose = "login"


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    code: str
    purpose: Purpose = "login"


def _user_response(user: users.User) -> dict:
    return {"email": user.email, "name": user.name, "phone": user.phone}


@router.post("/register")
async def register(body: RegisterRequest) -> JSONResponse:
    existing = await users.get_user_by_email(body.email)
    if existing:
        return JSONResponse(
            status_code=409, content={"error": "An account with this email already exists"}
        )

    if len(body.password) < 8:
        return JSONResponse(
            status_code=400, content={"error": "Password must be at least 8 characters"}
        )

    user = await users.create_user(body.email, body.name, password=body.password, phone=body.phone)
    token = create_access_token(user.email)
    return JSONResponse({"token": token, "user": _user_response(user)})


@router.post("/login")
async def login(body: LoginRequest) -> JSONResponse:
    user = await users.get_user_by_email(body.email)
    if not user or not user.password_hash:
        return JSONResponse(status_code=401, content={"error": "Invalid email or password"})

    if not users.verify_password(body.password, user.password_hash):
        return JSONResponse(status_code=401, content={"error": "Invalid email or password"})

    await users.mark_logged_in(user.email)
    token = create_access_token(user.email)
    return JSONResponse({"token": token, "user": _user_response(user)})


@router.post("/otp/request")
async def otp_request(body: OtpRequestRequest) -> JSONResponse:
    existing = await users.get_user_by_email(body.email)

    if body.purpose == "login" and not existing:
        return JSONResponse(
            status_code=404, content={"error": "No account found with this email"}
        )
    if body.purpose == "register" and existing:
        return JSONResponse(
            status_code=409, content={"error": "An account with this email already exists"}
        )

    code = await otp.create_otp(body.email, body.purpose)
    delivered = await send_otp_email(body.email, code, body.purpose)

    return JSONResponse(
        {
            "message": "OTP sent" if delivered else "OTP generated (email delivery not configured -- check server logs)",
            "delivered": delivered,
        }
    )


@router.post("/otp/verify")
async def otp_verify(body: OtpVerifyRequest) -> JSONResponse:
    ok = await otp.verify_otp(body.email, body.purpose, body.code)
    if not ok:
        return JSONResponse(status_code=401, content={"error": "Invalid or expired code"})

    user = await users.get_user_by_email(body.email)

    if body.purpose == "register" and not user:
        name = body.email.split("@")[0]
        user = await users.create_user(body.email, name, password=None)

    if not user:
        return JSONResponse(status_code=404, content={"error": "No account found with this email"})

    await users.mark_logged_in(user.email)
    token = create_access_token(user.email)
    return JSONResponse({"token": token, "user": _user_response(user)})
