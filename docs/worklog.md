# Work Log

---

## 2026-07-11

### 今日やったこと

- CLAUDE.md を新規作成。プロジェクト概要、環境構築・主要コマンド、開発フロー、アーキテクチャ、作業規約（`docs/instruction.md`・`docs/開発の仕方.md` の内容を反映）をまとめた
- CLAUDE.md に Work Log のルール（作業が一区切りついたら `docs/worklog.md` を更新するルール）を追加

### 決定事項

- CLAUDE.md の内容は `docs/instruction.md` と `docs/開発の仕方.md` の既存ルールを踏襲し、重複・矛盾する新規ルールは作らない方針とする
- 作業ログは `docs/worklog.md` に日付ごとに追記し、既存内容は削除しない運用とする

### 発生した問題

- `.gitignore` に `databricks.yml` / `pyproject.toml` / `uv.lock` / `.python-version` / `.vscode` が記載されているが、実際には git 管理下（追跡中）にあり矛盾していることが判明。過去の追跡解除コミット（`62269c1`）が後続コミットで実質的に取り消されていた

### 解決方法

- 上記の矛盾は CLAUDE.md に「Gotcha」として明記し、コミット前に `git status` を確認するよう注意喚起する形で対応。`.gitignore` 自体の修正は未実施

### TODO

- `.gitignore` と実際の追跡状態の矛盾を解消する（意図的に追跡するか、正式に除外するか方針を決める）
- `notebooks/detasets.ipynb` のデータセット作成処理（商品マスタ・売上・在庫データ）を実装する
- `src/` / `tests/` / `jobs/` の中身を実装する

---
