from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass(frozen=True)
class SonosPolicy:
    allowed_rooms: List[str]
    max_volume: int
    quiet_hours_enabled: bool

@dataclass(frozen=True)
class GitHubPolicy:
    allowed_repos: List[str]
    draft_only: bool
    allow_merge: bool
    allow_push_to_main: bool

@dataclass(frozen=True)
class ExecutionPolicy:
    default_mode: str
    approvals_required_for: List[str]

@dataclass(frozen=True)
class PolicyConfig:
    timezone: str
    execution: ExecutionPolicy
    github: Optional[GitHubPolicy]
    sonos: Optional[SonosPolicy]

def load_policy_config(path: Path) -> PolicyConfig:
    raw: Dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))

    tz = raw.get("timezone", "America/Chicago")

    exec_raw = raw.get("execution", {})
    execution = ExecutionPolicy(
        default_mode=exec_raw.get("default_mode", "read_only"),
        approvals_required_for=exec_raw.get("approvals_required_for", ["execute_gated"]),
    )

    tools_raw = raw.get("tools", {})

    gh_raw = tools_raw.get("github.pr")
    github = None
    if gh_raw:
        pr_rules = gh_raw.get("pr_rules", {})
        github = GitHubPolicy(
            allowed_repos=gh_raw.get("allowed_repos", []),
            draft_only=bool(pr_rules.get("draft_only", True)),
            allow_merge=bool(pr_rules.get("allow_merge", False)),
            allow_push_to_main=bool(pr_rules.get("allow_push_to_main", False)),
        )

    sonos_raw = tools_raw.get("sonos")
    sonos = None
    if sonos_raw:
        qh = sonos_raw.get("quiet_hours", {}) or {}
        sonos = SonosPolicy(
            allowed_rooms=sonos_raw.get("allowed_rooms", []),
            max_volume=int(sonos_raw.get("max_volume", 40)),
            quiet_hours_enabled=bool(qh.get("enabled", False)),
        )

    return PolicyConfig(
        timezone=tz,
        execution=execution,
        github=github,
        sonos=sonos,
    )