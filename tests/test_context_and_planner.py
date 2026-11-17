"""
Tests for ContextManager and TodoTracker.
"""

from archforge.agent.context import ContextManager
from archforge.agent.planner import TodoTracker


def test_context_manager_truncation():
    mgr = ContextManager(max_tool_output_chars=200)

    short_out = "Short output"
    assert mgr.truncate_tool_output(short_out) == short_out

    long_out = "A" * 500
    truncated = mgr.truncate_tool_output(long_out)
    assert len(truncated) < 300
    assert "[TRUNCATED" in truncated


def test_todo_tracker_lifecycle():
    updates = []
    tracker = TodoTracker(on_change=lambda todos: updates.append(len(todos)))

    tracker.set_todos([
        {"id": "1", "task": "Task 1", "status": "pending"},
        {"id": "2", "task": "Task 2", "status": "pending"},
    ])
    assert len(tracker.todos) == 2
    assert tracker.todos[0].status == "pending"

    tracker.update_item_status("1", "completed")
    assert tracker.todos[0].status == "completed"

    tracker.mark_all_completed()
    assert all(t.status == "completed" for t in tracker.todos)
    assert len(updates) >= 3
