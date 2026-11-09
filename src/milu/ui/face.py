"""Deterministic, asset-free rendering on a small 480 x 320 logical canvas."""

import math

import pygame

from milu.state import FaceState, Mood

SIZE = (480, 320)
BG = (15, 27, 39)
INK = (34, 51, 57)
CREAM = (250, 224, 179)
EAR = (166, 106, 76)
MUZZLE = (255, 241, 213)
ACCENTS = {
    Mood.IDLE: (131, 216, 191),
    Mood.LISTENING: (123, 204, 248),
    Mood.THINKING: (192, 165, 242),
    Mood.SPEAKING: (143, 223, 164),
    Mood.ERROR: (255, 179, 119),
}
LABELS = {
    Mood.IDLE: "READY",
    Mood.LISTENING: "LISTENING",
    Mood.THINKING: "THINKING",
    Mood.SPEAKING: "SPEAKING",
    Mood.ERROR: "OOPS!",
}


class FaceRenderer:
    def __init__(self) -> None:
        self.canvas = pygame.Surface(SIZE)
        self.title_font = pygame.font.Font(None, 25)
        self.label_font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 16)

    def text(self, value, font, color, center) -> None:
        image = font.render(value, True, color)
        self.canvas.blit(image, image.get_rect(center=center))

    def draw(self, target: pygame.Surface, state: FaceState, elapsed: float) -> None:
        canvas = self.canvas
        canvas.fill(BG)
        accent = ACCENTS[state.mood]
        self.text("M I L U", self.title_font, (228, 236, 231), (240, 28))
        pygame.draw.circle(canvas, accent, (430, 27), 4)
        self.text("OFFLINE", self.small_font, (145, 162, 173), (392, 28))

        # Soft oval behind the face; all artwork is drawn here, no downloads.
        pygame.draw.ellipse(canvas, (23, 42, 53), (121, 63, 238, 186))
        bob = round(2 * math.sin(elapsed * 2))
        self.draw_dog(state.mood, elapsed, bob, accent)

        if state.mood == Mood.LISTENING:
            for index in range(4):
                height = round(7 + 12 * abs(math.sin(elapsed * 4 + index)))
                for x in (94 - index * 9, 386 + index * 9):
                    pygame.draw.rect(
                        canvas, accent, (x, 158 - height // 2, 4, height), border_radius=2
                    )
        elif state.mood == Mood.THINKING:
            for index in range(3):
                radius = 4 if int(elapsed * 3) % 3 == index else 2
                pygame.draw.circle(canvas, accent, (359 + 12 * index, 100), radius)
        elif state.mood == Mood.ERROR:
            self.text("?", self.title_font, accent, (365, 118))

        pygame.draw.rect(canvas, (27, 46, 57), (163, 250, 154, 27), border_radius=13)
        self.text(LABELS[state.mood], self.label_font, accent, (240, 264))
        hint = "1-5: mood   SPACE: demo   H: help   ESC: quit"
        if state.show_help:
            self.text(hint, self.small_font, (147, 166, 178), (240, 300))
        elif state.demo:
            self.text("DEMO", self.small_font, accent, (240, 300))

        # Letterbox rather than distort the face on a different LCD aspect ratio.
        width, height = target.get_size()
        scale = min(width / SIZE[0], height / SIZE[1])
        output_size = (max(1, round(SIZE[0] * scale)), max(1, round(SIZE[1] * scale)))
        target.fill(BG)
        scaled = pygame.transform.smoothscale(canvas, output_size)
        target.blit(scaled, ((width - output_size[0]) // 2, (height - output_size[1]) // 2))

    def draw_dog(self, mood: Mood, elapsed: float, bob: int, accent) -> None:
        canvas = self.canvas
        # Floppy ears, a warm face and a cream muzzle.
        pygame.draw.ellipse(canvas, (8, 20, 29), (164, 228, 152, 11))
        pygame.draw.ellipse(canvas, EAR, (125, 84 + bob, 70, 125))
        pygame.draw.ellipse(canvas, EAR, (285, 84 + bob, 70, 125))
        pygame.draw.ellipse(canvas, (129, 82, 62), (139, 107 + bob, 35, 78))
        pygame.draw.ellipse(canvas, (129, 82, 62), (306, 107 + bob, 35, 78))
        pygame.draw.ellipse(canvas, CREAM, (158, 76 + bob, 164, 151))
        pygame.draw.ellipse(canvas, MUZZLE, (185, 155 + bob, 110, 65))
        pygame.draw.ellipse(canvas, (232, 173, 143), (174, 164 + bob, 24, 12))
        pygame.draw.ellipse(canvas, (232, 173, 143), (282, 164 + bob, 24, 12))

        blink = elapsed % 4.6 > 4.42 and mood != Mood.ERROR
        for x in (205, 275):
            y = 140 + bob
            if blink or mood == Mood.SPEAKING:
                pygame.draw.arc(canvas, INK, (x - 12, y - 5, 24, 20), 0.1, math.pi - 0.1, 4)
            elif mood == Mood.THINKING:
                pygame.draw.ellipse(canvas, INK, (x - 9, y - 6, 18, 16))
                pygame.draw.circle(canvas, (255, 255, 245), (x - 3, y - 2), 3)
            else:
                eye_height = 28 if mood == Mood.LISTENING else 23
                pygame.draw.ellipse(canvas, INK, (x - 10, y - eye_height // 2, 20, eye_height))
                pygame.draw.circle(canvas, (255, 255, 245), (x - 3, y - 5), 4)

        if mood == Mood.ERROR:
            pygame.draw.line(canvas, INK, (193, 119 + bob), (215, 112 + bob), 3)
            pygame.draw.line(canvas, INK, (265, 112 + bob), (287, 119 + bob), 3)
        pygame.draw.ellipse(canvas, INK, (227, 163 + bob, 26, 18))
        pygame.draw.ellipse(canvas, (76, 92, 95), (232, 166 + bob, 10, 4))
        pygame.draw.line(canvas, INK, (240, 179 + bob), (240, 188 + bob), 3)

        if mood == Mood.SPEAKING:
            opening = round(10 + 9 * (1 + math.sin(elapsed * 9)) / 2)
            pygame.draw.ellipse(canvas, INK, (225, 184 + bob, 30, opening))
            pygame.draw.ellipse(canvas, (233, 140, 141), (231, 188 + bob, 18, max(4, opening - 5)))
        elif mood == Mood.ERROR:
            pygame.draw.line(canvas, INK, (230, 194 + bob), (250, 191 + bob), 3)
        else:
            pygame.draw.arc(canvas, INK, (216, 177 + bob, 24, 20), math.pi, 2 * math.pi, 3)
            pygame.draw.arc(canvas, INK, (240, 177 + bob, 24, 20), math.pi, 2 * math.pi, 3)
        # Small collar and tag finish the dog silhouette.
        pygame.draw.rect(canvas, accent, (197, 218 + bob, 86, 10), border_radius=5)
        pygame.draw.circle(canvas, (247, 204, 115), (240, 229 + bob), 8)
