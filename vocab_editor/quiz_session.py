
import json
import sqlite3
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "learning_logs" / "quiz_sessions.db"



def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_sessions (
            quiz_id TEXT PRIMARY KEY,
            learner_id TEXT NOT NULL,
            quiz_type TEXT NOT NULL,
            questions TEXT NOT NULL
        )
    """)

    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(quiz_sessions)")
    }
    if "quiz_scope" not in columns:
        conn.execute(
            "ALTER TABLE quiz_sessions ADD COLUMN quiz_scope TEXT"
        )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_answers (
            quiz_id TEXT NOT NULL,
            question_index INTEGER NOT NULL,
            PRIMARY KEY (quiz_id, question_index)
        )
    """)

    return conn



def save_quiz_session(learner_id, quiz_type, questions, quiz_scope=None):
    """出題した問題を保存し、テストIDを返す"""
    quiz_id = uuid.uuid4().hex

    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO quiz_sessions
            (quiz_id, learner_id, quiz_type, questions, quiz_scope)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                quiz_id,
                learner_id,
                quiz_type,
                json.dumps(questions, ensure_ascii=False),
                quiz_scope
            )
        )

    return quiz_id


def get_quiz_session(quiz_id, learner_id):
    """指定した学習者のテストを取得する"""
    with connect_db() as conn:
        row = conn.execute(
            """
            SELECT quiz_type, questions, quiz_scope
            FROM quiz_sessions
            WHERE quiz_id = ? AND learner_id = ?
            """,
            (quiz_id, learner_id)
        ).fetchone()

    if row is None:
        return None

    return {
        "quiz_type": row[0],
        "questions": json.loads(row[1]),
        "quiz_scope": row[2]
    }


def mark_answered(quiz_id, question_index):
    """初回回答なら記録してTrue、回答済みならFalseを返す"""
    with connect_db() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO quiz_answers
            (quiz_id, question_index)
            VALUES (?, ?)
            """,
            (quiz_id, question_index)
        )

        return cursor.rowcount == 1

def unmark_answered(quiz_id, question_index):
    """ログ保存失敗時に回答済み記録を取り消す"""
    with connect_db() as conn:
        conn.execute(
            """
            DELETE FROM quiz_answers
            WHERE quiz_id = ? AND question_index = ?
            """,
            (quiz_id, question_index)
        )
