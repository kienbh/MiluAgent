"""Milu face and optional text chat. Cloud access requires explicit configuration."""

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
    result = argparse.ArgumentParser(
        description="Milu face demo and optional text chat. Offline by default."
    )
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
    result.add_argument("--chat", action="store_true", help="enable text input and conversation")
    result.add_argument("--provider", choices=("fake", "openai", "anthropic"), default="fake")
    result.add_argument(
        "--model", help="explicit cloud model ID; no cloud model is selected by default"
    )
    result.add_argument(
        "--allow-cloud",
        action="store_true",
        help="allow typed messages and session context to go to the selected API",
    )
    result.add_argument("--timeout", type=positive_seconds, default=20.0)
    result.add_argument("--max-requests", type=bounded_int(1, 100), default=20)
    result.add_argument("--max-output-tokens", type=bounded_int(64, 2048), default=512)
    return result


def create_conversation(args):
    from milu.conversation import Conversation
    from milu.providers import ProviderError, create_provider

    if not args.chat:
        if args.provider != "fake" or args.model or args.allow_cloud:
            raise ValueError("Provider options require --chat.")
        return None
    if args.demo:
        raise ValueError("--chat cannot be combined with --demo; conversation controls the face.")
    if args.provider != "fake" and not args.allow_cloud:
        raise ValueError(
            "Cloud chat requires --allow-cloud. Typed messages and up to four prior turns will be sent to the selected provider."
        )
    try:
        provider = create_provider(args.provider, model=args.model)
    except ProviderError as error:
        raise ValueError(str(error)) from None
    return Conversation(
        provider,
        timeout=args.timeout,
        max_requests=args.max_requests,
        max_output_tokens=args.max_output_tokens,
    )


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

    try:
        conversation = create_conversation(args)
    except (ValueError, RuntimeError) as error:
        print(f"Cannot configure Milu: {error}", file=sys.stderr)
        return 1
    # Only initialize the display and font modules, not the microphone/mixer.
    try:
        pygame.display.init()
        pygame.font.init()
        flags = pygame.FULLSCREEN if args.fullscreen else pygame.RESIZABLE
        size = (0, 0) if args.fullscreen else (args.width, args.height)
        screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption(
            "Milu | Text chat" if conversation else "Milu | Offline face demo"
        )
        renderer = FaceRenderer()
        chat_view = None
        if conversation is not None:
            from milu.ui.chat import ChatView

            chat_view = ChatView(conversation)
            pygame.key.start_text_input()
        started = time.monotonic()
        state = FaceState(Mood(args.state), demo=args.demo, entered_at=started)
        clock = pygame.time.Clock()
        while True:
            now = time.monotonic()
            should_quit = False
            for event in pygame.event.get():
                keep_running = (
                    chat_view.handle(event) if chat_view else handle_event(event, state, now)
                )
                if not keep_running:
                    should_quit = True
                    break
                elif event.type == pygame.VIDEORESIZE and not args.fullscreen:
                    size = (min(3840, max(240, event.w)), min(2160, max(160, event.h)))
                    screen = pygame.display.set_mode(size, flags)
            if should_quit:
                break
            if chat_view:
                conversation.poll()
                chat_view.draw(screen, now - started)
            else:
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
        if conversation is not None:
            conversation.close()
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
