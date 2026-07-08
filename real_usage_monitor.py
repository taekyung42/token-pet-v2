import threading

from PySide6.QtCore import QObject, QTimer, Signal

import usage_api

POLL_INTERVAL_MS = 45_000
RETRY_INTERVAL_MS = 8_000
MAX_RETRY_INTERVAL_MS = POLL_INTERVAL_MS


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
        self.updated.connect(self._schedule_next)

    def start(self):
        self._trigger_fetch()

    def _trigger_fetch(self):
        if self._fetching:
            return
        self._fetching = True
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        result = usage_api.fetch_real_usage()
        self._fetching = False
        self.updated.emit(result)

    def _schedule_next(self, result):
        if result:
            self._retry_interval_ms = RETRY_INTERVAL_MS
            self._timer.start(POLL_INTERVAL_MS)
        else:
            self._timer.start(self._retry_interval_ms)
            self._retry_interval_ms = min(self._retry_interval_ms * 2, MAX_RETRY_INTERVAL_MS)
