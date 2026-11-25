
import re
from datetime import datetime
from flask import Flask, render_template, request, abort, redirect, url_for, jsonify
from pathlib import Path
import yaml

import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)

BASE_DIR = Path(__file__).resolve().parent.parent


@app.route("/api/usage", methods=["POST"])
def record_usage():
    from .usage_logger import save_usage_log

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        save_usage_log(
            session_id=data["session_id"],
            event_id=data["event_id"],
            activity_type=data["activity_type"],
            visible_seconds=data["visible_seconds"],
            active_seconds=data["active_seconds"]
        )
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid usage data"}), 400

    return jsonify({"status": "ok"})

@app.route("/api/network/log", methods=["POST"])
def record_network():
    from .network_logger import save_network_log

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        save_network_log(data)

    except (KeyError, TypeError, ValueError, OverflowError):
        return jsonify({"error": "Invalid network data"}), 400

    return jsonify({"status": "ok"})

from vocab_editor.learner import get_learner_id, save_learner_id


@app.route("/learner/setup", methods=["GET", "POST"])
def learner_setup():
    error = None

    if request.method == "POST":
        learner_id = request.form.get("learner_id", "").strip()

        try:
            save_learner_id(learner_id)
            return redirect(url_for("home"))
        except ValueError as e:
            error = str(e)

    return render_template(
        "learner_setup.html",
        error=error,
        learner_id=get_learner_id()
    )


@app.before_request
def require_learner_id():
    if request.endpoint in ("learner_setup", "static"):
        return

    if get_learner_id() is None:
        return redirect(url_for("learner_setup"))



@app.route("/")
def home():
    return render_template("home.html")


