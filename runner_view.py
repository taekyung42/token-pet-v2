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

import expressions as expr

OUTLINE_COLOR = QColor("#8a5a34")
INK_COLOR = QColor("#4a3625")

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SPRITE_HEIGHT = 132

RESET_SOON_SECONDS = 300
CLICK_BURST_DURATION = 1.2
AMBIENT_MESSAGE_DURATION = (1.8, 2.6)
AMBIENT_CHECK_INTERVAL = (3.5, 7.0)


class RunnerView(QWidget):
    """Fully transparent strip: a big puppy mascot runs in place. No track,
    no flag, no scene box -- just the dog, bouncing faster the more tokens
    are flowing, floating directly on the desktop.

    The pet's "mood" (message pool + tint/overlay) is derived from speed,
    5-hour usage %, and time-to-reset together (see expressions.py), so the
    same running animation reads very differently depending on context
    instead of always showing the same handful of messages.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(190)

        self._intensity = 0.0
        self._pct = 0.0
        self._active = False
        self._reset_soon = False
        self._mood = None

        self._bounce_phase = 0.0
        self._message = None
        self._message_until = 0.0
        self._next_message_check = 0.0
        self._click_burst_until = 0.0

        self._tint_cache = {}

        self._sprite_idle = self._load_sprite("dog_idle.png")
        self._sprite_run = self._load_sprite("dog_run.png") or self._sprite_idle

    @staticmethod
    def _load_sprite(filename):
        path = os.path.join(ASSETS_DIR, filename)
        raw = QPixmap(path) if os.path.exists(path) else QPixmap()
        if raw.isNull():
            return None
        return raw.scaledToHeight(SPRITE_HEIGHT, Qt.SmoothTransformation)

    # ---- state feed ----

    def update_state(self, intensity, pct, remaining_seconds, active, just_reset=False):
        self._intensity = max(0.0, min(1.0, intensity))
        self._pct = max(0.0, pct)
        self._active = active
        self._reset_soon = active and 0 < remaining_seconds <= RESET_SOON_SECONDS
        self._mood = expr.get_mood(self._pct, self._intensity, self._active)

        if just_reset:
            self._show_message(random.choice(expr.CELEBRATE_MESSAGES), 2.6, force=True)

    def trigger_click_reaction(self):
        self._show_message(random.choice(expr.CLICK_MESSAGES), 2.0, force=True)
        self._click_burst_until = time.time() + CLICK_BURST_DURATION

    # ---- messages ----

    def _show_message(self, text, duration, force=False):
        if self._message and not force:
            return
        self._message = text
        self._message_until = time.time() + duration
        self._next_message_check = time.time() + random.uniform(*AMBIENT_CHECK_INTERVAL)

    def _pick_ambient_message(self):
        if self._reset_soon and random.random() < 0.35:
            return random.choice(expr.RESET_SOON_MESSAGES)
        if not self._active:
            return random.choice(expr.NO_SESSION_MESSAGES) if random.random() < 0.5 else None
        if self._mood:
            return random.choice(self._mood.messages)
        return None

    # ---- animation ----

    def advance(self, dt):
        if self._intensity > 0.01:
            self._bounce_phase += dt * (1.5 + self._intensity * 4) * 2 * math.pi

        now = time.time()
        if self._message and now > self._message_until:
            self._message = None

        if self._message is None and now > self._next_message_check:
            picked = self._pick_ambient_message()
            if picked:
                self._message = picked
                self._message_until = now + random.uniform(*AMBIENT_MESSAGE_DURATION)
            self._next_message_check = now + random.uniform(*AMBIENT_CHECK_INTERVAL)

        self.update()

    # ---- drawing helpers ----

    def _tinted_sprite(self, sprite, tint_name):
        if not tint_name or sprite is None:
            return sprite
        cache_key = (id(sprite), tint_name)
        cached = self._tint_cache.get(cache_key)
        if cached is not None:
            return cached

        tinted = QPixmap(sprite.size())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, sprite)
        painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        painter.fillRect(tinted.rect(), QColor(*expr.TINT_COLORS[tint_name]))
        painter.end()

        self._tint_cache[cache_key] = tinted
        return tinted

    def _draw_floating_glyph(self, painter, x, y, glyph, color, point_size, alpha_mult=1.0):
        font = QFont()
        font.setPointSize(point_size)
        font.setBold(True)
        painter.setFont(font)
        c = QColor(color)
        c.setAlpha(int(c.alpha() * alpha_mult))
        painter.setPen(c)
        painter.drawText(QRectF(x - 12, y - 12, 24, 24), Qt.AlignCenter, glyph)

    def _draw_sweat(self, painter, cx, top_y):
        # A drop flicks off near the head and streaks diagonally outward,
        # stretching along its flight path and fading -- reads as "flung
        # off while working hard" rather than a static blob sitting there.
        t = time.time()
        cycle = 0.85
        visible_fraction = 0.65
        painter.setPen(Qt.NoPen)
        for i, side in enumerate((-1, 1)):
            local_t = (t + i * cycle * 0.5) % cycle
            if local_t > cycle * visible_fraction:
                continue
            p = local_t / (cycle * visible_fraction)
            dx = side * (10 + p * 24)
            dy = -(6 + p * 20)
            x = cx + side * 12 + dx
            y = top_y + 4 + dy
            alpha = int(230 * (1 - p))
            length = 11 + p * 7
            width = max(1.5, 4.5 * (1 - p * 0.5))
            angle = math.degrees(math.atan2(dy, dx))

            painter.save()
            painter.translate(x, y)
            painter.rotate(angle)
            painter.setBrush(QColor(140, 205, 255, alpha))
            painter.drawEllipse(QRectF(-length / 2, -width / 2, length, width))
            painter.restore()

    def _draw_exclaim(self, painter, cx, y):
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.setPen(QPen(QColor("#c0392b"), 1.4))
        painter.drawEllipse(QRectF(cx - 11, y - 11, 22, 22))
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#c0392b"))
        painter.drawText(QRectF(cx - 11, y - 11, 22, 22), Qt.AlignCenter, "!")

    def _draw_sparkle_trail(self, painter, cx, base_y):
        t = time.time()
        painter.setPen(Qt.NoPen)
        for i in range(3):
            seed = i * 1.7
            p = (t * 1.3 + seed) % 1.0
            x = cx - 55 - i * 16 - p * 10
            y = base_y - 34 - i * 10 + math.sin(t * 4 + seed) * 4
            alpha = int(255 * (1 - p))
            radius = 3 + (1 - p) * 2
            painter.setBrush(QColor(255, 221, 89, alpha))
            painter.drawEllipse(QRectF(x - radius, y - radius, radius * 2, radius * 2))

    def _draw_hearts(self, painter, cx, top_y):
        remaining = self._click_burst_until - time.time()
        if remaining <= 0:
            return
        progress = 1.0 - remaining / CLICK_BURST_DURATION
        for i, dx in enumerate((-18, 0, 18)):
            p = progress - i * 0.12
            if p <= 0 or p >= 1:
                continue
            y = top_y - p * 34
            self._draw_floating_glyph(painter, cx + dx, y, "♥", QColor(255, 105, 150), 13, 1.0 - p)

    def _draw_overlay(self, painter, cx, base_y):
        top_y = base_y - SPRITE_HEIGHT - 4
        overlay = self._mood.overlay if self._mood else None

        if overlay in ("sweat", "sweat_exclaim"):
            self._draw_sweat(painter, cx, top_y)
        if overlay in ("exclaim", "sweat_exclaim"):
            self._draw_exclaim(painter, cx, top_y - 22)
        if overlay == "sparkle_trail":
            self._draw_sparkle_trail(painter, cx, base_y)

        if self._click_burst_until > time.time():
            self._draw_hearts(painter, cx, top_y)

    def _draw_mascot(self, painter, cx, base_y):
        running = self._intensity > 0.01

        if running:
            sprite = self._sprite_run if math.sin(self._bounce_phase) > 0 else self._sprite_idle
        else:
            sprite = self._sprite_idle
        if sprite is None:
            return

        tint = self._mood.tint if self._mood else None
        sprite = self._tinted_sprite(sprite, tint)

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

        if self._mood and self._mood.shake:
            cx += random.uniform(-2, 2)
            base_y += random.uniform(-2, 2)

        self._draw_mascot(painter, cx, base_y)
        self._draw_overlay(painter, cx, base_y)

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
