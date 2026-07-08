import json
import os

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".token-pet-v2")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    # Rough starting guess for the (cache-read-discounted) weighted-token
    # budget -- see log_monitor.py. Self-calibrates upward/downward once the
    # real usage API is reachable (see PetWidget._maybe_calibrate_budget).
    "block_budget_tokens": 30_000_000,
    "window_x": None,
    "window_y": None,
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULTS)
            merged.update(data)
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULTS)


def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
