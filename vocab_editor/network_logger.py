import csv
import math
from datetime import datetime
from pathlib import Path
from threading import Lock

from .learner import get_learner_id

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "learning_logs" / "network_log.csv"
NETWORK_LOCK = Lock()

FIELDS = [
    "learner_id",
    "timestamp",
    "session_id",
    "event_id",
    "visible_seconds",
    "active_seconds",
    "open_count",
]


def save_network_log(data):

    for key in ("session_id", "event_id"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Invalid {key}")

    row = {key: data.get(key, "") for key in FIELDS}

    for key in ("visible_seconds", "active_seconds"):
        value = float(data.get(key, 0))
        if not math.isfinite(value):
            raise ValueError(f"Invalid {key}")
        row[key] = max(0, value)

    row["active_seconds"] = min(
        row["active_seconds"], row["visible_seconds"]
    )

    row["open_count"] = max(0, int(data.get("open_count", 0)))

    row["learner_id"] = get_learner_id()
    row["timestamp"] = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with NETWORK_LOCK:
        if LOG_FILE.exists():
            with LOG_FILE.open(
                "r", newline="", encoding="utf-8"
            ) as f:
                for saved in csv.DictReader(f):
                    if saved.get("event_id") == row["event_id"]:
                        return

        new_file = (
            not LOG_FILE.exists()
            or LOG_FILE.stat().st_size == 0
        )

        with LOG_FILE.open(
            "a", newline="", encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)

            if new_file:
                writer.writeheader()

            writer.writerow(row)