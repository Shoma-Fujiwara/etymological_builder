import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone

LOG_DIR = Path(__file__).resolve().parent.parent / "learning_logs"


def load_log(filename, learner_id, days=None):
    path = LOG_DIR / filename

    if not path.exists():
        return []

    today = datetime.now(
        timezone(timedelta(hours=9))
    ).date()

    cutoff = (
        (today - timedelta(days=days - 1)).isoformat()
        if days is not None else None
    )

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [
            row for row in csv.DictReader(f)
            if row.get("learner_id") == learner_id
            and (
                cutoff is None
                or cutoff <= row["timestamp"][:10] <= today.isoformat()
            )
        ]


def get_registration_stats(learner_id, days=None):
    rows = load_log("registration_log.csv", learner_id, days)

    daily = defaultdict(lambda: {
        "registered": 0,
        "verified": 0,
        "edited": 0,
        "deleted": 0,
    })

    actions = {
        "register": "registered",
        "verify": "verified",
        "edit": "edited",
        "delete": "deleted",
    }

    for row in rows:
        date = row["timestamp"][:10]
        action = actions.get(row["action"])

        if action:
            daily[date][action] += 1

    return dict(sorted(daily.items()))


def get_usage_stats(learner_id, days=None):
    rows = load_log("usage_log.csv", learner_id, days)

    daily = defaultdict(lambda: {
        "visible_seconds": 0.0,
        "active_seconds": 0.0,
    })

    seen_events = set()

    for row in rows:
        if row["activity_type"] not in ("registration", "editing"):
            continue

        event_id = row.get("event_id")

        if event_id:
            if event_id in seen_events:
                continue
            seen_events.add(event_id)

        date = row["timestamp"][:10]

        daily[date]["visible_seconds"] += float(
            row["visible_seconds"] or 0
        )
        daily[date]["active_seconds"] += float(
            row["active_seconds"] or 0
        )

    return dict(sorted(daily.items()))

def get_quiz_stats(learner_id, days=None):
    rows = load_log("quiz_log.csv", learner_id, days)

    def new_stats():
        return {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "response_time": 0.0,
            "timed_count": 0,
        }

    daily = defaultdict(new_stats)
    chapters = defaultdict(new_stats)

    for row in rows:
        if row.get("quiz_type") not in ("daily", "free"):
            continue

        result = row.get("is_correct", "").lower()

        if result not in ("true", "false"):
            continue

        date = row["timestamp"][:10]
        chapter = row["chapter"]

        try:
            response_time = float(row["response_time"])
        except (ValueError, TypeError):
            response_time = None

        for stats in (daily[date], chapters[chapter]):
            stats["total"] += 1

            if result == "true":
                stats["correct"] += 1
            else:
                stats["incorrect"] += 1

            if response_time is not None and response_time >= 0:
                stats["response_time"] += response_time
                stats["timed_count"] += 1

    for group in (daily, chapters):
        for stats in group.values():
            stats["accuracy"] = round(
                stats["correct"] / stats["total"] * 100, 1
            )

            stats["average_time"] = (
                round(
                    stats["response_time"] / stats["timed_count"], 2
                )
                if stats["timed_count"] else None
            )

    return {
        "daily": dict(sorted(daily.items())),
        "chapters": dict(sorted(chapters.items())),
    }

def get_vocabulary_stats():
    import yaml
    from vocab_editor.quiz_core import VOCAB_DIR

    chapters = set()
    stacks = set()
    total = 0
    verified = 0

    for path in sorted(VOCAB_DIR.glob("chapter_*/*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            continue

        for word_data in data.get("words", []):
            if not isinstance(word_data, dict):
                continue

            if not word_data.get("word"):
                continue

            chapters.add(data.get("chapter"))
            stacks.add((data.get("chapter"), data.get("stack")))

            total += 1

            if word_data.get("verified") is True:
                verified += 1

    return {
        "chapters": len(chapters),
        "stacks": len(stacks),
        "total": total,
        "verified": verified,
        "unverified": total - verified,
        "verification_rate": round(verified / total * 100, 1)
        if total else 0,
    }

def get_network_stats(learner_id, days=None):
    rows = load_log("network_log.csv", learner_id, days)

    daily = defaultdict(lambda: {
        "open_count": 0,
        "visible_seconds": 0.0,
        "active_seconds": 0.0,
    })

    seen_events = set()

    for row in rows:
        event_id = row.get("event_id")

        if event_id:
            if event_id in seen_events:
                continue
            seen_events.add(event_id)

        date = row["timestamp"][:10]

        daily[date]["open_count"] += int(
            row["open_count"] or 0
        )
        daily[date]["visible_seconds"] += float(
            row["visible_seconds"] or 0
        )
        daily[date]["active_seconds"] += float(
            row["active_seconds"] or 0
        )

    return dict(sorted(daily.items()))