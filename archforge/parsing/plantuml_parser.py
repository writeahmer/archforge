"""
Deterministic Preprocessing Pipeline for Architecture_View.md.
Extracts and parses PlantUML diagrams across 4+1 architectural views into views.json.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ParsedDiagram:
    name: str
    view_category: str  # ScenarioView, LogicView, ProcessView, DevelopmentView, PhysicalView
    diagram_type: str   # usecase, class, object, state, activity, sequence, collaboration, package, component, deployment, container
    raw_uml: str
    actors: List[str] = field(default_factory=list)
    usecases: List[str] = field(default_factory=list)
    classes: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)
    states: List[str] = field(default_factory=list)
    transitions: List[str] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    packages: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    nodes: List[str] = field(default_factory=list)
    containers: List[str] = field(default_factory=list)
    syntax_anomalies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParsedViews:
    title: str = ""
    diagrams: List[ParsedDiagram] = field(default_factory=list)
    summary_by_view: Dict[str, List[str]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "diagrams": [d.to_dict() for d in self.diagrams],
            "summary_by_view": self.summary_by_view,
            "warnings": self.warnings,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class PlantUMLParser:
    """Robust parser for PlantUML architectural views."""

    def __init__(self) -> None:
        self.warnings: List[str] = []

    def parse_file(self, file_path: str | Path) -> ParsedViews:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Architecture views file not found: {path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        return self.parse_text(content)

    def parse_text(self, text: str) -> ParsedViews:
        self.warnings = []
        result = ParsedViews()

        # Extract title
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            result.title = title_match.group(1).strip()

        # Find all @startuml ... @enduml blocks
        uml_pattern = re.compile(r"@startuml(?:\s+([A-Za-z0-9_]+))?\n([\s\S]*?)@enduml", re.MULTILINE)

        for match in uml_pattern.finditer(text):
            diag_name = match.group(1) or "UnnamedDiagram"
            raw_body = match.group(2).strip()

            # Determine surrounding context (which markdown header is above this)
            start_idx = match.start()
            preceding_text = text[:start_idx]
            view_cat = self._infer_view_category(preceding_text, diag_name, raw_body)
            diag_type = self._infer_diagram_type(diag_name, raw_body, view_cat)

            diagram = ParsedDiagram(
                name=diag_name,
                view_category=view_cat,
                diagram_type=diag_type,
                raw_uml=raw_body,
            )

            self._parse_elements(diagram, raw_body)
            result.diagrams.append(diagram)

            if view_cat not in result.summary_by_view:
                result.summary_by_view[view_cat] = []
            result.summary_by_view[view_cat].append(diag_name)

        result.warnings = list(self.warnings)
        return result

    def _infer_view_category(self, preceding_text: str, name: str, body: str) -> str:
        # Search backward for the most recent section header
        headers = re.findall(r"^##\s+(?:[0-9]+\.\s*)?([^\n]+)", preceding_text, re.MULTILINE)
        last_header = headers[-1].lower() if headers else ""

        if "scenario" in last_header or "use case" in last_header:
            return "ScenarioView"
        if "logic" in last_header or "class" in last_header:
            return "LogicView"
        if "process" in last_header or "state" in last_header or "sequence" in last_header:
            return "ProcessView"
        if "development" in last_header or "package" in last_header or "component" in last_header:
            return "DevelopmentView"
        if "physical" in last_header or "deployment" in last_header or "container" in last_header:
            return "PhysicalView"

        # Fallback heuristic based on diagram name or body
        lower_all = f"{name} {body}".lower()
        if "usecase" in lower_all or "actor" in lower_all:
            return "ScenarioView"
        if "class " in lower_all or "object " in lower_all:
            return "LogicView"
        if "state" in lower_all or "autonumber" in lower_all or "repeat" in lower_all:
            return "ProcessView"
        if "package " in lower_all or "component [" in lower_all or "[player interface]" in lower_all:
            return "DevelopmentView"
        if "node " in lower_all or "artifact " in lower_all or "container" in lower_all:
            return "PhysicalView"

        return "LogicView"

    def _infer_diagram_type(self, name: str, body: str, view_cat: str) -> str:
        lower_all = f"{name} {body}".lower()
        if "usecase" in lower_all:
            return "usecase"
        if "object" in lower_all and "object " in body.lower():
            return "object"
        if "class " in body.lower():
            return "class"
        if "[*] -->" in body or "--> [*]" in body:
            return "state"
        if "start" in body.lower() and "stop" in body.lower():
            return "activity"
        if "participant" in lower_all or "autonumber" in lower_all:
            return "sequence"
        if "collaboration" in lower_all or re.search(r"\d+:\s*\w+\(", body):
            return "collaboration"
        if "package " in body.lower() and "component" not in body.lower():
            return "package"
        if "component" in lower_all or "comp" in lower_all:
            return "component"
        if "container" in lower_all:
            return "container"
        if "node " in body.lower():
            return "deployment"
        return "general"

    def _parse_elements(self, diagram: ParsedDiagram, body: str) -> None:
        lines = body.splitlines()

        # Parse Actors
        actor_pattern = re.compile(r'actor\s+(?:"([^"]+)"|([A-Za-z0-9_]+))(?:\s+as\s+([A-Za-z0-9_]+))?')
        for match in actor_pattern.finditer(body):
            act_name = match.group(1) or match.group(2)
            diagram.actors.append(act_name)

        # Parse Use Cases
        usecase_pattern = re.compile(r'usecase\s+(?:"([^"]+)"|([A-Za-z0-9_]+))(?:\s+as\s+([A-Za-z0-9_]+))?')
        for match in usecase_pattern.finditer(body):
            uc_name = match.group(1) or match.group(2)
            diagram.usecases.append(uc_name)

        # Parse Classes
        class_pattern = re.compile(r"class\s+([A-Za-z0-9_]+)\s*\{([^}]*)\}", re.DOTALL)
        for match in class_pattern.finditer(body):
            cls_name = match.group(1)
            cls_body = match.group(2)
            attrs = []
            methods = []
            for line in cls_body.splitlines():
                line = line.strip()
                if not line or line.startswith("'"):
                    continue
                if "(" in line and ")" in line:
                    methods.append(line)
                else:
                    attrs.append(line)
            diagram.classes.append({"name": cls_name, "attributes": attrs, "methods": methods})

        # Parse Components
        comp_pattern = re.compile(r'\[([A-Za-z0-9_\s]+)\](?:\s+as\s+([A-Za-z0-9_]+))?')
        for match in comp_pattern.finditer(body):
            diagram.components.append(match.group(1).strip())

        # Parse Nodes
        node_pattern = re.compile(r'node\s+"([^"]+)"')
        for match in node_pattern.finditer(body):
            diagram.nodes.append(match.group(1).strip())

        # Parse Packages
        pkg_pattern = re.compile(r'package\s+"([^"]+)"')
        for match in pkg_pattern.finditer(body):
            diagram.packages.append(match.group(1).strip())

        # Parse Participants
        part_pattern = re.compile(r'participant\s+([A-Za-z0-9_]+)')
        for match in part_pattern.finditer(body):
            diagram.participants.append(match.group(1).strip())

        # Parse States & Transitions
        if diagram.diagram_type == "state":
            state_trans_pattern = re.compile(r'([A-Za-z0-9_\[\*\]]+)\s*-->\s*([A-Za-z0-9_\[\*\]]+)(?:\s*:\s*(.+))?')
            for match in state_trans_pattern.finditer(body):
                src = match.group(1).strip()
                dst = match.group(2).strip()
                lbl = match.group(3).strip() if match.group(3) else ""
                diagram.transitions.append(f"{src} --> {dst} ({lbl})" if lbl else f"{src} --> {dst}")
                for s in (src, dst):
                    if s not in ("[*]", "") and s not in diagram.states:
                        diagram.states.append(s)

        # Parse Relations & Syntax anomalies
        for line in lines:
            line = line.strip()
            if not line or line.startswith("'"):
                continue
            if "--*" in line:
                diagram.syntax_anomalies.append(f"Odd composition syntax: {line}")
                diagram.relations.append(line)
            elif "-->" in line or ".." in line or "--" in line:
                diagram.relations.append(line)

        # Detect Object diagram syntax issues
        if diagram.diagram_type == "object":
            if "object :" in body or "contains ->" in body:
                diagram.syntax_anomalies.append("Legacy/non-standard object relationship syntax found in object diagram")
