from __future__ import annotations

import re
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class CodeBlock:
    language: str
    content: str
    section: str = ""
    start_line: int = 0


@dataclass
class ProtoMessage:
    name: str
    fields: List[str] = field(default_factory=list)


@dataclass
class ProtoService:
    name: str
    rpcs: List[str] = field(default_factory=list)


@dataclass
class ProtoParsed:
    raw: str = ""
    services: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedArchitecture:
    raw_text: str = ""
    title: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    executive_summary: str = ""
    risks: List[Dict[str, str]] = field(default_factory=list)
    qa_mapping: List[Dict[str, str]] = field(default_factory=list)
    traceability_matrix: List[Dict[str, str]] = field(default_factory=list)
    components: List[Dict[str, Any]] = field(default_factory=list)
    openapi: Dict[str, Any] = field(default_factory=dict)
    openapi_raw: str = ""
    proto: Dict[str, Any] = field(default_factory=dict)
    sql_ddl: List[str] = field(default_factory=list)
    sql_tables: List[str] = field(default_factory=list)
    k8s_manifest: List[Dict[str, Any]] = field(default_factory=list)
    k8s_raw: str = ""
    security: str = ""
    observability: Dict[str, Any] = field(default_factory=dict)
    testing_matrix: List[Dict[str, str]] = field(default_factory=list)
    migration_plan: str = ""
    tradeoffs: str = ""
    assumptions: str = ""
    open_questions: str = ""
    deliverables: List[str] = field(default_factory=list)
    code_blocks: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def parse_markdown_table(table_text: str) -> List[Dict[str, str]]:
    """Parses a markdown table into a list of row dictionaries."""
    rows: List[Dict[str, str]] = []
    lines = [line.strip() for line in table_text.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        return rows

    # First row is header
    header_line = lines[0]
    headers = [col.strip() for col in header_line.split("|")]
    if headers and headers[0] == "":
        headers.pop(0)
    if headers and headers[-1] == "":
        headers.pop(-1)

    # Second row is separator (e.g. |---|---|)
    start_row = 1
    if len(lines) > 1 and re.match(r"^\|?[\s\-:]+(\|[\s\-:]+)+\|?$", lines[1]):
        start_row = 2

    for line in lines[start_row:]:
        if not line.startswith("|") and not ("|" in line):
            continue
        cols = [c.strip() for c in line.split("|")]
        if cols and cols[0] == "":
            cols.pop(0)
        if cols and cols[-1] == "":
            cols.pop(-1)

        row_dict: Dict[str, str] = {}
        for idx, h in enumerate(headers):
            val = cols[idx] if idx < len(cols) else ""
            row_dict[h] = val
        if row_dict:
            rows.append(row_dict)

    return rows


def parse_proto(proto_content: str) -> ProtoParsed:
    """Parses raw protobuf content into services and messages."""
    services: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []

    # Match service blocks
    service_pattern = re.compile(r"service\s+([A-Za-z0-9_]+)\s*\{([^}]*)\}", re.DOTALL)
    rpc_pattern = re.compile(r"rpc\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*returns\s*\(([^)]*)\)")

    for svc_match in service_pattern.finditer(proto_content):
        svc_name = svc_match.group(1)
        body = svc_match.group(2)
        rpcs = []
        for rpc_match in rpc_pattern.finditer(body):
            rpcs.append({
                "method": rpc_match.group(1),
                "request": rpc_match.group(2).strip(),
                "response": rpc_match.group(3).strip(),
            })
        services.append({"name": svc_name, "rpcs": rpcs})

    # Match message blocks
    message_pattern = re.compile(r"message\s+([A-Za-z0-9_]+)\s*\{([^}]*)\}", re.DOTALL)
    for msg_match in message_pattern.finditer(proto_content):
        msg_name = msg_match.group(1)
        body = msg_match.group(2)
        fields = []
        for line in body.splitlines():
            line = line.strip()
            if line and not line.startswith("//"):
                fields.append(line.rstrip(";"))
        messages.append({"name": msg_name, "fields": fields})

    return ProtoParsed(raw=proto_content, services=services, messages=messages)


def parse_sql_ddl(sql_content: str) -> tuple[List[str], List[str]]:
    """Splits SQL DDL into statements and extracts table names."""
    # Remove single line comments
    clean_lines = []
    for line in sql_content.splitlines():
        if line.strip().startswith("--"):
            continue
        clean_lines.append(line)
    clean_sql = "\n".join(clean_lines)

    statements = [stmt.strip() for stmt in clean_sql.split(";") if stmt.strip()]
    tables = []
    table_pattern = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_]+)", re.IGNORECASE)
    for stmt in statements:
        m = table_pattern.search(stmt)
        if m:
            tables.append(m.group(1))

    return statements, tables


