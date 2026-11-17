"""
Core Agent Loop for ArchForge.
Implements the Claude-Code style cycle: Think -> Act -> Observe -> Repeat with self-repair verification.
"""

from __future__ import annotations

import logging
from threading import Event
from typing import Any, Callable, Dict, List, Optional

from archforge.agent.context import ContextManager, build_compact_summary
from archforge.agent.events import EventBus, EventType
from archforge.agent.planner import TodoTracker
from archforge.agent.prompts import PLANNING_PROMPT, SYSTEM_PROMPT, format_repair_prompt
from archforge.agent.sandbox import ExecutionSandbox
from archforge.agent.tools import ToolRegistry
from archforge.config import AgentConfig
from archforge.llm.deepseek_client import DeepSeekClient, ToolCall
from archforge.parsing.doc_parser import ParsedArchitecture
from archforge.parsing.plantuml_parser import ParsedViews
from archforge.parsing.validator import ConsistencyIssue

logger = logging.getLogger(__name__)


class AgentLoop:
    """Orchestrates LLM reasoning, sandboxed tool execution, and automated test repair."""

    def __init__(
        self,
        config: AgentConfig,
        llm_client: DeepSeekClient,
        sandbox: ExecutionSandbox,
        architecture: ParsedArchitecture,
        views: ParsedViews,
        validation_issues: List[ConsistencyIssue],
        event_bus: EventBus,
        cancel_event: Optional[Event] = None,
    ) -> None:
        self.config = config
        self.llm_client = llm_client
        self.sandbox = sandbox
        self.architecture = architecture
        self.views = views
        self.validation_issues = validation_issues
        self.event_bus = event_bus
        self.cancel_event = cancel_event or Event()

        self.todo_tracker = TodoTracker(on_change=self._on_todo_update)
        self.tool_registry = ToolRegistry(
            sandbox=self.sandbox,
            architecture=self.architecture,
            views=self.views,
            todo_callback=self.todo_tracker.set_todos,
        )
        self.context_manager = ContextManager()
        self.steps_executed = 0

    def _on_todo_update(self, todos: list) -> None:
        self.event_bus.emit(
            EventType.PLAN,
            message="Plan updated",
            data={"todos": [t.to_dict() for t in todos]},
        )

    def run(self) -> Dict[str, Any]:
        """Runs the agent loop to completion or until cancelled/failed."""
        self.event_bus.emit(EventType.STATUS, "Initializing agent context and plan...")

        # Build initial compact context
        summary = build_compact_summary(self.architecture, self.views, self.validation_issues)
        self.context_manager.add_message("system", SYSTEM_PROMPT)
        self.context_manager.add_message(
            "user",
            f"Here is the architectural summary for the project to build:\n\n{summary}\n\n{PLANNING_PROMPT}",
        )

        tools = self.tool_registry.get_tool_definitions()

        # Phase 1: Interactive Tool Execution Loop
        while self.steps_executed < self.config.max_agent_steps:
            if self.cancel_event.is_set():
                self.event_bus.emit(EventType.WARNING, "Generation cancelled by user.")
                return {"success": False, "reason": "cancelled"}

            self.steps_executed += 1
            self.event_bus.emit(
                EventType.STATUS,
                f"Agent step {self.steps_executed}/{self.config.max_agent_steps}: Consulting model...",
            )

            try:
                def chunk_handler(token: str) -> None:
                    # Stream tokens if needed
                    pass

                response = self.llm_client.complete(
                    messages=self.context_manager.get_messages(),
                    tools=tools,
                    cancel_event=self.cancel_event,
                    on_chunk=chunk_handler,
                )
            except Exception as e:
                err_msg = f"LLM Invocation error: {e}"
                logger.error(err_msg)
                self.event_bus.emit(EventType.ERROR, err_msg)
                return {"success": False, "error": err_msg}

            # Handle Model Thoughts / Reasoning
            if response.reasoning_content:
                self.event_bus.emit(
                    EventType.THOUGHT,
                    message=response.reasoning_content[:200] + "...",
                    data={"reasoning": response.reasoning_content},
                )

            # Record Assistant turn in context
            assistant_msg: Dict[str, Any] = {"role": "assistant"}
            if response.content:
                assistant_msg["content"] = response.content
                self.event_bus.emit(EventType.MESSAGE, message=response.content)

            if response.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.raw_arguments},
                    }
                    for tc in response.tool_calls
                ]
                self.context_manager.messages.append(assistant_msg)

                # Execute all requested tool calls
                for tc in response.tool_calls:
                    if self.cancel_event.is_set():
                        break

                    self.event_bus.emit(
                        EventType.TOOL_CALL,
                        message=f"Executing tool: {tc.name}",
                        data={"tool": tc.name, "args": tc.arguments},
                    )

                    result = self.tool_registry.execute(tc.name, tc.arguments)

                    self.event_bus.emit(
                        EventType.TOOL_RESULT,
                        message=f"Tool {tc.name} returned ({len(result)} chars)",
                        data={"tool": tc.name, "result": result[:300]},
                    )

                    self.context_manager.add_tool_result(tc.id, tc.name, result)

                if self.tool_registry.finished:
                    self.event_bus.emit(EventType.STATUS, "Agent declared completion.")
                    break
            else:
                self.context_manager.messages.append(assistant_msg)
                # If model returned text without tools and didn't finish, prompt it to proceed
                if not self.tool_registry.finished:
                    self.context_manager.add_message(
                        "user",
                        "Please continue executing your plan by calling the appropriate file writing or testing tools.",
                    )

        # Phase 2: Autonomous Self-Verification & Repair Loop
        self.event_bus.emit(EventType.STATUS, "Running self-verification on generated tests...")
        verification_passed = self._run_self_repair_loop(tools)

        # Mark all remaining todos completed if tests passed
        if verification_passed:
            self.todo_tracker.mark_all_completed()

        summary_report = self.tool_registry.finish_summary or "Project generated and verified successfully."
        self.event_bus.emit(
            EventType.DONE,
            message="ArchForge generation finished.",
            data={
                "success": verification_passed,
                "summary": summary_report,
                "output_dir": str(self.sandbox.root_dir),
            },
        )

        return {
            "success": verification_passed,
            "summary": summary_report,
            "steps": self.steps_executed,
            "output_dir": str(self.sandbox.root_dir),
        }

    def _run_self_repair_loop(self, tools: List[Dict[str, Any]]) -> bool:
        """Executes pytest in the workspace, feeding back any failures for up to max_repair_rounds."""
        tests_dir = self.sandbox.root_dir / "tests"
        if not tests_dir.exists():
            self.event_bus.emit(EventType.WARNING, "No tests directory found to verify.")
            return True

        for repair_round in range(1, self.config.max_repair_rounds + 1):
            if self.cancel_event.is_set():
                return False

            self.event_bus.emit(
                EventType.STATUS,
                f"Verification attempt {repair_round}/{self.config.max_repair_rounds}: Running pytest...",
            )

            code, stdout, stderr = self.sandbox.run_command("python -m pytest tests/ -v")
            output = f"{stdout}\n{stderr}".strip()

            if code == 0:
                self.event_bus.emit(EventType.STATUS, "All automated tests passed successfully!")
                return True

            self.event_bus.emit(
                EventType.WARNING,
                f"Test failure detected (Exit code {code}). Starting repair round {repair_round}...",
            )

            # Feed test output back to the agent
            repair_prompt = format_repair_prompt(output, repair_round, self.config.max_repair_rounds)
            self.context_manager.add_message("user", repair_prompt)

            try:
                response = self.llm_client.complete(
                    messages=self.context_manager.get_messages(),
                    tools=tools,
                    cancel_event=self.cancel_event,
                )
            except Exception as e:
                self.event_bus.emit(EventType.ERROR, f"Repair round {repair_round} error: {e}")
                return False

            # Record assistant response into context manager before any tool results
            assistant_msg: Dict[str, Any] = {"role": "assistant"}
            if response.content:
                assistant_msg["content"] = response.content

            if response.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.raw_arguments},
                    }
                    for tc in response.tool_calls
                ]
                self.context_manager.messages.append(assistant_msg)

                # Execute model's repair tool calls
                for tc in response.tool_calls:
                    self.event_bus.emit(
                        EventType.TOOL_CALL,
                        message=f"[Repair] Executing {tc.name}",
                        data={"tool": tc.name, "args": tc.arguments},
                    )
                    res = self.tool_registry.execute(tc.name, tc.arguments)
                    self.context_manager.add_tool_result(tc.id, tc.name, res)
            else:
                self.context_manager.messages.append(assistant_msg)

        # Final re-check
        code, stdout, stderr = self.sandbox.run_command("python -m pytest tests/ -v")
        return code == 0
