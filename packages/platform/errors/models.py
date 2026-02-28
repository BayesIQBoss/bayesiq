from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class ToolError(Exception):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_json(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details or {},
        }