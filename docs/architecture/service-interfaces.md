# Service Interfaces (v0.1)

## Tool Gateway API (internal)
`run_tool(tool_name: string, input: json, context: {profile_id, session_id}) -> output: json`

### Required behavior
- Validate `input` against tool schema
- Enforce timeout per tool
- Redact secrets in stored logs
- Write `tool_runs` record on completion
- If tool requires approval, create `approvals` record and return `approval_required`

## Tool schemas (contract-first)

### calendar.google.get_agenda
**Input**
- time_min (RFC3339)
- time_max (RFC3339)
- timezone (IANA)
**Output**
- events: [{ start, end, title, location?, attendees?, description? }]
- warnings: [{ type, message }]
- meta: { source: "google", fetched_at }

### github.pr.create_draft
**Input**
- repo (owner/name)
- base_branch
- head_branch
- title
- body
- draft (must be true)
**Output**
- pr_url
- pr_number
- head_branch
- base_branch
- meta: { source: "github", created_at }

### sonos.discover
**Output**
- speakers: [{ speaker_id, name, room, capabilities }]

### sonos.set_volume (gated)
**Input**
- speaker_id
- volume (0-100)
**Output**
- speaker_id
- previous_volume
- new_volume
- status