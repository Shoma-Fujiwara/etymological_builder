# 英単語学習支援システム

## 1. システム概要

英単語の意味や語源、派生語などを自分で登録し、教材を構築しながら学習するシステムです。

### 主な機能

- 教材登録・編集・確認
- 今日のテスト
- 自由テスト
- 誤答集
- 語源ネットワーク
- 学習記録

## 2. 動作環境

- WSL（Ubuntu）
- fish
- Python 3.10以上
- Webブラウザ
- インターネット接続

## 3. 初回の環境構築

システムのディレクトリに移動する。

```bash
cd ~/etymological_builder_public
```

Pythonの仮想環境を作成する。

```bash
python3 -m venv .venv
```

仮想環境を有効化する。

```bash
source .venv/bin/activate.fish
```

必要なライブラリをインストールする。

```bash
pip install -r requirements.txt
```

## 4. システムの起動

```bash
python3 -m flask --app vocab_editor.app run
```

Webブラウザで以下のURLを開く。

http://localhost:5000/

初回起動時は、指定された学習者IDを入力する。

## 5. 2回目以降の起動

```bash
cd ~/etymological_builder_public
source .venv/bin/activate.fish
python3 -m flask --app vocab_editor.app run
```

初回の環境構築を再度行う必要はありません。

## 6. システムの終了

起動中のターミナルで Ctrl+C を押す。

仮想環境を終了する。

```bash
deactivate
```

登録した教材や学習記録は保存されるため、次回起動時も引き続き利用できます。

## 7. データの保存先

| ディレクトリ・ファイル | 内容 |
|---|---|
| vocab_data/ | 登録した教材データ |
| learning_logs/ | 学習記録 |
| learner_config.json | 学習者ID |
| vocab_editor/ | 学習システム |
| vocab_network/ | 語源ネットワーク生成プログラム |
| docs/ | 学習ガイド |

## 8. 注意事項

- 指定された学習者IDを使用してください。
- 教材データや学習ログを直接変更・削除しないでください。
- 学習期間中は同じ環境でシステムを使用してください。
- エラーが発生した場合は、画面やターミナルの内容を報告してください。

## 9. システムの使い方

具体的な学習手順については、[学習ガイド](docs/learning_guide.md)を参照してください。