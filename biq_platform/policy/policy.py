from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from biq_platform.registry.types import ToolSpec
from biq_platform.policy.types import PolicyDecision
from biq_platform.policy.config import PolicyConfig


class PolicyEngine:
    """
    Evaluates whether a tool call is allowed, denied, or requires approval.
    This is the single choke point for safety decisions.
    """

    def __init__(self, config: PolicyConfig):
        self.config = config

    def evaluate(
        self,
        tool_spec: ToolSpec,
        input_json: Dict[str, Any],
        context: Dict[str, Any],
    ) -> PolicyDecision:
        name = tool_spec.name
        mode = tool_spec.mode

        # Default decision by mode:
        # - read_only: allow
        # - draft: allow
        # - execute_gated: require approval
        if mode == "read_only":
            return PolicyDecision("allow", sanitized_input=input_json)

        if mode == "draft":
            # Additional per-tool constraints can be checked here.
            if name.startswith("github.pr."):
                return self._eval_github_pr(tool_spec, input_json, context)
            return PolicyDecision("allow", sanitized_input=input_json)

        if mode == "execute_gated":
            # Per-tool enforcement + approval
            if name.startswith("sonos."):
                return self._eval_sonos(tool_spec, input_json, context)
            return PolicyDecision(
                "require_approval",
                sanitized_input=input_json,
                reason="execute_gated tool requires approval",
            )

        # Unknown mode -> deny
        return PolicyDecision(
            "deny",
            sanitized_input=input_json,
            reason=f"Unknown tool mode '{mode}'",
            details={"tool": name, "mode": mode},
        )

    def _eval_github_pr(
        self,
        tool_spec: ToolSpec,
        input_json: Dict[str, Any],
        context: Dict[str, Any],
    ) -> PolicyDecision:
        gh = self.config.github
        if gh is None:
            return PolicyDecision("deny", input_json, reason="GitHub policy not configured")

        repo = input_json.get("repo")
        if repo not in gh.allowed_repos:
            return PolicyDecision(
                "deny",
                input_json,
                reason="Repo not allowlisted",
                details={"repo": repo, "allowed_repos": gh.allowed_repos},
            )

        # Enforce draft-only regardless of caller.
        if gh.draft_only:
            if input_json.get("draft") is not True:
                sanitized = dict(input_json)
                sanitized["draft"] = True
                return PolicyDecision(
                    "allow",
                    sanitized_input=sanitized,
                    reason="Enforced draft-only PR creation",
                    details={"repo": repo},
                )

        # Merging is out of scope; if you ever add merge tools, deny here.
        return PolicyDecision("allow", sanitized_input=input_json)

    def _eval_sonos(
        self,
        tool_spec: ToolSpec,
        input_json: Dict[str, Any],
        context: Dict[str, Any],
    ) -> PolicyDecision:
        s = self.config.sonos
        if s is None:
            return PolicyDecision("deny", input_json, reason="Sonos policy not configured")

        # Allow discovery without approval if you model it as read-like tool later.
        # For now, sonos.* is execute_gated so require approval.

        sanitized = dict(input_json)

        # Room allowlist (support either room or speaker_id input styles)
        room = sanitized.get("room")
        if room is not None and room not in s.allowed_rooms:
            return PolicyDecision(
                "deny",
                sanitized,
                reason="Room not allowlisted",
                details={"room": room, "allowed_rooms": s.allowed_rooms},
            )

        # Volume cap enforcement (if present)
        if "volume" in sanitized and sanitized["volume"] is not None:
            try:
                v = int(sanitized["volume"])
            except Exception:
                return PolicyDecision(
                    "deny",
                    sanitized,
                    reason="Invalid volume type",
                    details={"volume": sanitized.get("volume")},
                )

            if v > s.max_volume:
                sanitized["volume"] = s.max_volume
                return PolicyDecision(
                    "require_approval",
                    sanitized_input=sanitized,
                    reason="Requested volume exceeds cap; capped and requires approval",
                    details={"requested": v, "capped_to": s.max_volume},
                )

        return PolicyDecision(
            "require_approval",
            sanitized_input=sanitized,
            reason="Sonos actions require approval",
        )