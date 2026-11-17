"""
Sandbox and Security Engine for ArchForge.
Enforces path boundaries, command allowlisting, timeout limits, and secret redaction.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Permitted command line binaries for self-verification and build steps
ALLOWED_BINARIES: Set[str] = {
    "python",
    "python3",
    "pytest",
    "pip",
    "pip3",
    "node",
    "npm",
}


class SecurityError(Exception):
    """Raised when an operation violates security policies."""
    pass


class ExecutionSandbox:
    """Restricts filesystem operations and subprocess execution within output directory."""

    def __init__(self, root_dir: str | Path, api_key: str = "") -> None:
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key.strip()

    def resolve_safe_path(self, relative_path: str | Path) -> Path:
        """
        Resolves a path relative to the root directory and guarantees that
        it cannot escape the root boundary via traversal (e.g. '../').
        """
        # Strip leading slashes to prevent treating it as absolute root
        clean_path_str = str(relative_path).lstrip("/\\")
        candidate = (self.root_dir / clean_path_str).resolve()

        try:
            candidate.relative_to(self.root_dir)
        except ValueError:
            raise SecurityError(
                f"Path traversal access denied: '{relative_path}' resolves outside root directory '{self.root_dir}'"
            )

        return candidate

    def redact_secrets(self, text: str) -> str:
        """Redacts sensitive credentials like API keys from text logs or outputs."""
        if not text:
            return ""
        if self.api_key and len(self.api_key) > 5:
            text = text.replace(self.api_key, "[REDACTED_API_KEY]")
        # Also redact generic pattern for sk-... or dsk-...
        text = re.sub(r"(?:sk|dsk)-[a-zA-Z0-9]{20,}", "[REDACTED_API_KEY]", text)
        return text

    def run_command(self, command_line: str, timeout: int = 30) -> Tuple[int, str, str]:
        """
        Executes a sandboxed command inside root_dir if the executable is allowlisted.
        Returns (exit_code, stdout, stderr).
        """
        command_line = command_line.strip()
        if not command_line:
            return 1, "", "Empty command provided."

        # Parse command tokens safely
        try:
            tokens = shlex.split(command_line, posix=False)
        except Exception:
            tokens = command_line.split()

        if not tokens:
            return 1, "", "Failed to parse command arguments."

        base_cmd = Path(tokens[0]).name.lower()
        if base_cmd.endswith(".exe"):
            base_cmd = base_cmd[:-4]

        if base_cmd not in ALLOWED_BINARIES:
            raise SecurityError(
                f"Command '{tokens[0]}' is not permitted. Allowlisted commands: {sorted(list(ALLOWED_BINARIES))}"
            )

        # Sanitize environment variables so API keys are never leaked to child process
        env: Dict[str, str] = os.environ.copy()
        for sensitive_var in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "API_KEY", "SECRET_KEY"]:
            env.pop(sensitive_var, None)

        try:
            proc = subprocess.run(
                command_line,
                cwd=str(self.root_dir),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            stdout = self.redact_secrets(proc.stdout)
            stderr = self.redact_secrets(proc.stderr)
            return proc.returncode, stdout, stderr

        except subprocess.TimeoutExpired:
            return -1, "", f"Command execution timed out after {timeout} seconds."
        except Exception as e:
            return -1, "", f"Execution error: {e}"
