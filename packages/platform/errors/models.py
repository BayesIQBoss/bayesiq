from pydantic import BaseModel
from typing import Dict, Any


class ToolError(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = {}