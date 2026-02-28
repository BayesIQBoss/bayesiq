# Tool Schemas (v0.1)

This document defines the JSON schemas for tool inputs/outputs. These schemas are **contracts** between:
- Agent Runtime (caller)
- Tool Gateway (executor)
- Connectors/Tools (implementations)

## Conventions

### Common envelope (recommended)
Tool Gateway SHOULD persist and (optionally) return responses using this envelope:

```json
{
  "status": "ok|error|timeout|approval_required",
  "tool_name": "string",
  "tool_version": "string",
  "request_id": "string",
  "data": {},
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  },
  "meta": {
    "fetched_at": "RFC3339 timestamp",
    "latency_ms": 1234,
    "source": "string"
  }
}