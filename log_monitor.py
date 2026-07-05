import glob
import json
import os
import time
from collections import deque
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QTimer, Signal

CLAUDE_PROJECTS_DIR = os.path.join(os.path.expanduser("~"), ".claude", "projects")
BLOCK_SECONDS = 5 * 60 * 60
VELOCITY_WINDOW_SECONDS = 15
SCAN_LOOKBACK_SECONDS = BLOCK_SECONDS + 600
POLL_INTERVAL_MS = 1500


def _parse_timestamp(ts_str):
    ts_str = ts_str.rstrip("Z")
    fmt = "%Y-%m-%dT%H:%M:%S.%f" if "." in ts_str else "%Y-%m-%dT%H:%M:%S"
    dt = datetime.strptime(ts_str, fmt)
    return dt.replace(tzinfo=timezone.utc).timestamp()


def _extract_usage(line):
    try:
        obj = json.loads(line)
    except ValueError:
        return None
    if obj.get("type") != "assistant":
        return None
    message = obj.get("message") or {}
    usage = message.get("usage")
    ts_str = obj.get("timestamp")
    if not usage or not ts_str:
        return None
    try:
        ts = _parse_timestamp(ts_str)
    except ValueError:
        return None
    input_tok = usage.get("input_tokens", 0)
    output_tok = usage.get("output_tokens", 0)
    cache_creation_tok = usage.get("cache_creation_input_tokens", 0)
    cache_read_tok = usage.get("cache_read_input_tokens", 0)

    # Total, for the (fallback) 5-hour budget estimate -- the real quota
    # counts cache reads too.
    total_tokens = input_tok + output_tok + cache_creation_tok + cache_read_tok
    # "New work" only, for the running-speed gauge. cache_read_tokens is the
    # same old context getting re-sent every single turn regardless of how
    # much Claude is actually doing right now -- in a long conversation it's
    # already hundreds of thousands of tokens per message, so including it
    # saturates the speed reading at ~max on every turn, big or small.
    activity_tokens = input_tok + output_tok + cache_creation_tok

    # Claude Code writes one JSONL line per content block, but repeats the
    # same aggregate `usage` on every line for a given API call. Dedupe by
    # requestId (falling back to message id) so a single call is counted once.
    dedupe_key = obj.get("requestId") or message.get("id")
    return ts, total_tokens, activity_tokens, dedupe_key


class LogMonitor(QObject):
    """Tails Claude Code's local session logs to derive live token velocity
    and 5-hour rolling usage-block stats. No official quota API exists, so
    the token budget itself is a user-configured estimate (see config.py)."""

    updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._offsets = {}
        self._events = deque()  # (timestamp, total_tokens, activity_tokens, dedupe_key)
        self._seen_keys = set()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    def start(self):
        self._initial_scan()
        self._poll()
        self._timer.start(POLL_INTERVAL_MS)

    def _iter_jsonl_files(self):
        pattern = os.path.join(CLAUDE_PROJECTS_DIR, "**", "*.jsonl")
        return glob.glob(pattern, recursive=True)

    def _initial_scan(self):
        now = time.time()
        for path in self._iter_jsonl_files():
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if now - mtime > SCAN_LOOKBACK_SECONDS:
                try:
                    self._offsets[path] = os.path.getsize(path)
                except OSError:
                    pass
                continue
            self._read_new_lines(path, from_start=True)

    def _read_new_lines(self, path, from_start=False):
        offset = 0 if from_start else self._offsets.get(path, 0)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(offset)
                lines = f.readlines()
                new_offset = f.tell()
        except OSError:
            return
        self._offsets[path] = new_offset
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parsed = _extract_usage(line)
            if not parsed:
                continue
            ts, total_tok, activity_tok, key = parsed
            if key is not None:
                if key in self._seen_keys:
                    continue
                self._seen_keys.add(key)
            self._events.append((ts, total_tok, activity_tok, key))

    def _poll(self):
        now = time.time()
        for path in self._iter_jsonl_files():
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            last_offset = self._offsets.get(path)
            if last_offset is None:
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    mtime = now
                if now - mtime > SCAN_LOOKBACK_SECONDS:
                    self._offsets[path] = size
                    continue
                self._read_new_lines(path, from_start=True)
            elif size > last_offset:
                self._read_new_lines(path, from_start=False)
            elif size < last_offset:
                self._read_new_lines(path, from_start=True)

        cutoff = now - SCAN_LOOKBACK_SECONDS
        while self._events and self._events[0][0] < cutoff:
            _, _, _, expired_key = self._events.popleft()
            self._seen_keys.discard(expired_key)

        self.updated.emit(self._compute_stats(now))

    def _compute_stats(self, now):
        events = sorted(self._events, key=lambda e: e[0])

        vel_cutoff = now - VELOCITY_WINDOW_SECONDS
        recent_activity_tokens = sum(a for ts, _, a, _ in events if ts >= vel_cutoff)
        velocity_tps = recent_activity_tokens / VELOCITY_WINDOW_SECONDS

        # Fixed 5-hour rolling windows: a window rolls over once BLOCK_SECONDS
        # has elapsed since it started, even under continuous, gap-free
        # activity (this mirrors Anthropic's rate-limit window, not a
        # gap-based "session" grouping).
        block_start = None
        block_end = None
        block_events = []
        for ts, total_tok, _, _ in events:
            if block_start is None or ts >= block_end:
                block_start = ts
                block_end = ts + BLOCK_SECONDS
                block_events = []
            block_events.append(total_tok)

        if block_start is None:
            return {
                "velocity_tps": velocity_tps,
                "active": False,
                "block_used": 0,
                "remaining_seconds": 0,
            }

        is_active = now < block_end
        block_used = sum(block_events) if is_active else 0
        remaining_seconds = max(0, block_end - now) if is_active else 0

        return {
            "velocity_tps": velocity_tps,
            "active": is_active,
            "block_used": block_used,
            "remaining_seconds": remaining_seconds,
        }
