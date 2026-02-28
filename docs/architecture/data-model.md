# Data Model (v0.1)

## Tables

### profiles
- profile_id (pk)
- display_name
- role (admin|family)
- timezone
- created_at

### sessions
- session_id (pk)
- profile_id (fk)
- channel (cli|web|imessage)
- started_at

### events (append-only)
- event_id (pk)
- ts
- profile_id
- session_id
- event_type
- payload_json (redacted)

### tool_runs
- tool_run_id (pk)
- ts
- profile_id
- session_id
- tool_name
- input_json (redacted)
- output_json (summary)
- status (ok|error|timeout|approval_required)
- latency_ms

### approvals
- approval_id (pk)
- tool_run_id (fk)
- profile_id
- ts_requested
- ts_resolved
- status (pending|approved|denied)
- approval_context_json

## Indexes
- tool_runs(profile_id, ts desc)
- events(profile_id, ts desc)
- approvals(status, ts_requested desc)