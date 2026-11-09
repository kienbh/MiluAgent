"""Offline display application. It never records audio or calls a service."""

import argparse
import math
import os
import sys
import time
from pathlib import Path

from milu.state import MOODS, FaceState, Mood


def bounded_int(low, high):
    def parse(value):
        try:
            number = int(value)
        except ValueError as error:
            raise argparse.ArgumentTypeError("must be an integer") from error
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(f"must be between {low} and {high}")
        return number

    return parse


def positive_seconds(value):
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive number") from error
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def parser():
    result = argparse.ArgumentParser(description="Milu offline face demo (no API, mic or memory).")
    result.add_argument("--width", type=bounded_int(240, 3840), default=480)
    result.add_argument("--height", type=bounded_int(160, 2160), default=320)
    result.add_argument("--fps", type=bounded_int(1, 60), default=30)
    result.add_argument("--state", choices=[mood.value for mood in MOODS], default="idle")
    result.add_argument("--demo", action="store_true", help="cycle moods every three seconds")
    result.add_argument(
        "--fullscreen", action="store_true", help="use the display's current resolution"
    )
    result.add_argument(
        "--headless", action="store_true", help="use SDL's dummy display for testing"
    )
    result.add_argument(
        "--seconds", type=positive_seconds, help="exit automatically after this duration"
    )
    result.add_argument(
        "--screenshot", type=Path, help="save the final frame as PNG at this local path"
    )
    return result


def handle_event(event, state, now):
    """Return False to quit. Keep this separate so keyboard and quit flows can be tested."""
    import pygame

    if event.type == pygame.QUIT:
        return False
    if event.type != pygame.KEYDOWN:
        return True
    if event.key in (pygame.K_ESCAPE, pygame.K_q):
        return False
    if pygame.K_1 <= event.key <= pygame.K_5:
        state.select(MOODS[event.key - pygame.K_1], now)
    elif event.key in (pygame.K_RIGHT, pygame.K_LEFT):
        state.cycle(1 if event.key == pygame.K_RIGHT else -1, now)
    elif event.key == pygame.K_SPACE:
        state.toggle_demo(now)
    elif event.key == pygame.K_h:
        state.show_help = not state.show_help
    return True


def main(argv=None):
    args = parser().parse_args(argv)
    if args.headless and args.fullscreen:
        parser().error("--headless and --fullscreen cannot be used together")
    if args.headless and args.seconds is None:
        parser().error("--headless requires --seconds so the test terminates")
    if args.screenshot and args.screenshot.suffix.lower() != ".png":
        parser().error("--screenshot must name a .png file")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    try:
        import pygame

        from milu.ui.face import FaceRenderer
    except ModuleNotFoundError as error:
        if error.name != "pygame":
            raise
        print("Install the project first: python -m pip install -e .", file=sys.stderr)
        return 1

    # Only initialize the display and font modules, not the microphone/mixer.
    try:
        pygame.display.init()
        pygame.font.init()
        flags = pygame.FULLSCREEN if args.fullscreen else pygame.RESIZABLE
        size = (0, 0) if args.fullscreen else (args.width, args.height)
        screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Milu | Offline face demo")
        renderer = FaceRenderer()
        started = time.monotonic()
        state = FaceState(Mood(args.state), demo=args.demo, entered_at=started)
        clock = pygame.time.Clock()
        while True:
            now = time.monotonic()
            should_quit = False
            for event in pygame.event.get():
                if not handle_event(event, state, now):
                    should_quit = True
                elif event.type == pygame.VIDEORESIZE and not args.fullscreen:
                    size = (min(3840, max(240, event.w)), min(2160, max(160, event.h)))
                    screen = pygame.display.set_mode(size, flags)
            if should_quit:
                break
            state.tick(now)
            renderer.draw(screen, state, now - started)
            pygame.display.flip()
            if args.seconds is not None and now - started >= args.seconds:
                break
            clock.tick(args.fps)
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(screen, str(args.screenshot))
    except (pygame.error, OSError) as error:
        print(f"Cannot run Milu: {error}", file=sys.stderr)
        print("Use a graphical desktop, or --headless --seconds 1 for a test.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
