
import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from vocab_editor.learner import get_learner_id


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "learning_logs"
LOG_FILE = LOG_DIR / "quiz_log.csv"

FIELDS = [
    "learner_id",
    "timestamp",
    "quiz_id",
    "word",
    "quiz_type",
    "quiz_scope",
    "chapter",
    "stack",
    "selected_answer",
    "correct_answer",
    "is_correct",
    "response_time",
]


def save_quiz_log(
    word,
    quiz_type,
    chapter,
    stack,
    selected_answer,
    correct_answer,
    is_correct,
    response_time,
    quiz_id=None,
    quiz_scope=None,
):
    """1問分の回答結果をCSVに保存する"""

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_exists = LOG_FILE.exists() and LOG_FILE.stat().st_size > 0

    row = {
        "learner_id": get_learner_id(),
        "timestamp": datetime.now(
            ZoneInfo("Asia/Tokyo")
        ).isoformat(timespec="seconds"),
        "word": word,
        "quiz_type": quiz_type,
        "quiz_id": quiz_id,
        "quiz_scope": quiz_scope,
        "chapter": chapter,
        "stack": stack,
        "selected_answer": selected_answer,
        "correct_answer": correct_answer,
        "is_correct": is_correct,
        "response_time": response_time,
    }

    with LOG_FILE.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)
