"""
Optional live integration test against official DeepSeek API.
Skipped automatically unless DEEPSEEK_API_KEY is present in environment.
"""

import os
import pytest
from archforge.config import AgentConfig
from archforge.llm.deepseek_client import DeepSeekClient


@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY environment variable is not set; skipping live integration test.",
)
def test_live_deepseek_api_connection():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    cfg = AgentConfig.load()
    client = DeepSeekClient(
        api_key=api_key,
        base_url=cfg.base_url,
        model=cfg.model,
    )

    success, msg = client.test_connection()
    assert success is True, f"Live DeepSeek API test failed: {msg}"
