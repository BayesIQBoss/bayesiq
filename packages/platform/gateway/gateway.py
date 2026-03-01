from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from packages.platform.errors import ErrorCode, ToolError
from packages.platform.policy import PolicyEngine
from packages.platform.registry.registry import ToolRegistry

from apps.agent.db.engine import db_session
from apps.agent.db import repo as dbrepo


@dataclass
class ToolResult:
    status: str  # ok|error|timeout|approval_required
    tool_name: str
    tool_version: str
    request_id: str
    data: Dict[str, Any]
    error: Optional[Dict[str, Any]]
    meta: Dict[str, Any]


class ToolGateway:
    """
    Single choke point for running tools safely.

    Responsibilities:
    - Discover tool
    - Validate input JSON against tool input schema
    - Policy evaluate (allow/deny/require_approval)
    - Execute tool handler with timeout (simple first pass)
    - Validate output (optional)
    - Return standardized result envelope
    """

    def __init__(
        self,
        registry: ToolRegistry,
        policy: PolicyEngine,
        default_timeout_ms: int = 10_000,
        tool_version: str = "v0.1",
    ):
        self.registry = registry
        self.policy = policy
        self.default_timeout_ms = default_timeout_ms
        self.tool_version = tool_version

    def run_tool(
        self,
        tool_name: str,
        input_json: Dict[str, Any],
        context: Dict[str, Any],
        timeout_ms: Optional[int] = None,
        validate_output: bool = True,
    ) -> ToolResult:
        request_id = str(uuid.uuid4())
        t0 = time.time()
        timeout_ms = timeout_ms or self.default_timeout_ms

        profile_id = context.get("profile_id", "unknown")
        session_id = context.get("session_id", "unknown")

        with db_session() as db:
            # Log that we received a tool call
            dbrepo.log_event(
                db,
                profile_id,
                session_id,
                "tool_called",
                {"tool_name": tool_name, "request_id": request_id},
            )

            # Create tool_run row early (audit even if we fail validation/policy)
            tool_run_id = dbrepo.create_tool_run(
                db,
                profile_id,
                session_id,
                request_id,
                tool_name,
                input_json=input_json,
                status="started",
            )

            # ---- Lookup tool ----
            try:
                tool = self.registry.get(tool_name)
            except Exception as e:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.NOT_FOUND,
                    message=f"Unknown tool '{tool_name}'",
                    details={"error": str(e)},
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "request_id": request_id, "error": res.error})
                return res

        # ---- Input validation ----
        try:
            input_schema = self.registry.get_input_schema(tool_name)
            Draft202012Validator(input_schema).validate(input_json)
        except JsonSchemaValidationError as ve:
            res = self._err(
                tool_name=tool_name,
                request_id=request_id,
                code=ErrorCode.VALIDATION_ERROR,
                message="Input validation failed",
                details={
                    "schema_id": input_schema.get("$id") if isinstance(input_schema, dict) else None,
                    "error": ve.message,
                    "path": [str(p) for p in ve.path],
                },
                latency_ms=self._ms_since(t0),
            )
            dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
            dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "request_id": request_id, "error": res.error})
            return res
        except Exception as e:
            res = self._err(
                tool_name=tool_name,
                request_id=request_id,
                code=ErrorCode.INTERNAL_ERROR,
                message="Failed to load/validate input schema",
                details={"error": str(e)},
                latency_ms=self._ms_since(t0),
            )
            dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
            dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "request_id": request_id, "error": res.error})
            return res

        # ---- Policy ----
        decision = self.policy.evaluate(tool.spec, input_json, context)

        if decision.decision == "deny":
            res = self._err(
                tool_name=tool_name,
                request_id=request_id,
                code=ErrorCode.POLICY_VIOLATION,
                message=decision.reason or "Policy denied tool execution",
                details=decision.details,
                latency_ms=self._ms_since(t0),
                status="error",
            )
            dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
            dbrepo.log_event(db, profile_id, session_id, "policy_violation", {"tool_name": tool_name, "request_id": request_id, "details": decision.details})
            return res

        if decision.decision == "require_approval":
            approval_payload = {
                "tool_name": tool_name,
                "mode": tool.spec.mode,
                "reason": decision.reason or "Approval required",
                "proposed_input": decision.sanitized_input,
            }
        
            # ✅ INSERT approval row
            approval_id = dbrepo.create_approval(
                db,
                tool_run_id,                 # this must be the string id returned by create_tool_run
                profile_id=profile_id,
                context=approval_payload,
            )

            res = ToolResult(
                status="approval_required",
                tool_name=tool_name,
                tool_version=self.tool_version,
                request_id=request_id,
                data={"approval_request": approval_payload, "approval_id": approval_id},
                error=None,
                meta={
                    "latency_ms": self._ms_since(t0),
                    "timeout_ms": timeout_ms,
                    "source": "gateway",
                },
            )
        
            # ✅ UPDATE tool_run row
            dbrepo.finalize_tool_run(
                db,
                tool_run_id,
                status="approval_required",
                output_json=res.data,
                error_json={},
                latency_ms=res.meta["latency_ms"],
            )
        
            dbrepo.log_event(
                db,
                profile_id,
                session_id,
                "approval_requested",
                {"tool_name": tool_name, "request_id": request_id, "approval_id": approval_id},
            )
        
            return res
        
        # ---- Execute ----
        try:
            out = tool.fn(decision.sanitized_input, context)
        except ToolError as te:
            res = self._err(
                tool_name=tool_name,
                request_id=request_id,
                code=te.code,
                message=te.message,
                details=te.details,
                latency_ms=self._ms_since(t0),
            )
            dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
            dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "request_id": request_id, "error": res.error})
            return res
        except Exception as e:
            res = self._err(
                tool_name=tool_name,
                request_id=request_id,
                code=ErrorCode.INTERNAL_ERROR,
                message="Tool execution failed",
                details={"error": str(e)},
                latency_ms=self._ms_since(t0),
            )
            dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
            dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "request_id": request_id, "error": res.error})
            return res

        elapsed_ms = self._ms_since(t0)
        if elapsed_ms > timeout_ms:
            res = self._err(
                tool_name=tool_name,
                request_id=request_id,
                code=ErrorCode.TIMEOUT,
                message=f"Tool exceeded timeout ({timeout_ms}ms)",
                details={"elapsed_ms": elapsed_ms},
                latency_ms=elapsed_ms,
                status="timeout",
            )
            dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, res.error or {}, elapsed_ms)
            dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "request_id": request_id, "error": res.error})
            return res

        # ---- Output validation ----
        if validate_output:
            try:
                out_schema = self.registry.get_output_schema(tool_name)
                if out_schema:
                    Draft202012Validator(out_schema).validate(out)
            except JsonSchemaValidationError as ve:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Output validation failed",
                    details={"error": ve.message, "path": [str(p) for p in ve.path]},
                    latency_ms=elapsed_ms,
                )
                dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, res.error or {}, elapsed_ms)
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "request_id": request_id, "error": res.error})
                return res
            except Exception as e:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Failed to load/validate output schema",
                    details={"error": str(e)},
                    latency_ms=elapsed_ms,
                )
                dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, res.error or {}, elapsed_ms)
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "request_id": request_id, "error": res.error})
                return res

        res = ToolResult(
            status="ok",
            tool_name=tool_name,
            tool_version=self.tool_version,
            request_id=request_id,
            data=out,
            error=None,
            meta={"latency_ms": elapsed_ms, "timeout_ms": timeout_ms, "source": "gateway"},
        )
        dbrepo.finalize_tool_run(db, tool_run_id, res.status, res.data, {}, elapsed_ms)
        dbrepo.log_event(db, profile_id, session_id, "tool_succeeded", {"tool_name": tool_name, "request_id": request_id})
        return res

    def run_approved(
    self,
    approval_id: str,
    context: Dict[str, Any],
    timeout_ms: Optional[int] = None,
    validate_output: bool = True,
) -> ToolResult:
        request_id = str(uuid.uuid4())
        t0 = time.time()
        timeout_ms = timeout_ms or self.default_timeout_ms

        profile_id = context.get("profile_id", "unknown")
        session_id = context.get("session_id", "unknown")

        from apps.agent.db.engine import db_session
        from apps.agent.db import repo as dbrepo

        with db_session() as db:
            ap = dbrepo.get_approval(db, approval_id)
            if ap is None:
                return self._err(
                    tool_name="approval.resolve",
                    request_id=request_id,
                    code=ErrorCode.NOT_FOUND,
                    message="Approval not found",
                    details={"approval_id": approval_id},
                    latency_ms=self._ms_since(t0),
                )

            if ap.status != "pending":
                return self._err(
                    tool_name="approval.resolve",
                    request_id=request_id,
                    code=ErrorCode.POLICY_VIOLATION,
                    message="Approval is not pending",
                    details={"approval_id": approval_id, "status": ap.status},
                    latency_ms=self._ms_since(t0),
                )

            tr = dbrepo.get_tool_run(db, ap.tool_run_id)
            if tr is None:
                return self._err(
                    tool_name="approval.resolve",
                    request_id=request_id,
                    code=ErrorCode.NOT_FOUND,
                    message="Tool run for approval not found",
                    details={"approval_id": approval_id, "tool_run_id": ap.tool_run_id},
                    latency_ms=self._ms_since(t0),
                )

            approval_request = (ap.approval_context_json or {})
            tool_name = approval_request.get("tool_name")
            proposed_input = approval_request.get("proposed_input", {})

            if not tool_name:
                return self._err(
                    tool_name="approval.resolve",
                    request_id=request_id,
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Malformed approval context (missing tool_name)",
                    details={"approval_id": approval_id},
                    latency_ms=self._ms_since(t0),
                )

            # Mark approval approved
            dbrepo.resolve_approval(db, approval_id, status="approved")
            dbrepo.log_event(db, profile_id, session_id, "approval_granted", {"approval_id": approval_id, "tool_name": tool_name})

            # Execute tool (we still validate input + output)
            # (We bypass policy "require approval" because approval is granted,
            # but we still enforce allowlists/caps by re-running policy and requiring it to not DENY.)
            try:
                tool = self.registry.get(tool_name)
            except Exception as e:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.NOT_FOUND,
                    message=f"Unknown tool '{tool_name}'",
                    details={"error": str(e)},
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res

            # Validate input schema
            try:
                input_schema = self.registry.get_input_schema(tool_name)
                Draft202012Validator(input_schema).validate(proposed_input)
            except JsonSchemaValidationError as ve:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Input validation failed (approved run)",
                    details={"error": ve.message, "path": [str(p) for p in ve.path]},
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res

            # Re-run policy; approved runs must not be DENIED (allowlists still enforced).
            decision = self.policy.evaluate(tool.spec, proposed_input, context)
            if decision.decision == "deny":
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.POLICY_VIOLATION,
                    message=decision.reason or "Policy denied approved execution",
                    details=decision.details,
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "policy_violation", {"tool_name": tool_name, "approval_id": approval_id, "details": decision.details})
                return res

            # Execute
            try:
                out = tool.fn(decision.sanitized_input, context)
            except ToolError as te:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=te.code,
                    message=te.message,
                    details=te.details,
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res
            except Exception as e:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Tool execution failed (approved run)",
                    details={"error": str(e)},
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res

            elapsed_ms = self._ms_since(t0)
            if elapsed_ms > timeout_ms:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.TIMEOUT,
                    message=f"Tool exceeded timeout ({timeout_ms}ms)",
                    details={"elapsed_ms": elapsed_ms},
                    latency_ms=elapsed_ms,
                    status="timeout",
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, elapsed_ms)
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res

            # Validate output schema
            if validate_output:
                try:
                    out_schema = self.registry.get_output_schema(tool_name)
                    if out_schema:
                        Draft202012Validator(out_schema).validate(out)
                except JsonSchemaValidationError as ve:
                    res = self._err(
                        tool_name=tool_name,
                        request_id=request_id,
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Output validation failed (approved run)",
                        details={"error": ve.message, "path": [str(p) for p in ve.path]},
                        latency_ms=elapsed_ms,
                    )
                    dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, elapsed_ms)
                    dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                    return res

            res = ToolResult(
                status="ok",
                tool_name=tool_name,
                tool_version=self.tool_version,
                request_id=request_id,
                data=out,
                error=None,
                meta={"latency_ms": elapsed_ms, "timeout_ms": timeout_ms, "source": "gateway"},
            )
            dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, {}, elapsed_ms)
            dbrepo.log_event(db, profile_id, session_id, "tool_succeeded", {"tool_name": tool_name, "approval_id": approval_id})
            return res

    def deny_approval(self, approval_id: str, context: Dict[str, Any]) -> None:
        from apps.agent.db.engine import db_session
        from apps.agent.db import repo as dbrepo

        profile_id = context.get("profile_id", "unknown")
        session_id = context.get("session_id", "unknown")

        with db_session() as db:
            ap = dbrepo.get_approval(db, approval_id)
            if ap and ap.status == "pending":
                dbrepo.resolve_approval(db, approval_id, status="denied")
                dbrepo.log_event(db, profile_id, session_id, "approval_denied", {"approval_id": approval_id})

    
    def run_approved(
        self,
        approval_id: str,
        context: Dict[str, Any],
        timeout_ms: Optional[int] = None,
        validate_output: bool = True,
    ) -> ToolResult:
        request_id = str(uuid.uuid4())
        t0 = time.time()
        timeout_ms = timeout_ms or self.default_timeout_ms

        profile_id = context.get("profile_id", "unknown")
        session_id = context.get("session_id", "unknown")

        from apps.agent.db.engine import db_session
        from apps.agent.db import repo as dbrepo

        with db_session() as db:
            ap = dbrepo.get_approval(db, approval_id)
            if ap is None:
                return self._err(
                    tool_name="approval.resolve",
                    request_id=request_id,
                    code=ErrorCode.NOT_FOUND,
                    message="Approval not found",
                    details={"approval_id": approval_id},
                    latency_ms=self._ms_since(t0),
                )

            if ap.status != "pending":
                return self._err(
                    tool_name="approval.resolve",
                    request_id=request_id,
                    code=ErrorCode.POLICY_VIOLATION,
                    message="Approval is not pending",
                    details={"approval_id": approval_id, "status": ap.status},
                    latency_ms=self._ms_since(t0),
                )

            tr = dbrepo.get_tool_run(db, ap.tool_run_id)
            if tr is None:
                return self._err(
                    tool_name="approval.resolve",
                    request_id=request_id,
                    code=ErrorCode.NOT_FOUND,
                    message="Tool run for approval not found",
                    details={"approval_id": approval_id, "tool_run_id": ap.tool_run_id},
                    latency_ms=self._ms_since(t0),
                )

            approval_request = ap.approval_context_json or {}
            tool_name = approval_request.get("tool_name")
            proposed_input = approval_request.get("proposed_input", {})

            if not tool_name:
                return self._err(
                    tool_name="approval.resolve",
                    request_id=request_id,
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Malformed approval context (missing tool_name)",
                    details={"approval_id": approval_id},
                    latency_ms=self._ms_since(t0),
                )

            # Mark approved
            dbrepo.resolve_approval(db, approval_id, status="approved")
            dbrepo.log_event(db, profile_id, session_id, "approval_granted", {"approval_id": approval_id, "tool_name": tool_name})

            # Tool lookup
            try:
                tool = self.registry.get(tool_name)
            except Exception as e:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.NOT_FOUND,
                    message=f"Unknown tool '{tool_name}'",
                    details={"error": str(e)},
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res

            # Validate input again
            try:
                input_schema = self.registry.get_input_schema(tool_name)
                Draft202012Validator(input_schema).validate(proposed_input)
            except JsonSchemaValidationError as ve:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Input validation failed (approved run)",
                    details={"error": ve.message, "path": [str(p) for p in ve.path]},
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res

            # Re-run policy; must not DENY (still enforce allowlists/caps)
            decision = self.policy.evaluate(tool.spec, proposed_input, context)
            if decision.decision == "deny":
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.POLICY_VIOLATION,
                    message=decision.reason or "Policy denied approved execution",
                    details=decision.details,
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "policy_violation", {"tool_name": tool_name, "approval_id": approval_id, "details": decision.details})
                return res

            # Execute
            try:
                out = tool.fn(decision.sanitized_input, context)
            except ToolError as te:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=te.code,
                    message=te.message,
                    details=te.details,
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res
            except Exception as e:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Tool execution failed (approved run)",
                    details={"error": str(e)},
                    latency_ms=self._ms_since(t0),
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, res.meta["latency_ms"])
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res

            elapsed_ms = self._ms_since(t0)
            if elapsed_ms > timeout_ms:
                res = self._err(
                    tool_name=tool_name,
                    request_id=request_id,
                    code=ErrorCode.TIMEOUT,
                    message=f"Tool exceeded timeout ({timeout_ms}ms)",
                    details={"elapsed_ms": elapsed_ms},
                    latency_ms=elapsed_ms,
                    status="timeout",
                )
                dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, elapsed_ms)
                dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                return res

            # Output validation
            if validate_output:
                try:
                    out_schema = self.registry.get_output_schema(tool_name)
                    if out_schema:
                        Draft202012Validator(out_schema).validate(out)
                except JsonSchemaValidationError as ve:
                    res = self._err(
                        tool_name=tool_name,
                        request_id=request_id,
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Output validation failed (approved run)",
                        details={"error": ve.message, "path": [str(p) for p in ve.path]},
                        latency_ms=elapsed_ms,
                    )
                    dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, res.error or {}, elapsed_ms)
                    dbrepo.log_event(db, profile_id, session_id, "tool_failed", {"tool_name": tool_name, "approval_id": approval_id, "error": res.error})
                    return res

            res = ToolResult(
                status="ok",
                tool_name=tool_name,
                tool_version=self.tool_version,
                request_id=request_id,
                data=out,
                error=None,
                meta={"latency_ms": elapsed_ms, "timeout_ms": timeout_ms, "source": "gateway"},
            )
            dbrepo.finalize_tool_run(db, tr.tool_run_id, res.status, res.data, {}, elapsed_ms)
            dbrepo.log_event(db, profile_id, session_id, "tool_succeeded", {"tool_name": tool_name, "approval_id": approval_id})
            return res


    @staticmethod
    def _ms_since(t0: float) -> int:
        return int((time.time() - t0) * 1000)

    def _err(
        self,
        tool_name: str,
        request_id: str,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]],
        latency_ms: int,
        status: str = "error",
    ) -> ToolResult:
        return ToolResult(
            status=status,
            tool_name=tool_name,
            tool_version=self.tool_version,
            request_id=request_id,
            data={},
            error={"code": code, "message": message, "details": details or {}},
            meta={"latency_ms": latency_ms, "source": "gateway"},
        )