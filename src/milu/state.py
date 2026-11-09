"""Display state, deliberately independent of hardware and rendering."""

from dataclasses import dataclass
from enum import Enum


class Mood(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


MOODS = tuple(Mood)
DEMO_INTERVAL = 3.0


@dataclass
class FaceState:
    mood: Mood = Mood.IDLE
    demo: bool = False
    show_help: bool = True
    entered_at: float = 0.0

    def select(self, mood: Mood, now: float) -> None:
        """A manual choice stops the demo, including repeated key presses."""
        self.mood = mood
        self.demo = False
        self.entered_at = now

    def cycle(self, direction: int, now: float) -> None:
        self.select(MOODS[(MOODS.index(self.mood) + direction) % len(MOODS)], now)

    def toggle_demo(self, now: float) -> None:
        self.demo = not self.demo
        self.entered_at = now

    def tick(self, now: float) -> None:
        if not self.demo:
            return
        steps = int(max(0.0, now - self.entered_at) / DEMO_INTERVAL)
        if steps:
            self.mood = MOODS[(MOODS.index(self.mood) + steps) % len(MOODS)]
            self.entered_at += steps * DEMO_INTERVAL
