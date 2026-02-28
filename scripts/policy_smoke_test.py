from pathlib import Path

from packages.platform.registry.registry import ToolRegistry
from packages.platform.policy import PolicyEngine, load_policy_config

repo_root = Path(__file__).resolve().parents[1]

# Discover tools
reg = ToolRegistry(repo_root)
reg.discover()

# Load policy config
cfg = load_policy_config(repo_root / "config" / "policy.yaml")
policy = PolicyEngine(cfg)

# Evaluate calendar (should allow)
spec = reg.get("calendar.google.get_agenda").spec
decision = policy.evaluate(
    spec,
    {"time_min": "2026-02-28T00:00:00-06:00", "time_max": "2026-03-01T00:00:00-06:00", "timezone": "America/Chicago"},
    {"profile_id": "dev", "session_id": "dev"},
)
print("calendar decision:", decision.decision, decision.reason, decision.sanitized_input)