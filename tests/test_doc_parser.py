"""
Tests for DocParser on Architecture_Documentation.md.
"""

from pathlib import Path
import pytest
from archforge.parsing.doc_parser import DocParser


@pytest.fixture
def sample_doc_path():
    p = Path("samples/Architecture_Documentation.md")
    assert p.exists()
    return p


def test_doc_parser_sections(sample_doc_path):
    parser = DocParser()
    doc = parser.parse_file(sample_doc_path)

    assert "Space Fractions" in doc.title
    assert "Section_A" in doc.sections
    assert "Section_L" in doc.sections
    assert len(doc.sections) >= 12


def test_doc_parser_tables(sample_doc_path):
    parser = DocParser()
    doc = parser.parse_file(sample_doc_path)

    # Risks table
    assert len(doc.risks) >= 3
    assert any("RSK-01" in r.get("Risk ID", "") for r in doc.risks)

    # QA mapping table
    assert len(doc.qa_mapping) >= 3
    assert any("99.99%" in r.get("Goal", "") for r in doc.qa_mapping)

    # Traceability matrix
    assert len(doc.traceability_matrix) >= 8
    assert any("FR-01" in r.get("Req ID", "") for r in doc.traceability_matrix)
    assert any("sql/question_ddl.sql" in r.get("Deliverable Artifact", "") for r in doc.traceability_matrix)


def test_doc_parser_code_blocks(sample_doc_path):
    parser = DocParser()
    doc = parser.parse_file(sample_doc_path)

    # OpenAPI YAML
    assert "openapi" in doc.openapi
    assert "/game/start" in doc.openapi.get("paths", {})

    # Protobuf
    assert len(doc.proto.get("services", [])) >= 2
    svc_names = [s["name"] for s in doc.proto["services"]]
    assert "GameService" in svc_names
    assert "QuestionService" in svc_names

    # SQL DDL
    assert len(doc.sql_ddl) >= 4
    assert "users" in doc.sql_tables
    assert "game_sessions" in doc.sql_tables
    assert "scores" in doc.sql_tables

    # K8s manifest
    assert len(doc.k8s_manifest) >= 2


def test_doc_parser_deliverables(sample_doc_path):
    parser = DocParser()
    doc = parser.parse_file(sample_doc_path)

    assert len(doc.deliverables) >= 5
    assert any("sql/game_ddl.sql" in d for d in doc.deliverables)
