from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

DecisionType = Literal["allow", "deny", "require_approval"]

@dataclass(frozen=True)
class PolicyDecision:
    decision: DecisionType
    # sanitized_input may be modified (e.g., cap volume)
    sanitized_input: Dict[str, Any]
    reason: Optional[str] = None
    # for audit/debugging
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            object.__setattr__(self, "details", {})