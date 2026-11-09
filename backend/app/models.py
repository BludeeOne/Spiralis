"""
models.py — the database tables

Three tables:

  users        one row per account. Only the bcrypt HASH of the password is
               stored, never the password itself
  auth_tokens  one row per logged-in browser. The browser holds a random
               token in a cookie, the database holds the sha256 of it, so a
               leaked database can't be used to log in as anyone
  songs        a saved session: the chords you played (or typed), the key
               that was found, BPM, and where it came from

    users 1 ── * auth_tokens
    users 1 ── * songs

Deleting a user deletes their tokens and songs with them (cascade).
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tokens: Mapped[list["AuthToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    songs: Mapped[list["Song"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="tokens")


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(16), default="live")   # live | written | midi | upload
    key_name: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "G major"
    bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    chords: Mapped[list] = mapped_column(JSON, default=list)          # [{"name": "G", "numeral": "I"}, ...]
    notes: Mapped[str] = mapped_column(Text, default="")              # free text, lyrics, reminders
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="songs")
