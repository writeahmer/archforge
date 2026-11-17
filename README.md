# ArchForge

**ArchForge** is a simplified autonomous "Code Agent" inspired by Anthropic's **Claude Code**. Designed primarily as a Windows desktop application (with CLI and browser fallback options), ArchForge ingests architectural specifications and visual diagram models, detects inconsistencies, and synthesizes a full, runnable software project.

---

## 1. What ArchForge Does

Given:
1. **`Architecture_Documentation.md`**: Architecture specification containing sections A through L, quality attribute mappings, OpenAPI 3.0 contracts, Protocol Buffers (`.proto`), SQL DDL, Kubernetes manifests, and a traceability matrix.
2. **`Architecture_View.md`**: PlantUML diagrams across the 4+1 Architectural Views (Scenario, Logic, Process, Development, and Physical).

ArchForge autonomously produces:
- A clean, modular software project layout (e.g. `Game`, `Question`, `Score`, `Admin`, `User`).
- Full working Python source code implementing all use cases.
- `requirements.txt` and optional `Dockerfile`.
- `openapi.yaml`, `internal.proto`, `sql/game_ddl.sql`, and `k8s/deployment.yaml`.
- Fully regenerated and complete `traceability_matrix.csv`.
- An architectural guide `architecture.md` and project `README.md`.
- Automated test suites (`pytest`) verifying question arithmetic, API endpoints, and game state transitions.
- A deterministic `validation_report.md` documenting inconsistencies detected in the input documents and how they were reconciled.

---

## 2. Modes of Operation

### Primary Mode: Windows Desktop GUI (.exe)
ArchForge is packaged as a standalone, double-click-to-run Windows desktop application that requires **no preinstalled Python runtime** on target machines.
- **Run Standalone Executable**:
  ```cmd
  dist\ArchForge.exe
  ```
- **GUI Features**:
  - Masked DeepSeek API Key entry with show/hide toggle and credential testing.
  - Optional key persistence to `%APPDATA%\ArchForge\config.json`.
  - Configurable model name (defaults to `deepseek-chat` / `deepseek-v4-pro`) and base URL (`https://api.deepseek.com`).
  - File choosers for Architecture Documentation and Architecture Views.
  - Output directory picker.
  - "Generate" and "Cancel" buttons operating asynchronously in a background worker thread.
  - Live progress display: todo checklist with real-time status markers (`[✓]`, `[►]`, `[ ]`), tool call telemetry, model reasoning thoughts, and terminal logs.
  - "Open output folder" button upon task completion.

### CLI Mode (Command Line)
Direct command-line interface for automation or headless environments:
```bash
python -m archforge --doc samples/Architecture_Documentation.md --views samples/Architecture_View.md --out generated_project
```
Options:
- `--api-key <KEY>`: DeepSeek API key (defaults to `DEEPSEEK_API_KEY` environment variable).
- `--model <MODEL>`: DeepSeek model name (default: `deepseek-chat` / `deepseek-v4-pro`).
- `--base-url <URL>`: API endpoint (default: `https://api.deepseek.com`).
- `--mock`: Runs offline deterministic generator without making external API calls.

### Fallback Web Mode
A browser-based control panel launched via FastAPI and uvicorn:
```bash
python -m archforge.web
```
Access at: `http://127.0.0.1:5000`

---

## 3. Architecture & Mechanisms Borrowed from Claude Code

As documented in [`docs/RESEARCH.md`](docs/RESEARCH.md), ArchForge implements core architectural patterns from `ultraworkers/claw-code`, `Windy3f3f3f3f/how-claude-code-works`, and `anthropics/claude-code`:

1. **Deterministic Preprocessing Pipeline**:
   - `DocParser`: Extracts markdown sections A to L, code blocks, tables, schemas, and contracts.
   - `PlantUMLParser`: Categorizes `@startuml` blocks across the 4+1 views and parses elements.
   - `ConsistencyValidator`: Identifies discrepancies between text documentation and diagrams.
2. **Claude-Code-Style Agent Loop**:
   - Continuous `Think -> Act -> Observe -> Repeat` cycle.
   - Plan-first execution: creates and displays a todo checklist via `update_todo`.
   - Dynamic context management: compact summaries + on-demand document lookup tools (`read_architecture_section`, `read_diagram`) to minimize token usage.
3. **Safety & Sandboxing**:
   - Path confinement strictly enforces writes inside the designated output workspace.
   - Command execution allowlist (`python`, `pip`, `pytest`, `node`, `npm`).
   - Redaction of API keys and credentials from logs and subprocess environments.
4. **Self-Verification & Autonomous Repair**:
   - Executes generated test suite (`pytest tests/ -v`).
   - Catches test failures, feeds back tracebacks to the LLM, and repairs defects iteratively (up to 5 rounds).

---

## 4. Building the Windows Executable

> [!IMPORTANT]
> The Windows executable must be compiled on a Windows machine. If building in a CI/CD environment, use GitHub Actions with a `windows-latest` runner as configured in `.github/workflows/build-windows.yml`.

### Using PowerShell:
```powershell
.\build_exe.ps1
```

### Using Command Prompt:
```cmd
build_exe.bat
```

The compiled standalone executable will be generated at:
```
dist\ArchForge.exe
```

---

## 5. Running ArchForge Tests

ArchForge contains comprehensive automated tests for all components (doc parser, PlantUML parser, consistency validator, sandbox, tools, context manager, and the agent loop with a mock LLM):

```bash
pytest -v
```

All offline tests execute without requiring a DeepSeek API key. To run the optional live API integration test, export your key:
```bash
set DEEPSEEK_API_KEY=your_key_here
pytest -v
```

---

## 6. Assumptions & Architectural Trade-offs

1. **DeepSeek API Model Identifier**: In the official DeepSeek API, `deepseek-chat` is the standard production identifier pointing to the latest V3/V4 chat models. ArchForge defaults to `deepseek-chat` while fully supporting `deepseek-v4-pro` and `deepseek-reasoner`.
2. **Microservices vs. Modular Monolith**: The draft documentation proposed RabbitMQ and Elasticsearch clusters for a 6th-grade math game. ArchForge rationalizes this into a clean, single-process **FastAPI Modular Monolith** for instant local execution in classroom environments, while preserving enterprise deployment templates (`k8s/deployment.yaml`, `internal.proto`).
3. **Persisted Entites & DDL Naming**: The naming mismatch between `sql/question_ddl.sql` and `sql/game_ddl.sql` is resolved by providing unified entity schemas in `sql/game_ddl.sql` and aliasing `sql/question_ddl.sql`.
