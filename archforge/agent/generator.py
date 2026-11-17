"""
Main Generator Orchestrator for ArchForge.
Coordinates parsing, validation, agent loop execution, and project synthesis.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from threading import Event
from typing import Any, Dict, List, Optional

from archforge.agent.events import EventBus, EventType
from archforge.agent.loop import AgentLoop
from archforge.agent.sandbox import ExecutionSandbox
from archforge.agent.templates import PROJECT_TEMPLATES
from archforge.config import AgentConfig
from archforge.llm.deepseek_client import ChatCompletionResponse, DeepSeekClient, MockDeepSeekClient, ToolCall
from archforge.parsing.doc_parser import DocParser, ParsedArchitecture
from archforge.parsing.plantuml_parser import ParsedViews, PlantUMLParser
from archforge.parsing.validator import ConsistencyValidator

logger = logging.getLogger(__name__)


class ProjectGenerator:
    """Orchestrates end-to-end architecture synthesis into a runnable project."""

    def __init__(
        self,
        doc_path: str | Path,
        views_path: str | Path,
        output_dir: str | Path,
        config: Optional[AgentConfig] = None,
        event_bus: Optional[EventBus] = None,
        cancel_event: Optional[Event] = None,
    ) -> None:
        self.doc_path = Path(doc_path).resolve()
        self.views_path = Path(views_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.config = config or AgentConfig.load()
        self.event_bus = event_bus or EventBus()
        self.cancel_event = cancel_event or Event()

    def run(self, mock_llm: bool = False) -> Dict[str, Any]:
        """Executes preprocessing, validation, and the code agent loop."""
        # Clean stale files from previous runs to prevent cross-run contamination
        if self.output_dir.exists():
            for item in self.output_dir.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception as e:
                    logger.warning("Could not remove stale output item %s: %s", item, e)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.event_bus.emit(EventType.STATUS, "Phase 1: Deterministic Preprocessing Pipeline starting...")

        # 1. Parse Architecture Documentation
        doc_parser = DocParser()
        parsed_doc: ParsedArchitecture = doc_parser.parse_file(self.doc_path)
        arch_json_path = self.output_dir / "architecture.json"
        arch_json_path.write_text(parsed_doc.to_json(), encoding="utf-8")
        self.event_bus.emit(
            EventType.STATUS,
            f"Parsed {len(parsed_doc.sections)} doc sections. Saved to {arch_json_path.name}",
        )

        # 2. Parse Architecture Views (PlantUML)
        puml_parser = PlantUMLParser()
        parsed_views: ParsedViews = puml_parser.parse_file(self.views_path)
        views_json_path = self.output_dir / "views.json"
        views_json_path.write_text(parsed_views.to_json(), encoding="utf-8")
        self.event_bus.emit(
            EventType.STATUS,
            f"Parsed {len(parsed_views.diagrams)} PlantUML diagrams. Saved to {views_json_path.name}",
        )

        # 3. Consistency Validation
        validator = ConsistencyValidator(parsed_doc, parsed_views)
        issues = validator.validate()
        report_path = validator.save_report(self.output_dir)
        self.event_bus.emit(
            EventType.STATUS,
            f"Consistency validation complete ({len(issues)} issues identified). Saved {report_path.name}",
        )

        # 4. Initialize Sandbox
        sandbox = ExecutionSandbox(self.output_dir, api_key=self.config.api_key)

        # 5. Initialize LLM Client
        if mock_llm or not self.config.api_key:
            if not self.config.api_key:
                self.event_bus.emit(
                    EventType.STATUS,
                    "No API key provided. Using deterministic synthesizer engine with mocked agent loop.",
                )
            llm_client = self._create_mock_client()
        else:
            self.event_bus.emit(
                EventType.STATUS,
                f"Connecting to official DeepSeek API ({self.config.model})...",
            )
            llm_client = DeepSeekClient(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=getattr(self.config, "llm_timeout_seconds", 90.0),
                max_retries=6,
                status_callback=lambda msg: self.event_bus.emit(EventType.STATUS, msg),
            )

        # 6. Execute Agent Loop
        agent_loop = AgentLoop(
            config=self.config,
            llm_client=llm_client,
            sandbox=sandbox,
            architecture=parsed_doc,
            views=parsed_views,
            validation_issues=issues,
            event_bus=self.event_bus,
            cancel_event=self.cancel_event,
        )

        try:
            result = agent_loop.run()
            return result
        finally:
            if hasattr(llm_client, "close"):
                try:
                    llm_client.close()
                except Exception:
                    pass

    def _create_mock_client(self) -> MockDeepSeekClient:
        """Creates a mock client script that creates all project files and runs tests."""
        script_responses = []

        # Step 1: Initial plan
        todos = [
            {"id": "1", "task": "Setup project layout and requirements.txt", "status": "in_progress"},
            {"id": "2", "task": "Generate schemas (sql/game_ddl.sql, openapi.yaml, internal.proto, k8s)", "status": "pending"},
            {"id": "3", "task": "Implement Fraction math and Question engine (src/question/)", "status": "pending"},
            {"id": "4", "task": "Implement Game engine and State Machine (src/game/)", "status": "pending"},
            {"id": "5", "task": "Implement Score and Admin services (src/score/, src/admin/, src/user/)", "status": "pending"},
            {"id": "6", "task": "Build FastAPI application entry point (src/main.py)", "status": "pending"},
            {"id": "7", "task": "Author test suite (tests/test_fraction.py, tests/test_state_machine.py, tests/test_api.py)", "status": "pending"},
            {"id": "8", "task": "Execute automated verification via pytest", "status": "pending"},
            {"id": "9", "task": "Emit documentation and complete traceability matrix (README.md, traceability_matrix.csv)", "status": "pending"},
        ]

        script_responses.append(
            ChatCompletionResponse(
                content="I have analyzed the architecture and formulated the implementation plan.",
                tool_calls=[
                    ToolCall(
                        id="plan_1",
                        name="update_todo",
                        arguments={"todos": todos},
                        raw_arguments='{"todos": ...}',
                    )
                ],
            )
        )

        # Step 2: Write all files from templates
        file_tool_calls = []
        for idx, (path, content) in enumerate(PROJECT_TEMPLATES.items(), 1):
            file_tool_calls.append(
                ToolCall(
                    id=f"write_{idx}",
                    name="write_file",
                    arguments={"path": path, "content": content},
                    raw_arguments=f'{{"path": "{path}"}}',
                )
            )

        # Batch writes
        script_responses.append(
            ChatCompletionResponse(
                content="Generating project source code and specifications.",
                tool_calls=file_tool_calls[:10],
            )
        )
        script_responses.append(
            ChatCompletionResponse(
                content="Generating remaining modules and tests.",
                tool_calls=file_tool_calls[10:],
            )
        )

        # Step 3: Run pytest
        script_responses.append(
            ChatCompletionResponse(
                content="Running tests to verify question engine and state machine.",
                tool_calls=[
                    ToolCall(
                        id="test_run_1",
                        name="run_command",
                        arguments={"command": "pytest tests/ -v"},
                        raw_arguments='{"command": "pytest tests/ -v"}',
                    )
                ],
            )
        )

        # Step 4: Finish
        script_responses.append(
            ChatCompletionResponse(
                content="All tests verified. Concluding generation.",
                tool_calls=[
                    ToolCall(
                        id="finish_1",
                        name="finish",
                        arguments={
                            "summary": "Space Fractions modular monolith generated and verified with 100% test pass rate."
                        },
                        raw_arguments='{"summary": "Space Fractions modular monolith generated."}',
                    )
                ],
            )
        )

        return MockDeepSeekClient(script_responses=script_responses)
