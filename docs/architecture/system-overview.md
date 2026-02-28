# System Overview (v0.1)

## Components
1) **Channel (CLI)**
- Accepts user input and renders responses

2) **Agent Runtime**
- Interprets intent
- Applies policy gates
- Calls tools via Tool Gateway
- Produces user-facing output

3) **Tool Gateway**
- Single entrypoint for all tool execution
- Enforces: timeouts, retries policy, redaction, logging, approvals

4) **Connectors / Tools**
- calendar.google (read-only)
- github.pr (draft-only)
- sonos.control (gated execute)

5) **Storage (Postgres)**
- append-only audit events
- tool run records
- approval records
- profiles/sessions

## Data flow
User -> CLI -> Agent Runtime
  -> (optional) Tool Gateway -> Connector
  -> persist events/tool_runs/approvals
  -> response to user

## Environments
- dev: laptop, local docker compose
- prod: Mac mini, always-on services, remote access