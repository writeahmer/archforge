"""
Context engineering and token budget management for ArchForge.
Summarizes input documents and truncates old tool results to prevent context blowout.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from archforge.parsing.doc_parser import ParsedArchitecture
from archforge.parsing.plantuml_parser import ParsedViews
from archforge.parsing.validator import ConsistencyIssue

MAX_TOOL_OUTPUT_CHARS = 4000
MAX_HISTORY_MESSAGES = 60


def build_compact_summary(
    doc: ParsedArchitecture,
    views: ParsedViews,
    issues: List[ConsistencyIssue],
) -> str:
    """
    Constructs a concise, high-level summary of the architecture and views.
    Detailed sections and diagrams are retrieved on demand via tools.
    """
    comp_names = [c.get("name", "Unknown") for c in doc.components]
    diag_catalog = [f"{d.name} ({d.view_category}: {d.diagram_type})" for d in views.diagrams]

    high_issues = [f"[{i.category}] {i.summary}" for i in issues if i.severity == "HIGH"]
    med_issues = [f"[{i.category}] {i.summary}" for i in issues if i.severity == "MEDIUM"]

    summary_lines = [
        f"# Project: {doc.title or 'Software Architecture'}",
        f"**Executive Intent**: {doc.executive_summary[:350]}...",
        "",
        "## Discovered Components in Architecture Doc:",
        f"- {', '.join(comp_names) if comp_names else 'None detailed explicitly'}",
        "",
        "## Available PlantUML Views (4+1):",
        "- " + "\n- ".join(diag_catalog[:10]),
        "",
        "## Key Consistency Validator Findings to Reconcile:",
        f"- High Severity: {', '.join(high_issues) if high_issues else 'None'}",
        f"- Medium Severity: {', '.join(med_issues) if med_issues else 'None'}",
        "",
        "## Persistence & Contracts Available:",
        f"- OpenAPI endpoints: {len(doc.openapi.get('paths', {}))} routes defined in spec",
        f"- Proto Services: {len(doc.proto.get('services', []))} services defined",
        f"- SQL Tables: {', '.join(doc.sql_tables) if doc.sql_tables else 'None'}",
        f"- Kubernetes Manifest: {len(doc.k8s_manifest)} workloads defined",
        "",
        "> Use `read_architecture_section(name)` and `read_diagram(name)` to fetch exact specifications as needed."
    ]

    return "\n".join(summary_lines)


class ContextManager:
    """Maintains message conversation history within configured size and token constraints."""

    def __init__(self, max_tool_output_chars: int = MAX_TOOL_OUTPUT_CHARS) -> None:
        self.max_tool_output_chars = max_tool_output_chars
        self.messages: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        msg: Dict[str, Any] = {"role": role, "content": content}
        msg.update(kwargs)
        self.messages.append(msg)
        self._prune_if_needed()

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str) -> None:
        truncated_result = self.truncate_tool_output(result)
        msg: Dict[str, Any] = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": truncated_result,
        }
        self.messages.append(msg)
        self._prune_if_needed()

    def truncate_tool_output(self, text: str) -> str:
        if len(text) <= self.max_tool_output_chars:
            return text
        head = text[: self.max_tool_output_chars // 2]
        tail = text[-self.max_tool_output_chars // 2 :]
        return (
            f"{head}\n\n... [TRUNCATED {len(text) - self.max_tool_output_chars} characters by ContextManager] ...\n\n{tail}"
        )

    def _prune_if_needed(self) -> None:
        # Keep system prompt at index 0 and initial user prompt at index 1
        if len(self.messages) > MAX_HISTORY_MESSAGES:
            prefix = self.messages[:2] if len(self.messages) >= 2 else self.messages[:1]
            remaining = self.messages[len(prefix):]

            # We need to trim from the start of remaining.
            # Crucially: the trimmed segment MUST start with a role='user' or role='assistant' (without dangling tool calls)
            # It must never start with a role='tool' message, which violates OpenAI API schemas.
            target_keep = MAX_HISTORY_MESSAGES - len(prefix)
            cutoff = len(remaining) - target_keep

            while cutoff < len(remaining) and remaining[cutoff].get("role") == "tool":
                cutoff += 1

            trimmed = remaining[cutoff:]
            self.messages = prefix + trimmed

    def get_messages(self) -> List[Dict[str, Any]]:
        return list(self.messages)
