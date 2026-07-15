"""
Shared data layer for the WhatsApp Notes app.

Both the Streamlit UI (app.py) and the WhatsApp webhook (webhook.py) import
from here, so they read and write the same store.

The database is chosen by the DATABASE_URL environment variable:
  - Neon / any Postgres (recommended, always-on):
        postgresql://USER:PASS@HOST/db?sslmode=require
  - Local SQLite (fallback, PC-on-only):
        sqlite:///notes.db
If DATABASE_URL is unset it defaults to a local SQLite file so the app still
runs out of the box.
"""

import os
from datetime import datetime, timezone

# Load a local .env file if present (harmless in the cloud, where you set real
# environment variables in the host's dashboard instead).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip() or "sqlite:///notes.db"

# Neon and some hosts hand you a "postgresql://" (or "postgres://") URL, which
# SQLAlchemy tries to open with the old psycopg2 driver. Nudge it to psycopg 3.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

# SQLite needs this flag when touched from more than one thread
# (Streamlit and FastAPI both do).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,        # quietly reconnect if the pooled connection went stale
    connect_args=connect_args,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="whatsapp")
    sender: Mapped[str] = mapped_column(String(128), default="")       # e.g. whatsapp:+1...
    sender_name: Mapped[str] = mapped_column(String(128), default="")  # WhatsApp profile name
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    Base.metadata.create_all(engine)


# ---------------------------------------------------------------------------
# CRUD helpers — thin wrappers so both apps share identical logic.
# ---------------------------------------------------------------------------

def add_note(body, source="whatsapp", sender="", sender_name=""):
    body = (body or "").strip()
    if not body:
        raise ValueError("Empty note body")
    with SessionLocal() as s:
        note = Note(body=body, source=source, sender=sender, sender_name=sender_name)
        s.add(note)
        s.commit()
        s.refresh(note)
        return note


def list_notes(search="", pinned_only=False):
    with SessionLocal() as s:
        stmt = select(Note)
        if pinned_only:
            stmt = stmt.where(Note.pinned.is_(True))
        if search:
            stmt = stmt.where(func.lower(Note.body).like(f"%{search.lower()}%"))
        # Pinned first, then newest first.
        stmt = stmt.order_by(Note.pinned.desc(), Note.created_at.desc())
        return list(s.scalars(stmt).all())


def update_note(note_id, body=None, pinned=None):
    with SessionLocal() as s:
        note = s.get(Note, note_id)
        if not note:
            return
        if body is not None:
            note.body = body.strip()
        if pinned is not None:
            note.pinned = pinned
        s.commit()


def delete_note(note_id):
    with SessionLocal() as s:
        note = s.get(Note, note_id)
        if note:
            s.delete(note)
            s.commit()


def count_notes():
    with SessionLocal() as s:
        return s.scalar(select(func.count()).select_from(Note)) or 0
