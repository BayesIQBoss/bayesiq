# Definition of Done (v0.1)

This checklist defines completion criteria for milestones M1–M4.

## M1 — Foundation: Docs + Storage + Tool Gateway + CLI scaffold
### Engineering
- [ ] Repo contains: PRD, architecture, ADRs, ops docs, threat model, privacy doc
- [ ] Postgres schema created for: profiles, sessions, events, tool_runs, approvals
- [ ] Tool Gateway implemented with:
  - [ ] per-tool timeout
  - [ ] structured input/output
  - [ ] status codes: ok|error|timeout|approval_required
  - [ ] redaction for secrets before persistence/logging
- [ ] CLI supports: start session, run command, render response
- [ ] “policy config” is loaded at runtime and affects behavior

### Quality
- [ ] Unit tests for: redaction, policy evaluation, schema validation
- [ ] A failing tool call produces a tool_runs record and a user-friendly error

### Ops
- [ ] Local dev: `docker compose up` starts Postgres
- [ ] Local dev: one command runs CLI against dev DB

---

## M2 — Google Calendar agenda end-to-end (read-only)
### Functionality
- [ ] OAuth configured and tokens stored securely (not in repo)
- [ ] `calendar.google.get_agenda(time_min,time_max,timezone)` implemented
- [ ] Agenda output includes:
  - [ ] chronological list
  - [ ] conflict detection (overlaps)
  - [ ] back-to-back warning (<= 5 min gaps)
- [ ] All calls are logged to tool_runs + events

### Quality
- [ ] Handles token refresh and expired tokens gracefully
- [ ] Timezone correctness validated for America/Chicago
- [ ] Timeout behavior is deterministic

---

## M3 — GitHub draft PR creation end-to-end (draft-only)
### Functionality
- [ ] Repo allowlist enforced (default only: YOUR_GITHUB_ORG_OR_USER/bayesiq)
- [ ] `github.pr.create_draft(...)` enforces `draft=true`
- [ ] PR output includes: PR URL, PR number, branches
- [ ] Agent flow supports:
  - [ ] branch naming convention
  - [ ] PR title/body template
  - [ ] checklist in PR body
- [ ] No merge capability exists in v0.1

### Quality & Safety
- [ ] Attempts to target non-allowlisted repo are blocked with an audit event
- [ ] Attempts to create non-draft PR are blocked and logged
- [ ] Token scopes are least-privilege (no admin unless needed)

---

## M4 — Sonos discovery + gated action end-to-end
### Functionality
- [ ] `sonos.discover` lists available speakers on LAN/VPN
- [ ] `sonos.set_volume` implemented with policy enforcement:
  - [ ] allowed rooms only (Living Room, Dining Room, Kitchen)
  - [ ] max volume cap 40/100
- [ ] Execute requires approval:
  - [ ] approval record created (pending)
  - [ ] CLI prompts user to approve/deny
  - [ ] on approve, tool executes and logs result
- [ ] “Wrong room” attempts are blocked and logged

### Quality
- [ ] Idempotency: repeated approve doesn’t double-apply (best-effort)
- [ ] Clear UX when speaker is not found/offline