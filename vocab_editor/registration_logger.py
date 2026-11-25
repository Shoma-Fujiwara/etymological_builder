
import csv
from datetime import datetime
from pathlib import Path

from .learner import get_learner_id

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "learning_logs" / "registration_log.csv"

FIELDS = [
    "learner_id",
    "timestamp",
    "action",
    "chapter",
    "stack",
    "word",
]


def save_registration_log(action, chapter, stack, word):
    """教材の登録・編集・確認操作をCSVに記録する"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    new_file = not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0

    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)

        if new_file:
            writer.writeheader()

        writer.writerow({
            "learner_id": get_learner_id(),
            "timestamp": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "action": action,
            "chapter": chapter,
            "stack": stack,
            "word": word,
        })
