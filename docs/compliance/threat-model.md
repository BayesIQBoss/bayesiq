# Threat Model (v0.1)

## Assets
- OAuth tokens (Google, GitHub)
- Calendar data
- Repo write capabilities
- Sonos control

## Threats
- Token leakage via logs
- Unauthorized remote access
- Prompt injection leading to unsafe tool calls
- Overbroad OAuth scopes

## Mitigations
- redaction layer + secret scanning
- Tailscale for remote access
- tool allowlists + approvals for execute
- least-privilege scopes/tokens