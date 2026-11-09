"""Bounded in-memory conversation, with one background request at a time."""

import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable

from milu.providers import Message, Provider, ProviderError, Reply
from milu.state import Mood

SYSTEM_PROMPT = (
    "You are Milu, a friendly dog-themed assistant. Reply concisely in the user's language. "
    "Do not pretend to hear audio, control hardware, access other products' memory, "
    "or perform actions. This app currently supports text conversation only."
)
MAX_INPUT_CHARS = 2000
MAX_REPLY_CHARS = 4000


@dataclass
class Usage:
    requests: int = 0
    successes: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class Conversation:
    """No transcript persistence, no automatic retries and no unbounded work queue.

    Cancel/timeout discards a result; it cannot undo an HTTP request already sent.
    A replacement request waits until the prior worker exits, avoiding thread growth.
    All methods except the private worker are called on the UI thread.
    """

    def __init__(
        self,
        provider: Provider,
        *,
        timeout: float = 20.0,
        max_requests: int = 20,
        max_output_tokens: int = 512,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 0 < timeout <= 120:
            raise ValueError("Timeout must be between 0 and 120 seconds.")
        if not 1 <= max_requests <= 100:
            raise ValueError("Request limit must be between 1 and 100.")
        if not 64 <= max_output_tokens <= 2048:
            raise ValueError("Output token limit must be between 64 and 2048.")
        self.provider = provider
        self.timeout = timeout
        self.max_requests = max_requests
        self.max_output_tokens = max_output_tokens
        self.clock = clock
        self.history: list[Message] = []
        self.last_prompt = ""
        self.last_reply = ""
        self.error = ""
        self.mood = Mood.IDLE
        self.usage = Usage()
        self._results = queue.SimpleQueue()
        self._thread: threading.Thread | None = None
        self._generation = 0
        self._active: int | None = None
        self._deadline = 0.0
        self._speaking_until = 0.0
        self._pending = ""
        self._closed = False

    @property
    def busy(self) -> bool:
        return self._active is not None

    @property
    def worker_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def submit(self, prompt: str) -> None:
        self.poll()
        if self._closed:
            raise ValueError("Cuộc trò chuyện đã đóng.")
        prompt = prompt.strip()
        if not prompt or len(prompt) > MAX_INPUT_CHARS:
            raise ValueError(f"Nhập từ 1 đến {MAX_INPUT_CHARS} ký tự.")
        if self.busy or self.worker_running:
            raise ValueError("Yêu cầu trước chưa kết thúc. Vui lòng chờ một chút.")
        if self.usage.requests >= self.max_requests:
            raise ValueError("Đã đạt giới hạn lượt gọi của phiên này. Mở lại ứng dụng để tiếp tục.")
        self._generation += 1
        request_id = self._generation
        self._active = request_id
        self._deadline = self.clock() + self.timeout
        self._pending = prompt
        self.last_prompt = prompt
        self.last_reply = ""
        self.error = ""
        self.mood = Mood.THINKING
        self.usage.requests += 1
        messages = [Message("system", SYSTEM_PROMPT), *self.history, Message("user", prompt)]
        self._thread = threading.Thread(
            target=self._request, args=(request_id, messages), daemon=True, name="milu-request"
        )
        self._thread.start()

    def _request(self, request_id: int, messages: list[Message]) -> None:
        try:
            reply = self.provider.complete(
                messages, timeout=self.timeout, max_output_tokens=self.max_output_tokens
            )
            if (
                not isinstance(reply, Reply)
                or not isinstance(reply.text, str)
                or not reply.text.strip()
            ):
                raise ValueError("Invalid provider reply")
            result = (request_id, self.clock(), reply, "")
        except ProviderError as error:
            # Adapters expose safe messages, never raw HTTP bodies or credentials.
            result = (request_id, self.clock(), None, str(error))
        except Exception:
            result = (request_id, self.clock(), None, "Không nhận được câu trả lời hợp lệ.")
        self._results.put(result)

    def poll(self) -> None:
        now = self.clock()
        while True:
            try:
                request_id, finished_at, reply, error = self._results.get_nowait()
            except queue.Empty:
                break
            if request_id != self._active or self._closed:
                continue
            if finished_at > self._deadline:
                self._timeout()
                continue
            self._active = None
            if error:
                self.error = error
                self.mood = Mood.ERROR
            else:
                text = reply.text.strip()
                if len(text) > MAX_REPLY_CHARS:
                    text = text[:MAX_REPLY_CHARS] + "… [rút gọn]"
                self.last_reply = text
                self.history.extend([Message("user", self._pending), Message("assistant", text)])
                self.history = self.history[-8:]  # Four successful turns; errors are not history.
                self.mood = Mood.SPEAKING
                self._speaking_until = now + 3.0
                self.usage.successes += 1
                self.usage.input_tokens += max(0, reply.input_tokens or 0)
                self.usage.output_tokens += max(0, reply.output_tokens or 0)
            self._pending = ""
        if self._active is not None and now >= self._deadline:
            self._timeout()
        elif self.mood == Mood.SPEAKING and now >= self._speaking_until:
            self.mood = Mood.IDLE

    def _timeout(self) -> None:
        self._active = None
        self._pending = ""
        self.error = "Hết thời gian chờ. Yêu cầu đã gửi có thể vẫn được dịch vụ xử lý."
        self.mood = Mood.ERROR

    def cancel(self) -> None:
        self._active = None
        self._pending = ""
        self.error = ""
        self.mood = Mood.IDLE

    def clear(self) -> None:
        self.cancel()
        self.history.clear()
        self.last_prompt = ""
        self.last_reply = ""
        # Clearing context deliberately does not reset the request/cost limit.

    def close(self) -> None:
        self.clear()
        self._closed = True
