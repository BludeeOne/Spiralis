"""
security.py — handles passwords and login sessions for Spiralis

This file is gonna be the way to maintin passwords and protections for users

Passwords are hashed with bcrypt before being stored in the database.
Bcrypt also adds a salt to each hash, so two accounts with the same
password will still have different stored values muhaha

Login sessions use random tokens stored in browser cookies. The database
only keeps a SHA-256 hash of each token, so the original token is never
stored alongside the user information.

The main pieces are:

    hash_password()     hashes a password before saving it
    verify_password()   checks a password against its stored hash
    create_session()    creates a new login session
    end_session()       removes a single login session
    end_all_sessions()  removes all sessions belonging to a user
    optional_user()     checks for a logged-in user, if one exists
    current_user()      requires a logged-in user

Sessions last 30 days and are stored in an httpOnly cookie. This feels long but google said im good

I use database-backed sessions instead of JWTs because removing a
session from the database immediately logs that browser out. It also
means we don't have to manage a separate signing key.

Bcrypt only processes the first 72 bytes of a password, so signup
rejects longer passwords rather than silently ignoring the extra bytes.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection_to_db import get_db
from app.database.models import AuthToken, User

COOKIE_NAME = "spiralis_session"
SESSION_DAYS = 30
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        # passwords over 72 bytes or invalid hashes are not a match
        return False


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def as_utc(dt: datetime) -> datetime:
    # sqlite returns datetimes without timezone information
    # the values were stored in utc, so we add it back here
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def create_session(db: Session, user: User) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)

    db.add(AuthToken(
        token_hash=_digest(token),
        user_id=user.id,
        expires_at=expires
    ))
    db.commit()

    return token, expires


def end_session(db: Session, token: str | None) -> None:
    if not token:
        return

    row = db.scalar(
        select(AuthToken).where(AuthToken.token_hash == _digest(token))
    )

    if row:
        db.delete(row)
        db.commit()


def end_all_sessions(db: Session, user: User, keep: str | None = None) -> None:
    # remove every session except the current browser, if requested
    keep_hash = _digest(keep) if keep else None

    for row in list(user.tokens):
        if row.token_hash != keep_hash:
            db.delete(row)

    db.commit()


def optional_user(
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User | None:
    # check whether the browser has a valid login session
    if not token:
        return None

    row = db.scalar(
        select(AuthToken).where(AuthToken.token_hash == _digest(token))
    )

    if row is None:
        return None

    if as_utc(row.expires_at) < datetime.now(timezone.utc):
        db.delete(row)
        db.commit()
        return None

    return row.user


def current_user(user: User | None = Depends(optional_user)) -> User:
    # some routes require an account before they can continue
    if user is None:
        raise HTTPException(401, "Not logged in")

    return user
