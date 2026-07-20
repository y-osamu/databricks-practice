# Work Log

---

## 2026-07-11

### 今日やったこと

- CLAUDE.md を新規作成。プロジェクト概要、環境構築・主要コマンド、開発フロー、アーキテクチャ、作業規約（`docs/instruction.md`・`docs/開発の仕方.md` の内容を反映）をまとめた
- CLAUDE.md に Work Log のルール（作業が一区切りついたら `docs/worklog.md` を更新するルール）を追加
- `notebooks/bronze/bronze.ipynb` にメダリオンアーキテクチャの Bronze layer 取り込み処理を実装
    - `workspace.practice.{products,sales,inventory}` を読み込み、`_ingested_at` / `_source_table` のメタデータ列のみ付与して `workspace.bronze` スキーマへ書き込む共通関数 `ingest_to_bronze` を作成
    - 取り込み後に件数・内容を確認するセルを追加

### 決定事項

- CLAUDE.md の内容は `docs/instruction.md` と `docs/開発の仕方.md` の既存ルールを踏襲し、重複・矛盾する新規ルールは作らない方針とする
- 作業ログは `docs/worklog.md` に日付ごとに追記し、既存内容は削除しない運用とする
- Bronze layer ではカラムの加工・型変換・フィルタは行わず、メタデータ列の付与のみにとどめる
- ソース（`workspace.practice`）は毎回フルスナップショットで再生成される想定のため、Bronze への書き込みは `overwrite` を採用（再実行しても結果が変わらない冪等な方式）

### 発生した問題

- `.gitignore` に `databricks.yml` / `pyproject.toml` / `uv.lock` / `.python-version` / `.vscode` が記載されているが、実際には git 管理下（追跡中）にあり矛盾していることが判明。過去の追跡解除コミット（`62269c1`）が後続コミットで実質的に取り消されていた

### 解決方法

- 上記の矛盾は CLAUDE.md に「Gotcha」として明記し、コミット前に `git status` を確認するよう注意喚起する形で対応。`.gitignore` 自体の修正は未実施

### TODO

- `.gitignore` と実際の追跡状態の矛盾を解消する（意図的に追跡するか、正式に除外するか方針を決める）
- `notebooks/detasets.ipynb` のデータセット作成処理（商品マスタ・売上・在庫データ）を実装する
- `src/` / `tests/` / `jobs/` の中身を実装する
- `notebooks/bronze/bronze.ipynb` を Databricks 上で実行し、`workspace.bronze.{products,sales,inventory}` の取り込み結果を確認する（バグ修正後の再実行が必要）
- Silver layer を Databricks 上で実行し、`workspace.silver.{products,sales,inventory}` の件数・スキーマ・除去件数ログを確認する

---

## 2026-07-11 (2)

### 今日やったこと

- `notebooks/bronze/bronze.ipynb` のバグを修正
    - `SOURCE_FILE_PATHS`（`iventory.csv, products.csv, sales.csv` の順）と `BRONZE_TABLES`（`products, sales, inventory` の順）がインデックスで対応しておらず、`_10_bronze_products` に在庫データ、`_10_bronze_sales` に商品マスタ、`_10_bronze_inventory` に売上データが誤って書き込まれる状態だった
    - `SOURCE_FILE_PATHS` の並び順を `BRONZE_TABLES` に合わせて修正（`products.csv, sales.csv, iventory.csv` の順）
- `notebooks/silver/silver.ipynb` を実装（それまではBronzeのコードがコピーされたプレースホルダーだった）
    - `workspace.bronze._10_bronze_{products,sales,inventory}` を読み込み、テーブルごとに `clean_products` / `clean_sales` / `clean_inventory` 関数で型変換・null/不正値の除去・重複排除を行い、`workspace.silver._20_silver_{table}` へ書き込む共通関数 `ingest_to_silver` を作成
    - 除去件数（Bronze件数 → Silver件数）をログ出力
    - 書き込み後にスキーマ・件数を確認するセルを追加

### 決定事項

- テーブル間の結合（sales × products × inventory など）はSilver層では行わず、Gold層の責務とする
- Silverの書き込みもBronzeと同様に `overwrite`（フルスナップショット想定の冪等書き込み）を踏襲
- Silverテーブルは `_20_silver_{table}` の接頭辞とし、Bronzeの `_10_bronze_{table}` と揃えた命名規則にする
- メタデータ列は Bronze の `_ingested_at`（リネージュ）を保持し、`_silver_processed_at` を新規付与、`_source_table` はSilverでは不要なため drop する

