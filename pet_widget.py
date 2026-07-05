import math
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QMenu,
    QInputDialog,
    QApplication,
)

import config as cfg
from runner_view import RunnerView

WIDTH, HEIGHT = 260, 255
ANIM_INTERVAL_MS = 40

# Calibrated against real "new work" (output+input+cache-creation, i.e.
# excluding re-sent cache-read context) token rates: a single quiet turn is
# ~50-100 tok/s, a hefty bursty one is ~1,000+ tok/s. Log scale spreads that
# range out so light vs. heavy activity actually looks different -- speed
# you can read by eye, not just the percent label.
LOG_VELOCITY_CEILING = 3_000.0


def _velocity_to_intensity(tps):
    if tps <= 0:
        return 0.0
    intensity = math.log10(tps + 1) / math.log10(LOG_VELOCITY_CEILING + 1)
    return max(0.0, min(1.0, intensity))


def _fmt_hms(seconds):
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}"


class PetWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._config = cfg.load_config()
        self._drag_offset = None
        self._last_tick = time.monotonic()
        self._real_usage = None

        self._setup_window()
        self._setup_ui()
        self._restore_position()

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_animation)
        self._anim_timer.start(ANIM_INTERVAL_MS)

    # ---- window setup ----

    def _setup_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(WIDTH, HEIGHT)

    def _setup_ui(self):
        self.setStyleSheet(
            """
            #infobox {
                background-color: rgba(30, 30, 40, 190);
                border-radius: 14px;
            }
            QLabel {
                color: white;
                background: transparent;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(6)

        self.runner = RunnerView(self)

        self.info_box = QWidget(self)
        self.info_box.setObjectName("infobox")
        self.info_box.setFixedWidth(180)
        info_layout = QVBoxLayout(self.info_box)
        info_layout.setContentsMargins(8, 3, 8, 4)
        info_layout.setSpacing(0)

        small_font = QFont()
        small_font.setPointSize(8)

        self.speed_label = QLabel("🏃 속도 0%")
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed_label.setFont(small_font)

        self.usage_label = QLabel("사용량 로딩 중...")
        self.usage_label.setAlignment(Qt.AlignCenter)
        self.usage_label.setFont(small_font)
        self.usage_label.setWordWrap(True)

        self.reset_label = QLabel("")
        self.reset_label.setAlignment(Qt.AlignCenter)
        self.reset_label.setFont(small_font)

        info_layout.addWidget(self.speed_label)
        info_layout.addWidget(self.usage_label)
        info_layout.addWidget(self.reset_label)

        outer.addWidget(self.runner)
        outer.addWidget(self.info_box, 0, Qt.AlignHCenter)

    # ---- position persistence ----

    def _restore_position(self):
        x, y = self._config.get("window_x"), self._config.get("window_y")
        if x is not None and y is not None:
            self.move(int(x), int(y))
            return
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - WIDTH - 24, screen.top() + 24)

    def _save_position(self):
        self._config["window_x"] = self.x()
        self._config["window_y"] = self.y()
        cfg.save_config(self._config)

    # ---- data updates ----

    def on_real_usage_updated(self, data):
        if data and data.get("five_hour_pct") is not None:
            self._real_usage = data

    def on_stats_updated(self, stats):
        velocity_tps = stats.get("velocity_tps", 0.0)
        active = stats.get("active", False)

        intensity = _velocity_to_intensity(velocity_tps)
        self.speed_label.setText(f"🏃 속도 {round(intensity * 100)}%")
        self.runner.set_intensity(intensity if active else 0.0)

        if self._real_usage is not None:
            pct = max(0.0, self._real_usage["five_hour_pct"])
            resets_at = self._real_usage.get("five_hour_resets_at")
            remaining = max(0.0, resets_at - time.time()) if resets_at else 0.0
            self.usage_label.setText(f"이번 5시간 사용률 {round(pct)}%")
            self.reset_label.setText(f"⏳ 리셋까지 {_fmt_hms(remaining)}")
            self.runner.set_progress(pct)
        elif active:
            budget = self._config.get("block_budget_tokens", 30_000_000)
            used = stats.get("block_used", 0)
            pct = (used / budget * 100.0) if budget else 0.0
            self.usage_label.setText(f"이번 5시간 사용률 {round(pct)}% (추정)")
            remaining = stats.get("remaining_seconds", 0)
            self.reset_label.setText(f"⏳ 리셋까지 {_fmt_hms(remaining)}")
            self.runner.set_progress(pct)
        else:
            self.usage_label.setText("대기 중 (활성 세션 없음)")
            self.reset_label.setText("")
            self.runner.set_progress(0.0)

    # ---- animation ----

    def _tick_animation(self):
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now
        self.runner.advance(dt)

    # ---- drag to move ----

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            self._save_position()

    # ---- context menu ----

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        set_budget_action = menu.addAction("5시간 토큰 예산 설정...")
        reset_pos_action = menu.addAction("위치 초기화")
        menu.addSeparator()
        quit_action = menu.addAction("종료")

        chosen = menu.exec(event.globalPos())
        if chosen == set_budget_action:
            self._prompt_budget()
        elif chosen == reset_pos_action:
            self._config["window_x"] = None
            self._config["window_y"] = None
            cfg.save_config(self._config)
            self._restore_position()
        elif chosen == quit_action:
            QApplication.instance().quit()

    def _prompt_budget(self):
        current = self._config.get("block_budget_tokens", 30_000_000)
        value, ok = QInputDialog.getInt(
            self,
            "5시간 토큰 예산 설정",
            "5시간 블록당 예상 토큰 예산 (공식 수치가 아닌 추정값입니다):",
            value=current,
            minValue=10_000,
            maxValue=1_000_000_000,
            step=100_000,
        )
        if ok:
            self._config["block_budget_tokens"] = value
            cfg.save_config(self._config)
