"""
Tests for ToolRegistry handlers.
"""

from pathlib import Path
import pytest
from archforge.agent.sandbox import ExecutionSandbox
from archforge.agent.tools import ToolRegistry
from archforge.parsing.doc_parser import DocParser
from archforge.parsing.plantuml_parser import PlantUMLParser


@pytest.fixture
def registry(tmp_path):
    doc = DocParser().parse_file("samples/Architecture_Documentation.md")
    views = PlantUMLParser().parse_file("samples/Architecture_View.md")
    sandbox = ExecutionSandbox(tmp_path)
    return ToolRegistry(sandbox=sandbox, architecture=doc, views=views)


def test_tool_write_read_edit_search(registry):
    # 1. Write file
    w_res = registry.execute("write_file", {"path": "src/hello.py", "content": "print('hello world')\n"})
    assert "Successfully wrote" in w_res

    # 2. Read file
    r_res = registry.execute("read_file", {"path": "src/hello.py"})
    assert "print('hello world')" in r_res

    # 3. Edit file
    e_res = registry.execute("edit_file", {"path": "src/hello.py", "target": "world", "replacement": "universe"})
    assert "Successfully replaced 1" in e_res

    # 4. Search in files
    s_res = registry.execute("search_in_files", {"pattern": "universe"})
    assert "src/hello.py" in s_res
    assert "universe" in s_res

    # 5. List dir
    l_res = registry.execute("list_dir", {"subpath": ""})
    assert "src/" in l_res


def test_tool_architecture_retrieval(registry):
    # Retrieve OpenAPI
    res_api = registry.execute("read_architecture_section", {"name": "openapi"})
    assert "paths:" in res_api or "/game/start" in res_api

    # Retrieve Diagram
    res_diag = registry.execute("read_diagram", {"name": "SpaceFractions_GameState"})
    assert "Playing" in res_diag
    assert "@startuml" in res_diag
