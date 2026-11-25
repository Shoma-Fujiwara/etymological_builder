from datetime import date, datetime
from pathlib import Path
import yaml
import random
import csv


BASE_DIR = Path(__file__).resolve().parent.parent
VOCAB_DIR = BASE_DIR / "vocab_data"

QUIZ_LOG_PATH = BASE_DIR / "learning_logs" / "quiz_log.csv"


def load_answered_words(learner_id):
    """振り返りテストで回答済みの単語を取得する"""
    answered = set()

    if not QUIZ_LOG_PATH.exists():
        return answered

    with QUIZ_LOG_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row.get("learner_id") != learner_id:
                continue

            if row.get("quiz_type") != "daily":
                continue

            key = (
                str(row.get("chapter", "")),
                str(row.get("stack", "")),
                row.get("word", ""),
            )

            answered.add(key)

    return answered


def is_today(value, today):
    """日時が指定日と一致するか確認する"""
    if not value:
        return False

    try:
        if isinstance(value, datetime):
            return value.date() == today

        if isinstance(value, date):
            return value == today

        return datetime.fromisoformat(str(value)).date() == today
    except (ValueError, TypeError):
        return False


def load_today_words(learner_id):
    """確認済みで、振り返りテストに未回答の単語を取得する"""
    answered_words = load_answered_words(learner_id)

    questions = []
    seen = set()

    for path in sorted(VOCAB_DIR.glob("chapter_*/*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            continue

        for word_data in data.get("words", []):
            if not isinstance(word_data, dict):
                continue

            if word_data.get("verified") is not True:
                continue

            word = word_data.get("word")
            meanings = word_data.get("meanings", {})

            if not word or not isinstance(meanings, dict):
                continue

            answers = [
                meaning
                for values in meanings.values()
                if isinstance(values, list)
                for meaning in values
                if isinstance(meaning, str) and meaning.strip()
            ]

            if not answers:
                continue

            key = (
                str(data.get("chapter", "")),
                str(data.get("stack", "")),
                word,
            )

            if key in seen or key in answered_words:
                continue

            seen.add(key)

            questions.append({
                "word": word,
                "answers": answers,
                "chapter": data.get("chapter"),
                "stack": data.get("stack"),
            })

    return questions

def load_verified_words():
    """全Stackから確認済み単語を取得する"""
    words = []

    for path in sorted(VOCAB_DIR.glob("chapter_*/*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            continue

        for word_data in data.get("words", []):
            if not isinstance(word_data, dict):
                continue

            if word_data.get("verified") is not True:
                continue

            word = word_data.get("word")
            meanings = word_data.get("meanings", {})

            if not word or not isinstance(meanings, dict):
                continue

            answers = [
                meaning.strip()
                for values in meanings.values()
                if isinstance(values, list)
                for meaning in values
                if isinstance(meaning, str) and meaning.strip()
            ]

            if not answers:
                continue

            words.append({
                "word": word,
                "answers": answers,
                "chapter": data.get("chapter"),
                "stack": data.get("stack"),
                "parts": word_data.get("parts", []),
                "derivatives": word_data.get("derivatives", []),
            })

    return words

def select_wrong_answers(word_data, all_words):
    """同じStackを優先して誤答を3つ選ぶ"""
    correct_answers = set(word_data["answers"])

    same_stack = set()
    other_stack = set()

    for other in all_words:
        if (
            other["word"] == word_data["word"]
            and str(other["chapter"]) == str(word_data["chapter"])
            and str(other["stack"]) == str(word_data["stack"])
        ):
            continue

        target = (
            same_stack
            if str(other["chapter"]) == str(word_data["chapter"])
            and str(other["stack"]) == str(word_data["stack"])
            else other_stack
        )

        for meaning in other["answers"]:
            meaning = meaning.strip()
            if meaning and meaning not in correct_answers:
                target.add(meaning)

    same_stack = list(same_stack)
    other_stack = list(other_stack - set(same_stack))

    random.shuffle(same_stack)
    random.shuffle(other_stack)

    candidates = same_stack + other_stack

    return candidates[:3]

def create_quiz_questions(learner_id):
    """未回答の確認済み単語から4択問題を生成する"""
    target_words = load_today_words(learner_id)
    all_words = load_verified_words()

    questions = []

    for word_data in target_words:
        correct_answers = word_data["answers"]
        correct = correct_answers[0]

        wrong_answers = select_wrong_answers(
            word_data, all_words
        )

        if len(wrong_answers) < 3:
            raise ValueError(
                f"4択の候補が不足しています: {word_data['word']}"
            )

        choices = [correct] + wrong_answers
        random.shuffle(choices)

        questions.append({
            "word": word_data["word"],
            "choices": choices,
            "correct": correct,
            "chapter": word_data["chapter"],
            "stack": word_data["stack"],
        })

    random.shuffle(questions)
    return questions

def create_free_quiz_questions(
    question_count=None,
    scope="all",
    chapter=None,
    stack=None,
    learner_id=None,
):
    """指定された範囲の確認済み単語から4択問題を生成する"""

    all_words = load_verified_words()

    if scope == "chapter":
        target_words = [
            w for w in all_words
            if str(w["chapter"]) == str(chapter)
        ]

    elif scope == "stack":
        target_words = [
            w for w in all_words
            if str(w["chapter"]) == str(chapter)
            and str(w["stack"]) == str(stack)
        ]

    elif scope == "incorrect":
        target_words = load_incorrect_words(learner_id)

    else:
        target_words = all_words

    questions = []

    for word_data in target_words:
        # 自由テストでは正解の意味をランダムに選ぶ
        correct = random.choice(word_data["answers"])

        # 同じStackを優先して誤答を選ぶ
        wrong_answers = select_wrong_answers(
            word_data, all_words
        )

        if len(wrong_answers) < 3:
            raise ValueError(
                f"4択の候補が不足しています: {word_data['word']}"
            )

        choices = [correct] + wrong_answers
        random.shuffle(choices)

        questions.append({
            "word": word_data["word"],
            "choices": choices,
            "correct": correct,
            "chapter": word_data["chapter"],
            "stack": word_data["stack"],
        })

    random.shuffle(questions)

    if question_count is not None:
        questions = questions[:question_count]

    return questions

def load_incorrect_words(learner_id):
    """誤答後、2回連続正解していない苦手単語を取得する"""
    if not QUIZ_LOG_PATH.exists():
        return []

    history = []

    with QUIZ_LOG_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row.get("learner_id") != learner_id:
                continue

            if row.get("quiz_type") not in ("daily", "free"):
                continue

            result = row.get("is_correct", "").lower()
            if result not in ("true", "false"):
                continue

            key = (
                str(row.get("chapter", "")),
                str(row.get("stack", "")),
                row.get("word", ""),
            )

            history.append((
                row.get("timestamp", ""),
                key,
                result == "true",
            ))

    # 回答日時順に処理する
    history.sort(key=lambda item: item[0])

    # 各単語の状態: [苦手かどうか, 連続正解数]
    states = {}

    for _, key, is_correct in history:
        weak, streak = states.get(key, (False, 0))

        if not is_correct:
            states[key] = (True, 0)

        elif weak:
            streak += 1

            if streak >= 2:
                states[key] = (False, 0)
            else:
                states[key] = (True, streak)

    incorrect_keys = {
        key for key, (weak, _) in states.items()
        if weak
    }

    return [
        word_data
        for word_data in load_verified_words()
        if (
            str(word_data["chapter"]),
            str(word_data["stack"]),
            word_data["word"],
        ) in incorrect_keys
    ]

def classify_recommended_words(learner_id):
    """おすすめ出題用に単語を3種類に分類する"""

    all_words = load_verified_words()

    # 現在の苦手単語
    incorrect_words = load_incorrect_words(learner_id)

    def word_key(w):
        return (
            str(w["chapter"]),
            str(w["stack"]),
            w["word"],
        )

    incorrect_keys = {
        word_key(w) for w in incorrect_words
    }

    # 自由テストで回答済みの単語
    answered_keys = set()

    if QUIZ_LOG_PATH.exists():
        with QUIZ_LOG_PATH.open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            reader = csv.DictReader(f)

            for row in reader:
                if row.get("learner_id") != learner_id:
                    continue

                if row.get("quiz_type") != "free":
                    continue

                key = (
                    str(row.get("chapter", "")),
                    str(row.get("stack", "")),
                    row.get("word", ""),
                )
                answered_keys.add(key)

    categories = {
        "new": [],
        "incorrect": [],
        "other": [],
    }

    for word_data in all_words:
        key = word_key(word_data)

        if key in incorrect_keys:
            categories["incorrect"].append(word_data)

        elif key not in answered_keys:
            categories["new"].append(word_data)

        else:
            categories["other"].append(word_data)

    return categories

def calculate_correct_streaks(learner_id):
    """振り返り・自由テストの履歴から連続正解回数を計算する"""

    streaks = {}

    if not QUIZ_LOG_PATH.exists():
        return streaks

    history = []

    with QUIZ_LOG_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row.get("learner_id") != learner_id:
                continue

            if row.get("quiz_type") not in ("daily", "free"):
                continue

            result = row.get("is_correct", "").lower()
            if result not in ("true", "false"):
                continue

            key = (
                str(row.get("chapter", "")),
                str(row.get("stack", "")),
                row.get("word", ""),
            )

            history.append((
                row.get("timestamp", ""),
                key,
                result == "true",
            ))

    # 回答日時順に並べる
    history.sort(key=lambda item: item[0])

    for _, key, is_correct in history:
        if is_correct:
            streaks[key] = streaks.get(key, 0) + 1
        else:
            streaks[key] = 0

    return streaks

def select_recommended_words(learner_id, question_count=None):
    """連続正解回数に応じた重み付きランダム選択"""

    all_words = load_verified_words()
    streaks = calculate_correct_streaks(learner_id)

    def get_weight(word_data):
        key = (
            str(word_data["chapter"]),
            str(word_data["stack"]),
            word_data["word"],
        )

        # 未回答の単語
        if key not in streaks:
            return 10

        streak = streaks[key]

        if streak == 0:
            return 10
        elif streak == 1:
            return 6
        elif streak == 2:
            return 4
        elif streak == 3:
            return 2
        else:
            return 1

    # 重みに応じて、重複なしで単語を選択
    remaining = all_words.copy()
    selected = []

    if question_count is None:
        question_count = len(remaining)

    while remaining and len(selected) < question_count:
        weights = [get_weight(w) for w in remaining]

        chosen = random.choices(
            remaining,
            weights=weights,
            k=1,
        )[0]

        selected.append(chosen)
        remaining.remove(chosen)

    return selected