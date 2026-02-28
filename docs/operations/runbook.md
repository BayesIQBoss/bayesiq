# Runbook (v0.1)

## Common operations
- Start services
- Stop services
- Restart after crash
- Rotate tokens
- Verify health

## Health checks
- Postgres reachable
- Tool gateway responds
- Google token valid (refresh path works)
- GitHub token valid
- Sonos discovery works on LAN/VPN

## Incident response
1) Check logs + last tool_runs
2) Identify failing connector
3) Revoke/rotate tokens if needed
4) Restart service
5) Validate with a known-good command