### 発生した問題

- Bronze層で `SOURCE_FILE_PATHS` と `BRONZE_TABLES` の順序が対応しておらず、テーブル名と中身が入れ替わって書き込まれるバグがあった（上記の通り修正済み）

### 解決方法

- `SOURCE_FILE_PATHS` の並び順を `BRONZE_TABLES` に合わせて修正することで対応

### TODO

- `notebooks/bronze/bronze.ipynb` を Databricks 上で再実行し、修正後の `workspace.bronze.{products,sales,inventory}` の中身が正しいことを確認する
- `notebooks/silver/silver.ipynb` を Databricks 上で実行し、`workspace.silver.{products,sales,inventory}` の件数・スキーマ・除去件数ログを確認する
- Gold layer（sales × products × inventory の結合・集計）の実装

---

## 2026-07-12

### 今日やったこと

- `notebooks/silver/silver_demo.ipynb` と `notebooks/practice/silver_practice.ipynb` の `clean_sales` 内のバグ（`df_typedvfkffffffffavfaokoakokivfiavfa.withColumn(...)` という壊れたコード）を修正し、`df_typed = df.withColumn(...)` から始まる正しいメソッドチェーンに直した
- `notebooks/gold/gold_practice.ipynb` を実装（これまではBronzeのコードがそのままコピーされたプレースホルダーだった）
    - `workspace.silver._20_silver_{sales,products,inventory}` を結合・集計し、`workspace.gold._30_gold_{daily_sales_summary,inventory_status,product_ranking}` の3テーブルを作成する処理を実装
    - 日次売上サマリ: sales×productsを結合し、sale_date×store×product/category単位でquantity/sales_amountを集計
    - 在庫ステータス: inventory×productsを結合し、在庫評価額（stock_quantity×unit_price）と欠品/低在庫フラグを算出
    - 商品別販売実績ランキング: salesをproduct_id単位で集計し、productsと結合してdense_rankで売上高降順のランキングを付与
    - 各テーブルにGold処理時刻 `_gold_processed_at` を新規付与
    - 書き込み後にスキーマ・件数を確認するセルを追加

### 決定事項

- Gold層の3テーブルは `_30_gold_` の接頭辞とし、Bronze(`_10_`)/Silver(`_20_`)の連番規則を継承する
- Gold結合時、Silverの `_ingested_at` / `_silver_processed_at` はリネージュとして引き継がず、結合前にdropしてカラム名の衝突（ambiguous reference）を回避し、Gold固有の `_gold_processed_at` のみを付与する
- 低在庫しきい値は暫定的に10個未満と定義（在庫データがstore×product当たり0〜100のランダム値であるため）。実運用では要調整の想定
- `notebooks/gold/gold_demo.ipynb` は今回新規作成しない（既存の `gold_practice.ipynb` のみが存在し、bronze/silverのようなdemo/practiceの対になる既存ファイルがまだ無いため。将来demo版が必要になれば `gold_practice.ipynb` をコピーして作成する）

### 発生した問題

- Silverの `clean_sales` に壊れた変数名（`df_typedvfkffffffffavfaokoakokivfiavfa`）を含むコードがあり、そのままでは NameError/SyntaxError で失敗する状態だった（Gold実装がSilverのsalesに依存するため、先に修正が必要だった）

### 解決方法

- 該当セルの `df_typedvfkffffffffavfaokoakokivfiavfa.withColumn(...)` を `df_typed = df.withColumn(...)` から始まるメソッドチェーンに修正（silver_demo.ipynb / silver_practice.ipynb 両方）

### TODO

- Databricks上で修正後の `silver_practice.ipynb` を再実行し、`workspace.silver._20_silver_sales` が正しく作成されることを確認する
- Databricks上で `gold_practice.ipynb` を実行し、`workspace.gold._30_gold_{daily_sales_summary,inventory_status,product_ranking}` の件数・スキーマ・サンプル行を確認する
- 低在庫しきい値（`LOW_STOCK_THRESHOLD`）を実際のデータ・要件に合わせて見直す

---

## 2026-07-12 (2)

### 今日やったこと