@app.route("/registration", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        print("送信データ全体:", request.form.to_dict(flat=False))

        chapter = request.form.get("chapter")
        prefix = request.form.get("prefix")
        prefix_meaning = request.form.get("prefix_meaning")
        stack = request.form.get("stack")
        main_word = request.form.get("main_word")
        # Stackの語根情報（カンマ区切り）
        root_forms = [
            x.strip()
            for x in request.form.get("root_forms", "").split(",")
            if x.strip()
        ]

        root_meanings = [
            x.strip()
            for x in request.form.get("root_meanings", "").split(",")
            if x.strip()
        ]
        word = request.form.get("word")
        role = request.form.get("role")

        word_meanings = {}
        parts_of_speech = []

        for key in request.form:
            if key.startswith("part_of_speech_"):
                index = key.removeprefix("part_of_speech_")
                pos = request.form.get(key)

                meaning_list = request.form.getlist(f"meaning_{index}[]")
                meaning_list = [m.strip() for m in meaning_list if m.strip()]

                parts_of_speech.append(pos)

                if meaning_list:
                    word_meanings.setdefault(pos, []).extend(meaning_list)

        part_forms = request.form.getlist("part_form[]")
        part_meanings = request.form.getlist("part_meaning[]")
        derivative_words = request.form.getlist("derivative_word[]")
        derivative_meanings = request.form.getlist("derivative_meaning[]")




        print("Chapter:", chapter)
        print("接頭辞:", prefix)
        print("接頭辞の意味:", prefix_meaning)
        print("Stack:", stack)
        print("メイン単語:", main_word)
        print("英単語:", word)
        print("役割:", role)
        print("品詞一覧:", parts_of_speech)
        print("品詞ごとの意味:", word_meanings)
        print("語の構成:")
        for form, part_meaning in zip(part_forms, part_meanings):
            print("  構成要素:", form, "意味:", part_meaning)
        print("派生語:")
        for derivative_word, derivative_meaning in zip(derivative_words, derivative_meanings):
            print("  派生語:", derivative_word, "意味:", derivative_meaning)

        print("=== 複数単語の確認 ===")

        word_indices = sorted({
            key.split("]")[0][6:]
            for key in request.form
            if key.startswith("words[")
        }, key=int)


        words = []

        for index in word_indices:
            word = request.form.get(f"words[{index}][word]", "").strip()
            role = request.form.get(f"words[{index}][role]", "related")

            if not word:
                continue

            # 品詞と意味
            meanings = {}
            prefix_key = f"words[{index}][pos_"

            for key in request.form:
                if key.startswith(prefix_key):
                    pos_index = key[len(prefix_key):].split("]")[0]
                    pos = request.form.get(key)
                    meaning_list = request.form.getlist(
                        f"words[{index}][meaning_{pos_index}][]"
                    )
                    meaning_list = [m.strip() for m in meaning_list if m.strip()]
                    if meaning_list:
                        meanings.setdefault(pos, []).extend(meaning_list)

            # 語の構成
            part_forms = request.form.getlist(f"words[{index}][part_form][]")
            part_meanings = request.form.getlist(f"words[{index}][part_meaning][]")

            parts = [
                {"form": form.strip(), "meaning": meaning.strip()}
                for form, meaning in zip(part_forms, part_meanings)
                if form.strip()
            ]

            # 派生語
            derivative_words = request.form.getlist(
                f"words[{index}][derivative_word][]"
            )
            derivative_meanings = request.form.getlist(
                f"words[{index}][derivative_meaning][]"
            )

            derivatives = [
                {"word": dw.strip(), "meaning": dm.strip()}
                for dw, dm in zip(derivative_words, derivative_meanings)
                if dw.strip()
            ]

            word_data = {
                "word": word,
                "role": role,
                "meanings": meanings,
                "parts": parts,
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "verified": False,
            }

            if derivatives:
                word_data["derivatives"] = derivatives

            words.append(word_data)

        # Stack全体のデータ
        new_data = {
            "chapter": int(chapter),
            "prefix": prefix,
            "prefix_meaning": prefix_meaning,
            "stack": stack,
            "main_word": main_word,
            "words": words,
        }

        # 語根情報が入力された場合のみ保存
        if root_forms or root_meanings:
            new_data["root"] = {
                "forms": root_forms,
                "meanings": root_meanings,
            }

        print(yaml.safe_dump(
            new_data,
            allow_unicode=True,
            sort_keys=False
        ))


        # 保存先の名前を安全に作成
        if not re.fullmatch(r"[1-9]\d*", str(chapter)):
            return "Chapter番号が不正です", 400

        if not re.fullmatch(r"\d+-\d+", stack):
            return "Stack番号は 2-1 の形式で入力してください", 400

        if int(stack.split("-")[0]) != int(chapter):
            return "Chapter番号とStack番号が一致しません", 400

        if not re.fullmatch(r"[A-Za-z][A-Za-z'-]*", main_word):
            return "メイン単語は英字で入力してください", 400

        if not words:
            return "単語が登録されていません", 400

        prefix_slug = re.match(r"[A-Za-z]+", prefix.strip())
        if not prefix_slug:
            return "接頭辞を入力してください", 400

        folder = (
            BASE_DIR
            / "vocab_data"
            / f"chapter_{int(chapter):02d}_{prefix_slug.group().lower()}"
        )
        folder.mkdir(parents=True, exist_ok=True)

        stack_number = int(stack.split("-")[1])
        filename = f"{int(chapter)}-{stack_number:02d}_{main_word.lower()}.yaml"
        save_path = folder / filename

        # 既存ファイルを上書きしない
        try:
            with open(save_path, "x", encoding="utf-8") as file:
                yaml.safe_dump(
                    new_data,
                    file,
                    allow_unicode=True,
                    sort_keys=False
                )
        except FileExistsError:
            return f"同名ファイルが既に存在します: {save_path.name}", 409

        print("保存成功:", save_path)

        # 新規登録した単語を学習ログに記録
        from .registration_logger import save_registration_log

        for word_data in words:
            save_registration_log(
                action="register",
                chapter=chapter,
                stack=stack,
                word=word_data["word"]
            )








    if request.method == "POST":
        # 新しく登録したYAMLを表示
        with open(save_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

    elif request.args.get("file"):
        # 一覧から選択したYAMLを表示
        vocab_dir = (BASE_DIR / "vocab_data").resolve()
        selected = request.args.get("file", "")

        yaml_path = (vocab_dir / selected).resolve()

        # vocab_data外のファイルを読み込ませない
        if (
            not yaml_path.is_relative_to(vocab_dir)
            or yaml_path.suffix not in (".yaml", ".yml")
            or not yaml_path.is_file()
        ):
            abort(404)

        with open(yaml_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        if not isinstance(data, dict):
            abort(404)

    else:
        # 初回表示は空の教材
        data = {}



    # 保存済みStackの一覧を取得
    stack_list = []

    vocab_dir = BASE_DIR / "vocab_data"

    for yaml_file in sorted(vocab_dir.glob("chapter_*/*.yaml")):
        try:
            with open(yaml_file, "r", encoding="utf-8") as file:
                stack_data = yaml.safe_load(file)

            if not isinstance(stack_data, dict):
                continue

            if "chapter" not in stack_data or "stack" not in stack_data:
                continue

            words = stack_data.get("words", [])
            if not isinstance(words, list):
                words = []

            verified_count = sum(
                1 for word in words
                if isinstance(word, dict) and word.get("verified", False)
            )
            stack_list.append({
                "chapter": stack_data["chapter"],
                "stack": stack_data["stack"],
                "main_word": stack_data.get("main_word", ""),
                "path": str(yaml_file.relative_to(vocab_dir)),
                "word_count": len(words),
                "verified_count": verified_count
            })

        except (OSError, yaml.YAMLError) as error:
            print("YAML読み込みエラー:", yaml_file, error)

    # 教材構築の全体進捗を集計
    total_stacks = len(stack_list)

    total_words = sum(
        item["word_count"] for item in stack_list
    )

    total_verified = sum(
        item["verified_count"] for item in stack_list
    )

    verification_rate = (
        round(total_verified / total_words * 100, 1)
        if total_words > 0 else 0
    )

    return render_template(
        "index.html",
        vocab=data,
        stack_list=stack_list,
        total_stacks=total_stacks,
        total_words=total_words,
        total_verified=total_verified,
        verification_rate=verification_rate
    )



def safe_yaml_path(relative_path):
    base = (BASE_DIR / "vocab_data").resolve()
    path = (base / relative_path).resolve()
    if not path.is_relative_to(base) or path.suffix not in (".yaml", ".yml") or not path.is_file() or not path.parent.name.startswith("chapter_"):
        abort(404)
    return path

@app.route("/delete_stack", methods=["POST"])
def delete_stack():
    from .registration_logger import save_registration_log

    relative_path = request.form.get("file", "")
    path = safe_yaml_path(relative_path)

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or not isinstance(data.get("words"), list):
        abort(400)

    path.unlink()

    for word_data in data["words"]:
        if word_data.get("word"):
            save_registration_log(
                action="delete",
                chapter=data["chapter"],
                stack=data["stack"],
                word=word_data["word"]
            )

    return redirect(url_for("index"))
@app.route("/edit", methods=["GET", "POST"])
def edit_stack():
    relative_path = request.values.get("file", "")
    path = safe_yaml_path(relative_path)
    with path.open(encoding="utf-8") as f:
        original = yaml.safe_load(f)
    if not isinstance(original, dict) or not isinstance(original.get("words"), list):
        abort(400)

    if request.method == "POST":
        # ファイルの識別情報は元データを保持。フォーム値では変更しない。
        updated = dict(original)
        updated["prefix_meaning"] = request.form.get("prefix_meaning", "").strip()
        updated["prefix"] = request.form.get("prefix", "").strip()
        if not updated["prefix"]:
            return "接頭辞を入力してください", 400

        # Stackの語根情報
        root_forms = [
            x.strip()
            for x in request.form.get("root_forms", "").split(",")
            if x.strip()
        ]

        root_meanings = [
            x.strip()
            for x in request.form.get("root_meanings", "").split(",")
            if x.strip()
        ]

        # 入力欄が送信された場合のみ更新する
        if "root_forms" in request.form and "root_meanings" in request.form:
            if root_forms or root_meanings:
                updated["root"] = {
                    "forms": root_forms,
                    "meanings": root_meanings
                }
            else:
                updated.pop("root", None)
        indices = sorted({int(m.group(1)) for key in request.form if (m := re.fullmatch(r"words\[(\d+)\]\[word\]", key))})
        words = []
        for i in indices:
            word = request.form.get(f"words[{i}][word]", "").strip()
            if not word:
                continue
            role = request.form.get(f"words[{i}][role]", "related")
            if role not in ("main", "related"):
                return "単語の役割が不正です", 400
            meanings = {}
            for key in request.form:
                match = re.fullmatch(r"words\[" + str(i) + r"\]\[pos_(\d+)\]", key)
                if match:
                    pos_id = match.group(1)
                    pos = request.form.get(key, "").strip()
                    vals = [v.strip() for v in request.form.getlist(f"words[{i}][meaning_{pos_id}][]") if v.strip()]
                    if pos and vals:
                        meanings.setdefault(pos, []).extend(vals)
            forms = request.form.getlist(f"words[{i}][part_form][]")
            part_meanings = request.form.getlist(f"words[{i}][part_meaning][]")
            parts = [{"form": a.strip(), "meaning": b.strip()} for a, b in zip(forms, part_meanings) if a.strip()]
            dwords = request.form.getlist(f"words[{i}][derivative_word][]")
            dmeanings = request.form.getlist(f"words[{i}][derivative_meaning][]")
            derivatives = [{"word": a.strip(), "meaning": b.strip()} for a, b in zip(dwords, dmeanings) if a.strip()]
            # 元の単語から確認状態を引き継ぐ
            original_word = next(
                (w for w in original["words"]
                 if isinstance(w, dict) and w.get("word") == word),
                None
            )

            verified = (
                original_word.get("verified", False)
                if original_word else False
            )

            verified_at = (
                original_word.get("verified_at")
                if original_word else None
            )
            created_at = (
                original_word.get("created_at")
                if original_word
                else datetime.now().astimezone().isoformat(timespec="seconds")
            )

            entry = {
                "word": word,
                "role": role,
                "meanings": meanings,
                "parts": parts,
                "verified": verified,
                "verified_at": verified_at
            }
            if created_at is not None:
                entry["created_at"] = created_at
            if derivatives:
                entry["derivatives"] = derivatives
            words.append(entry)
        if not words:
            return "単語が登録されていません", 400
        if not any(w["word"] == original.get("main_word") and w["role"] == "main" for w in words):
            return "メイン単語は削除・変更できません", 400
        for item in words:
            old = next(
                (w for w in original["words"]
                 if w.get("word") == item["word"]),
                None
            )
            if old and any(
                old.get(k) != item.get(k)
                for k in ("role", "meanings", "parts", "derivatives")
            ):
                item["verified"] = False
                item["verified_at"] = None
        updated["words"] = words
        # 初回編集時の原本バックアップ（プロジェクト外のバックアップフォルダ）
        backup = BASE_DIR / "vocab_backups" / path.parent.name / path.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            import shutil
            shutil.copy2(path, backup)
        # 一時ファイルを同じディレクトリに保存してから置き換え
        import os, tempfile
        fd, tmp = tempfile.mkstemp(prefix=".edit_", suffix=".yaml", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.safe_dump(updated, f, allow_unicode=True, sort_keys=False)
            os.replace(tmp, path)

        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

        # 実際に変更された単語だけを編集ログに記録
        from .registration_logger import save_registration_log

        original_words = {
            w["word"]: w
            for w in original.get("words", [])
            if isinstance(w, dict) and w.get("word")
        }

        for word_data in words:
            word_name = word_data["word"]
            old_word = original_words.get(word_name)

            if old_word is None:
                action = "register"
            elif any(
                old_word.get(k) != word_data.get(k)
                for k in ("role", "meanings", "parts", "derivatives")
            ):
                action = "edit"
            else:
                continue

            save_registration_log(
                action=action,
                chapter=updated["chapter"],
                stack=updated["stack"],
                word=word_name
            )

        current_words = {w["word"] for w in words}

        for word_name in original_words:
            if word_name not in current_words:
                save_registration_log(
                    action="delete",
                    chapter=updated["chapter"],
                    stack=updated["stack"],
                    word=word_name
                )

        return redirect(url_for("index", file=relative_path))


    # 既存の一覧画面を利用し、編集対象のYAMLをJSに渡す
    vocab_dir = BASE_DIR / "vocab_data"
    stack_list = []
    for yaml_file in sorted(vocab_dir.glob("chapter_*/*.yaml")):
        try:
            with yaml_file.open(encoding="utf-8") as f:
                d = yaml.safe_load(f)
            if isinstance(d, dict) and "chapter" in d and "stack" in d:
                words = d.get("words", [])
                if not isinstance(words, list):
                    words = []

                verified_count = sum(
                    1 for word in words
                    if isinstance(word, dict) and word.get("verified", False)
                )

                stack_list.append({
                    "chapter": d["chapter"],
                    "stack": d["stack"],
                    "main_word": d.get("main_word", ""),
                    "path": str(yaml_file.relative_to(vocab_dir)),
                    "word_count": len(words),
                    "verified_count": verified_count
                })
        except (OSError, yaml.YAMLError):
            continue
     # 教材構築の全体進捗を集計
    total_stacks = len(stack_list)
    total_words = sum(item["word_count"] for item in stack_list)
    total_verified = sum(item["verified_count"] for item in stack_list)

    verification_rate = (
        round(total_verified / total_words * 100, 1)
        if total_words > 0 else 0
    )

    return render_template(
        "index.html",
        vocab=original,
        stack_list=stack_list,
        edit_data=original,
        edit_file=relative_path,
        total_stacks=total_stacks,
        total_words=total_words,
        total_verified=total_verified,
        verification_rate=verification_rate
    )
from vocab_network.network_core import build_network


@app.route("/network")
def network():
    network_data = build_network(BASE_DIR / "vocab_data")
    return render_template("network.html", network=network_data)

@app.route("/verify", methods=["POST"])
def verify_stack():
    import os
    import tempfile
    from datetime import datetime

    relative_path = request.form.get("file", "")
    path = safe_yaml_path(relative_path)

    if path is None or not path.is_file():
        abort(400)

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        abort(400)

    words = data.get("words", [])

    if not isinstance(words, list):
        abort(400)


    now = datetime.now().astimezone().isoformat(timespec="seconds")

    # 今回新しく確認された単語だけを記録
    newly_verified_words = []

    for word in words:
        if isinstance(word, dict) and not word.get("verified", False):
            word["verified"] = True
            word["verified_at"] = now

            if word.get("word"):
                newly_verified_words.append(word["word"])


    fd, tmp = tempfile.mkstemp(
        prefix=".verify_",
        suffix=".yaml",
        dir=path.parent
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                data,
                f,
                allow_unicode=True,
                sort_keys=False
            )

        os.replace(tmp, path)

    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)



    # 今回初めて確認された単語だけをログに記録
    from .registration_logger import save_registration_log

    for word_name in newly_verified_words:
        save_registration_log(
            action="verify",
            chapter=data["chapter"],
            stack=data["stack"],
            word=word_name
        )

    
    return redirect(url_for("index", file=relative_path))

@app.route("/quiz")
def quiz_menu():
    return render_template("quiz_menu.html")

@app.route("/learning")
def learning():
    from vocab_editor.learning_stats import (
        get_registration_stats,
        get_usage_stats,
        get_quiz_stats,
        get_vocabulary_stats,
        get_network_stats,
    )
    from vocab_editor.quiz_core import load_incorrect_words

    learner_id = get_learner_id()

    period = request.args.get("period", "7")

    if period not in ("7", "30", "all"):
        period = "7"

    days = None if period == "all" else int(period)

    return render_template(
        "learning.html",
        registration=get_registration_stats(learner_id, days),
        usage=get_usage_stats(learner_id, days),
        network=get_network_stats(learner_id, days),
        quiz=get_quiz_stats(learner_id, days),
        vocabulary=get_vocabulary_stats(),
        incorrect_count=len(load_incorrect_words(learner_id)),
        period=period,
    )
@app.route("/incorrect")
def incorrect():
    from vocab_editor.quiz_core import load_incorrect_words

    learner_id = get_learner_id()
    words = load_incorrect_words(learner_id)

    grouped = {}

    for word in words:
        chapter = word["chapter"]
        stack = word["stack"]

        grouped.setdefault(chapter, {})
        grouped[chapter].setdefault(stack, [])
        grouped[chapter][stack].append(word)

    return render_template(
        "incorrect.html",
        words=words,
        grouped=grouped
    )

@app.route("/quiz/today")
def quiz_today():
    from flask import session
    from vocab_editor.quiz_core import create_quiz_questions
    from vocab_editor.quiz_session import save_quiz_session

    learner_id = get_learner_id()
    questions = create_quiz_questions(learner_id)

    quiz_id = save_quiz_session(
        learner_id,
        quiz_type="daily",
        questions=questions,
        quiz_scope="daily"
    )

    session["daily_quiz_id"] = quiz_id

    return render_template(
        "quiz_today.html",
        questions=questions
    )



@app.route("/quiz/log", methods=["POST"])
def quiz_log():
    from flask import session, request, jsonify
    from vocab_editor.quiz_logger import save_quiz_log
    from vocab_editor.quiz_session import (
        get_quiz_session,
        mark_answered,
        unmark_answered
    )
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "不正なデータです"}), 400

    question_index = data.get("question_index")
    selected_answer = data.get("selected_answer")
    response_time = data.get("response_time")

    if type(question_index) is not int:
        return jsonify({"error": "問題番号が不正です"}), 400

    if not isinstance(selected_answer, str):
        return jsonify({"error": "回答データが不正です"}), 400

    try:
        response_time = float(response_time)
    except (TypeError, ValueError):
        return jsonify({"error": "回答時間が不正です"}), 400

    quiz_type = data.get("quiz_type", "daily")

    if quiz_type not in ("daily", "free"):
        return jsonify({"error": "テスト形式が不正です"}), 400

    session_key = (
        "daily_quiz_id" if quiz_type == "daily"
        else "free_quiz_id"
    )

    quiz_id = session.get(session_key)
    if not quiz_id:
        return jsonify({"error": "テスト情報がありません"}), 400

    saved_quiz = get_quiz_session(
        quiz_id,
        get_learner_id()
    )

    if saved_quiz is None:
        return jsonify({"error": "テストが見つかりません"}), 400
    if saved_quiz["quiz_type"] != quiz_type:
        return jsonify({"error": "テスト形式が一致しません"}), 400

    questions = saved_quiz["questions"]

    if not (0 <= question_index < len(questions)):
        return jsonify({"error": "問題番号が範囲外です"}), 400

    question = questions[question_index]

    if selected_answer not in question["choices"]:
        return jsonify({"error": "選択肢が不正です"}), 400

    correct_answer = question["correct"]
    is_correct = selected_answer == correct_answer

    # 同じテストの同じ問題を二重記録しない
    if not mark_answered(quiz_id, question_index):
        return jsonify({
            "error": "この問題はすでに回答済みです"
        }), 409
    try:
        save_quiz_log(
            word=question["word"],
            quiz_type=quiz_type,
            quiz_id=quiz_id,
            quiz_scope=saved_quiz["quiz_scope"],
            chapter=question["chapter"],
            stack=question["stack"],
            selected_answer=selected_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            response_time=response_time,
        )
    except Exception:
        unmark_answered(quiz_id, question_index)
        app.logger.exception("回答ログの保存に失敗しました")
        return jsonify({
            "error": "回答ログを保存できませんでした"
        }), 500

    return jsonify({
        "success": True,
        "is_correct": is_correct,
        "correct_answer": correct_answer
    })

@app.route("/quiz/free/settings")
def quiz_free_settings():
    from vocab_editor.quiz_core import load_verified_words

    words = load_verified_words()

    chapters = sorted(
        {str(w["chapter"]) for w in words},
        key=lambda x: int(x) if x.isdigit() else x
    )

    stacks = sorted({
        str(w["stack"]) for w in words
    })

    return render_template(
        "quiz_free_settings.html",
        chapters=chapters,
        stacks=stacks,
    )

@app.route("/quiz/free", methods=["POST"])
def quiz_free():
    from flask import request, session
    from vocab_editor.quiz_core import (
        create_free_quiz_questions,
        select_recommended_words,
        select_wrong_answers,
        load_verified_words,
    )
    from vocab_editor.quiz_session import save_quiz_session

    learner_id = get_learner_id()

    count_value = request.form.get("question_count", "10")

    if count_value == "all":
        question_count = None
    elif count_value in ("5", "10", "20"):
        question_count = int(count_value)
    else:
        return "問題数が不正です", 400

    mode = request.form.get("mode", "recommended")

    if mode == "recommended":
        import random

        selected_words = select_recommended_words(
            learner_id, question_count
        )
        all_words = load_verified_words()
        questions = []

        for word_data in selected_words:
            correct = random.choice(word_data["answers"])
            wrong_answers = select_wrong_answers(
                word_data, all_words
            )

            if len(wrong_answers) < 3:
                return "4択の選択肢が不足しています", 400

            choices = [correct] + wrong_answers
            random.shuffle(choices)

            questions.append({
                "word": word_data["word"],
                "choices": choices,
                "correct": correct,
                "chapter": word_data["chapter"],
                "stack": word_data["stack"],
            })

    elif mode == "selected":
        scope = request.form.get("scope", "all")
        chapter = request.form.get("chapter")
        stack = request.form.get("stack")

        if scope not in ("all", "chapter", "stack", "incorrect"):
            return "未対応の出題範囲です", 400

        questions = create_free_quiz_questions(
            question_count=question_count,
            scope=scope,
            chapter=chapter,
            stack=stack,
            learner_id=learner_id,
        )

    else:
        return "未対応の出題モードです", 400

    if mode == "recommended":
        quiz_scope = "recommended"
    elif scope == "chapter":
        quiz_scope = f"chapter:{chapter}"
    elif scope == "stack":
        quiz_scope = f"stack:{chapter}:{stack}"
    else:
        quiz_scope = scope

    quiz_id = save_quiz_session(
        learner_id=learner_id,
        quiz_type="free",
        questions=questions,
        quiz_scope=quiz_scope,
    )

    session["free_quiz_id"] = quiz_id

    return render_template(
        "quiz_free.html",
        questions=questions,
    )


if __name__ == "__main__":
    app.run(debug=True)