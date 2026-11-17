# ArchForge: Autonomous Architectural Coding Agent

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-brightgreen.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Pytest](https://img.shields.io/badge/Tests-Passing%20(100%25)-success.svg)](https://pytest.org)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek--Chat%20%2F%20V4%20Pro-blueviolet.svg)](https://deepseek.com)

**ArchForge** is a cross-platform autonomous "Code Agent" inspired by Anthropic's **Claude Code** architecture. Built with a native Desktop GUI (with CLI and Web fallback modes), ArchForge ingests formal architectural specifications and visual 4+1 PlantUML diagrams, automatically detects and reconciles specification inconsistencies, and synthesizes a complete, production-grade, verified software project.

As a reference showcase, ArchForge ingests the system design for **Space Fractions**—a gamified educational math game for 6th-grade students—and autonomously outputs the full codebase, database schemas, test suites, and a cross-platform **Desktop GUI Game Application** running on **Windows**, **macOS**, and **Linux**.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Project Architecture & Directory Layout](#project-architecture--directory-layout)
3. [Step 1: Environment Setup (Windows, macOS, Linux)](#step-1-environment-setup-windows-macos-linux)
   - [1.1 System Prerequisites by OS](#11-system-prerequisites-by-os)
   - [1.2 Clone Repository](#12-clone-repository)
   - [1.3 Create & Activate Virtual Environment](#13-create--activate-virtual-environment)
   - [1.4 Install Dependencies](#14-install-dependencies)
   - [1.5 Configure DeepSeek API Key](#15-configure-deepseek-api-key)
4. [Step 2: How to Run the Coding Agent](#step-2-how-to-run-the-coding-agent)
   - [Option A: Desktop GUI (Recommended)](#option-a-desktop-gui-recommended)
   - [Option B: Pre-Compiled Standalone Executable (.exe / binary)](#option-b-pre-compiled-standalone-executable-exe--binary)
   - [Option C: Command-Line Interface (CLI)](#option-c-command-line-interface-cli)
   - [Option D: Web Control Panel](#option-d-web-control-panel)
5. [Step 3: Generate and Launch the Game as a Desktop Application](#step-3-generate-and-launch-the-game-as-a-desktop-application)
   - [3.1 Synthesizing the Game](#31-synthesizing-the-game)
   - [3.2 Inspecting Generated Artifacts](#32-inspecting-generated-artifacts)
   - [3.3 Launching the Desktop Game (Tkinter Cockpit GUI)](#33-launching-the-desktop-game-tkinter-cockpit-gui)
   - [3.4 Packaging the Game into a Standalone Desktop Executable](#34-packaging-the-game-into-a-standalone-desktop-executable)
   - [3.5 Launching the REST API Backend (Optional)](#35-launching-the-rest-api-backend-optional)
   - [3.6 Running the Game's Automated Test Suite](#36-running-the-games-automated-test-suite)
6. [Step 4: Compiling ArchForge into a Standalone Executable](#step-4-compiling-archforge-into-a-standalone-executable)
7. [Running ArchForge Internal Tests](#running-archforge-internal-tests)
8. [Claude Code Architectural Mechanisms](#claude-code-architectural-mechanisms)
9. [Troubleshooting & FAQ across Operating Systems](#troubleshooting--faq-across-operating-systems)

---

## Key Features

- **Multi-Modal Architectural Ingestion**: Ingests markdown architecture documentation (sections A through L, quality attribute mappings, OpenAPI 3.0 specs, Protobuf, SQL DDL, Kubernetes manifests) and PlantUML diagrams (4+1 views: Scenario, Logic, Process, Development, and Physical).
- **Cross-Platform Compatibility**: Full first-class support for **Windows (10/11)**, **macOS (Intel & Apple Silicon)**, and **Linux (Ubuntu, Debian, Fedora, Arch)**.
- **Automated Consistency Validation**: Detects cross-document discrepancies (e.g., entity naming mismatches, port conflicts, unreferenced microservices) and generates a deterministic `validation_report.md`.
- **Claude Code Autonomous Loop**: Implements plan-first execution with real-time todo checklists, dynamic context management, path-confinement sandboxing, tool-use telemetry, and autonomous multi-round test repair.
- **Dual Desktop Experience**:
  1. **ArchForge Desktop Studio**: A responsive Tkinter agent studio to monitor code generation, todos, and DeepSeek reasoning in real time.
  2. **Space Fractions Desktop Game**: A standalone, gamified deep-space cockpit GUI application for students, featuring fraction arithmetic challenges, animated starship shield bars, rank progression, and Hall of Fame leaderboards.
- **Offline / Mock Generation Mode**: Full deterministic project synthesis and testing available without requiring an active DeepSeek API key or internet access.

---

## Project Architecture & Directory Layout

```
archforge/
├── archforge/                   # Core agent package (Cross-Platform)
│   ├── agent/                   # Agent loop, context, planner, sandbox, tools, templates
│   ├── gui/                     # Tkinter Desktop GUI application for the coding agent
│   ├── llm/                     # DeepSeek client with resilient retries & mock fallback
│   ├── parsing/                 # Markdown doc parser, PlantUML parser, consistency validator
│   └── web/                     # Fallback FastAPI / HTML5 web studio
├── samples/                     # Architectural inputs
│   ├── Architecture_Documentation.md
│   └── Architecture_View.md
├── generated_project/           # Output directory generated by ArchForge
│   ├── src/                     # Synthesized modular monolith source code
│   │   ├── gui_game.py          # Native Desktop Game (Tkinter GUI - Win/macOS/Linux)
│   │   ├── main.py              # FastAPI REST API application entry point
│   │   ├── game/                # Game engine, session manager, state machine
│   │   ├── question/            # Fraction math generator and answer validator
│   │   ├── score/               # Leaderboard and scoring service
│   │   └── user/                # User authentication and player profiles
│   ├── sql/                     # SQLite / PostgreSQL DDL schemas
│   ├── tests/                   # 140+ automated pytest verification tests
│   ├── validation_report.md     # Consistency discrepancies and resolution report
│   ├── architecture.json        # Parsed structured documentation
│   └── views.json               # Parsed PlantUML diagrams
├── dist/                        # Standalone compiled executables
│   ├── ArchForge.exe / binary   # Standalone Coding Agent GUI
│   └── SpaceFractions.exe / bin # Standalone Desktop Game GUI
├── tests/                       # ArchForge internal unit & integration tests
├── ArchForge.spec               # PyInstaller specification for ArchForge
├── SpaceFractions.spec          # PyInstaller specification for SpaceFractions
├── build_exe.ps1                # Windows PowerShell build script
├── build_exe.bat                # Windows Command Prompt build batch script
└── requirements.txt             # Project Python dependencies
```

---

## Step 1: Environment Setup (Windows, macOS, Linux)

### 1.1 System Prerequisites by OS

ArchForge requires **Python 3.11** or **3.12** and **Git**. Choose your operating system below:

#### Windows
- Install Python 3.11+ from [python.org](https://www.python.org/downloads/) (ensure **"Add python.exe to PATH"** is checked).
- Install Git from [git-scm.com](https://git-scm.com/).
- Tkinter is included automatically with the official Python Windows installer.

#### macOS
- Install Python and Git via [Homebrew](https://brew.sh/):
  ```bash
  brew install python@3.12 git
  ```
- Tkinter is bundled with Homebrew Python. Verify with `python3 -m tkinter`.

#### Linux (Ubuntu / Debian / Mint)
- Install Python, virtual environment tools, Git, and Tkinter:
  ```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv python3-tk git
  ```

#### Linux (Fedora / RHEL)
- Install packages via `dnf`:
  ```bash
  sudo dnf install -y python3 python3-pip python3-tkinter git
  ```

#### Linux (Arch Linux)
- Install packages via `pacman`:
  ```bash
  sudo pacman -S python python-pip tk git
  ```

---

### 1.2 Clone Repository

```bash
git clone https://github.com/your-username/archforge.git
cd archforge
```

---

### 1.3 Create & Activate Virtual Environment

Isolate project dependencies within a local virtual environment:

#### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If you see an execution policy error, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

#### Windows (Command Prompt - CMD)
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

#### macOS & Linux (bash / zsh)
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 1.4 Install Dependencies

Upgrade package installer and install requirements:

- **Windows**:
  ```powershell
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  ```

- **macOS / Linux**:
  ```bash
  python3 -m pip install --upgrade pip
  pip install -r requirements.txt
  ```

---

### 1.5 Configure DeepSeek API Key

ArchForge uses DeepSeek LLMs (`deepseek-chat` / `deepseek-v4-pro` / `deepseek-reasoner`).

#### Configure via Environment Variable:

- **Windows (PowerShell)**:
  ```powershell
  $env:DEEPSEEK_API_KEY="sk-your-deepseek-api-key"
  ```

- **Windows (CMD)**:
  ```cmd
  set DEEPSEEK_API_KEY=sk-your-deepseek-api-key
  ```

- **macOS / Linux (bash / zsh)**:
  ```bash
  export DEEPSEEK_API_KEY="sk-your-deepseek-api-key"
  ```
  *(To persist across terminal sessions, add this line to your `~/.bashrc` or `~/.zshrc`)*

> [!TIP]
> **No API Key? Offline / Mock Mode is Fully Supported!**
> You can run the entire agent workflow without a DeepSeek API key by using the `--mock` flag in CLI or by leaving the API Key field blank in the Desktop GUI. ArchForge will execute its deterministic synthesizer engine offline.

---

## Step 2: How to Run the Coding Agent

ArchForge provides four execution modes tailored to your workflow:

### Option A: Desktop GUI (Recommended)

Launch the native Tkinter graphical studio across all platforms:

- **Windows**:
  ```powershell
  python -m archforge
  ```
- **macOS / Linux**:
  ```bash
  python3 -m archforge
  ```

*(You can also pass `--gui` explicitly: `python -m archforge --gui`)*

#### Desktop GUI Workflow:
1. **API Configuration**: Enter your DeepSeek API Key (masked with show/hide toggle), select the model (default: `deepseek-chat`), and test connectivity. *(Leave blank for offline mock mode).*
2. **Architecture Specification**: Verify or browse for `samples/Architecture_Documentation.md`.
3. **Architecture Views**: Verify or browse for `samples/Architecture_View.md`.
4. **Target Output Directory**: Defaults to `generated_project/`.
5. **Execution**: Click **"🚀 Generate Project"**.
6. **Live Telemetry**:
   - **Todo Tracker**: Real-time status indicators (`[✓]` completed, `[►]` in-progress, `[ ]` pending).
   - **Console & Thoughts**: Live streaming DeepSeek reasoning, tool execution (`write_file`, `run_command`), and validation logs.
7. **Complete**: When finished, click **"📂 Open Output Folder"** to inspect the generated code.

---

### Option B: Pre-Compiled Standalone Executable (.exe / binary)

If using a pre-compiled standalone release, no Python environment is required:

- **Windows**:
  ```cmd
  dist\ArchForge.exe
  ```
  *(or double-click `dist\ArchForge.exe` in Windows Explorer)*

- **Linux / macOS**:
  ```bash
  ./dist/ArchForge
  ```

---

### Option C: Command-Line Interface (CLI)

Ideal for headless servers, containers, or script automation:

#### 1. Live DeepSeek Generation:
- **Windows (PowerShell)**:
  ```powershell
  python -m archforge --doc samples/Architecture_Documentation.md --views samples/Architecture_View.md --out generated_project --api-key sk-your-api-key
  ```
- **macOS / Linux**:
  ```bash
  python3 -m archforge --doc samples/Architecture_Documentation.md --views samples/Architecture_View.md --out generated_project --api-key sk-your-api-key
  ```

#### 2. Offline / Deterministic Mock Mode (Zero tokens, 100% offline):
- **Windows (PowerShell / CMD)**:
  ```powershell
  python -m archforge --doc samples/Architecture_Documentation.md --views samples/Architecture_View.md --out generated_project --mock
  ```
- **macOS / Linux**:
  ```bash
  python3 -m archforge --doc samples/Architecture_Documentation.md --views samples/Architecture_View.md --out generated_project --mock
  ```

#### CLI Options Reference:
| Option | Default | Description |
|--------|---------|-------------|
| `--doc` | `samples/Architecture_Documentation.md` | Path to markdown architecture document. |
| `--views` | `samples/Architecture_View.md` | Path to PlantUML architecture views. |
| `--out` | `generated_project` | Output directory for the synthesized project. |
| `--api-key` | `$DEEPSEEK_API_KEY` | DeepSeek API key. |
| `--model` | `deepseek-chat` | Model ID (`deepseek-chat`, `deepseek-v4-pro`, `deepseek-reasoner`). |
| `--base-url`| `https://api.deepseek.com` | API endpoint URL. |
| `--mock` | `False` | Run deterministic synthesis offline without calling external APIs. |

---

### Option D: Web Control Panel

ArchForge embeds an asynchronous FastAPI web interface for browser-based orchestration:

- **Windows**:
  ```powershell
  python -m archforge.web
  ```
- **macOS / Linux**:
  ```bash
  python3 -m archforge.web
  ```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## Step 3: Generate and Launch the Game as a Desktop Application

### 3.1 Synthesizing the Game

Run the agent to synthesize the project:

- **Windows**:
  ```powershell
  python -m archforge --doc samples/Architecture_Documentation.md --views samples/Architecture_View.md --out generated_project --mock
  ```
- **macOS / Linux**:
  ```bash
  python3 -m archforge --doc samples/Architecture_Documentation.md --views samples/Architecture_View.md --out generated_project --mock
  ```

The agent executes the deterministic preprocessing pipeline (doc parsing, PlantUML parsing, and consistency reconciliation), scaffolds the project structure, generates source files, and verifies them via `pytest`.

---

### 3.2 Inspecting Generated Artifacts

Once generation finishes, inspect the contents of `generated_project/`:

- **Windows**:
  ```powershell
  cd generated_project
  dir
  ```
- **macOS / Linux**:
  ```bash
  cd generated_project
  ls -la
  ```

Key files generated:
- `src/gui_game.py`: The cross-platform Tkinter desktop game application.
- `src/main.py`: The FastAPI REST API entry point.
- `src/`: Modular packages (`game`, `question`, `score`, `user`, `admin`).
- `sql/game_ddl.sql`: Database schema definitions (SQLite / PostgreSQL).
- `tests/`: Automated unit and integration test suite (140+ test cases).
- `validation_report.md`: Reconciled architecture discrepancies and audit log.

---

### 3.3 Launching the Desktop Game (Tkinter Cockpit GUI)

The synthesized game is **Space Fractions: Mission to Sector Math 🚀**, an educational game where students navigate deep space by answering fraction challenges to restore shields.

#### Launch via Python (All Operating Systems):

1. From the repository root, enter `generated_project`:
   - **Windows**:
     ```powershell
     cd generated_project
     pip install -r requirements.txt
     python src/gui_game.py
     ```
   - **macOS / Linux**:
     ```bash
     cd generated_project
     pip install -r requirements.txt
     python3 src/gui_game.py
     ```

#### Cross-Platform Game Features:
- **Cockpit Dashboard**: Displays real-time starship shields, score counter, streak multipliers, and pilot ranks (Cadet &rarr; Admiral).
- **Fraction Engine**: Dynamically generates addition, subtraction, multiplication, and division questions across 3 difficulty tiers.
- **Hall of Fame**: SQLite-backed local leaderboard (`spacefractions.db`) tracking top scores, accuracy rates, and game completion timestamps.
- **Native OS Integration**: High-DPI scaling on Windows (`windll.shcore`), native menu bars on macOS, and X11/Wayland responsiveness on Linux.

---

### 3.4 Packaging the Game into a Standalone Desktop Executable

You can compile the synthesized game into a standalone binary that runs on target computers without a Python installation:

From the root directory:

#### On Windows:
```powershell
pyinstaller SpaceFractions.spec --clean --noconfirm
```
Produces: `dist\SpaceFractions.exe` (run with `.\dist\SpaceFractions.exe` or double-click in Explorer).

#### On macOS:
```bash
pyinstaller SpaceFractions.spec --clean --noconfirm
```
Produces: `dist/SpaceFractions` (standalone executable binary).

#### On Linux:
```bash
pyinstaller SpaceFractions.spec --clean --noconfirm
```
Produces: `dist/SpaceFractions` (standalone ELF binary).

---

### 3.5 Launching the REST API Backend (Optional)

You can also run the synthesized application as a headless REST API service:

- **Windows**:
  ```powershell
  cd generated_project
  uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
  ```
- **macOS / Linux**:
  ```bash
  cd generated_project
  uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
  ```

- **Interactive Swagger UI**: Navigate to `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: Navigate to `http://127.0.0.1:8000/redoc`
- **Health Endpoint**: `GET http://127.0.0.1:8000/ops/health`

---

### 3.6 Running the Game's Automated Test Suite

The generated game includes over 140 automated tests:

- **Windows**:
  ```powershell
  cd generated_project
  pytest tests/ -v
  ```
- **macOS / Linux**:
  ```bash
  cd generated_project
  pytest tests/ -v
  ```

All 142 tests pass across all platforms:
```text
generated_project/tests/test_fraction.py ...... [PASSED]
generated_project/tests/test_state_machine.py .. [PASSED]
generated_project/tests/test_api.py ............ [PASSED]
======================= 142 passed in 7.85s =======================
```

---

## Step 4: Compiling ArchForge into a Standalone Executable

To compile the **ArchForge Coding Agent** itself into a standalone desktop executable:

### Windows:
- **Using PowerShell**:
  ```powershell
  .\build_exe.ps1
  ```
- **Using Command Prompt**:
  ```cmd
  build_exe.bat
  ```

### macOS & Linux:
Run PyInstaller directly with the included specification file:
```bash
pyinstaller ArchForge.spec --clean --noconfirm
```

The resulting standalone executable will be located in:
- Windows: `dist\ArchForge.exe`
- macOS / Linux: `dist/ArchForge`

---

## Running ArchForge Internal Tests

ArchForge contains comprehensive test suites covering the documentation parser, PlantUML parser, consistency validator, sandbox confinement, tool dispatch, and mock agent loops:

- **Windows**:
  ```powershell
  pytest -v
  ```
- **macOS / Linux**:
  ```bash
  pytest -v
  ```

To run the optional live DeepSeek API connectivity test:
- **Windows (PowerShell)**:
  ```powershell
  $env:DEEPSEEK_API_KEY="sk-your-key"
  pytest tests/test_live_deepseek_optional.py -v
  ```
- **macOS / Linux**:
  ```bash
  export DEEPSEEK_API_KEY="sk-your-key"
  pytest tests/test_live_deepseek_optional.py -v
  ```

---

## Claude Code Architectural Mechanisms

ArchForge incorporates the core design patterns of Anthropic's Claude Code:

1. **Deterministic Preprocessing Pipeline**:
   - `DocParser`: Extracts markdown sections A through L, tables, code blocks, and data contracts.
   - `PlantUMLParser`: Categorizes `@startuml` diagrams across the 4+1 views (Scenario, Logic, Process, Development, Physical).
   - `ConsistencyValidator`: Identifies discrepancies between text specifications and diagrams (e.g. DDL naming, missing endpoints, port mismatches).
2. **Plan-First Agent Execution**:
   - Dynamic plan management via `update_todo`.
   - Real-time status reporting (`completed`, `in_progress`, `pending`) broadcast to the UI.
3. **Sandboxed Execution & Confinement**:
   - Strict path confinement ensuring all file writes remain within the target output workspace.
   - Command allowlist restricting subprocess execution to approved development binaries (`python`, `pip`, `pytest`).
   - Secret redaction preventing API keys from leaking into log files or subprocess environments.
4. **Self-Verification & Autonomous Repair**:
   - Automatically executes test suites (`pytest tests/ -v`).
   - Catches test failures, feeds tracebacks back to the LLM, and autonomously applies source code repairs.

---

## Troubleshooting & FAQ across Operating Systems

### 1. Tkinter Missing on Linux (`ModuleNotFoundError: No module named '_tkinter'`)
On some Linux distributions, Tkinter is not installed by default with Python. Install it using your distribution's package manager:
- Ubuntu / Debian / Mint: `sudo apt install python3-tk`
- Fedora / RHEL: `sudo apt install python3-tkinter`
- Arch Linux: `sudo pacman -S tk`

### 2. High-DPI Scaling on Windows vs. macOS
- **Windows**: ArchForge and SpaceFractions automatically configure Windows DPI awareness via `ctypes.windll.shcore.SetProcessDpiAwareness(1)`.
- **macOS**: High-DPI (Retina) scaling is handled natively by macOS Quartz window manager.

### 3. PowerShell Script Execution Policy on Windows
If running `.\venv\Scripts\Activate.ps1` produces a script execution policy error:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### 4. Running Without Internet or API Keys (Offline Mock Mode)
Pass `--mock` on the command line or leave the API Key field empty in the GUI. ArchForge will synthesize the complete Space Fractions project and run all 142 verification tests locally without consuming any tokens or making external network calls.

### 5. Where is the SQLite Database Created?
- When running from source (`python src/gui_game.py`), the database file is saved at `generated_project/spacefractions.db`.
- When running the standalone executable (`SpaceFractions.exe` or `SpaceFractions`), the database is created in the executable's directory.
- You can customize the database location on any OS by setting the `SPACEFRACTIONS_DB` environment variable:
  - **Windows (PowerShell)**: `$env:SPACEFRACTIONS_DB="C:\path\to\spacefractions.db"`
  - **macOS / Linux**: `export SPACEFRACTIONS_DB="/path/to/spacefractions.db"`

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
