import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent / "schemas"

with open(SCHEMA_DIR / "get_agenda.input.schema.json") as f:
    GET_AGENDA_INPUT_SCHEMA = json.load(f)

with open(SCHEMA_DIR / "get_agenda.output.schema.json") as f:
    GET_AGENDA_OUTPUT_SCHEMA = json.load(f)