import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from milu.app import handle_event, main, parser
from milu.state import DEMO_INTERVAL, MOODS, FaceState, Mood
from milu.ui.face import BG, FaceRenderer


class StateTests(unittest.TestCase):
    def test_defaults_are_offline_idle(self):
        state = FaceState()
        self.assertEqual(state.mood, Mood.IDLE)
        self.assertFalse(state.demo)

    def test_manual_choice_stops_demo_and_resets_time(self):
        state = FaceState(demo=True)
        state.select(Mood.LISTENING, 5)
        self.assertEqual((state.mood, state.demo, state.entered_at), (Mood.LISTENING, False, 5))

    def test_manual_cycle_wraps_both_ways(self):
        state = FaceState()
        state.cycle(-1, 1)
        self.assertEqual(state.mood, Mood.ERROR)
        state.cycle(1, 2)
        self.assertEqual(state.mood, Mood.IDLE)

    def test_demo_advances_and_preserves_remainder(self):
        state = FaceState(demo=True, entered_at=10)
        state.tick(10 + DEMO_INTERVAL * 2 + 0.2)
        self.assertEqual(state.mood, Mood.THINKING)
        self.assertEqual(state.entered_at, 16)

    def test_demo_wraps_after_long_pause(self):
        state = FaceState(demo=True)
        state.tick(DEMO_INTERVAL * 6)
        self.assertEqual(state.mood, Mood.LISTENING)

    def test_tick_does_nothing_when_paused(self):
        state = FaceState()
        state.tick(100)
        self.assertEqual(state.mood, Mood.IDLE)

    def test_backwards_clock_does_not_advance(self):
        state = FaceState(demo=True, entered_at=10)
        state.tick(9)
        self.assertEqual(state.mood, Mood.IDLE)

    def test_toggle_resets_demo_timer(self):
        state = FaceState()
        state.toggle_demo(20)
        state.tick(22)
        self.assertEqual(state.mood, Mood.IDLE)
        state.toggle_demo(23)
        self.assertFalse(state.demo)


class EventTests(unittest.TestCase):
    def key(self, key):
        return pygame.event.Event(pygame.KEYDOWN, key=key)

    def test_numeric_keys_select_every_mood(self):
        state = FaceState()
        for key, mood in zip(range(pygame.K_1, pygame.K_5 + 1), MOODS):
            self.assertTrue(handle_event(self.key(key), state, 3))
            self.assertEqual(state.mood, mood)

    def test_repeated_selection_does_not_start_demo(self):
        state = FaceState(demo=True)
        for _ in range(5):
            handle_event(self.key(pygame.K_2), state, 2)
        self.assertFalse(state.demo)
        self.assertEqual(state.mood, Mood.LISTENING)

    def test_arrows_wrap(self):
        state = FaceState()
        handle_event(self.key(pygame.K_LEFT), state, 0)
        self.assertEqual(state.mood, Mood.ERROR)
        handle_event(self.key(pygame.K_RIGHT), state, 0)
        self.assertEqual(state.mood, Mood.IDLE)

    def test_space_and_help_toggle_repeatedly(self):
        state = FaceState()
        for _ in range(2):
            handle_event(self.key(pygame.K_SPACE), state, 0)
            handle_event(self.key(pygame.K_h), state, 0)
        self.assertFalse(state.demo)
        self.assertTrue(state.show_help)

    def test_escape_q_and_close_exit(self):
        for event in (
            self.key(pygame.K_ESCAPE),
            self.key(pygame.K_q),
            pygame.event.Event(pygame.QUIT),
        ):
            self.assertFalse(handle_event(event, FaceState(), 0))

    def test_unrelated_events_are_ignored(self):
        state = FaceState()
        self.assertTrue(handle_event(pygame.event.Event(pygame.MOUSEMOTION), state, 0))
        self.assertTrue(handle_event(self.key(pygame.K_a), state, 0))
        self.assertEqual(state.mood, Mood.IDLE)


class RenderingTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.renderer = FaceRenderer()

    def tearDown(self):
        pygame.quit()

    def test_all_moods_render_differently(self):
        images = set()
        for mood in MOODS:
            surface = pygame.Surface((480, 320))
            self.renderer.draw(surface, FaceState(mood), 0.5)
            images.add(pygame.image.tostring(surface, "RGB"))
        self.assertEqual(len(images), 5)

    def test_landscape_portrait_and_minimum_sizes(self):
        for size in ((480, 320), (320, 480), (240, 160), (800, 480), (1, 1)):
            for mood in MOODS:
                surface = pygame.Surface(size)
                self.renderer.draw(surface, FaceState(mood), 4.5)
                self.assertEqual(surface.get_size(), size)

    def test_portrait_letterboxing(self):
        surface = pygame.Surface((320, 480))
        self.renderer.draw(surface, FaceState(), 0)
        self.assertEqual(surface.get_at((160, 0))[:3], BG)
        self.assertNotEqual(surface.get_at((160, 240))[:3], BG)

    def test_animation_changes_pixels(self):
        surface = pygame.Surface((480, 320))
        self.renderer.draw(surface, FaceState(Mood.SPEAKING), 0)
        before = pygame.image.tostring(surface, "RGB")
        self.renderer.draw(surface, FaceState(Mood.SPEAKING), 0.2)
        self.assertNotEqual(before, pygame.image.tostring(surface, "RGB"))


class CliTests(unittest.TestCase):
    def test_defaults(self):
        args = parser().parse_args([])
        self.assertEqual((args.width, args.height, args.fps), (480, 320, 30))

    def test_invalid_arguments(self):
        for arguments in (
            ["--width", "0"],
            ["--height", "-1"],
            ["--fps", "61"],
            ["--seconds", "0"],
            ["--seconds", "nan"],
            ["--seconds", "inf"],
            ["--state", "unknown"],
            ["--width", "abc"],
        ):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    parser().parse_args(arguments)
                self.assertEqual(raised.exception.code, 2)

    def test_unsafe_headless_options_rejected(self):
        for arguments in (
            ["--headless"],
            ["--headless", "--fullscreen", "--seconds", "1"],
            ["--screenshot", "bad.txt"],
        ):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    main(arguments)

    def test_headless_smoke_saves_png_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "frame.png"
            code = main(["--headless", "--seconds", "0.05", "--screenshot", str(output)])
            self.assertEqual(code, 0)
            self.assertTrue(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(pygame.image.load(str(output)).get_size(), (480, 320))
            self.assertFalse(pygame.display.get_init())
            self.assertFalse(pygame.mixer.get_init())

    def test_resize_then_close_and_restart(self):
        events = [
            [pygame.event.Event(pygame.VIDEORESIZE, w=800, h=480)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3)],
            [pygame.event.Event(pygame.QUIT)],
        ]
        with patch("pygame.event.get", side_effect=events):
            self.assertEqual(main(["--headless", "--seconds", "2"]), 0)
        self.assertEqual(main(["--headless", "--seconds", "0.02"]), 0)

    def test_display_error_is_friendly(self):
        with patch("pygame.display.set_mode", side_effect=pygame.error("test display failure")):
            with contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(main(["--headless", "--seconds", "1"]), 1)
                self.assertIn("Cannot run Milu", error.getvalue())
        self.assertFalse(pygame.display.get_init())


if __name__ == "__main__":
    unittest.main()
