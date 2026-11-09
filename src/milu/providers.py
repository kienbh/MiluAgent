"""Small text-only providers. No retries, persistence, tools, or implicit cloud model.

Timeout is a socket-operation timeout, not a guaranteed total wall-clock deadline
(DNS and a slowly arriving body can exceed it). Run cloud calls off the UI thread.
"""

import http.client
import json
import math
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

MAX_RESPONSE_BYTES = 1_048_576
MAX_TEXT_CHARS = 16_384
MAX_INPUT_CHARS = 64_000
MAX_MESSAGES = 101


@dataclass(frozen=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True)
class Reply:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


_ERRORS = {
    "invalid_request": "Invalid conversation or request limits.",
    "configuration": "An explicit model and valid API key are required.",
    "authentication": "Provider authentication failed. Check your API key and access.",
    "rate_limit": "Provider rate limit reached. Try again later.",
    "timeout": "Provider request timed out. Its billing outcome may be unknown.",
    "network": "Could not complete the provider connection.",
    "redirect": "Provider redirect refused for credential safety.",
    "http_error": "Provider rejected the request or is unavailable.",
    "invalid_response": "Provider returned an invalid response.",
    "response_too_large": "Provider response exceeded the local size limit.",
    "empty_response": "Provider returned no usable text.",
    "incomplete_response": "Provider did not complete its response.",
}


class ProviderError(Exception):
    """Only fixed local messages, never server bodies or transport exception text."""

    def __init__(self, code: str):
        self.code = code if code in _ERRORS else "invalid_response"
        super().__init__(_ERRORS[self.code])


class Provider(Protocol):
    name: str

    def complete(
        self, messages: list[Message], *, timeout: float, max_output_tokens: int
    ) -> Reply: ...


def _validate(messages: list[Message], timeout: float, limit: int) -> None:
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or not 0 < timeout <= 120
        or type(limit) is not int
        or not 1 <= limit <= 4096
        or not isinstance(messages, list)
        or not 1 <= len(messages) <= MAX_MESSAGES
    ):
        raise ProviderError("invalid_request")
    total = 0
    for i, message in enumerate(messages):
        if (
            not isinstance(message, Message)
            or message.role not in ("system", "user", "assistant")
            or (message.role == "system" and i != 0)
            or not isinstance(message.content, str)
            or not message.content.strip()
        ):
            raise ProviderError("invalid_request")
        total += len(message.content)
        if total > MAX_INPUT_CHARS:
            raise ProviderError("invalid_request")
    turns = messages[1:] if messages[0].role == "system" else messages
    if not turns or turns[0].role != "user" or turns[-1].role != "user":
        raise ProviderError("invalid_request")


class FakeProvider:
    name = "fake"

    def complete(self, messages: list[Message], *, timeout: float, max_output_tokens: int) -> Reply:
        _validate(messages, timeout, max_output_tokens)
        # Deliberately does not echo input or pretend to have performed an action.
        return Reply("Milu đang ở chế độ thử ngoại tuyến. Chưa có dịch vụ AI nào được gọi.")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _status_error(status: int) -> ProviderError:
    if 300 <= status < 400:
        return ProviderError("redirect")
    if status in (401, 403):
        return ProviderError("authentication")
    if status == 429:
        return ProviderError("rate_limit")
    return ProviderError("http_error")