- `notebooks/model/build_model.ipynb` に日次売上数量予測モデル（回帰）を実装
    - `workspace.silver._20_silver_{sales,products,inventory}` から直接特徴量を作成（Goldの結合済みテーブルは使わず自己完結）
    - カレンダー×店舗×商品マスタの全組み合わせに実績売上を左結合し欠損を0埋めするdenseパネルを構築（売上ゼロの日を正当な観測として扱う）
    - 商品属性（category, unit_price）・在庫スナップショット（stock_quantity）・カレンダー特徴（day_of_week, is_weekend）を特徴量として結合、カテゴリ変数は整数コード化
    - 直近7日をテストとする時系列分割で `RandomForestRegressor` を学習し、RMSE/MAE/R2を評価
    - MLflow（`mlflow.sklearn.autolog` + 明示的な `log_metric`/`log_model`）でrunを記録
    - Unity Catalog Model Registry（`workspace.model.daily_sales_quantity_predictor`）にモデルを登録し、`champion` エイリアスを付与
    - `mlflow.pyfunc.load_model` で登録済みモデルを読み込み直し、サンプル予測のラウンドトリップを確認するセルを追加
- `pyproject.toml` に `mlflow` / `scikit-learn` を追加（`uv add mlflow scikit-learn`）

### 決定事項

- モデルはGoldの結合済みテーブルを使わず、Silverの3テーブルから直接特徴量エンジニアリングを行い、notebookを自己完結させる方針とした
- 売上のない(店舗,商品,日)もdenseパネルにより数量0の観測として扱うことにした（ゼロインフレーションのリスクはpractice用途として許容）
- `sales_amount` は `quantity × unit_price` に由来しリーケージとなるため特徴量から除外し、参考列としてのみ保持
- `toPandas()` によるdriver集約は全体で最大1,920行に収まるため許容し、notebook内にmarkdown/コメントで明示
- UC Model Registryのスキーマは `workspace.model`、モデル名は `daily_sales_quantity_predictor` とし、テーブル層の `_NN_` 連番プレフィックスはModel Registryには適用しないことを明記した

### 発生した問題

- 特になし（Silver層は前回のバグ修正により正常に動作する前提で実装）

### 解決方法

- （該当なし）

### TODO

- バッチ推論（スコアリング）notebookの追加検討
- ゼロインフレーション対応（2段階モデル / Tweedie損失など）の検討
- モデルエイリアス運用ルール（champion/challenger）の整備
- Databricks上で `build_model.ipynb` を実行し、denseパネルの行数（1,920件想定）・RMSE/MAE/R2・MLflow runの記録・UC Model Registryへの登録・ラウンドトリップ検証を確認する

---

## 2026-07-12 (3)

### 今日やったこと

- `notebooks/model/build_model.ipynb` のモデルを `RandomForestRegressor` から `LightGBM`（`objective="tweedie"`）に変更
    - 二乗誤差（MSE）は誤差が対称・等分散であることを仮定するが、日次売上数量はゼロインフレーション・平均依存の分散を持つカウントデータであるため、Tweedie目的関数の方が実態に即しているという理由をmarkdownに明記
    - カテゴリ変数（store_id_code, product_id_code, category_code）は `categorical_feature` パラメータでLightGBMに明示
    - MLflowトラッキングは `mlflow.sklearn` から `mlflow.lightgbm`（`autolog` / `log_model`）に切り替え
- `notebooks/model/build_model.ipynb` の `import pyspark.sql.functions as F` を廃止し、`from pyspark.sql.functions import *` に統一（`F.` プレフィックスを使わない書き方に変更）
- `notebooks/inference/batch_inference.ipynb` を新規作成
    - UC Model Registryに登録済みのモデル（デフォルト `workspace.model.daily_sales_quantity_predictor` の `champion` エイリアス）を読み込み、指定日の店舗×商品ごとの需要を推論するテンプレートnotebook
    - `dbutils.widgets` でモデル名・エイリアス・推論対象日をパラメータ化し、使い回せるようにした
    - 特徴量は学習時と同じ列構成を `workspace.silver._20_silver_{products,inventory}` から再構築（推論は1日分なのでdenseパネル化は不要、店舗×商品マスタにカレンダー特徴を付与するのみ）
- `pyproject.toml` に `lightgbm` を追加（`uv add lightgbm`）

### 決定事項

