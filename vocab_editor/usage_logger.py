
import csv
from datetime import datetime
from pathlib import Path

from .learner import get_learner_id
from threading import Lock

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "learning_logs" / "usage_log.csv"
USAGE_LOCK = Lock()

FIELDS = [
    "learner_id",
    "timestamp",
    "session_id",
    "event_id",
    "activity_type",
    "visible_seconds",
    "active_seconds",
]


def save_usage_log(session_id, event_id, activity_type,
                   visible_seconds, active_seconds):

    if activity_type not in ("registration", "editing"):
        raise ValueError("Invalid activity type")

    visible_seconds = max(0, float(visible_seconds))
    active_seconds = max(0, float(active_seconds))

    # 推定操作時間が滞在時間を超えないようにする
    active_seconds = min(active_seconds, visible_seconds)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # event_idが空欄ならエラー
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("Invalid event_id")

    with USAGE_LOCK:
        # 同じevent_idが記録済みなら保存しない
        if LOG_FILE.exists():
            with LOG_FILE.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    if row.get("event_id") == event_id:
                        return

        new_file = (
            not LOG_FILE.exists()
            or LOG_FILE.stat().st_size == 0
        )

        with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)

            if new_file:
                writer.writeheader()

            writer.writerow({
                "learner_id": get_learner_id(),
                "timestamp": datetime.now().astimezone().isoformat(
                    timespec="seconds"
                ),
                "session_id": session_id,
                "event_id": event_id,
                "activity_type": activity_type,
                "visible_seconds": visible_seconds,
                "active_seconds": active_seconds,
            })