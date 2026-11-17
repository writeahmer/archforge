"""
Event bus and listener interfaces for ArchForge.
Allows real-time streaming of progress, plan updates, and tool calls to GUI and CLI.
"""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventType(str, Enum):
    STATUS = "status"
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    MESSAGE = "message"
    THOUGHT = "thought"
    WARNING = "warning"
    ERROR = "error"
    DONE = "done"


@dataclass
class AgentEvent:
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        }


EventListener = Callable[[AgentEvent], None]


class EventBus:
    """Thread-safe event dispatcher and subscriber registry."""

    def __init__(self) -> None:
        self._listeners: List[EventListener] = []
        self._queue: queue.Queue[AgentEvent] = queue.Queue()

    def subscribe(self, listener: EventListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def emit(self, event_type: EventType, message: str = "", data: Optional[Dict[str, Any]] = None) -> None:
        event = AgentEvent(
            event_type=event_type,
            message=message,
            data=data or {},
        )
        self._queue.put(event)
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                pass

    def get_queue(self) -> queue.Queue[AgentEvent]:
        return self._queue
