from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.platform.registry.registry import ToolRegistry
from packages.platform.policy import PolicyEngine, load_policy_config
from packages.platform.gateway import ToolGateway

from apps.agent.db.engine import db_session
from apps.agent.db import repo as dbrepo


def make_gateway() -> ToolGateway:
    repo_root = Path(__file__).resolve().parents[2]  # apps/agent/cli.py -> repo root
    reg = ToolRegistry(repo_root)
    reg.discover()

    cfg = load_policy_config(repo_root / "config" / "policy.yaml")
    policy = PolicyEngine(cfg)

    return ToolGateway(reg, policy)


def default_context() -> dict:
    # v0.1: hardcode dev identity
    return {"profile_id": "dev", "session_id": "dev", "channel": "cli"}


def cmd_run(args):
    gw = make_gateway()
    ctx = default_context()

    payload = json.loads(args.json)
    res = gw.run_tool(args.tool, payload, ctx)

    print("status:", res.status)
    if res.error:
        print("error:", res.error)
    print("data:", res.data)
    print("meta:", res.meta)

    if res.status == "approval_required":
        print("\napproval_id:", res.data.get("approval_id"))


def cmd_approve(args):
    gw = make_gateway()
    ctx = default_context()

    res = gw.run_approved(args.approval_id, ctx)

    print("status:", res.status)
    if res.error:
        print("error:", res.error)
    print("data:", res.data)
    print("meta:", res.meta)


def cmd_deny(args):
    gw = make_gateway()
    ctx = default_context()

    gw.deny_approval(args.approval_id, ctx)
    print("denied:", args.approval_id)


def cmd_approvals(args):
    with db_session() as db:
        aps = dbrepo.list_approvals(db, status=args.status, limit=args.limit)

    if not aps:
        print(f"No approvals with status='{args.status}'.")
        return

    for ap in aps:
        ctx = ap.approval_context_json or {}
        print(
            f"- approval_id={ap.approval_id} status={ap.status} requested={ap.ts_requested} "
            f"tool={ctx.get('tool_name')} reason={ctx.get('reason')}"
        )


def main():
    p = argparse.ArgumentParser(prog="assistant")
    sub = p.add_subparsers(dest="cmd", required=True)

    runp = sub.add_parser("run", help="Run a tool with JSON input (may require approval).")
    runp.add_argument("tool", help="Tool name, e.g. calendar.google.get_agenda")
    runp.add_argument("json", help='JSON payload, e.g. \'{"time_min":"...","time_max":"...","timezone":"America/Chicago"}\'')
    runp.set_defaults(func=cmd_run)

    ap = sub.add_parser("approve", help="Approve and execute a pending approval_id.")
    ap.add_argument("approval_id")
    ap.set_defaults(func=cmd_approve)

    dn = sub.add_parser("deny", help="Deny a pending approval_id.")
    dn.add_argument("approval_id")
    dn.set_defaults(func=cmd_deny)

    ls = sub.add_parser("approvals", help="List approvals.")
    ls.add_argument("--status", default="pending", choices=["pending", "approved", "denied"])
    ls.add_argument("--limit", type=int, default=20)
    ls.set_defaults(func=cmd_approvals)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()