- モデルアルゴリズムはLightGBM（Tweedie目的関数）を採用し、ゼロインフレーションなカウントデータに理論的に適した損失関数を使う方針とした
- pysparkの関数importは `as F` エイリアスを使わず `from pyspark.sql.functions import *` に統一する（今後のnotebookでもこのルールを踏襲する）
- 推論notebookはバッチ推論用の出力テーブル書き込みまでは行わず、`display()` による結果確認までをスコープとする（シンプルなテンプレートとして提供）
- 推論時のカテゴリエンコーディングは学習時と同じ全量マスタ（4店舗・16商品・5カテゴリ）から都度導出する方式とし、エンコーダの永続化は行わない（対象ドメインが変わらないpractice用途としての簡略化）

### 発生した問題

- `notebooks/model/build_model.ipynb` に一度追加した「結果サマリ」のmarkdownセルが、何らかの理由でファイルに保存されていなかった（再度セルを追加する際に発覚）

### 解決方法

- 該当のmarkdownセルを末尾に再追加し、ファイルに保存されていることを`grep`で確認した

### TODO

- Databricks上で `build_model.ipynb`（LightGBM版）を実行し、RMSE/MAE/R2・MLflow runの記録・UC Model Registryへの新バージョン登録を確認する
- Databricks上で `notebooks/inference/batch_inference.ipynb` を実行し、widgetパラメータの動作・推論結果を確認する
- 推論notebookの出力をテーブルに書き込む機能（バッチスコアリングの永続化）の追加を検討する
- カテゴリエンコーディングのエンコーダ永続化（学習時のマッピングを再利用する仕組み）を検討する

---

## 2026-07-13

### 今日やったこと

- `datasets/detasets_demo.ipynb` を、`docs/開発方針.md` の不正検知アセスメント要件（ファクト表1000万行・ディメンション5,000〜2万口座）に沿って作り直した
    - ディメンション表 `workspace.datasets.account`（10,000口座）を新規実装。`account_id`（`ACC00001`形式）・`open_date`・`region`・`account_type`・`risk_category` を持つ。Python `random` でリスト生成 → `spark.createDataFrame` → `saveAsTable`
    - ファクト表 `workspace.datasets.transaction`（1000万行）を、従来の `sender`/`accepter`（人名文字列・100行のみ）から全面的に作り直し。`account_id` / `counter_account_id`（振替時のみ） / `transaction_type`（入金・出金・振替の3種） / `channel` / `amount` / `transaction_timestamp` の構成に変更
    - 1000万行はPythonのリスト内包ではなく `spark.range(NUM_TRANSACTIONS)` + 列演算（`rand()`/`floor()`/`element_at()` など）によるSpark-native生成とし、`account_id` はaccount表と算術的に対応する採番（`ACC` + 0埋め5桁）にすることでjoinを不要にした
    - 両テーブルとも `CREATE SCHEMA IF NOT EXISTS workspace.datasets` → `saveAsTable(mode="overwrite", overwriteSchema=true)` という既存notebook（bronze/silver）と同じ書き込みパターンを踏襲
    - 確認セルで `count()` とtransaction_typeごとの `groupBy().count()` を追加

### 決定事項

- ユーザー確認の結果、`transaction_type` は要件文言「入出金・振替」をそのまま2値にせず、入金・出金・振替の3値に分解する方針とした（不正検知では入出金の方向が重要な特徴量になるため）
- 口座数は5,000〜20,000の範囲の中央値である10,000件を採用
- 既存の `transaction` テーブル作成セル（100行・sender/accepter方式）は新スキーマに合わせて作り直す方針とし、後方互換は維持しない
- `pyspark.sql.functions` のimportは、2026-07-12時点の決定事項（`from pyspark.sql.functions import *` に統一し `as F` エイリアスは使わない）に合わせて実装した

### 発生した問題

- 特になし

### 解決方法

- （該当なし）

### TODO

- Databricks上で `datasets/detasets_demo.ipynb` を実行し、`workspace.datasets.account` が10,000件、`workspace.datasets.transaction` が1000万件作成されることを確認する
- `docs/開発方針.md` に記載の可視化（地域別・口座別の取引状況サマリ）の実装を検討する

---

## 2026-07-13 (2)

### 今日やったこと

