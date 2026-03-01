# Devlog — Gateway Transaction Boundary Refactor

**Date:** 2026-03-01
**Author:** BayesIQ
**Phase:** Assistant Platform — Phase 1
**PR Scope:** Execution lifecycle + approval persistence

---

## Summary

Today we refactored the assistant execution model to enforce a single transactional boundary owned by the application layer (CLI).

This change converts the assistant from a collection of tool invocations into a transactional execution platform capable of safe, resumable actions.

---

## Problem

Tool executions previously created database sessions across multiple layers:

* CLI
* Gateway
* Repository layer

This resulted in:

* approvals not persisting
* inconsistent commits
* detached SQLAlchemy instances
* non-deterministic execution state
* inability to resume approved actions

Execution state could silently disappear between processes.

---

## Decision

Adopt the invariant:

> **The caller owns the database transaction boundary.**

Rules introduced:

1. CLI opens the database session.
2. Gateway receives an injected session.
3. Repository performs persistence only.
4. Gateway never creates or commits sessions.
5. Exactly one commit occurs per command execution.

---

## Architectural Outcome

Execution now follows:

Tool Call
→ Policy Evaluation
→ Approval Persistence
→ ToolRun Finalization
→ Single Transaction Commit

This guarantees atomic execution state.

---

## New System Properties

* Tool executions are durable.
* Approval workflows persist across processes.
* Execution can be resumed safely.
* Full audit history exists.
* Gateway acts as orchestration runtime rather than executor.

---

## Key Insight

The assistant now behaves as a **state machine**, not a script runner.

This enables future capabilities:

* async execution workers
* background agents
* remote approvals
* web UI control surfaces
* scheduled automation
* multi-device assistant usage

---

## Lessons Learned

* Database ownership boundaries must be explicit.
* Hidden session creation causes systemic instability.
* Agent systems require transactional guarantees earlier than expected.

---

## Follow-Up Work

Phase 2:

* resumable execution (`run_approved`)
* execution replay
* async job model

---

## Status

✅ Phase 1 Complete
Assistant execution platform operational.
