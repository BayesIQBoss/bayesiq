# Local Development Runbook

This doc describes how to run the BayesIQ assistant locally in a repeatable way.

## Prereqs

- Python installed
- Virtual environment created and activated
- Repo root is the working directory for all commands

## Setup

### 1) Create/activate venv

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies (editable)

```bash
pip install -e .
```

## Database

### Canonical dev database location

Use a single absolute DB path to avoid "different process/different cwd"

Issues:

```bash
export DATABASE_URL="sqlite:///$PWD/.local/bayesiq_dev.db"
```

### Initialize database

```bash
rm -f .local/bayesiq_dev.db
python -m storage.db.init_db
```

### Quick sanity check: tables exist

```base
python - <<'PY'
import sqlite3, os
p=os.path.join(os.getcwd(), ".local", "bayesiq_dev.db")
con=sqlite3.connect(p); cur=con.cursor()
print([r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name")])
con.close()
PY
```

Expected tables include: `tool_runs`, `approvals`, `events`, `profiles`, `sessions`.

### CLI
The CLI is the operator interface for local development

#### Run a tool

```bash
python -m apps.assistant_cli.main run noop.execute '{"message":"hello", "count":3}'
```

Expected outcomes:
* `status: ok` for read_only/draft tools that execute immediately
* `status: approval_required` for execute_gated tools

#### List approvals

```bash
python -m apps.assistant_cli.main approvals
```

By default this lists `pending` approvals.

#### Approve an action

```bash
python -m apps.assistant_cli.main approve <APPROVAL_ID>
```


#### Deny an action

```bash
python -m apps.assistant_cli.main deny <APPROVAL_ID>
```

#### Smoke test: approvals end-to-end
1. Initialize DB:

```bash
export DATABASE_URL="sqlite:///$PWD/.local/bayesiq_dev.db"
rm -f .local/bayesiq_dev.db
python -m storage.db.init_db
```

2. Trigger a gated tool:

```bash
python -m apps.assistant_cli.main run noop.execute '{"message":"pr1-smoke", "count":2}'
```

Copy the printed `approval_id`.

3.  Confirm it appears:

```bash
python -m apps.assistant_cli.main approvals
```

4. Approve it:

```bash
python -m apps.assistant_cli.main approve <APPROVAL_ID>
```

5. Confirm resolution:

```bash
python -m apps.assistant_cli.main approvals <APPROVAL_ID>
```

#### Core Invariant (important)
* Apps (CLI/API) own the DB session boundary: they open with db_session() as db:
* Gateway never creates DB sessions
* Repo never commits
* One command execution should result in one transaction + one commit

If this invariant is violated, approvals/tool_runs may appear to “disappear” between processes.

#### Troubleshooting
“No approvals with status='pending'” but a tool returned approval_required

Run raw SQLite verification:

```bash
python - <<'PY'
import sqlite3, os
p=os.path.join(os.getcwd(), ".local", "bayesiq_dev.db")
con=sqlite3.connect(p); cur=con.cursor()
print("approvals:", cur.execute("select approval_id, status from approvals order by ts_requested desc limit 10").fetchall())
print("tool_runs:", cur.execute("select tool_name, status from tool_runs order by ts desc limit 10").fetchall())
con.close()
PY
```

If rows exist here but the CLI doesn’t show them, the CLI is likely:
* querying a different DB path, or
* filtering a different status value.

#### Want verbose SQL logs?

Temporarily set SQLAlchemy echo=True in storage/db/engine.py, reproduce the issue, then set it back to False.