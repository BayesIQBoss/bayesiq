from pathlib import Path

from biq_platform.registry.registry import ToolRegistry
from biq_platform.policy import PolicyEngine, load_policy_config
from biq_platform.gateway import ToolGateway

repo_root = Path(__file__).resolve().parents[1]

# registry
reg = ToolRegistry(repo_root)
reg.discover()

# policy
cfg = load_policy_config(repo_root / "config" / "policy.yaml")
policy = PolicyEngine(cfg)

# gateway
gw = ToolGateway(reg, policy)

# run calendar tool (should pass schema + allow + return ok)
res = gw.run_tool(
    "calendar.google.get_agenda",
    {
        "time_min": "2026-02-28T00:00:00-06:00",
        "time_max": "2026-03-01T00:00:00-06:00",
        "timezone": "America/Chicago"
    },
    {"profile_id": "dev", "session_id": "dev"},
)

print("status:", res.status)
print("error:", res.error)
print("data:", res.data)
print("meta:", res.meta)