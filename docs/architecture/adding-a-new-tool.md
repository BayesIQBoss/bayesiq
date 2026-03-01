# Adding a New Tool

## Purpose

This document defines the **standard process for adding new capabilities**
to the BayesIQ Assistant Platform.

All assistant functionality must be implemented as a Tool.

Direct API calls from agents or application code are prohibited.

---

## Core Principle

Capabilities are added through the platform — not around it.

❌ Assistant → API Call
✅ Assistant → Gateway → Tool

This guarantees:

- policy enforcement
- validation
- audit logging
- approval workflows
- execution consistency

---

## Tool Definition

A Tool represents a single executable capability.

Examples:

- `calendar.google.get_agenda`
- `github.pr.create`
- `sonos.set_volume`

Each tool contains:

- manifest
- input schema
- output schema
- handler implementation

---

## Directory Structure

All tools live under:

`packages/tools/`

Example:
* `packages/tools/calendar`
* `manifest.json`
* `tools.py`
* `schemas/`
* `get_agenda.input.schema.json`
* `get_agenda.output.schema.json`


---

## Step 1 — Define Tool Intent

Before writing code, answer:

- What action does this tool perform?
- Is it read-only or mutating?
- Could it cause real-world impact?
- Does it require approval?

Choose execution mode:

| Mode | Usage |
|------|------|
| `read_only` | Safe data retrieval |
| `draft` | Non-destructive mutation |
| `execute_gated` | Requires approval |

---

## Step 2 — Create Manifest

`manifest.json`

Example:

```json
{
  "package": "calendar",
  "tools": [
    {
      "name": "calendar.google.get_agenda",
      "mode": "read_only",
      "description": "Retrieve calendar events.",
      "handler": "biq_packages.tools.calendar.tool:get_agenda",
      "schemas": {
        "input": "schemas/get_agenda.input.schema.json",
        "output": "schemas/get_agenda.output.schema.json"
      }
    }
  ]
}
```

The manifest registers the tool with the Bayes IQ platform.


---

## Step 3 — Define Input Schema

Input schemas define allowed execution parameters.

Example:

```json
{
  "type": "object",
  "required": ["time_min", "time_max"],
  "properties": {
    "time_min": { "type": "string" },
    "time_max": { "type": "string" }
  }
}
```

#### Rules
* Reject unknown fields (additionalProperties: false)
* Prefer explicit typing
* Avoid optional ambiguity

Schemas are the primary safety boundary.

---

## Step 4 - Define Output Schema

Output schemas guarantee predictable responses.

Benefits:
* downstream stability
* agent reliability
* replay safety

All handlers must conform to declared output schema.

---

## Step 5 - Implement Handler

`tool.py`

Example:
```python
def get_agenda(input_json, context):
    ...
    return {
        "events": [],
        "meta": {...}
    }
```

Handler requirements:
* pure execution logic
* no policy decisions
* no direct database writes
* no approval logic

Handlers execute only business logic.

---

## Step 6 - Tool Discovery

Tools are automatically discovered by the Registry.

No manual registry required.

Verification:

```
assistant tools
```

(or registry smoke test)

---

## Step 7 - Policy Configuration

Update:

```
config/policy.yaml
```

Example:

```YAML
calendar.google:
  mode: read_only
```

Policy controls runtime permissions independently from tool implementation.

---

## Step 8 - Test Execution
Run locally:

```
assistant run <tool_name> '<json>'
```

Verify lifecycle:
```
started → ok
```

or

```
started → approval_required
```

---

## Step 9 - Approval Testing (if gated)

```
assistant approvals
assistant approve <approval_id>
```

Confirm execution finalizes correctly.

---
# Tool Design Guidelines
## Keep Tools Small

Each tool should perform one action only.

Bad:
```
github.manage_repository
```

Good:
```
github.pr.create
github.pr.merge
github.repo.list
```

---
## Prefer Deterministic Behavior
Tools should behave predictably given identical inputs.

Avoid hidden state.

---
## Fail Explicitly
Raise structured errors rather than returning partial results.

---
## Never Bypass Gateway
Do not call tools directly.

All execution must flow through:
```
Gateway → Policy → Execution
```

---
## Anti-Patterns
### ❌ Direct API Calls from Agent

Breaks auditability and safety.
---
### ❌ Policy Logic Inside Tools

Permissions belong to Policy Engine.
---
### ❌ Database Writes Inside Tools

Persistence belongs to Gateway layer.
---
### ❌ Multi-Purpose Tools

Leads to unclear approvals and risk escalation.

---

### Lifecycle Integration

All tools automatically inherit:
* schema validation
* approval workflows
* logging
* execution tracking
* timeout handling

No additional infrastructure required.
---
Summary

Adding a tool extends assistant capability without
modifying platform architecture.

The system scales by adding tools, not rewriting logic.

This separation allows safe long-term evolution
toward autonomous operation.