def _post(url: str, headers: dict, payload: dict, timeout: float) -> dict:
    # JSON escaping also handles lone surrogates without a raw encoding exception.
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=True).encode("ascii"),
        headers={"Content-Type": "application/json", "Accept": "application/json", **headers},
        method="POST",
    )
    try:
        opener = urllib.request.build_opener(_NoRedirect())
        with opener.open(request, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise _status_error(response.status)
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        exc.close()
        raise _status_error(exc.code) from None
    except (TimeoutError, socket.timeout):
        raise ProviderError("timeout") from None
    except urllib.error.URLError as exc:
        code = "timeout" if isinstance(exc.reason, TimeoutError) else "network"
        raise ProviderError(code) from None
    except (OSError, http.client.HTTPException, ValueError):
        raise ProviderError("network") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ProviderError("response_too_large")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise ProviderError("invalid_response") from None
    if not isinstance(data, dict):
        raise ProviderError("invalid_response")
    return data


def _reply(parts: list[str], usage) -> Reply:
    text = "\n".join(parts).strip()
    if not text:
        raise ProviderError("empty_response")
    if len(text) > MAX_TEXT_CHARS:
        raise ProviderError("response_too_large")
    if usage is None:
        usage = {}
    if not isinstance(usage, dict):
        raise ProviderError("invalid_response")
    counts = [usage.get("input_tokens"), usage.get("output_tokens")]
    if any(n is not None and (type(n) is not int or n < 0) for n in counts):
        raise ProviderError("invalid_response")
    return Reply(text, *counts)


def _blocks(blocks, kind: str) -> list[str]:
    if not isinstance(blocks, list):
        raise ProviderError("invalid_response")
    texts = []
    for block in blocks:
        if not isinstance(block, dict):
            raise ProviderError("invalid_response")
        if block.get("type") == kind:
            if not isinstance(block.get("text"), str):
                raise ProviderError("invalid_response")
            texts.append(block["text"])
    return texts


class _CloudProvider:
    def __init__(self, api_key: str, model: str):
        if (
            not isinstance(api_key, str)
            or not api_key
            or len(api_key) > 4096
            or any(not 33 <= ord(c) <= 126 for c in api_key)
            or not isinstance(model, str)
            or not model.strip()
            or len(model) > 256
            or any(ord(c) < 33 or ord(c) > 126 for c in model)
        ):
            raise ProviderError("configuration")
        self._api_key = api_key
        self.model = model


class OpenAIProvider(_CloudProvider):
    name = "openai"

    def complete(self, messages: list[Message], *, timeout: float, max_output_tokens: int) -> Reply:
        _validate(messages, timeout, max_output_tokens)
        data = _post(
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {self._api_key}"},
            {
                "model": self.model,
                "input": [{"role": m.role, "content": m.content} for m in messages],
                "max_output_tokens": max_output_tokens,
                "store": False,
                "stream": False,
            },
            timeout,
        )
        if data.get("status") != "completed" or data.get("error"):
            raise ProviderError("incomplete_response")
        output = data.get("output")
        if not isinstance(output, list):
            raise ProviderError("invalid_response")
        texts = []
        for item in output:
            if not isinstance(item, dict):
                raise ProviderError("invalid_response")
            if item.get("type") == "message" and item.get("role") == "assistant":
                texts.extend(_blocks(item.get("content"), "output_text"))
        return _reply(texts, data.get("usage"))


class AnthropicProvider(_CloudProvider):
    name = "anthropic"

    def complete(self, messages: list[Message], *, timeout: float, max_output_tokens: int) -> Reply:
        _validate(messages, timeout, max_output_tokens)
        payload = {
            "model": self.model,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages if m.role != "system"
            ],
            "max_tokens": max_output_tokens,
            "stream": False,
        }
        if messages[0].role == "system":
            payload["system"] = messages[0].content
        data = _post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": self._api_key, "anthropic-version": "2023-06-01"},
            payload,
            timeout,
        )
        if data.get("type") != "message" or data.get("role") != "assistant":
            raise ProviderError("invalid_response")
        if data.get("stop_reason") not in ("end_turn", "stop_sequence"):
            raise ProviderError("incomplete_response")
        return _reply(_blocks(data.get("content"), "text"), data.get("usage"))


def create_provider(name: str = "fake", model: str | None = None) -> Provider:
    if name == "fake":
        return FakeProvider()
    if name == "openai":
        return OpenAIProvider(os.environ.get("OPENAI_API_KEY", ""), model)
    if name == "anthropic":
        return AnthropicProvider(os.environ.get("ANTHROPIC_API_KEY", ""), model)
    raise ValueError("Unknown provider. Choose fake, openai, or anthropic.")
