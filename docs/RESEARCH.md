# ArchForge Research: Architecture & Mechanisms of Claude Code

This document analyzes the architecture and design patterns of Anthropic's **Claude Code** and its open-source reference implementations, specifically:
- [`ultraworkers/claw-code`](https://github.com/ultraworkers/claw-code) (Rust & Python reimplementation of the CLI agent harness)
- [`Windy3f3f3f3f/how-claude-code-works`](https://github.com/Windy3f3f3f3f/how-claude-code-works) (Deep-dive architectural analysis and reverse-engineering of Claude Code)
- [`anthropics/claude-code`](https://github.com/anthropics/claude-code) (Official client architecture, UX principles, and security boundaries)

Below are the key architectural mechanisms studied and how **ArchForge** adapts them into a simplified, robust Windows code agent.

---

## 1. The Agent Loop (Think → Tool Call → Observe → Repeat)

### Reference Design
In Claude Code, the agent loop (`QueryEngine` / session manager) drives multi-turn interactions through an event-driven loop rather than a single-shot execution:
1. **User Request / Prompt Injection**: The user's goal or repair instructions are ingested.
2. **Model Invocation (Think)**: Accumulated context, system instructions, and tool definitions are submitted to the LLM. The model returns either conversational text or one or more structured tool calls (`tool_use`).
3. **Tool Execution (Act)**: The engine validates tool arguments against JSON schemas, confirms security/permission constraints, and invokes the underlying tool.
4. **Observation Feedback (Observe)**: The output (stdout, stderr, exit code, or error message) is packaged into a `tool_result` message and appended to the conversation history.
5. **Termination Conditions**: The loop terminates when the model declares completion (`finish` tool or no further tool calls), when an unrecoverable error occurs, or when the step budget is exhausted.

### ArchForge Implementation
ArchForge implements an explicit, transparent `AgentLoop` in `archforge/agent/loop.py`:
- Configurable step limit (default: 30 steps) to prevent runaways.
- State machine tracking `INITIALIZING` → `PLANNING` → `EXECUTING` → `SELF_REPAIR` → `COMPLETED` / `FAILED`.
- Multi-channel event dispatching via `archforge/agent/events.py` so that desktop GUI and web frontends receive real-time notifications for each phase, thought, tool invocation, and observation.

---

## 2. Tool Registry and JSON Schemas

### Reference Design
Claude Code employs a unified tool interface across 60+ built-in tools (and dynamic MCP tools):
- Each tool defines a name, human-readable description, JSON schema for input parameters, and validation rules.
- Common tools include `Bash`, `GlobTool`, `GrepTool`, `FileReadTool`, `FileWriteTool`, `FileEditTool`, and `TodoTracker`.
- The interface enforces strict input validation, timeout parameters, and standardized error responses so the model receives actionable failure explanations (e.g. "Target string not found" instead of an unhandled crash).

### ArchForge Implementation
ArchForge standardizes tool definitions in `archforge/agent/tools.py` conforming to OpenAI function-calling specifications:
- **`list_dir(subpath)`**: Inspect directory contents relative to the output workspace.
- **`read_file(path)`**: Read contents of a project file.
- **`write_file(path, content)`**: Atomically write or overwrite files within the sandboxed target.
- **`edit_file(path, target, replacement)`**: Precise single-string search-and-replace, requiring exact whitespace match to prevent unintentional drift.
- **`search_in_files(pattern, subpath)`**: Grep-style regular expression or literal search across generated project files.
- **`run_command(command)`**: Execute authorized build, verification, and testing commands (`pytest`, `python`, `pip`).
- **`read_architecture_section(section_name)`**: Dynamic retrieval of specific documentation sections on demand.
- **`read_diagram(diagram_name)`**: Dynamic retrieval of specific PlantUML diagram models on demand.
- **`update_todo(todos)`**: Update the progress checklist displayed live in the user interface.
- **`finish(summary)`**: Signal project generation and validation completion.

---

## 3. System Prompt Construction & Caching Strategies

### Reference Design
Claude Code organizes its system prompt hierarchically:
1. **Role & Identity**: The persona of an elite autonomous software engineer.
2. **Environment & Sandbox Rules**: Directory limitations, available binaries, OS quirks.
3. **Behavioral Guidelines**: Incremental verification, minimal unnecessary modifications, test-driven validation.
4. **Tool Documentation**: Concise schemas and best practices for tool usage.
5. **Prompt Caching Structure**: Static instructions are ordered before dynamic session variables to leverage LLM prompt caching (lowering cost and latency).

### ArchForge Implementation
In `archforge/agent/prompts.py`:
- The system prompt defines ArchForge as a Senior Software Architect and Engineer tasked with synthesizing architecture specifications into runnable code.
- Clear structural guidelines (e.g., modular monolith vs microservice trade-offs, standard Python package conventions, test requirements).
- Domain rules resolving the deliberate architectural contradictions discovered during the preprocessing validation phase.

---

## 4. Context & Memory Management

### Reference Design
Stuffing hundreds of pages of architecture docs, multiple PlantUML diagrams, and large command outputs into the context window causes token exhaustion, high inference latency, and hallucination. Claude Code handles this via:
- **Progressive Compression**: Summarizing older message turns.
- **Dynamic Output Truncation**: Limiting stdout/stderr outputs to a safe token ceiling (e.g., returning the first and last N lines of long outputs).
- **On-Demand Retrieval**: Instead of keeping full documents in context, giving the agent search and section-lookup tools.

### ArchForge Implementation
In `archforge/agent/context.py`:
- Preprocessing parses `Architecture_Documentation.md` and `Architecture_View.md` into structured JSON models (`architecture.json` and `views.json`).
- The initial agent context is provided with a compact architectural index (executive summary, component listing, view catalog, and key validation findings).
- Tools `read_architecture_section(name)` and `read_diagram(name)` enable the model to inspect detailed OpenAPI specs, DDLs, and diagrams only when implementing those specific components.
- Tool output truncation caps terminal/file reading buffers (e.g., 4000 characters) with clear indication of truncated length.

---

## 5. Planning and Todo Tracking

### Reference Design
Claude Code uses a "Plan Mode" and a dedicated `TodoTracker` tool:
- The agent explicitly outlines the subtasks required to solve an objective.
- Tasks are categorized with statuses (`pending`, `in_progress`, `completed`).
- Maintaining an explicit todo list grounds the LLM, reducing catastrophic forgetting and avoiding premature task abandonment.

### ArchForge Implementation
In `archforge/agent/planner.py`:
- Phase 1 of execution enforces a Planning Turn: the model analyzes the architecture summary and outputs a structured list of actionable steps.
- The `update_todo` tool allows the agent to check off completed items in real time.
- The UI (both Tkinter desktop and Web fallback) renders this checklist with live visual checkmarks.

---

## 6. Permission and Safety Model

### Reference Design
Claude Code implements defense-in-depth safety:
- **Filesystem Isolation**: Strictly limiting read and write paths to the project root.
- **Command Whitelisting & Sandboxing**: Disallowing arbitrary destructive shell operations (e.g., `rm -rf /`, network exfiltration).
- **Credential Protection**: Redacting API keys and tokens from logs, shell environments, and stdout streams.

### ArchForge Implementation
In `archforge/agent/sandbox.py`:
- **Path Confinement**: All file paths are resolved relative to `output_dir`. Path traversal attacks (such as `../../windows/system32`) are immediately blocked and returned as security violations.
- **Command Allowlist**: Only sanctioned executable names (`python`, `pip`, `pytest`, `node`, `npm`) are permitted.
- **Process Isolation**: Commands run with an execution timeout (default 30 seconds) in a subprocess sandboxed to the target directory.
- **Environment Sanitization**: `DEEPSEEK_API_KEY` and other sensitive environment variables are scrubbed from child process environments, logs, and GUI telemetry.

---

## 7. Error Recovery and Self-Repair

### Reference Design
Claude Code does not assume generated code is flawless. It verifies results by:
- Running project tests or build commands immediately after authoring code.
- Capturing stack traces and test failure reports.
- Feeding back the error diagnostics to the LLM to inspect the offending files, perform targeted edits, and re-run tests.

### ArchForge Implementation
In `archforge/agent/loop.py`:
- After code generation, ArchForge triggers a **Self-Verification Cycle**.
- It invokes `pytest` on the generated test suite (`tests/`).
- If any test fails, ArchForge parses the failure output, injects the traceback into the model's conversation, and instructs the agent to fix the defect.
- Up to 5 repair iterations are supported, ensuring generated projects are fully functional and verifiable out of the box.

---

## 8. Summary Comparison

| Capability | Claude Code | ArchForge (Simplified) |
| :--- | :--- | :--- |
| **Runtime Target** | Multi-platform CLI (Node/TypeScript) | Windows Desktop App (`.exe`) + CLI + Web Fallback |
| **LLM Provider** | Anthropic Claude 3.5 / 3.7 | DeepSeek Official API (OpenAI-compatible) |
| **Agent Loop** | QueryEngine event loop | Python `AgentLoop` with State Machine |
| **Planning** | Plan Mode / TodoTracker | `TodoPlanner` + `update_todo` GUI integration |
| **Context Strategy**| Cache-aligned prompt + dynamic compression | Architecture index + On-demand section lookup tools |
| **Sandboxing** | AST bash analysis + path validation | Strict output path boundary + command allowlist |
| **Verification** | Test runner & repair loop | Automated `pytest` run-and-repair loop (max 5 rounds) |
