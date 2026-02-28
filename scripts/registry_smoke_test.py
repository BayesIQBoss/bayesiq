from pathlib import Path
from packages.platform.registry.registry import ToolRegistry

repo_root = Path(__file__).resolve().parents[1]
r = ToolRegistry(repo_root)
r.discover()

print("Discovered tools:")
for name, spec in r.list().items():
    print("-", name, spec.mode, spec.handler)

tool = r.get("calendar.google.get_agenda")
out = tool.fn(
    {"time_min": "2026-02-28T00:00:00-06:00", "time_max": "2026-03-01T00:00:00-06:00", "timezone": "America/Chicago"},
    {"profile_id": "dev", "session_id": "dev"}
)
print("Tool output:", out)