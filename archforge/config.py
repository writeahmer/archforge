"""
Configuration management and secure key storage for ArchForge.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Official DeepSeek endpoints and model constants
DEFAULT_BASE_URL: str = "https://api.deepseek.com"
# Official identifier in DeepSeek API docs is 'deepseek-chat' (DeepSeek-V3/V4 series).
# The user prompt also requests 'deepseek-v4-pro' as a default/configurable identifier.
DEFAULT_MODEL: str = "deepseek-chat"
SUPPORTED_MODELS = ["deepseek-chat", "deepseek-v4-pro", "deepseek-reasoner"]

DEFAULT_TEMPERATURE: float = 0.2
DEFAULT_MAX_TOKENS: int = 4096
DEFAULT_TIMEOUT_SECONDS: int = 60
DEFAULT_MAX_REPAIR_ROUNDS: int = 5
DEFAULT_MAX_AGENT_STEPS: int = 35


def get_appdata_dir() -> Path:
    """Returns the application data directory for ArchForge in the user profile."""
    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata)
    else:
        base = Path.home() / ".archforge"
    config_dir = base / "ArchForge"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _obfuscate(text: str) -> str:
    """Lightweight reversible obfuscation for local config storage (not a cryptographic secret)."""
    if not text:
        return ""
    encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    return "".join(reversed(encoded))


def _deobfuscate(text: str) -> str:
    """Deobfuscate text stored by _obfuscate."""
    if not text:
        return ""
    try:
        reversed_text = "".join(reversed(text))
        return base64.b64decode(reversed_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return text


@dataclass
class AgentConfig:
    api_key: str = ""
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    max_repair_rounds: int = DEFAULT_MAX_REPAIR_ROUNDS
    max_agent_steps: int = DEFAULT_MAX_AGENT_STEPS
    command_timeout_seconds: int = 30
    llm_timeout_seconds: int = 90
    save_api_key_locally: bool = False

    @classmethod
    def load(cls) -> AgentConfig:
        """Loads configuration from environment or persisted appdata config."""
        env_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        env_model = os.getenv("DEEPSEEK_MODEL", "").strip()
        env_base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip()

        cfg = cls()
        config_file = get_appdata_dir() / "config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "obf_key" in data and not env_key:
                    cfg.api_key = _deobfuscate(data.get("obf_key", ""))
                if "model" in data and not env_model:
                    cfg.model = data.get("model", DEFAULT_MODEL)
                if "base_url" in data and not env_base_url:
                    cfg.base_url = data.get("base_url", DEFAULT_BASE_URL)
                if "temperature" in data:
                    cfg.temperature = float(data.get("temperature", DEFAULT_TEMPERATURE))
                if "max_tokens" in data:
                    cfg.max_tokens = int(data.get("max_tokens", DEFAULT_MAX_TOKENS))
            except Exception:
                pass

        # Environment overrides persistent config if set
        if env_key:
            cfg.api_key = env_key
        if env_model:
            cfg.model = env_model
        if env_base_url:
            cfg.base_url = env_base_url

        return cfg

    def save(self) -> None:
        """Persists the current configuration to the user profile."""
        config_file = get_appdata_dir() / "config.json"
        data: Dict[str, Any] = {
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.save_api_key_locally and self.api_key:
            data["obf_key"] = _obfuscate(self.api_key)
        else:
            data["obf_key"] = ""

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_masked_api_key(self) -> str:
        """Returns a masked representation of the API key for safe display."""
        if not self.api_key:
            return ""
        if len(self.api_key) <= 8:
            return "********"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"
