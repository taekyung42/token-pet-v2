import threading

from PySide6.QtCore import QObject, QTimer, Signal

import usage_api

POLL_INTERVAL_MS = 45_000


class RealUsageMonitor(QObject):
    """Periodically calls Anthropic's own /api/oauth/usage endpoint (same
    one Claude Code's /usage popup uses) in a background thread so the exact
    five-hour utilization/reset time can replace the local log-based
    estimate whenever it's reachable."""

    updated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._trigger_fetch)
        self._fetching = False

    def start(self):
        self._trigger_fetch()
        self._timer.start(POLL_INTERVAL_MS)

    def _trigger_fetch(self):
        if self._fetching:
            return
        self._fetching = True
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        result = usage_api.fetch_real_usage()
        self._fetching = False
        self.updated.emit(result)
