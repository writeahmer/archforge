"""
Tests for ConsistencyValidator detecting deliberate architectural inconsistencies.
"""

from pathlib import Path
import pytest
from archforge.parsing.doc_parser import DocParser
from archforge.parsing.plantuml_parser import PlantUMLParser
from archforge.parsing.validator import ConsistencyValidator


@pytest.fixture
def doc_and_views():
    doc = DocParser().parse_file("samples/Architecture_Documentation.md")
    views = PlantUMLParser().parse_file("samples/Architecture_View.md")
    return doc, views


def test_validator_detects_all_required_inconsistencies(doc_and_views):
    doc, views = doc_and_views
    validator = ConsistencyValidator(doc, views)
    issues = validator.validate()

    assert len(issues) >= 5

    categories = {i.category for i in issues}

    # 1. Naming mismatch (sql/question_ddl.sql vs sql/game_ddl.sql)
    assert "NamingMismatch" in categories
    naming_issue = next(i for i in issues if i.category == "NamingMismatch")
    assert "question_ddl.sql" in naming_issue.summary and "game_ddl.sql" in naming_issue.summary

    # 2. Components in diagrams but missing in doc (AdminComponent, UserComponent)
    assert "MissingComponent" in categories
    comp_issue = next(i for i in issues if i.category == "MissingComponent")
    assert "Admin" in comp_issue.summary or "User" in comp_issue.summary

    # 3. Requirements not covered (FR-07 or NFR-03)
    assert "UncoveredRequirement" in categories

    # 4. Empty cells in testing matrix
    assert "EmptyTestMatrix" in categories

    # 5. Architecture contradictions (99.99% vs 1% error budget, heavy stack)
    assert "ArchitectureContradiction" in categories
    contradictions = [i for i in issues if i.category == "ArchitectureContradiction"]
    assert len(contradictions) >= 2

    # 6. Diagram syntax anomalies
    assert "DiagramSyntax" in categories

    # 7. Scope reconciliation
    assert "ScopeDiscrepancy" in categories


def test_validation_report_generation(doc_and_views, tmp_path):
    doc, views = doc_and_views
    validator = ConsistencyValidator(doc, views)
    validator.validate()

    report_file = validator.save_report(tmp_path)
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")

    assert "# ArchForge Consistency Validation Report" in content
    assert "Summary of Findings" in content
    assert "NamingMismatch" in content
    assert "MissingComponent" in content
    assert "ArchitectureContradiction" in content
