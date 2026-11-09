import contextlib
import io
import os
import threading
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from milu.app import create_conversation, main, parser
from milu.conversation import MAX_INPUT_CHARS, MAX_REPLY_CHARS, Conversation
from milu.providers import FakeProvider, ProviderError, Reply
from milu.state import Mood
from milu.ui.chat import ChatView


class RecordingProvider:
    name = "test"

    def __init__(self):
        self.calls = []
        self.response = Reply("Xin chào!", 4, 2)
        self.error = None
        self.gate = None

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if self.gate is not None:
            self.gate.wait(2)
        if self.error:
            raise self.error
        return self.response


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.provider = RecordingProvider()
        self.now = [0.0]
        self.session = Conversation(self.provider, clock=lambda: self.now[0])
        self.addCleanup(self.session.close)

    def finish(self):
        self.session._thread.join(1)
        self.assertFalse(self.session.worker_running)
        self.session.poll()

    def test_success_history_usage_and_expression(self):
        self.session.submit(" Xin chào ")
        self.assertEqual(self.session.mood, Mood.THINKING)
        self.finish()
        self.assertEqual(self.session.last_reply, "Xin chào!")
        self.assertEqual([m.role for m in self.session.history], ["user", "assistant"])
        self.assertEqual(self.session.usage.input_tokens, 4)
        self.assertEqual(self.session.usage.output_tokens, 2)
        self.assertEqual(self.session.mood, Mood.SPEAKING)
        self.now[0] = 4
        self.session.poll()
        self.assertEqual(self.session.mood, Mood.IDLE)

    def test_four_turn_history_bound(self):
        for index in range(7):
            self.session.submit(str(index))
            self.finish()
        self.assertEqual(len(self.session.history), 8)
        self.assertEqual(self.session.history[0].content, "3")
        self.assertEqual(len(self.provider.calls[-1][0]), 10)
        self.assertEqual(self.provider.calls[-1][0][0].role, "system")

    def test_invalid_input_and_budget_do_not_call(self):
        for prompt in ("", " \n", "x" * (MAX_INPUT_CHARS + 1)):
            with self.assertRaises(ValueError):
                self.session.submit(prompt)
        self.assertEqual(self.provider.calls, [])
        self.session.max_requests = 1
        self.session.submit("one")
        self.finish()
        self.session.clear()
        with self.assertRaises(ValueError):
            self.session.submit("two")
        self.assertEqual(self.session.usage.requests, 1)

    def test_cancel_late_response_and_no_extra_threads(self):
        gate = self.provider.gate = threading.Event()
        self.addCleanup(gate.set)
        self.session.submit("old")
        self.session.cancel()
        with self.assertRaises(ValueError):
            self.session.submit("new while old is running")
        gate.set()
        self.finish()
        self.assertEqual(self.session.last_reply, "")
        self.assertEqual(self.session.history, [])
        self.session.submit("new")
        self.finish()
        self.assertEqual(self.session.history[0].content, "new")

    def test_timeout_discards_late_result(self):
        gate = self.provider.gate = threading.Event()
        self.addCleanup(gate.set)
        self.session.submit("slow")
        self.now[0] = 21
        self.session.poll()
        self.assertEqual(self.session.mood, Mood.ERROR)
        self.assertFalse(self.session.busy)
        gate.set()
        self.finish()
        self.assertEqual(self.session.history, [])
        self.assertEqual(self.session.usage.successes, 0)

    def test_finished_after_deadline_is_not_accepted_before_poll(self):
        gate = self.provider.gate = threading.Event()
        self.addCleanup(gate.set)
        self.session.submit("slow")
        self.now[0] = 21
        gate.set()
        self.finish()
        self.assertEqual(self.session.mood, Mood.ERROR)
        self.assertEqual(self.session.last_reply, "")

    def test_finished_in_time_survives_delayed_poll(self):
        self.session.submit("quick")
        self.session._thread.join(1)
        self.now[0] = 30
        self.session.poll()
        self.assertEqual(self.session.last_reply, "Xin chào!")

    def test_provider_error_and_unexpected_exception_are_safe(self):
        for error in (ProviderError("rate_limit"), RuntimeError("private-token-sentinel")):
            self.provider.error = error
            self.session.submit("test")
            self.finish()
            self.assertEqual(self.session.mood, Mood.ERROR)
            self.assertNotIn("private-token-sentinel", self.session.error)
            self.assertEqual(self.session.history, [])

    def test_empty_invalid_and_oversized_replies(self):
        for response in (None, Reply("   ")):
            self.provider.response = response
            self.session.submit("test")
            self.finish()
            self.assertTrue(self.session.error)
        self.provider.response = Reply("x" * (MAX_REPLY_CHARS + 100))
        self.session.submit("test")
        self.finish()
        self.assertIn("rút gọn", self.session.last_reply)
        self.assertLess(len(self.session.last_reply), MAX_REPLY_CHARS + 30)

    def test_clear_and_close_drop_late_responses(self):
        gate = self.provider.gate = threading.Event()
        self.addCleanup(gate.set)
        self.session.submit("discard")
        self.session.close()
        gate.set()
        self.finish()
        self.assertEqual(self.session.history, [])
        with self.assertRaises(ValueError):
            self.session.submit("after close")

    def test_invalid_config_rejected(self):
        for options in (
            {"timeout": 0},
            {"timeout": float("nan")},
            {"timeout": 121},
            {"max_requests": 0},
            {"max_requests": 101},
            {"max_output_tokens": 1},
        ):
            with self.assertRaises(ValueError):
                Conversation(FakeProvider(), **options)


class ChatTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.session = Conversation(FakeProvider())
        self.view = ChatView(self.session)
        self.addCleanup(self.session.close)
        self.addCleanup(pygame.quit)

    def key(self, key, mod=0):
        return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)

    def test_unicode_input_backspace_send_and_reply(self):
        self.view.handle(pygame.event.Event(pygame.TEXTINPUT, text="Xin chào!"))
        self.view.handle(self.key(pygame.K_BACKSPACE))
        self.assertEqual(self.view.draft, "Xin chào")
        self.view.handle(self.key(pygame.K_RETURN))
        self.assertEqual(self.view.draft, "")
        self.session._thread.join(1)
        self.session.poll()
        self.assertTrue(self.session.last_reply)

    def test_q_is_text_not_quit_and_ctrl_q_quits(self):
        self.assertTrue(self.view.handle(self.key(pygame.K_q)))
        self.assertFalse(self.view.handle(self.key(pygame.K_q, pygame.KMOD_CTRL)))
        self.assertFalse(self.view.handle(pygame.event.Event(pygame.QUIT)))

    def test_limits_controls_empty_send_and_clear(self):
        self.view.handle(self.key(pygame.K_RETURN))
        self.assertTrue(self.view.notice)
        self.view.handle(pygame.event.Event(pygame.TEXTINPUT, text="x" * 3000 + "\x00\n"))
        self.assertEqual(len(self.view.draft), MAX_INPUT_CHARS)
        self.assertNotIn("\x00", self.view.draft)
        self.view.handle(self.key(pygame.K_ESCAPE))
        self.assertIn("hủy", self.view.notice)
        self.view.handle(self.key(pygame.K_l, pygame.KMOD_CTRL))
        self.assertEqual(self.view.draft, "")

    def test_vietnamese_font_and_long_draft(self):
        self.assertTrue(all(self.view.font.metrics("ếễữệậộĐ")))
        self.assertLessEqual(self.view.font.size(self.view._fit_tail("x" * 2000, 100))[0], 100)
        with patch("milu.ui.chat.find_text_font", return_value=None):
            with self.assertRaises(pygame.error):
                ChatView(self.session)

    def test_scroll_wrap_and_all_render_sizes(self):
        self.session.last_reply = "Tiếng Việt rất dài. " * 100
        surface = pygame.Surface((480, 320))
        self.view.draw(surface, 0)
        self.view.handle(self.key(pygame.K_PAGEDOWN))
        self.view.draw(surface, 0.1)
        self.assertEqual(self.view.scroll, 3)
        self.view.handle(self.key(pygame.K_PAGEUP))
        self.assertEqual(self.view.scroll, 0)
        for size in ((240, 160), (320, 480), (800, 600)):
            self.view.draw(pygame.Surface(size), 0.2)
        for line in self.view._wrap("x" * 100, 100):
            self.assertLessEqual(self.view.font.size(line)[0], 100)


class AppConfigurationTests(unittest.TestCase):
    def test_default_and_fake_never_construct_cloud_provider(self):
        with patch("milu.providers.OpenAIProvider") as cloud:
            self.assertIsNone(create_conversation(parser().parse_args([])))
            session = create_conversation(parser().parse_args(["--chat"]))
            self.assertEqual(session.provider.name, "fake")
            session.close()
            cloud.assert_not_called()

    def test_cloud_without_consent_is_rejected_before_factory(self):
        with patch("milu.providers.create_provider") as factory:
            with self.assertRaises(ValueError):
                create_conversation(parser().parse_args(["--chat", "--provider", "openai"]))
            factory.assert_not_called()

    def test_missing_configuration_and_conflicts_are_friendly(self):
        cases = (
            ["--provider", "openai"],
            ["--chat", "--demo"],
            ["--chat", "--provider", "openai", "--allow-cloud"],
            ["--chat", "--timeout", "121"],
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            for arguments in cases:
                with contextlib.redirect_stderr(io.StringIO()) as error:
                    self.assertEqual(main(arguments), 1)
                self.assertIn("Cannot configure Milu", error.getvalue())

    def test_explicit_cloud_config_does_not_send_until_submit(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("milu.providers._post") as post:
                session = create_conversation(
                    parser().parse_args(
                        ["--chat", "--provider", "openai", "--model", "test-model", "--allow-cloud"]
                    )
                )
                self.assertEqual(session.provider.name, "openai")
                session.close()
                post.assert_not_called()

    def test_quit_does_not_process_queued_send(self):
        events = [
            [
                pygame.event.Event(pygame.QUIT),
                pygame.event.Event(pygame.TEXTINPUT, text="should not send"),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0),
            ]
        ]
        with (
            patch("pygame.event.get", side_effect=events),
            patch("milu.conversation.Conversation.submit") as submit,
        ):
            self.assertEqual(main(["--chat", "--headless", "--seconds", "2"]), 0)
            submit.assert_not_called()

    def test_chat_app_loop_handles_input_and_exit(self):
        events = [
            [pygame.event.Event(pygame.TEXTINPUT, text="Xin chào")],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0)],
            [],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q, mod=pygame.KMOD_CTRL)],
        ]
        with patch("pygame.event.get", side_effect=events):
            self.assertEqual(main(["--chat", "--headless", "--seconds", "2"]), 0)
        self.assertFalse(pygame.display.get_init())


if __name__ == "__main__":
    unittest.main()
