"""
Tests for PlantUMLParser on Architecture_View.md.
"""

from pathlib import Path
import pytest
from archforge.parsing.plantuml_parser import PlantUMLParser


@pytest.fixture
def sample_views_path():
    p = Path("samples/Architecture_View.md")
    assert p.exists()
    return p


def test_plantuml_parser_views(sample_views_path):
    parser = PlantUMLParser()
    views = parser.parse_file(sample_views_path)

    assert "Space Fractions" in views.title
    assert len(views.diagrams) >= 8

    # Check 4+1 View coverage
    categories = {d.view_category for d in views.diagrams}
    assert "ScenarioView" in categories
    assert "LogicView" in categories
    assert "ProcessView" in categories
    assert "DevelopmentView" in categories
    assert "PhysicalView" in categories


def test_diagram_element_extraction(sample_views_path):
    parser = PlantUMLParser()
    views = parser.parse_file(sample_views_path)

    # Use Case diagram
    usecase_diag = next(d for d in views.diagrams if d.diagram_type == "usecase")
    assert "Student Player" in usecase_diag.actors
    assert any("Play Game" in uc for uc in usecase_diag.usecases)

    # Class diagram
    class_diag = next(d for d in views.diagrams if d.diagram_type == "class")
    class_names = [c["name"] for c in class_diag.classes]
    assert "GameSession" in class_names
    assert "Fraction" in class_names
    assert len(class_diag.syntax_anomalies) > 0  # Reversible composition arrows detected

    # State diagram
    state_diag = next(d for d in views.diagrams if d.diagram_type == "state")
    assert "Playing" in state_diag.states
    assert "Paused" in state_diag.states
    assert "GameOver" in state_diag.states

    # Component diagram
    comp_diag = next(d for d in views.diagrams if d.diagram_type == "component")
    comp_names = comp_diag.components
    assert any("AdminComponent" in c for c in comp_names)
    assert any("UserComponent" in c for c in comp_names)
