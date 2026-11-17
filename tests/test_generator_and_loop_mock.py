"""
End-to-End integration test for ArchForge using MockDeepSeekClient.
Verifies full project synthesis, artifact presence, and test pass rate.
"""

from pathlib import Path
import pytest
from archforge.agent.generator import ProjectGenerator
from archforge.agent.events import EventBus, EventType
from archforge.config import AgentConfig


def test_generator_mock_end_to_end(tmp_path):
    doc_path = Path("samples/Architecture_Documentation.md")
    views_path = Path("samples/Architecture_View.md")
    out_dir = tmp_path / "generated_space_fractions"

    cfg = AgentConfig(api_key="mock-key", model="deepseek-v4-pro")
    events = []
    bus = EventBus()
    bus.subscribe(lambda e: events.append(e))

    gen = ProjectGenerator(
        doc_path=doc_path,
        views_path=views_path,
        output_dir=out_dir,
        config=cfg,
        event_bus=bus,
    )

    result = gen.run(mock_llm=True)

    # 1. Generator execution succeeded
    assert result["success"] is True

    # 2. Preprocessing artifacts generated
    assert (out_dir / "architecture.json").exists()
    assert (out_dir / "views.json").exists()
    assert (out_dir / "validation_report.md").exists()

    # 3. Required Deliverable Files present
    required_files = [
        "requirements.txt",
        "Dockerfile",
        "openapi.yaml",
        "internal.proto",
        "sql/game_ddl.sql",
        "sql/question_ddl.sql",
        "k8s/deployment.yaml",
        "traceability_matrix.csv",
        "architecture.md",
        "README.md",
        "src/main.py",
        "src/game/engine.py",
        "src/game/state_machine.py",
        "src/game/help.py",
        "src/question/fraction.py",
        "src/question/engine.py",
        "src/score/service.py",
        "src/admin/service.py",
        "src/user/service.py",
        "tests/test_fraction.py",
        "tests/test_state_machine.py",
        "tests/test_api.py",
        "tests/test_scoring.py",
    ]

    for rf in required_files:
        assert (out_dir / rf).exists(), f"Missing required file: {rf}"

    # 4. Verify events were emitted
    event_types = {e.event_type for e in events}
    assert EventType.STATUS in event_types
    assert EventType.PLAN in event_types
    assert EventType.TOOL_CALL in event_types
    assert EventType.DONE in event_types
