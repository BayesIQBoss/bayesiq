from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .types import Tool, ToolSpec, ToolMode


class ToolRegistryError(Exception):
    pass


def _import_handler(handler: str):
    """
    handler format: "module.path:callable_name"
    example: "packages.tools.calendar.tool:get_agenda"
    """
    if ":" not in handler:
        raise ToolRegistryError(f"Invalid handler '{handler}'. Expected 'module:callable'.")
    module_path, fn_name = handler.split(":", 1)
    mod = importlib.import_module(module_path)
    fn = getattr(mod, fn_name, None)
    if fn is None:
        raise ToolRegistryError(f"Handler '{handler}' not found.")
    return fn


def _load_json(p: Path) -> Dict[str, Any]:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


class ToolRegistry:
    """
    Discovers tools by scanning packages/tools/**/manifest.json.
    """
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.tools_root = repo_root / "packages" / "tools"
        self._tools: Dict[str, Tool] = {}

    def discover(self) -> None:
        if not self.tools_root.exists():
            raise ToolRegistryError(f"Tools root does not exist: {self.tools_root}")

        manifests = list(self.tools_root.glob("*/manifest.json"))
        for manifest_path in manifests:
            self._register_from_manifest(manifest_path)

    def _register_from_manifest(self, manifest_path: Path) -> None:
        tool_dir = manifest_path.parent
        manifest = _load_json(manifest_path)

        # Validate top-level manifest structure
        pkg = manifest.get("package")
        tools = manifest.get("tools", [])
        if not pkg or not isinstance(tools, list) or not tools:
            raise ToolRegistryError(f"Invalid manifest format: {manifest_path}")

        for t in tools:
            name = t["name"]
            mode: ToolMode = t["mode"]
            handler = t["handler"]
            description = t.get("description", "")

            # schemas are relative to tool_dir
            in_rel = t["schemas"]["input"]
            out_rel = t["schemas"].get("output")

            input_schema_path = (tool_dir / in_rel).resolve()
            output_schema_path = (tool_dir / out_rel).resolve() if out_rel else None

            if not input_schema_path.exists():
                raise ToolRegistryError(f"Missing input schema for {name}: {input_schema_path}")
            if output_schema_path and not output_schema_path.exists():
                raise ToolRegistryError(f"Missing output schema for {name}: {output_schema_path}")

            spec = ToolSpec(
                name=name,
                mode=mode,
                handler=handler,
                input_schema_path=input_schema_path,
                output_schema_path=output_schema_path,
                description=description,
            )

            fn = _import_handler(handler)

            # Enforce a standard callable signature (input_json, context) -> output_json
            # We'll rely on runtime usage to pass correct args.
            tool = Tool(spec=spec, fn=fn)

            if name in self._tools:
                raise ToolRegistryError(f"Duplicate tool name '{name}' from {manifest_path}")

            self._tools[name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolRegistryError(f"Unknown tool '{name}'. Did you call discover()?")
        return self._tools[name]

    def list(self) -> Dict[str, ToolSpec]:
        return {k: v.spec for k, v in self._tools.items()}

    def get_input_schema(self, name: str) -> Dict[str, Any]:
        tool = self.get(name)
        return _load_json(tool.spec.input_schema_path)

    def get_output_schema(self, name: str) -> Optional[Dict[str, Any]]:
        tool = self.get(name)
        if not tool.spec.output_schema_path:
            return None
        return _load_json(tool.spec.output_schema_path)