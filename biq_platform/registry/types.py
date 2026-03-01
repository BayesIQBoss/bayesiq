from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Literal, Optional


ToolMode = Literal["read_only", "draft", "execute_gated"]


@dataclass(frozen=True)
class ToolSpec:
    """Static tool metadata discovered from a manifest."""
    name: str                              # e.g. "calendar.google.get_agenda"
    mode: ToolMode                         # read_only | draft | execute_gated
    handler: str                           # e.g. "tools.calendar.tool:get_agenda"
    input_schema_path: Path                # absolute path to JSON schema
    output_schema_path: Optional[Path]     # absolute path to JSON schema (optional)
    description: str = ""                  # optional


@dataclass
class Tool:
    """Resolved, executable tool."""
    spec: ToolSpec
    fn: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
    # signature: fn(input_json, context) -> output_json