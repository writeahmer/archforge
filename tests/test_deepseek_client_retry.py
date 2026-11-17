import socket
from unittest.mock import MagicMock, patch
import httpx
import pytest

from archforge.llm.deepseek_client import (
    DeepSeekAPIError,
    DeepSeekClient,
    RateLimitError,
)


def test_deepseek_client_persistent_client():
    client = DeepSeekClient(api_key="test-key")
    h1 = client._get_client()
    h2 = client._get_client()
    assert h1 is h2, "Should reuse the persistent httpx.Client across calls"
    client.close()
    assert client._client is None


def test_deepseek_client_retry_on_network_and_dns_error():
    statuses = []
    client = DeepSeekClient(
        api_key="test-key",
        max_retries=3,
        status_callback=lambda msg: statuses.append(msg),
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {"content": "Resolved successfully", "tool_calls": []},
                "finish_reason": "stop",
            }
        ],
        "usage": {"total_tokens": 10},
    }

    # Simulate 2 transient DNS/network failures followed by a success
    call_count = 0

    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("[Errno 11002] getaddrinfo failed")
        elif call_count == 2:
            raise socket.gaierror(11002, "getaddrinfo failed")
        return mock_response

    with patch.object(httpx.Client, "post", side_effect=mock_post):
        with patch("time.sleep", return_value=None):
            resp = client.complete(
                messages=[{"role": "user", "content": "hello"}]
            )
            assert resp.content == "Resolved successfully"
            assert call_count == 3
            assert len(statuses) == 2
            assert "Temporary network/DNS hiccup" in statuses[0]
            assert "attempt 1/3" in statuses[0]
            assert "attempt 2/3" in statuses[1]

    client.close()


def test_deepseek_client_retry_exhaustion_raises():
    client = DeepSeekClient(api_key="test-key", max_retries=2)

    def mock_post(*args, **kwargs):
        raise httpx.ConnectError("[Errno 11002] getaddrinfo failed")

    with patch.object(httpx.Client, "post", side_effect=mock_post):
        with patch("time.sleep", return_value=None):
            with pytest.raises(DeepSeekAPIError) as exc_info:
                client.complete(messages=[{"role": "user", "content": "hello"}])
            assert "Network/DNS error after 2 attempts" in str(exc_info.value)

    client.close()
