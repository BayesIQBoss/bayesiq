# Execution Lifecycle

## Purpose

This document defines the **execution lifecycle** for all assistant tool
operations within the BayesIQ Assistant Platform.

Every tool invocation follows a standardized lifecycle that guarantees:

- safety
- auditability
- observability
- recoverability
- deterministic behavior

This lifecycle acts as the operational contract between:

- tools
- policy engine
- gateway
- persistence layer
- operator interfaces

---

## High-Level Flow

All executions pass through the Gateway.

Tool Request

&darr;

ToolRun Created

&darr;

Policy Evaluation

&darr;

Approval (optional)

&darr;

Execution

&darr;

Validation

&darr;

Finalization

---

## Lifecycle States

A `tool_run` progresses through defined states stored in the
`tool_runs` table.

### 1. `started`

The execution request has been accepted by the Gateway.

At this stage:

- tool metadata is recorded
- input payload is persisted
- execution has not yet occurred

Created via:

`created_tool_run()`

Purpose:

- establishes audit record
- assigns unique execution identity
- enables later recovery

---

### 2. `approval_required`

The Policy Engine determined execution requires operator approval.

Typical causes:

- `execute_gated` tools
- potentially destructive actions
- real-world device control
- privileged mutations

System behavior:

- execution pauses
- approval record is created
- operator action is required

Database effects:

- row inserted into `approvals`
- `tool_runs.status` updated

Operator actions:

* assistant approvals
* assistant approve <approval_id>
* assistant deny <approval_id>

---

### 3. `approved` (implicit transition)

Approval resolution updates the approval record:

`approvals.status = approved`


Execution resumes through the Gateway using the originally
approved input payload.

Important:

Approval does **not** bypass policy entirely.
Policy is re-evaluated to enforce allowlists and safety limits.

---

### 4. `ok`

Execution completed successfully.

Characteristics:

- tool handler executed
- output validated against schema
- results persisted
- success event emitted

Database updates:

- output stored
- latency recorded
- lifecycle finalized

---

### 5. `error`

Execution failed due to:

- validation failure
- tool exception
- upstream API failure
- internal system error

Behavior:

- structured error stored
- execution finalized
- failure event logged

Errors are never silently discarded.

---

### 6. `timeout`

Execution exceeded allowed runtime.

Purpose:

Prevents indefinite blocking caused by:

- network stalls
- external APIs
- buggy tools

Timeouts finalize execution safely.

---

### 7. `denied`

Operator explicitly rejected execution.

Effects:

- approval marked denied
- tool execution never occurs
- audit event recorded

---

## State Transition Diagram

started

│

├──► approval_required ──► approved ──► ok

│ │

│ └────────► denied

│

├──► ok

├──► error

└──► timeout


---

## Persistence Model

### tool_runs

Represents execution lifecycle.

Stores:

- tool identity
- inputs
- outputs
- errors
- latency
- final status

A tool run is immutable once finalized.

---

### approvals

Represents human authorization events.

Stores:

- approval status
- associated tool_run
- approved payload
- timestamps

Approvals enable safe deferred execution.

---

### events

Append-only operational log.

Examples:

- `tool_called`
- `approval_requested`
- `approval_granted`
- `tool_succeeded`
- `tool_failed`

Events provide chronological system history.

---

## Execution Guarantees

The lifecycle guarantees:

### Deterministic Execution
Each tool run has a unique identity and recorded inputs.

### Auditability
All actions are persisted and reviewable.

### Safety
Dangerous operations require explicit approval.

### Recoverability
Paused executions may resume safely.

### Observability
System behavior can be reconstructed from logs.

---

## Design Principles

### Single Entry Point

All execution must occur through the Gateway.

Direct tool invocation is prohibited.

---

### Explicit State Transitions

Execution never moves implicitly between states.

Every transition is recorded.

---

### Fail Closed

If policy, validation, or execution fails,
the system defaults to non-execution.

---

### Human Override

Operators retain final authority over gated actions.

---

## Operational Examples

### Read-Only Tool

`assistant run calendar.google.get_agenda`

### Lifecycle:

started &rarr; ok

---

### Gated Tool

`assistant run sonos.set_volume`

### Lifecycle:

started &rarr; approval_required &rarr; approved &rarr; ok

---

### Failed Execution

`started &rarr; error`

---

## Future Extensions

This lifecycle enables future capabilities:

- scheduled execution
- retry policies
- background workers
- autonomous agents
- multi-step workflows
- distributed execution

No lifecycle redesign is required.

---

## Summary

The execution lifecycle transforms tool usage from
ad-hoc API calls into a controlled operational system.

The assistant operates as an execution platform rather
than a conversational interface.

This lifecycle is the foundation for safe autonomy.
