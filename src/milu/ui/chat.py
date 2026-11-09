"""Small-screen text chat UI, sharing the Milu face and conversation state."""

from pathlib import Path

import pygame

from milu.conversation import MAX_INPUT_CHARS, Conversation
from milu.state import FaceState
from milu.ui.face import BG, FaceRenderer


def find_text_font():
    # Standard Debian/Pi OS locations avoid a slow fontconfig subprocess at startup.
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file() and all(pygame.font.Font(candidate, 16).metrics("ếễữệậộĐ")):
            return candidate
    for name in ("dejavusans", "notosans", "liberationsans"):
        candidate = pygame.font.match_font(name)
        if candidate and all(pygame.font.Font(candidate, 16).metrics("ếễữệậộĐ")):
            return candidate
    return None


class ChatView:
    def __init__(self, conversation: Conversation) -> None:
        self.conversation = conversation
        self.draft = ""
        self.notice = ""
        self.scroll = 0
        self._shown = ""
        self._lines = []
        self.canvas = pygame.Surface((480, 320))
        self.face_surface = pygame.Surface((480, 172))
        self.face = FaceRenderer()
        font_path = find_text_font()
        if font_path is None:
            raise pygame.error(
                "Vietnamese chat needs DejaVu Sans, Noto Sans or Liberation Sans. Install fonts-dejavu-core on Raspberry Pi OS."
            )
        self.font = pygame.font.Font(font_path, 16)
        self.small = pygame.font.Font(font_path, 10)

    def handle(self, event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.TEXTINPUT:
            # Text input carries Unicode/IME output rather than raw key codes.
            text = "".join(char for char in event.text if char.isprintable())
            self.draft = (self.draft + text)[:MAX_INPUT_CHARS]
            self.notice = ""
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * 2)
        if event.type != pygame.KEYDOWN:
            return True
        modifiers = getattr(event, "mod", 0)
        if event.key == pygame.K_q and modifiers & pygame.KMOD_CTRL:
            return False
        if event.key == pygame.K_ESCAPE:
            self.conversation.cancel()
            self.notice = "Đã hủy chờ. Yêu cầu đã gửi có thể vẫn tính phí."
        elif event.key == pygame.K_l and modifiers & pygame.KMOD_CTRL:
            self.conversation.clear()
            self.draft = ""
            self.notice = "Đã xóa ngữ cảnh trong RAM; bộ đếm lượt gọi được giữ lại."
        elif event.key == pygame.K_BACKSPACE:
            self.draft = self.draft[:-1]
        elif event.key == pygame.K_PAGEUP:
            self.scroll = max(0, self.scroll - 3)
        elif event.key == pygame.K_PAGEDOWN:
            self.scroll += 3
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            try:
                self.conversation.submit(self.draft)
            except ValueError as error:
                self.notice = str(error)
            else:
                self.draft = ""
                self.notice = ""
                self.scroll = 0
        return True

    def _wrap(self, text: str, width: int) -> list[str]:
        # Character wrapping preserves long tokens and Vietnamese text on tiny LCDs.
        lines = []
        line = ""
        for char in text:
            if char == "\n":
                lines.append(line)
                line = ""
            elif self.font.size(line + char)[0] > width and line:
                lines.append(line)
                line = char
            else:
                line += char
        lines.append(line)
        return lines

    def _fit_tail(self, text: str, width: int) -> str:
        if self.font.size(text)[0] <= width:
            return text
        low, high = 0, len(text)
        while low < high:
            middle = (low + high) // 2
            if self.font.size("…" + text[middle:])[0] <= width:
                high = middle
            else:
                low = middle + 1
        return "…" + text[low:]

    def draw(self, target: pygame.Surface, elapsed: float) -> None:
        session = self.conversation
        self.canvas.fill(BG)
        state = FaceState(mood=session.mood, show_help=False)
        self.face.draw(self.face_surface, state, elapsed, badge=session.provider.name.upper())
        self.canvas.blit(self.face_surface, (0, 0))
        status = f"{session.provider.name.upper()} | {session.usage.requests}/{session.max_requests} calls"
        self.canvas.blit(self.small.render(status, True, (155, 183, 193)), (12, 171))
        content = (
            self.notice or session.error or ("Đang xử lý…" if session.busy else session.last_reply)
        )
        if not content:
            content = "Nhập lời nhắn. FAKE là phản hồi mô phỏng, không phải AI thật."
        if content != self._shown:
            self.scroll = 0
            self._shown = content
            self._lines = self._wrap(content, 450)
        lines = self._lines
        self.scroll = min(self.scroll, max(0, len(lines) - 4))
        color = (255, 186, 145) if session.error or self.notice else (232, 240, 237)
        for index, line in enumerate(lines[self.scroll : self.scroll + 4]):
            self.canvas.blit(self.font.render(line, True, color), (14, 188 + index * 19))
        if len(lines) > 4:
            counter = f"{self.scroll + 1}-{min(self.scroll + 4, len(lines))}/{len(lines)}"
            self.canvas.blit(self.small.render(counter, True, (155, 183, 193)), (408, 172))
        pygame.draw.rect(self.canvas, (30, 49, 60), (10, 266, 460, 29), border_radius=6)
        draft = self._fit_tail(self.draft, 430) if self.draft else "Nhập ở đây…"
        self.canvas.blit(self.font.render(draft, True, (215, 231, 229)), (18, 272))
        hint = "Enter: send | Esc: cancel | PgUp/Dn: scroll | Ctrl+L: clear | Ctrl+Q: quit"
        self.canvas.blit(self.small.render(hint, True, (147, 166, 178)), (10, 304))
        width, height = target.get_size()
        scale = min(width / 480, height / 320)
        size = (max(1, round(480 * scale)), max(1, round(320 * scale)))
        target.fill(BG)
        target.blit(
            pygame.transform.smoothscale(self.canvas, size),
            ((width - size[0]) // 2, (height - size[1]) // 2),
        )
