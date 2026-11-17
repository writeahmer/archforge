"""
Tool definitions and registry for ArchForge.
Implements standard OpenAI function-calling schemas and execution handlers.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from archforge.agent.sandbox import ExecutionSandbox, SecurityError
from archforge.parsing.doc_parser import ParsedArchitecture
from archforge.parsing.plantuml_parser import ParsedViews


class ToolRegistry:
    """Manages tool schemas and execution within the sandboxed project workspace."""

    def __init__(
        self,
        sandbox: ExecutionSandbox,
        architecture: ParsedArchitecture,
        views: ParsedViews,
        todo_callback: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    ) -> None:
        self.sandbox = sandbox
        self.architecture = architecture
        self.views = views
        self.todo_callback = todo_callback
        self.finished = False
        self.finish_summary = ""

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns the OpenAI-compatible function schema definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_dir",
                    "description": "List files and directories in the project workspace relative to output directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subpath": {
                                "type": "string",
                                "description": "Subdirectory to list (defaults to project root).",
                                "default": "",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of an existing file in the project workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path to the file inside the project workspace.",
                            }
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write or overwrite a file in the project workspace. Parent directories are created automatically.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path to write the file in the workspace.",
                            },
                            "content": {
                                "type": "string",
                                "description": "The full text content to write into the file.",
                            },
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Perform an exact string replacement on an existing file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path of the file to modify.",
                            },
                            "target": {
                                "type": "string",
                                "description": "The exact string sequence to replace (must match existing file text exactly).",
                            },
                            "replacement": {
                                "type": "string",
                                "description": "The replacement string.",
                            },
                        },
                        "required": ["path", "target", "replacement"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_in_files",
                    "description": "Search for a regex or substring pattern across all files in the project workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Regex or text pattern to search for.",
                            },
                            "subpath": {
                                "type": "string",
                                "description": "Subdirectory to limit the search (optional).",
                                "default": "",
                            },
                        },
                        "required": ["pattern"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Execute an authorized test or build command (e.g. pytest, python -m ...) inside the project workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The command string to execute (e.g. 'pytest tests/ -v').",
                            }
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_architecture_section",
                    "description": "Inspect a specific section of Architecture_Documentation.md on demand (e.g. 'Section_F', 'openapi', 'proto', 'traceability', 'risks').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Section identifier or topic (e.g. 'Section_A', 'openapi', 'proto', 'sql', 'k8s', 'traceability').",
                            }
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_diagram",
                    "description": "Inspect a specific PlantUML diagram from Architecture_View.md (e.g. 'SpaceFractions_Classes', 'SpaceFractions_GameState', 'SpaceFractions_UseCase').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name or keyword of the diagram to retrieve.",
                            }
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_todo",
                    "description": "Update the execution plan / todo checklist displayed in the GUI.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "todos": {
                                "type": "array",
                                "description": "List of task items with 'id', 'task', and 'status' ('pending', 'in_progress', 'completed', 'failed').",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "task": {"type": "string"},
                                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "failed"]},
                                    },
                                    "required": ["id", "task", "status"],
                                },
                            }
                        },
                        "required": ["todos"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "finish",
                    "description": "Conclude the generation process and provide a final summary of completed deliverables.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Detailed summary of generated project architecture, tests, and consistency reconciliation.",
                            }
                        },
                        "required": ["summary"],
                    },
                },
            },
        ]

    def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Executes a tool call by name with validated arguments."""
        try:
            handler = getattr(self, f"_tool_{tool_name}", None)
            if not handler:
                return f"Error: Tool '{tool_name}' is not recognized."
            return handler(**args)
        except SecurityError as se:
            return f"Security Violation: {se}"
        except Exception as e:
            return f"Error executing {tool_name}: {e}"

    # Tool Implementations

    def _tool_list_dir(self, subpath: str = "") -> str:
        target_dir = self.sandbox.resolve_safe_path(subpath)
        if not target_dir.exists():
            return f"Directory does not exist: {subpath}"
        if not target_dir.is_dir():
            return f"Path is not a directory: {subpath}"

        items = []
        for p in sorted(target_dir.iterdir()):
            rel = p.relative_to(self.sandbox.root_dir).as_posix()
            items.append(f"{rel}/" if p.is_dir() else rel)

        return "\n".join(items) if items else "(directory is empty)"

    def _tool_read_file(self, path: str) -> str:
        target_file = self.sandbox.resolve_safe_path(path)
        if not target_file.exists():
            return f"File not found: {path}"
        if not target_file.is_file():
            return f"Path is a directory, not a file: {path}"

        content = target_file.read_text(encoding="utf-8", errors="replace")
        return content

    def _tool_write_file(self, path: str, content: str) -> str:
        target_file = self.sandbox.resolve_safe_path(path)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content, encoding="utf-8")
        byte_count = len(content.encode("utf-8"))
        return f"Successfully wrote {byte_count} bytes to {path}"

    def _tool_edit_file(self, path: str, target: str, replacement: str) -> str:
        target_file = self.sandbox.resolve_safe_path(path)
        if not target_file.exists():
            return f"File not found: {path}"

        content = target_file.read_text(encoding="utf-8")
        if target not in content:
            return f"Error: Target text not found in file {path}."

        count = content.count(target)
        new_content = content.replace(target, replacement)
        target_file.write_text(new_content, encoding="utf-8")
        return f"Successfully replaced {count} occurrence(s) in {path}"

    def _tool_search_in_files(self, pattern: str, subpath: str = "") -> str:
        base_dir = self.sandbox.resolve_safe_path(subpath)
        if not base_dir.exists():
            return f"Path not found: {subpath}"

        regex = re.compile(pattern, re.IGNORECASE)
        results = []

        for root, _, files in os.walk(base_dir):
            for file in files:
                file_path = Path(root) / file
                # Skip binary extensions
                if file_path.suffix.lower() in [".png", ".ico", ".pyc", ".db", ".sqlite", ".exe"]:
                    continue
                try:
                    rel = file_path.relative_to(self.sandbox.root_dir).as_posix()
                    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    for idx, line in enumerate(lines, 1):
                        if regex.search(line):
                            results.append(f"{rel}:{idx}: {line.strip()}")
                except Exception:
                    continue

        return "\n".join(results[:50]) if results else "No matches found."

    def _tool_run_command(self, command: str) -> str:
        code, stdout, stderr = self.sandbox.run_command(command)
        output = []
        if stdout:
            output.append(stdout.strip())
        if stderr:
            output.append(f"STDERR:\n{stderr.strip()}")
        output.append(f"[Exit code: {code}]")
        return "\n".join(output)

    def _tool_read_architecture_section(self, name: str) -> str:
        name_clean = name.strip().lower()
        if "openapi" in name_clean or "yaml" in name_clean:
            return self.architecture.openapi_raw or json.dumps(self.architecture.openapi, indent=2)
        if "proto" in name_clean:
            return json.dumps(self.architecture.proto, indent=2)
        if "sql" in name_clean or "ddl" in name_clean:
            return "\n\n".join(self.architecture.sql_ddl)
        if "k8s" in name_clean or "manifest" in name_clean:
            return self.architecture.k8s_raw
        if "trace" in name_clean:
            return json.dumps(self.architecture.traceability_matrix, indent=2)
        if "test" in name_clean:
            return json.dumps(self.architecture.testing_matrix, indent=2)

        # Look in section dictionary
        for sec_key, sec_val in self.architecture.sections.items():
            if name_clean in sec_key.lower():
                return f"### {sec_key}\n\n{sec_val}"

        return f"Section '{name}' not found. Available sections: {list(self.architecture.sections.keys())}"

    def _tool_read_diagram(self, name: str) -> str:
        name_clean = name.strip().lower()
        for diag in self.views.diagrams:
            if name_clean in diag.name.lower() or name_clean in diag.diagram_type.lower():
                return f"Diagram: {diag.name} ({diag.view_category} / {diag.diagram_type})\n\n```plantuml\n@startuml {diag.name}\n{diag.raw_uml}\n@enduml\n```"

        avail = [f"{d.name} ({d.diagram_type})" for d in self.views.diagrams]
        return f"Diagram '{name}' not found. Available diagrams:\n- " + "\n- ".join(avail)

    def _tool_update_todo(self, todos: List[Dict[str, Any]]) -> str:
        if self.todo_callback:
            self.todo_callback(todos)
        completed = sum(1 for t in todos if t.get("status") == "completed")
        return f"Updated todo list: {completed}/{len(todos)} items marked completed."

    def _tool_finish(self, summary: str) -> str:
        self.finished = True
        self.finish_summary = summary
        return "Generation concluded successfully."
