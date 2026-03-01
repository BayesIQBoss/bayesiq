from __future__ import annotations

from typing import Any, Dict


def get_agenda(input_json: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stub implementation for now.
    Signature is standardized for all tools:
      - input_json: validated later by gateway against schema
      - context: {profile_id, session_id, ...}
    """
    # TODO: implement Google Calendar API call later.
    return {
        "events": [],
        "warnings": [
            {"type": "other", "message": "Stub: calendar tool not implemented yet", "event_ids": []}
        ],
        "meta": {"source": "google_calendar", "fetched_at": "1970-01-01T00:00:00Z"}
    }