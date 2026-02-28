# ADR-0001: Initial scope and safety model
Status: Accepted
Date: 2026-02-28

## Context
We are building an assistant that will eventually automate actions. Early safety and traceability are critical.

## Decision
Start with:
- CLI-first channel
- Postgres for events/tool_runs/approvals
- Read-only calendar tool
- Draft-only GitHub PR creation
- Sonos actions gated behind explicit approvals and guardrails

## Consequences
- Safer iteration and clearer debugging
- Slightly slower “wow factor” until execute automation matures