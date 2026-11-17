"""
Tests for ExecutionSandbox: path boundaries, command allowlisting, and secret redaction.
"""

from pathlib import Path
import pytest
from archforge.agent.sandbox import ExecutionSandbox, SecurityError


def test_sandbox_path_boundary(tmp_path):
    sandbox = ExecutionSandbox(tmp_path)

    # Valid internal paths
    p1 = sandbox.resolve_safe_path("src/game.py")
    assert p1 == (tmp_path / "src" / "game.py").resolve()

    # Traversal attack rejected
    with pytest.raises(SecurityError):
        sandbox.resolve_safe_path("../outside.py")

    with pytest.raises(SecurityError):
        sandbox.resolve_safe_path("../../windows/system32/cmd.exe")


def test_sandbox_command_allowlist(tmp_path):
    sandbox = ExecutionSandbox(tmp_path)

    # Allowed: python
    code, stdout, stderr = sandbox.run_command("python -c \"print('sandbox_test_ok')\"")
    assert code == 0
    assert "sandbox_test_ok" in stdout

    # Disallowed commands rejected
    with pytest.raises(SecurityError):
        sandbox.run_command("curl http://example.com")

    with pytest.raises(SecurityError):
        sandbox.run_command("powershell Get-Process")


def test_sandbox_secret_redaction(tmp_path):
    fake_key = "dsk-99887766554433221100aabbccddeeff"
    sandbox = ExecutionSandbox(tmp_path, api_key=fake_key)

    raw_text = f"Connection established using key {fake_key} successfully."
    redacted = sandbox.redact_secrets(raw_text)

    assert fake_key not in redacted
    assert "[REDACTED_API_KEY]" in redacted
