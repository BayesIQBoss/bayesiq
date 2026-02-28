from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, DateTime, Integer, ForeignKey, Text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"

    profile_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="admin")
    timezone: Mapped[str] = mapped_column(String(64), default="America/Chicago")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(64), ForeignKey("profiles.profile_id"))
    channel: Mapped[str] = mapped_column(String(32), default="cli")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)

    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ToolRun(Base):
    __tablename__ = "tool_runs"

    tool_run_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)

    request_id: Mapped[str] = mapped_column(String(64), index=True)
    tool_name: Mapped[str] = mapped_column(String(256), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)  # ok|error|timeout|approval_required

    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_json: Mapped[dict] = mapped_column(JSON, default=dict)

    latency_ms: Mapped[int] = mapped_column(Integer, default=0)


class Approval(Base):
    __tablename__ = "approvals"

    approval_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tool_run_id: Mapped[str] = mapped_column(String(64), ForeignKey("tool_runs.tool_run_id"), index=True)

    profile_id: Mapped[str] = mapped_column(String(64), index=True)

    ts_requested: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ts_resolved: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending|approved|denied
    approval_context_json: Mapped[dict] = mapped_column(JSON, default=dict)