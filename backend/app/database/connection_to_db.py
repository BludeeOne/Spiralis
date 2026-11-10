"""
db.py — im gonna make this the database file for spiralis

This file sets up the SQLite database used to store users and their
saved songs. Instead of keeping everything in React state, the database
lets that information stick around between visits.

SQLite works well here because it runs locally in a single file and
doesn't need a separate server. 

The main pieces are:

    engine       handles the connection to the database
    Base         parent class for the tables defined in models.py
    get_db()     opens a database session for each request and closes it
    init_db()    creates the tables when the application starts

create_all() only creates tables that don't already exist. It won't
update existing tables if we change their structure. 
"""

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DEFAULT_PATH = Path(__file__).resolve().parent.parent / "spiralis.db"
DATABASE_URL = os.getenv("SPIRALIS_DB_URL", f"sqlite:///{DEFAULT_PATH}")

# sqlite normally limits connections to the thread that created them
# fastapi can run sync routes in a threadpool, so disable the check
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # importing models registers their tables with Base
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
