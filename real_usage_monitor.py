import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal

import usage_api

POLL_INTERVAL_MS = 300_000   # 5분마다 폴링 (rate limit 방지)
RETRY_INTERVAL_MS = 60_000  # 실패 시 1분 후 재시도
MAX_RETRY_INTERVAL_MS = POLL_INTERVAL_MS
MANUAL_REFRESH_COOLDOWN_MS = 15_000  # 사용자가 연타해도 엔드포인트를 스팸하지 않도록
FAILURES_BEFORE_TOKEN_REFRESH = 2  # 단순 네트워크 blip이 아니라 진짜 토큰 만료로 보일 때만 시도


class RealUsageMonitor(QObject):
    """Periodically calls Anthropic's own /api/oauth/usage endpoint (same
    one Claude Code's /usage popup uses) in a background thread so the exact
    five-hour utilization/reset time can replace the local log-based
    estimate whenever it's reachable.

    On failure (rate limit, network blip, etc.) retries sooner than the
    normal poll cadence so a transient blip recovers quickly -- but backs
    off exponentially on repeated failures (capped at the normal cadence)
    so a sustained rate limit isn't kept alive by us hammering the endpoint
    every few seconds forever.
    """

    updated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._trigger_fetch)
        self._fetching = False
        self._retry_interval_ms = RETRY_INTERVAL_MS
        self._last_fetch_started = 0.0
        self._consecutive_failures = 0
        self.updated.connect(self._schedule_next)

    def start(self):
        self._trigger_fetch()

    def refresh_now(self):
        """Manual trigger (e.g. right-click menu) to bypass the wait for the
        next scheduled poll. Cooldown-gated so repeated clicks can't hammer
        the (unofficial, rate-limit-sensitive) endpoint."""
        since_last = time.monotonic() - self._last_fetch_started
        if self._fetching or since_last * 1000 < MANUAL_REFRESH_COOLDOWN_MS:
            return False
        self._timer.stop()
        self._trigger_fetch()
        return True

    def _trigger_fetch(self):
        if self._fetching:
            return
        self._fetching = True
        self._last_fetch_started = time.monotonic()
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        result = usage_api.fetch_real_usage()
        self._fetching = False
        self.updated.emit(result)

    def _schedule_next(self, result):
        if result:
            self._consecutive_failures = 0
            self._retry_interval_ms = RETRY_INTERVAL_MS
            self._timer.start(POLL_INTERVAL_MS)
        else:
            self._consecutive_failures += 1
            if self._consecutive_failures == FAILURES_BEFORE_TOKEN_REFRESH:
                threading.Thread(target=usage_api.try_refresh_token, daemon=True).start()
            self._timer.start(self._retry_interval_ms)
            self._retry_interval_ms = min(self._retry_interval_ms * 2, MAX_RETRY_INTERVAL_MS)
