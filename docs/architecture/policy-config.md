# Policy Config (v0.1)

This document defines the runtime policy configuration used to gate tools and enforce safety constraints.

## Defaults
- timezone: America/Chicago
- execution_mode: read_only (unless explicitly elevated per tool and approved)
- approvals_required_for: all execute_gated tools

## Sonos policy
- quiet_hours: disabled
- max_volume: 40 (0–100)
- allowed_rooms:
  - Living Room
  - Dining Room
  - Kitchen

## GitHub policy
- allowed_repos:
  - BayesIQBoss/bayesiq
- pr_rules:
  - draft_only: true
  - allow_merge: false
  - allow_push_to_main: false