class DocParser:
    """Robust deterministic parser for Architecture_Documentation.md."""

    def __init__(self) -> None:
        self.warnings: List[str] = []

    def parse_file(self, file_path: str | Path) -> ParsedArchitecture:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Architecture documentation file not found: {path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        return self.parse_text(content)

    def parse_text(self, text: str) -> ParsedArchitecture:
        self.warnings = []
        doc = ParsedArchitecture(raw_text=text)

        # Extract title
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            doc.title = title_match.group(1).strip()

        # Extract fenced code blocks
        code_block_pattern = re.compile(
            r"```(?P<lang>[a-zA-Z0-9_\-\+]*)\n(?P<code>[\s\S]*?)```", re.MULTILINE
        )
        for m in code_block_pattern.finditer(text):
            lang = m.group("lang").lower().strip()
            code = m.group("code").strip()
            start_pos = m.start()
            line_no = text[:start_pos].count("\n") + 1
            doc.code_blocks.append({
                "language": lang,
                "content": code,
                "start_line": line_no,
            })

        # Split into sections based on ## headers
        section_pattern = re.compile(r"^##\s+(?:Section\s+([A-Za-z0-9]+):\s*)?(.+)$", re.MULTILINE)
        matches = list(section_pattern.finditer(text))
        sections_dict: Dict[str, str] = {}

        for i, match in enumerate(matches):
            sec_letter = match.group(1) or ""
            sec_title = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sec_content = text[start:end].strip()

            key = f"Section_{sec_letter.upper()}" if sec_letter else sec_title
            sections_dict[key] = sec_content
            # Also store by title
            sections_dict[sec_title.lower()] = sec_content

        doc.sections = sections_dict

        # Process specific known sections
        self._parse_section_a(sections_dict, doc)
        self._parse_section_b(sections_dict, doc)
        self._parse_section_c(sections_dict, doc)
        self._parse_section_d(sections_dict, doc)
        self._parse_section_e(sections_dict, doc)
        self._parse_section_f(sections_dict, doc)
        self._parse_section_g(sections_dict, doc)
        self._parse_section_h(sections_dict, doc)
        self._parse_section_i(sections_dict, doc)
        self._parse_section_j(sections_dict, doc)
        self._parse_section_k(sections_dict, doc)
        self._parse_section_l(sections_dict, doc)

        doc.warnings = list(self.warnings)
        return doc

    def _get_section_text(self, sections: Dict[str, str], *keys: str) -> str:
        for k in keys:
            if k in sections:
                return sections[k]
            # Try lowercased keys
            for sec_k, v in sections.items():
                if k.lower() in sec_k.lower():
                    return v
        return ""

    def _parse_section_a(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_A", "Executive Summary")
        doc.executive_summary = content

    def _parse_section_b(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_B", "Risks")
        if content:
            doc.risks = parse_markdown_table(content)

    def _parse_section_c(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_C", "Quality Attribute")
        if content:
            doc.qa_mapping = parse_markdown_table(content)

    def _parse_section_d(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_D", "Traceability Matrix")
        if content:
            doc.traceability_matrix = parse_markdown_table(content)

    def _parse_section_e(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_E", "Components")
        if not content:
            return

        # Split components by subheadings ### Component ...
        comp_blocks = re.split(r"^###\s+", content, flags=re.MULTILINE)
        for block in comp_blocks:
            block = block.strip()
            if not block:
                continue
            lines = block.splitlines()
            first_line = lines[0].strip()

            comp_info: Dict[str, Any] = {"raw": block}
            name_match = re.search(r"Name\*\*:\s*`?([A-Za-z0-9_]+)`?", block)
            comp_info["name"] = name_match.group(1) if name_match else first_line

            resp_match = re.search(r"Responsibilities\*\*:\s*(.+)$", block, re.MULTILINE)
            if resp_match:
                comp_info["responsibilities"] = resp_match.group(1).strip()

            tech_match = re.search(r"Tech Options Considered\*\*:\s*(.+)$", block, re.MULTILINE)
            if tech_match:
                comp_info["tech_options"] = [t.strip() for t in tech_match.group(1).split(",")]

            stack_match = re.search(r"Recommended Stack\*\*:\s*(.+)$", block, re.MULTILINE)
            if stack_match:
                comp_info["recommended_stack"] = stack_match.group(1).strip()

            doc.components.append(comp_info)

    def _parse_section_f(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_F", "API Contracts")
        # Find yaml code block
        yaml_match = re.search(r"```ya?ml\n([\s\S]*?)```", content)
        if yaml_match:
            raw_yaml = yaml_match.group(1)
            doc.openapi_raw = raw_yaml
            try:
                doc.openapi = yaml.safe_load(raw_yaml) or {}
            except Exception as e:
                self.warnings.append(f"Failed to parse OpenAPI YAML: {e}")
        else:
            # Search among all code blocks for openapi
            for cb in doc.code_blocks:
                if cb["language"] in ("yaml", "yml") and "openapi" in cb["content"]:
                    doc.openapi_raw = cb["content"]
                    try:
                        doc.openapi = yaml.safe_load(cb["content"]) or {}
                    except Exception as e:
                        self.warnings.append(f"Failed to parse OpenAPI YAML from code block: {e}")
                    break

    def _parse_section_g(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_G", "Data Schemas")
        # Extract proto
        proto_match = re.search(r"```proto(?:3)?\n([\s\S]*?)```", content)
        if proto_match:
            raw_proto = proto_match.group(1)
            parsed_proto = parse_proto(raw_proto)
            doc.proto = asdict(parsed_proto)
        else:
            for cb in doc.code_blocks:
                if cb["language"] in ("proto", "proto3"):
                    parsed_proto = parse_proto(cb["content"])
                    doc.proto = asdict(parsed_proto)
                    break

        # Extract SQL
        sql_match = re.search(r"```sql\n([\s\S]*?)```", content)
        if sql_match:
            raw_sql = sql_match.group(1)
            stmts, tables = parse_sql_ddl(raw_sql)
            doc.sql_ddl = stmts
            doc.sql_tables = tables
        else:
            for cb in doc.code_blocks:
                if cb["language"] == "sql":
                    stmts, tables = parse_sql_ddl(cb["content"])
                    doc.sql_ddl = stmts
                    doc.sql_tables = tables
                    break

    def _parse_section_h(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_H", "Infrastructure")
        yaml_match = re.search(r"```ya?ml\n([\s\S]*?)```", content)
        if yaml_match:
            raw_yaml = yaml_match.group(1)
            doc.k8s_raw = raw_yaml
            try:
                doc.k8s_manifest = list(yaml.safe_load_all(raw_yaml))
            except Exception as e:
                self.warnings.append(f"Failed to parse Kubernetes YAML: {e}")

    def _parse_section_i(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_I", "Security")
        doc.security = content

    def _parse_section_j(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_J", "Observability")
        doc.observability = {"raw": content}
        slo_match = re.search(r"SLOs?\*\*?:?\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if slo_match:
            doc.observability["slo"] = slo_match.group(1).strip()
        rto_match = re.search(r"RTO\s*(?:≤|<=|\:)?\s*([0-9]+\s*[a-zA-Z]+)", content, re.IGNORECASE)
        if rto_match:
            doc.observability["rto"] = rto_match.group(1).strip()
        rpo_match = re.search(r"RPO\s*(?:≤|<=|\:)?\s*([0-9]+\s*[a-zA-Z]+)", content, re.IGNORECASE)
        if rpo_match:
            doc.observability["rpo"] = rpo_match.group(1).strip()

    def _parse_section_k(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_K", "Testing Matrix")
        if content:
            doc.testing_matrix = parse_markdown_table(content)

    def _parse_section_l(self, sections: Dict[str, str], doc: ParsedArchitecture) -> None:
        content = self._get_section_text(sections, "Section_L", "Deliverables")
        # Extract deliverables list
        deliv_match = re.search(r"###\s*Deliverables List\s*([\s\S]*?)(?:###|$)", content)
        if deliv_match:
            items = []
            for line in deliv_match.group(1).splitlines():
                line = line.strip()
                if re.match(r"^(?:[0-9]+\.|\-|\*)\s+", line):
                    cleaned = re.sub(r"^(?:[0-9]+\.|\-|\*)\s+", "", line)
                    items.append(cleaned.strip())
            doc.deliverables = items

        # Extract tradeoffs
        tradeoff_match = re.search(r"###\s*Architecture Trade-offs[^\n]*\n([\s\S]*?)(?:###|$)", content)
        if tradeoff_match:
            doc.tradeoffs = tradeoff_match.group(1).strip()

        # Extract assumptions
        assump_match = re.search(r"###\s*Assumptions[^\n]*\n([\s\S]*?)(?:###|$)", content)
        if assump_match:
            doc.assumptions = assump_match.group(1).strip()
