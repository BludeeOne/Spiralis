"""
db.py — where Spiralis keeps things between visits

Everything before this lived in React state and disappeared on refresh. This
file sets up a small SQLite database so users and their saved songs stick
around.

WHY SQLITE
  - It's a single file (backend/spiralis.db), no server to install or run
  - Python ships with it, SQLAlchemy talks to it
  - Plenty for a capstone. If Spiralis ever goes live for real, set
    SPIRALIS_DB_URL to a Postgres URL and nothing else in the app changes

THE PIECES
  engine       the connection to the database file
  Base         every table class in models.py inherits from this
  get_db()     FastAPI dependency: opens a session per request, always closes it
  init_db()    creates any tables that don't exist yet, called on startup

Tables are created with create_all(), which only ADDS missing tables. It does
not change a table that already exists. If a column changes during
development, delete backend/spiralis.db and restart (or add Alembic later).
"""
import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "spiralis.db"
DATABASE_URL = os.getenv("SPIRALIS_DB_URL", f"sqlite:///{DEFAULT_PATH}")

#sqlite only lets the thread that opened a connection use it by default,
#FastAPI runs plain `def` routes in a threadpool so that check has to go
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401  (importing registers the tables on Base)

    Base.metadata.create_all(bind=engine)
