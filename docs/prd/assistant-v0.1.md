# Personal Assistant PRD (v0.1)

## 1) One-liner
An always-on personal assistant that summarizes my day from Google Calendar, controls Sonos speakers with explicit approval, and creates GitHub draft PRs from specs—while keeping actions safe, auditable, and reversible.

## 2) Users
- Primary: Me (admin)
- Secondary: Family members (future milestone; separate profiles)

## 3) Jobs to be done (JTBD)

### JTBD-1: Calendar Summary (Read-only)
**Trigger:** On demand + scheduled daily run  
**Input:** time range (default: today), timezone  
**Output:** agenda with conflicts, back-to-back blocks, travel buffers, prep notes  
**Success:** <60 seconds to read; no missed meetings; consistent formatting

### JTBD-2: Sonos Control (Execute, gated)
**Trigger:** Explicit user command  
**Input:** room/speaker, action (play/pause/volume), content target  
**Output:** confirmation of device + action taken + resulting state  
**Success:** does not play in wrong room; respects quiet hours and volume caps

### JTBD-3: Create Pull Requests (Draft-only)
**Trigger:** “Turn this spec into a PR”  
**Input:** repo allowlist, base branch, spec (text or file)  
**Output:** local branch + commits + draft PR (title/body/checklist)  
**Success:** PR is reviewable; no merges; no writes outside allowlisted repos

## 4) Non-goals (v0.1)
- Autonomous execution without approval
- Merging PRs
- Sending emails/messages automatically
- Financial transactions
- Voice interface

## 5) Product principles
- Safe by default (read-only first; approvals for execute)
- Deterministic tool boundaries (structured inputs/outputs)
- Auditability (append-only event log for actions/tool runs)
- Minimal magic (predictable flows beat cleverness)

## 6) Requirements

### Functional
- CLI interface (v0.1 channel)
- Tool gateway with: timeout, retries (safe), redaction, logging
- Google Calendar connector (read-only)
- GitHub connector (create draft PR)
- Sonos connector (discover + one action path)
- Persistent storage: profiles, sessions, events, tool_runs, approvals

### Non-functional
- Reliability: recover on restart; idempotent tool calls where possible
- Security: secrets never in repo; least-privilege OAuth scopes/tokens
- Observability: structured logs + DB tool_runs; per-tool latency
- Latency: agenda response feels interactive; tool calls time out cleanly

## 7) Success metrics (v0.1)
- Weekly usage: ≥5 days/week
- Time saved: ≥10 min/day from calendar summary + reduced context switching
- Safety: 0 unapproved execute actions; 0 non-allowlisted repo writes
- Quality: ≤1 “wrong room / wrong volume / missed meeting” incident per month

## 8) Risks / failure modes
- Stale calendar data (token expiry / sync issue)
- Wrong speaker target
- PR created against wrong base branch
- Prompt injection (later) from web content used in PR text
- Logging leaks secrets if redaction is incomplete

## 9) Milestones
- M1: Docs + Postgres schema + tool gateway skeleton + CLI scaffolding
- M2: Google Calendar agenda end-to-end
- M3: GitHub draft PR creation end-to-end (allowlist)
- M4: Sonos discover + gated action end-to-end (quiet hours + caps)
- M5: Scheduler for daily briefing (optional, after mini arrives)

## 10) Open questions
- Family profiles: shared vs isolated memory? (default: isolated)
- Remote access: Tailscale-first vs Cloudflare tunnel (likely Tailscale-first)
- Where to store “tasks/todos” for briefing (file vs DB vs external)