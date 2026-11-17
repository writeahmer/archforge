"""
Todo and Plan Tracker for ArchForge.
Maintains live checklist state for UI rendering and agent grounding.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TodoItem:
    id: str
    task: str
    status: str = "pending"  # pending, in_progress, completed, failed

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TodoTracker:
    """Manages the agent's plan items and notifies listeners on updates."""

    def __init__(self, on_change: Optional[Callable[[List[TodoItem]], None]] = None) -> None:
        self.todos: List[TodoItem] = []
        self.on_change = on_change

    def set_todos(self, items: List[Dict[str, Any] | TodoItem]) -> None:
        parsed: List[TodoItem] = []
        for it in items:
            if isinstance(it, TodoItem):
                parsed.append(it)
            elif isinstance(it, dict):
                parsed.append(
                    TodoItem(
                        id=str(it.get("id", len(parsed) + 1)),
                        task=str(it.get("task", "")),
                        status=str(it.get("status", "pending")),
                    )
                )
        self.todos = parsed
        if self.on_change:
            self.on_change(self.todos)

    def update_item_status(self, item_id: str, status: str) -> None:
        for t in self.todos:
            if t.id == item_id:
                t.status = status
                break
        if self.on_change:
            self.on_change(self.todos)

    def mark_all_completed(self) -> None:
        for t in self.todos:
            t.status = "completed"
        if self.on_change:
            self.on_change(self.todos)

    def get_progress_summary(self) -> str:
        total = len(self.todos)
        if total == 0:
            return "No tasks scheduled."
        completed = sum(1 for t in self.todos if t.status == "completed")
        return f"{completed}/{total} tasks completed ({int(completed / total * 100)}%)"

    def to_markdown_checklist(self) -> str:
        lines = []
        for t in self.todos:
            box = "[x]" if t.status == "completed" else "[-]" if t.status == "in_progress" else "[ ]"
            lines.append(f"- {box} {t.id}: {t.task}")
        return "\n".join(lines)
