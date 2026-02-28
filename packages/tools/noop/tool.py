from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def execute(input_json: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    message = input_json["message"]
    count = int(input_json.get("count", 1))

    return {
        "echo": [message] * count,
        "meta": {
            "source": "noop",
            "applied_at": datetime.now(timezone.utc).isoformat(),
        },
    }