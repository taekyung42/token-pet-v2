import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

CREDENTIALS_PATH = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
REQUEST_TIMEOUT_SECONDS = 10


def _parse_iso(ts_str):
    if not ts_str:
        return None
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _read_access_token():
    with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("claudeAiOauth", {}).get("accessToken")


def fetch_real_usage():
    """Calls Anthropic's own /api/oauth/usage endpoint (the same one Claude
    Code's CLI uses for its /usage popup) using the locally stored OAuth
    token. Returns a dict with real five-hour utilization/reset data, or
    None if the token is missing/expired or the request fails for any
    reason (caller should fall back to local-log estimation)."""
    try:
        access_token = _read_access_token()
        if not access_token:
            return None

        req = urllib.request.Request(
            USAGE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "anthropic-beta": "oauth-2025-04-20",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError):
        return None

    five_hour = payload.get("five_hour") or {}
    seven_day = payload.get("seven_day") or {}

    return {
        "five_hour_pct": five_hour.get("utilization"),
        "five_hour_resets_at": _parse_iso(five_hour.get("resets_at")),
        "seven_day_pct": seven_day.get("utilization"),
        "seven_day_resets_at": _parse_iso(seven_day.get("resets_at")),
    }
