
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "learner_config.json"


def get_learner_id():
    """保存済みの学習者IDを取得する"""
    if not CONFIG_FILE.exists():
        return None

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None

    if not isinstance(data, dict):
        return None

    learner_id = data.get("learner_id")

    if isinstance(learner_id, str) and re.fullmatch(r"user\d{3}", learner_id):
        return learner_id

    return None


def save_learner_id(learner_id):
    """学習者IDを設定ファイルに保存する"""
    if not isinstance(learner_id, str) or not re.fullmatch(r"user\d{3}", learner_id):
        raise ValueError("学習者IDは user001 の形式で入力してください")

    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            {"learner_id": learner_id},
            f,
            ensure_ascii=False,
            indent=2
        )
