"""
Official DeepSeek API client for ArchForge.
Supports OpenAI-compatible chat completions, function/tool calling, retries, and cancellation.
"""

from __future__ import annotations

import json
import logging
import socket
import time
from dataclasses import dataclass, field
from threading import Event
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

import httpx

logger = logging.getLogger(__name__)


class DeepSeekAPIError(Exception):
    """Base exception for DeepSeek API failures."""
    pass


class AuthenticationError(DeepSeekAPIError):
    """Raised on HTTP 401 (Invalid API Key)."""
    pass


class RateLimitError(DeepSeekAPIError):
    """Raised on HTTP 429 (Rate limit reached or quota exhausted)."""
    pass


class InsufficientBalanceError(DeepSeekAPIError):
    """Raised on HTTP 402 (Insufficient Balance / Payment Required)."""
    pass


class ContextLengthExceededError(DeepSeekAPIError):
    """Raised on HTTP 400 when context length exceeds limit."""
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]
    raw_arguments: str = ""


@dataclass
class ChatCompletionResponse:
    content: str = ""
    reasoning_content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)


class DeepSeekClient:
    """Client for the official DeepSeek API (/chat/completions)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: float = 90.0,
        max_retries: int = 6,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        # If model is 'deepseek-v4-pro', map or keep as configured
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.status_callback = status_callback
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Returns or initializes a persistent HTTP client with connection pooling and keep-alive."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.timeout, connect=25.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=120.0),
                follow_redirects=True,
            )
        return self._client

    def _reset_client(self) -> None:
        """Closes and resets the cached HTTP client so the next attempt opens a clean socket."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def close(self) -> None:
        """Cleanly releases persistent HTTP connections."""
        self._reset_client()

    def __enter__(self) -> DeepSeekClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _notify_status(self, msg: str) -> None:
        if self.status_callback:
            try:
                self.status_callback(msg)
            except Exception:
                pass

    def _interruptible_sleep(self, seconds: float, cancel_event: Optional[Event] = None) -> None:
        """Sleeps for given duration while immediately responding to cancel_event."""
        if cancel_event is None:
            time.sleep(seconds)
            return
        end_time = time.time() + seconds
        while time.time() < end_time:
            if cancel_event.is_set():
                raise DeepSeekAPIError("Operation cancelled by user.")
            time.sleep(min(0.25, max(0.05, end_time - time.time())))

    def test_connection(self) -> Tuple[bool, str]:
        """Validates API credentials with a minimal ping request."""
        if not self.api_key:
            return False, "API key is empty."

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }

        try:
            client = self._get_client()
            res = client.post(url, headers=headers, json=payload, timeout=20.0)
            if res.status_code == 200:
                return True, "Connection successful."
            if res.status_code == 401:
                return False, "Authentication failed (401): Invalid API Key."
            if res.status_code == 402:
                return False, "Insufficient Balance (HTTP 402): DeepSeek account balance is insufficient. Please top up your account at https://platform.deepseek.com."
            if res.status_code == 404:
                return False, f"Model '{self.model}' not found on endpoint. Try 'deepseek-chat'."
            return False, f"API returned status {res.status_code}: {res.text[:100]}"
        except Exception as e:
            self._reset_client()
            return False, f"Network error connecting to {self.base_url}: {e}"

    def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        cancel_event: Optional[Event] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> ChatCompletionResponse:
        """
        Sends chat completion request with exponential backoff on retries.
        Supports tool definitions and streaming chunk callback.
        """
        if cancel_event and cancel_event.is_set():
            raise DeepSeekAPIError("Operation cancelled by user.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": on_chunk is not None,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        backoff = 2.0
        for attempt in range(1, self.max_retries + 1):
            if cancel_event and cancel_event.is_set():
                raise DeepSeekAPIError("Operation cancelled by user.")

            try:
                if on_chunk is not None:
                    return self._stream_request(url, headers, payload, cancel_event, on_chunk)
                else:
                    return self._sync_request(url, headers, payload, cancel_event)

            except (httpx.TimeoutException, httpx.NetworkError, socket.gaierror, OSError) as net_err:
                self._reset_client()
                if attempt == self.max_retries:
                    err_msg = (
                        f"Network/DNS error after {self.max_retries} attempts: {net_err}. "
                        "Please check your internet connection or DNS resolver."
                    )
                    logger.error(err_msg)
                    raise DeepSeekAPIError(err_msg)

                retry_msg = (
                    f"Temporary network/DNS hiccup ({net_err}). Retrying in {backoff:.0f}s "
                    f"(attempt {attempt}/{self.max_retries})..."
                )
                logger.warning(retry_msg)
                self._notify_status(f"[WARN] {retry_msg}")
                self._interruptible_sleep(backoff, cancel_event)
                backoff = min(backoff * 2.0, 30.0)

            except RateLimitError as rl_err:
                if attempt == self.max_retries:
                    raise rl_err
                retry_msg = f"Rate limited (429). Retrying in {backoff:.0f}s (attempt {attempt}/{self.max_retries})..."
                logger.warning(retry_msg)
                self._notify_status(f"[WARN] {retry_msg}")
                self._interruptible_sleep(backoff, cancel_event)
                backoff = min(backoff * 2.5, 60.0)

            except DeepSeekAPIError as err:
                # Fatal errors like 401 should not retry
                raise err

        raise DeepSeekAPIError("Exceeded maximum retries.")

    def _sync_request(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        cancel_event: Optional[Event],
    ) -> ChatCompletionResponse:
        payload["stream"] = False
        client = self._get_client()
        res = client.post(url, headers=headers, json=payload)
        self._check_status_code(res)

        data = res.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning_content") or ""
        finish_reason = choice.get("finish_reason", "stop")
        usage = data.get("usage", {})

        parsed_tool_calls: List[ToolCall] = []
        if "tool_calls" in msg and msg["tool_calls"]:
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    args = {"raw_argument": raw_args}
                parsed_tool_calls.append(
                    ToolCall(id=tc.get("id", ""), name=fn_name, arguments=args, raw_arguments=raw_args)
                )

        return ChatCompletionResponse(
            content=content,
            reasoning_content=reasoning,
            tool_calls=parsed_tool_calls,
            finish_reason=finish_reason,
            usage=usage,
        )

    def _stream_request(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        cancel_event: Optional[Event],
        on_chunk: Callable[[str], None],
    ) -> ChatCompletionResponse:
        payload["stream"] = True
        accumulated_content: List[str] = []
        accumulated_reasoning: List[str] = []
        tool_call_chunks: Dict[int, Dict[str, Any]] = {}
        finish_reason = "stop"

        client = self._get_client()
        with client.stream("POST", url, headers=headers, json=payload) as response:
            self._check_status_code(response)

            for line in response.iter_lines():
                if cancel_event and cancel_event.is_set():
                    raise DeepSeekAPIError("Operation cancelled during streaming.")
                if not line:
                    continue
                if line.startswith("data: "):
                    line_data = line[6:].strip()
                    if line_data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line_data)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            text_piece = delta["content"]
                            accumulated_content.append(text_piece)
                            on_chunk(text_piece)
                        if "reasoning_content" in delta and delta["reasoning_content"]:
                            accumulated_reasoning.append(delta["reasoning_content"])
                        if "finish_reason" in choices[0] and choices[0]["finish_reason"]:
                            finish_reason = choices[0]["finish_reason"]

                        if "tool_calls" in delta and delta["tool_calls"]:
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                if idx not in tool_call_chunks:
                                    tool_call_chunks[idx] = {
                                        "id": tc.get("id", ""),
                                        "name": tc.get("function", {}).get("name", ""),
                                        "args": "",
                                    }
                                if "id" in tc and tc["id"]:
                                    tool_call_chunks[idx]["id"] = tc["id"]
                                if "function" in tc:
                                    fn_delta = tc["function"]
                                    if "name" in fn_delta and fn_delta["name"]:
                                        tool_call_chunks[idx]["name"] = fn_delta["name"]
                                    if "arguments" in fn_delta and fn_delta["arguments"]:
                                        tool_call_chunks[idx]["args"] += fn_delta["arguments"]
                    except json.JSONDecodeError:
                        continue

        parsed_tool_calls: List[ToolCall] = []
        for idx in sorted(tool_call_chunks.keys()):
            tc_info = tool_call_chunks[idx]
            raw_args = tc_info["args"]
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                args = {"raw_argument": raw_args}
            parsed_tool_calls.append(
                ToolCall(id=tc_info["id"], name=tc_info["name"], arguments=args, raw_arguments=raw_args)
            )

        return ChatCompletionResponse(
            content="".join(accumulated_content),
            reasoning_content="".join(accumulated_reasoning),
            tool_calls=parsed_tool_calls,
            finish_reason=finish_reason,
        )

    def _check_status_code(self, response: httpx.Response) -> None:
        if response.status_code == 200:
            return
        try:
            response.read()
        except Exception:
            pass
        err_msg = response.text if hasattr(response, "text") else ""
        if response.status_code == 401:
            raise AuthenticationError(f"Invalid DeepSeek API key (HTTP 401): {err_msg}")
        if response.status_code == 402:
            raise InsufficientBalanceError(f"DeepSeek API balance insufficient (HTTP 402): {err_msg}")
        if response.status_code == 429:
            raise RateLimitError(f"DeepSeek API rate limit reached or account quota exhausted (HTTP 429): {err_msg}")
        if response.status_code == 400:
            if "context_length_exceeded" in err_msg.lower():
                raise ContextLengthExceededError(f"Context length limit exceeded: {err_msg}")
            raise DeepSeekAPIError(f"Bad Request (HTTP 400): {err_msg}")
        if response.status_code in (500, 502, 503, 504):
            raise DeepSeekAPIError(f"DeepSeek Server Error (HTTP {response.status_code}): {err_msg}")
        raise DeepSeekAPIError(f"API request failed with HTTP {response.status_code}: {err_msg}")


class MockDeepSeekClient(DeepSeekClient):
    """
    Mock DeepSeek Client for offline unit and integration tests.
    Replays deterministic tool calls to generate the project end-to-end.
    """

    def __init__(self, script_responses: Optional[List[ChatCompletionResponse]] = None) -> None:
        super().__init__(api_key="mock-key", model="deepseek-v4-pro")
        self.script_responses = script_responses or []
        self.call_history: List[List[Dict[str, Any]]] = []
        self._index = 0

    def test_connection(self) -> Tuple[bool, str]:
        return True, "Mock connection successful."

    def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        cancel_event: Optional[Event] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> ChatCompletionResponse:
        self.call_history.append(messages)
        if self._index < len(self.script_responses):
            res = self.script_responses[self._index]
            self._index += 1
            if on_chunk and res.content:
                on_chunk(res.content)
            return res

        # Default fallback completion when script exhausted
        return ChatCompletionResponse(
            content="Plan and generation finished.",
            tool_calls=[
                ToolCall(
                    id="finish_call",
                    name="finish",
                    arguments={"summary": "Mock generation completed successfully."},
                )
            ],
            finish_reason="stop",
        )
