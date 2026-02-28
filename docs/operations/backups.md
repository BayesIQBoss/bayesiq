# Backups (v0.1)

## What to back up
- Postgres database (events/tool_runs/approvals/profiles)
- Config (non-secret)
- Secrets (separately, securely)

## Strategy
- nightly pg_dump to encrypted storage
- keep 7 daily, 4 weekly, 6 monthly (tunable)