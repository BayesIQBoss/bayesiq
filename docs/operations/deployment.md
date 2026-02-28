# Deployment (v0.1)

## Dev (laptop)
- docker compose up (postgres)
- run agent CLI locally

## Prod (Mac mini)
- same compose file
- run agent/tool gateway as launchd service (or docker compose always-on)
- remote access via Tailscale