- `notebooks/visualize/visualize_demo.ipynb`（これまでプレースホルダーのスタブのみ）に、地域×チャネル・地域×時間帯のクロス集計ヒートマップを実装
    - `workspace.datasets.account`（region等）と `workspace.datasets.transaction`（1000万行）を `account_id` でjoinし、地域×チャネル、地域×時間帯（`transaction_timestamp` から `hour()` で導出した6時間区切り4バンド）の件数をSpark側で `groupBy().count()` 集計
    - 集計結果（最大8×4=32行）のみを `toPandas()` し、`REGION_ORDER`/`CHANNEL_ORDER`/`TIME_BAND_ORDER` で表示順を固定した上でpivot
    - 共通ヘルパー関数 `plot_crosstab_heatmap` を定義し、matplotlib `imshow` ベースのヒートマップ（件数を各セルに注記、単色系`Blues`カラーマップ、カラーバー付き）を1×2ダッシュボード図として表示
    - 既存の `notebooks/practice/visualize_practice.ipynb` の house style（`japanize-matplotlib`、`warnings.filterwarnings('ignore')`、`plt.subplots` + `fig.suptitle` によるダッシュボード形式）を踏襲

### 決定事項

- ファクト表（1000万行）は生データのまま `toPandas()` せず、必ずSpark側でjoin＋集計してから小さい結果のみをpandasに変換する方針とした
- 時間帯は6時間区切りの4バンド（深夜0-5時／午前6-11時／午後12-17時／夜18-23時）とし、`transaction_timestamp` が一様乱数生成のため実際の日内パターンは出ない旨をnotebook内に注記した
- pyspark importは既存の決定事項（`from pyspark.sql.functions import *`）に合わせた
- 2パネルのヒートマップ描画ロジックが構造的に同一なため、既存notebookの完全インライン方式から外れて共通ヘルパー関数化した（重複コピーの方が可読性を損なうと判断）

### 発生した問題

- 特になし

### 解決方法

- （該当なし）

### TODO

- Databricks上で `notebooks/visualize/visualize_demo.ipynb` を実行し、`pivot_channel`/`pivot_timeband` の形状（8×4）・ヒートマップの日本語表示・集計件数合計が `transaction` の総件数と一致することを確認する

---

## 2026-07-20

### 今日やったこと

- 地方銀行向けDatabricksデモ（`demo_bank/`）用のダミーデータ生成スクリプト `demo_bank/generate_dummy_bank_data.py` を新規作成
    - 基幹システム想定のRDBデータ（`customer.csv`, `transaction_summary.csv`）とCRM SaaS想定のデータ（`crm_activity.csv`）の2種類のデータソースを、`customer_id` をキーに統合できる構成にした
    - 企業10社（正常6社・注意3社・高優先1社）に対し `assign_scenarios` でシナリオを固定件数割り当て、代表企業（山城精密工業株式会社、`CUST01`固定）は高優先企業として売上入金▲30%（4月→7月）・預金残高▲20%（5月→7月）・延滞10日・CRM懸念文言を仕様通り再現
    - 出力先はUnity Catalog Volume（`/Volumes/workspace/bank/raw/{rdb,crm}/`）を既定値としつつ、環境変数 `DUMMY_BANK_OUTPUT_ROOT` でローカル動作確認用のパスに切り替えられるようにした
    - 生成後に件数・シナリオ別企業数・代表企業の数値整合性（▲30%/▲20%/延滞10日/CRM文言一致）を `assert` 付きで検証するセクションを実装

### 決定事項

- 当初検討していた30社・8ファイル（customer/loan/transaction/crm/external_company_info + metadata3種）の大規模仕様は不採用とし、10社・3ファイル（customer/transaction_summary/crm_activity）の簡易版に置き換えた
- 出力先は既存の `datasets/detasets_demo.ipynb` 系（不正検知デモ、`workspace.datasets.*`）とは無関係な独立デリバラブルとし、`demo_bank/` 配下に閉じる
- 本スクリプトはDatabricksクラスタ上で直接実行できることを前提に、`SparkSession`/`dbutils` を使わず標準的なPython I/O（`os`, `pandas.to_csv`）のみで `/Volumes/...` パスに書き込む方式とした
- 乱数は `np.random.default_rng(SEED)` を1つだけ生成し全関数に明示的に渡す方式にし、代表企業のみ主要指標のノイズをゼロにして数値検証を厳密化した

### 発生した問題

- 特になし

### 解決方法

- （該当なし）

### TODO

- Databricks上で `demo_bank/generate_dummy_bank_data.py` を実行し、`/Volumes/workspace/bank/raw/` 配下にファイルが生成されることを確認する
- Bronze/Silver/Goldレイヤーへの取り込みnotebook、および `customer_id` で統合した `company_360` Goldテーブルの実装を検討する

---
