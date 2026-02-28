# ADR-0002: Use Google Calendar API (read-only) for agenda summaries
Status: Accepted
Date: 2026-02-28

## Decision
Integrate Google Calendar via OAuth with minimal scopes required for reading events.

## Consequences
- Token refresh handling required
- Agenda summaries become a reliable daily workflow anchor