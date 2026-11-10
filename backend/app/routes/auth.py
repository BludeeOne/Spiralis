"""
auth.py — handles signup, login, logout, and password changes

These routes handle the account side of Spiralis:

    POST /api/auth/signup    creates an account and starts a session
    POST /api/auth/login     logs in with a username or email
    POST /api/auth/logout    ends the current session
    GET  /api/auth/me        returns the currently logged-in user
    POST /api/auth/password  changes the account password

The frontend never needs to handle the session token directly. The
server sends it as an httpOnly cookie, and the browser includes it
automatically with each request.

Login errors use the same message whether the username or password
is wrong. This keeps the login form from revealing which accounts
actually exist.
"""

import re
from datetime import datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database.connection_to_db import get_db
from app.database.models import User
from app.security import (
    COOKIE_NAME,
    MAX_PASSWORD_BYTES,
    SESSION_DAYS,
    as_utc,
    create_session,
    current_user,
    end_all_sessions,
    end_session,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _check_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    if len(password.encode()) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")

    return password


class SignupIn(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def _username(cls, value: str) -> str:
        value = value.strip()

        if not USERNAME_RE.match(value):
            raise ValueError("Username must be 3–32 characters: letters, numbers, _ . -")

        return value

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        value = value.strip().lower()

        if not EMAIL_RE.match(value):
            raise ValueError("That doesn't look like an email address")

        return value

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return _check_password(value)


class LoginIn(BaseModel):
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)


class PasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: str) -> str:
        return _check_password(value)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("created_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return as_utc(value)


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=False,  # use True when running behind https
        path="/",
    )


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(body: SignupIn, response: Response, db: Session = Depends(get_db)):
    # check whether the username or email is already in use
    taken = db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == body.username.lower(),
                User.email == body.email
            )
        )
    )

    if taken:
        field = "username" if taken.username.lower() == body.username.lower() else "email"
        raise HTTPException(409, f"That {field} is already taken")

    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password)
    )

    db.add(user)
    db.commit()

    token, _ = create_session(db, user)
    _set_cookie(response, token)

    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    # usernames and emails are both accepted here
    who = body.login.strip().lower()

    user = db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == who,
                User.email == who
            )
        )
    )

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password")

    token, _ = create_session(db, user)
    _set_cookie(response, token)

    return user


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
):
    end_session(db, token)
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/password", status_code=204)
def change_password(
    body: PasswordIn,
    user: User = Depends(current_user),
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is wrong")

    user.password_hash = hash_password(body.new_password)

    db.add(user)
    db.commit()

    # log out other browsers but keep the current session
    end_all_sessions(db, user, keep=token)
