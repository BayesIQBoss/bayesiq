from __future__ import annotations

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session as DBSession

from .models import Event, ToolRun, Approval


def log_event(
    db: DBSession,
    profile_id: str,
    session_id: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    db.add(Event(
        profile_id=profile_id,
        session_id=session_id,
        event_type=event_type,
        payload_json=payload or {},
    ))


def create_tool_run(
    db: DBSession,
    profile_id: str,
    session_id: str,
    request_id: str,
    tool_name: str,
    input_json: Dict[str, Any],
    status: str = "started",
) -> str:
    tr = ToolRun(
        profile_id=profile_id,
        session_id=session_id,
        request_id=request_id,
        tool_name=tool_name,
        status=status,
        input_json=input_json,
        output_json={},
        error_json={},
        latency_ms=0,
    )
    db.add(tr)
    db.flush()  # assigns tool_run_id
    return tr.tool_run_id


def finalize_tool_run(
    db: DBSession,
    tool_run_id: str,
    status: str,
    output_json: Dict[str, Any],
    error_json: Dict[str, Any],
    latency_ms: int,
) -> None:
    tr: ToolRun = db.get(ToolRun, tool_run_id)
    tr.status = status
    tr.output_json = output_json or {}
    tr.error_json = error_json or {}
    tr.latency_ms = latency_ms


def create_approval(
    db: DBSession,
    tool_run_id: str,
    profile_id: str,
    context: Dict[str, Any],
) -> Approval:
    ap = Approval(
        tool_run_id=tool_run_id,
        profile_id=profile_id,
        status="pending",
        approval_context_json=context or {},
    )
    db.add(ap)
    db.flush()
    return ap