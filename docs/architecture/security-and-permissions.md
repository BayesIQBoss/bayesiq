# Security & Permissions (v0.1)

This document defines the security posture, permission model, and guardrails for the Personal Assistant system.

## Goals
- Prevent unapproved or unsafe actions (especially anything that mutates external systems).
- Ensure every action is traceable (auditable) and debuggable.
- Minimize blast radius via least privilege and allowlists.

## Non-goals (v0.1)
- Fully autonomous execution.
- Perfect isolation across multiple human users (family profiles are a later milestone).
- Advanced zero-trust / enterprise IAM.

---

## Permission Levels

### read_only
Tools that **must not** mutate external state.
- Examples: calendar agenda fetch, status queries, discovery/list endpoints.

### draft
Tools that may create artifacts but **do not** finalize or apply irreversible changes.
- Examples: create *draft* GitHub PRs, generate PR descriptions, generate patches locally.

### execute_gated
Tools that **mutate external state** but are:
- reversible or low-risk in practice, and
- protected by explicit approvals + guardrails.
- Examples: Sonos play/pause/volume changes.

> Note: A future `execute` level (without gating) is explicitly out of scope for v0.1.

---

## Policy Configuration Defaults

- **timezone:** America/Chicago
- **default execution mode:** read_only
- **approvals required:** all `execute_gated` tools require explicit approval

Reference config example: `config/policy.example.yaml` (copied to `config/policy.yaml` in real environments).

---

## Tool Policy

### Google Calendar (read_only)
- Namespace: `calendar.google.*`
- Mode: `read_only`

**Rules**
- No event creation, edits, deletes.
- No emailing attendees or messaging participants.
- Store only the metadata required to render an agenda (prefer redacted summaries in logs).

**Security notes**
- Use least-privilege OAuth scopes required for reading events.
- Refresh tokens must never appear in logs or persisted tool_run inputs/outputs.

---

### GitHub PR Creation (draft)
- Namespace: `github.pr.*`
- Mode: `draft`

**Allowlist**
- Allowed repos:
  - `YOUR_GITHUB_ORG_OR_USER/bayesiq`

**Rules**
- PRs created by the assistant must be **draft PRs** (`draft=true` enforced).
- No merge capability in v0.1.
- No pushes to `main` (or protected branches) in v0.1.
- Block any repo not in the allowlist and log a policy violation event.

**Security notes**
- Use least-privilege tokens/scopes.
  - Prefer tokens that can open PRs but do not have admin/org-level scopes.
- Never log tokens, auth headers, or raw API responses that include secrets.

---

### Sonos Control (execute_gated)
- Namespace: `sonos.*`
- Mode: `execute_gated`

**Allowlist**
- Allowed rooms:
  - Living Room
  - Dining Room
  - Kitchen

**Guardrails**
- Max volume cap: **40/100**
- Quiet hours: **disabled**
- Any execute operation must require an explicit approval step before applying.

**Rules**
- Discovery/list endpoints are allowed without approval (`sonos.discover` is read-like).
- State mutation endpoints require approval:
  - `sonos.play`, `sonos.pause`, `sonos.set_volume`, etc.
- Block requests targeting non-allowlisted rooms/speakers and log as policy violations.

**Security notes**
- Treat Sonos control as “physical-world adjacent.”
- Prefer explicit speaker targeting (speaker_id) over fuzzy room matching once discovered.

---

## Approval Workflow

### When approval is required
- Any tool call in mode `execute_gated`.
- Any tool call that would violate policy if executed without review.

### Approval mechanics (v0.1)
- Create an `approvals` row with status `pending`.
- Present a human-readable summary of the action:
  - tool name
  - target (speaker/repo)
  - parameters (e.g., volume)
  - policy checks (e.g., within max volume)
- Only execute after user approves.
- Record approval outcome (`approved`/`denied`) and timestamp.

### Deny behavior
- Do not execute.
- Record denial event and return a clean, user-friendly message.

---

## Secrets Management

### Requirements
- No secrets in git.
- No secrets printed to stdout in normal operation.
- No secrets persisted in DB logs.

### Storage approach
- Dev: environment variables or local secrets file outside repo.
- Prod (Mac mini): locked-down secrets file readable only by the service user (or macOS Keychain integration later).

### Redaction
A redaction layer must remove or hash:
- OAuth tokens / refresh tokens
- Authorization headers
- Cookies
- Any credential-like fields in tool inputs/outputs

Redaction must occur:
1) before writing `tool_runs.input_json`
2) before writing `tool_runs.output_json`
3) before writing `events.payload_json`
4) before emitting logs

---

## Auditability & Logging

### Append-only audit trail
- Every user message -> `events`
- Every tool call -> `tool_runs`
- Every approval request/decision -> `approvals` + `events`

### Minimum event types
- `message_received`
- `tool_called`
- `tool_succeeded`
- `tool_failed`
- `approval_requested`
- `approval_granted`
- `approval_denied`
- `policy_violation`

### Correlation IDs
- All entries should include `profile_id` and `session_id`.
- Tool runs should be referenced from approvals and relevant events via `tool_run_id`.

---

## Threats & Mitigations (v0.1)

### Token leakage
- Mitigation: strict redaction + least privilege + no raw dumps in logs.

### Unauthorized remote access
- Mitigation: Tailscale-first remote access; restrict inbound exposure; no public endpoints by default.

### Wrong-target actions (Sonos)
- Mitigation: room/speaker allowlist + explicit approvals + discover then pin speaker_id.

### Wrong-repo writes (GitHub)
- Mitigation: hard allowlist + draft-only enforcement + no merge capability.

### Prompt injection (future concern)
- v0.1 mitigation: tool allowlists + policy gates + approvals for execute.
- Future: content provenance + sandboxing + stronger validation on tool inputs.

---

## Testing Requirements (Security)
- Unit tests for:
  - policy evaluation (allowlist enforcement)
  - draft-only PR enforcement
  - Sonos max volume enforcement
  - redaction correctness (known secret patterns)
- Integration tests (when practical):
  - calendar read flow with expired token path
  - github draft PR creation in allowlisted repo
  - sonos discover + gated volume change