import math
import os
import random
import time

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

HARD_MESSAGES = ["헥헥...", "힘들어 ㅠㅠ", "숨차...", "잠깐만!", "못 참겠어"]

HARD_INTENSITY_THRESHOLD = 0.55

OUTLINE_COLOR = QColor("#8a5a34")
INK_COLOR = QColor("#4a3625")

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SPRITE_HEIGHT = 132


class RunnerView(QWidget):
    """Fully transparent strip: a big puppy mascot runs in place. No track,
    no flag, no scene box -- just the dog, bouncing faster the more tokens
    are flowing, floating directly on the desktop."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(190)
        self._progress = 0.0
        self._intensity = 0.0
        self._bounce_phase = 0.0
        self._message = None
        self._message_until = 0.0
        self._next_message_check = 0.0

        self._sprite_idle = self._load_sprite("dog_idle.png")
        self._sprite_run = self._load_sprite("dog_run.png") or self._sprite_idle

    @staticmethod
    def _load_sprite(filename):
        path = os.path.join(ASSETS_DIR, filename)
        raw = QPixmap(path) if os.path.exists(path) else QPixmap()
        if raw.isNull():
            return None
        return raw.scaledToHeight(SPRITE_HEIGHT, Qt.SmoothTransformation)

    def set_progress(self, pct):
        pct = max(0.0, pct)
        if pct >= 100.0 and self._progress < 100.0:
            self._message = "성공!"
            self._message_until = time.time() + 2.5
        self._progress = pct

    def set_intensity(self, intensity):
        self._intensity = max(0.0, min(1.0, intensity))

    def advance(self, dt):
        if self._intensity > 0.01:
            self._bounce_phase += dt * (1.5 + self._intensity * 4) * 2 * math.pi

        now = time.time()
        if self._message and now > self._message_until:
            self._message = None
        if (
            self._intensity > HARD_INTENSITY_THRESHOLD
            and self._message is None
            and now > self._next_message_check
        ):
            self._message = random.choice(HARD_MESSAGES)
            self._message_until = now + 1.8
            self._next_message_check = now + random.uniform(3.0, 5.5)

        self.update()

    # ---- drawing helpers ----

    def _draw_mascot(self, painter, cx, base_y):
        running = self._intensity > 0.01

        if running:
            sprite = self._sprite_run if math.sin(self._bounce_phase) > 0 else self._sprite_idle
        else:
            sprite = self._sprite_idle
        if sprite is None:
            return

        painter.save()
        painter.translate(cx, base_y)
        w = sprite.width()
        h = sprite.height()
        painter.drawPixmap(QRectF(-w / 2, -h, w, h), sprite, QRectF(sprite.rect()))
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        cx = w / 2
        base_y = h - 6

        self._draw_mascot(painter, cx, base_y)

        if self._message:
            bubble_font = QFont()
            bubble_font.setPointSize(9)
            bubble_font.setBold(True)
            painter.setFont(bubble_font)
            metrics = painter.fontMetrics()
            text_w = metrics.horizontalAdvance(self._message) + 16
            bubble_x = min(max(cx - text_w / 2, 4), w - text_w - 4)
            bubble_y = base_y - SPRITE_HEIGHT - 26
            painter.setBrush(QColor(255, 255, 255, 235))
            painter.setPen(QPen(OUTLINE_COLOR, 1.4))
            painter.drawRoundedRect(QRectF(bubble_x, bubble_y, text_w, 22), 10, 10)
            painter.setPen(INK_COLOR)
            painter.drawText(QRectF(bubble_x, bubble_y, text_w, 22), Qt.AlignCenter, self._message)
