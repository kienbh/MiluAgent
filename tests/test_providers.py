import io
import json
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

from milu.providers import (
    MAX_RESPONSE_BYTES,
    AnthropicProvider,
    FakeProvider,
    Message,
    OpenAIProvider,
    ProviderError,
    _NoRedirect,
    create_provider,
)

HISTORY = [Message("system", "Be kind."), Message("user", "Hello")]
OPENAI = {
    "status": "completed",
    "output": [
        {"type": "reasoning"},
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Hello!"}],
        },
    ],
    "usage": {"input_tokens": 5, "output_tokens": 2},
}
ANTHROPIC = {
    "type": "message",
    "role": "assistant",
    "stop_reason": "end_turn",
    "content": [{"type": "text", "text": "Hello!"}],
    "usage": {"input_tokens": 5, "output_tokens": 2},
}


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.patch = patch("milu.providers.urllib.request.build_opener")
        self.build = self.patch.start()
        self.addCleanup(self.patch.stop)
        self.opener = self.build.return_value
        self.response = MagicMock()
        self.response.status = 200
        self.opener.open.return_value.__enter__.return_value = self.response
        self.provider = OpenAIProvider("test-secret", "explicit-test-model")
        self.response.read.return_value = json.dumps(OPENAI).encode()

    def call(self, provider=None, **kw):
        return (provider or self.provider).complete(
            kw.pop("messages", HISTORY),
            timeout=kw.pop("timeout", 12),
            max_output_tokens=kw.pop("max_output_tokens", 128),
            **kw,
        )

    def error(self, code, provider=None, **kw):
        with self.assertRaises(ProviderError) as caught:
            self.call(provider, **kw)
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn("test-secret", str(caught.exception))
        return caught.exception

    def test_openai_request_and_reply(self):
        reply = self.call()
        self.assertEqual((reply.text, reply.input_tokens, reply.output_tokens), ("Hello!", 5, 2))
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(
            json.loads(request.data),
            {
                "model": "explicit-test-model",
                "input": [
                    {"role": "system", "content": "Be kind."},
                    {"role": "user", "content": "Hello"},
                ],
                "max_output_tokens": 128,
                "store": False,
                "stream": False,
            },
        )
        self.assertEqual(self.opener.open.call_args.kwargs, {"timeout": 12})
        self.response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)
        self.assertIsInstance(self.build.call_args.args[0], _NoRedirect)

    def test_anthropic_separates_system(self):
        self.response.read.return_value = json.dumps(ANTHROPIC).encode()
        reply = self.call(AnthropicProvider("test-secret", "explicit-test-model"))
        self.assertEqual(reply.text, "Hello!")
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.get_header("X-api-key"), "test-secret")
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
        self.assertEqual(
            json.loads(request.data),
            {
                "model": "explicit-test-model",
                "system": "Be kind.",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 128,
                "stream": False,
            },
        )

    def test_fake_is_deterministic_and_offline(self):
        self.assertEqual(self.call(FakeProvider()), self.call(create_provider()))
        self.build.assert_not_called()

    def test_factory_does_not_fallback_or_guess_model(self):
        with patch.dict("os.environ", {}, clear=True):
            for name in ("openai", "anthropic"):
                with self.assertRaises(ProviderError):
                    create_provider(name, "test-model")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-secret"}, clear=True):
            with self.assertRaises(ProviderError):
                create_provider("openai")
            self.assertIsInstance(create_provider("openai", "test-model"), OpenAIProvider)
            with self.assertRaises(ProviderError):
                create_provider("anthropic", "test-model")
        with self.assertRaises(ValueError):
            create_provider("other")
        self.build.assert_not_called()

    def test_credentials_rejected_safely(self):
        for key, model in [
            ("", "model"),
            ("secret\nheader", "model"),
            ("é", "model"),
            ("test-secret", None),
            ("test-secret", " "),
        ]:
            with self.subTest(key=key, model=model), self.assertRaises(ProviderError):
                OpenAIProvider(key, model)
        self.assertNotIn("test-secret", repr(self.provider))

    def test_input_and_limits_rejected_before_network(self):
        bad = [
            [],
            [Message("system", "s")],
            [Message("tool", "x")],
            [Message("user", " ")],
            [Message("user", 3)],
            [None],
            [Message("user", "x"), Message("system", "s")],
            [Message("assistant", "x")],
            [Message("user", "x" * 64001)],
            [Message("user", "x")] * 102,
        ]
        for messages in bad:
            self.error("invalid_request", messages=messages)
        for timeout in (0, -1, 121, float("inf"), float("nan"), True, "5"):
            self.error("invalid_request", timeout=timeout)
        for limit in (0, -1, 4097, True, 1.5):
            self.error("invalid_request", max_output_tokens=limit)
        self.build.assert_not_called()

    def test_http_errors_never_read_bodies_or_retry(self):
        for status, code in [
            (301, "redirect"),
            (307, "redirect"),
            (401, "authentication"),
            (403, "authentication"),
            (429, "rate_limit"),
            (500, "http_error"),
        ]:
            body = io.BytesIO(b"test-secret unsafe raw body")
            self.opener.open.side_effect = urllib.error.HTTPError(
                "https://api.openai.com", status, "test-secret", {}, body
            )
            self.opener.open.reset_mock()
            self.error(code)
            self.opener.open.assert_called_once()
            self.assertTrue(body.closed)

    def test_transport_errors_are_safe(self):
        for exc, code in [
            (TimeoutError("test-secret"), "timeout"),
            (urllib.error.URLError(TimeoutError("test-secret")), "timeout"),
            (urllib.error.URLError("test-secret"), "network"),
            (OSError("test-secret"), "network"),
        ]:
            self.opener.open.side_effect = exc
            self.error(code)

    def test_malformed_and_large_responses(self):
        for body, code in [
            (b"not json test-secret", "invalid_response"),
            (b"\xff", "invalid_response"),
            (b"[]", "invalid_response"),
            (b"x" * (MAX_RESPONSE_BYTES + 1), "response_too_large"),
            (b'{"status":"completed","output":null}', "invalid_response"),
            (b'{"status":"completed","output":[]}', "empty_response"),
            (b'{"status":"incomplete"}', "incomplete_response"),
        ]:
            self.response.read.return_value = body
            self.error(code)

    def test_text_and_usage_validation(self):
        for value, code in [
            (None, "invalid_response"),
            ("", "empty_response"),
            ("x" * 16385, "response_too_large"),
        ]:
            data = json.loads(json.dumps(OPENAI))
            data["output"][1]["content"][0]["text"] = value
            self.response.read.return_value = json.dumps(data).encode()
            self.error(code)
        for usage in ([], {"input_tokens": -1}, {"output_tokens": True}):
            self.response.read.return_value = json.dumps({**OPENAI, "usage": usage}).encode()
            self.error("invalid_response")

    def test_anthropic_truncated_and_malformed(self):
        provider = AnthropicProvider("test-secret", "test-model")
        for changes, code in [
            ({"stop_reason": "max_tokens"}, "incomplete_response"),
            ({"content": {}}, "invalid_response"),
            ({"type": "error"}, "invalid_response"),
        ]:
            self.response.read.return_value = json.dumps({**ANTHROPIC, **changes}).encode()
            self.error(code, provider)

    def test_no_redirect_for_any_destination(self):
        handler = _NoRedirect()
        request = urllib.request.Request("https://api.openai.com/v1/responses")
        for code in (301, 302, 303, 307, 308):
            self.assertIsNone(
                handler.redirect_request(request, None, code, "", {}, "https://other.invalid")
            )


if __name__ == "__main__":
    unittest.main()
