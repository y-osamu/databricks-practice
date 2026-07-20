# Databricks notebook source
# MAGIC %md
# MAGIC ## デモデータ作成

# COMMAND ----------

# DBTITLE 1,ライブラリインポート

import os
from datetime import date, timedelta

import numpy as np
import pandas as pd


# COMMAND ----------

CATALOG = "workspace"
SCHEMA = "bank"
VOLUME = "vol"

# COMMAND ----------

OUTPUT_ROOT = f"/Volumes/workspace/bank/vol"
print(f"出力先: {OUTPUT_ROOT}")


# COMMAND ----------

SEED = 42
ANCHOR_DATE = date(2026, 7, 20)

REPRESENTATIVE_CUSTOMER_ID = "CUST01"
REPRESENTATIVE_COMPANY_NAME = "山城精密工業株式会社"
REPRESENTATIVE_INDUSTRY = "製造業"

N_NORMAL = 6
N_CAUTION = 3
N_HIGH_PRIORITY = 1
N_COMPANIES = N_NORMAL + N_CAUTION + N_HIGH_PRIORITY

INDUSTRIES = [
    "製造業", "小売業", "卸売業", "建設業", "運輸業",
    "情報通信業", "宿泊業", "飲食サービス業", "医療福祉", "農業", "不動産業",
]

INDUSTRY_WORDS = {
    "製造業": ["精密工業", "機械工業", "金属工業"],
    "小売業": ["商事", "商店"],
    "卸売業": ["卸商事", "商事"],
    "建設業": ["建設", "工務店"],
    "運輸業": ["運輸", "物流"],
    "情報通信業": ["システムズ", "情報サービス"],
    "宿泊業": ["観光", "旅館"],
    "飲食サービス業": ["フーズ", "フードサービス"],
    "医療福祉": ["メディカル", "ヘルスケア"],
    "農業": ["アグリ", "農産"],
    "不動産業": ["不動産", "開発"],
}

COMPANY_NAME_PREFIXES = [
    "桂川", "嵐山", "伏見", "近江", "丹波",
    "若狭", "淀", "東山", "洛北", "洛西",
]

BRANCH_NAMES = [
    "京都中央支店", "大阪北支店", "滋賀支店", "奈良支店", "神戸支店",
    "伏見支店", "河原町支店", "四条支店", "西京支店", "長岡京支店",
]

RELATIONSHIP_MANAGERS = [
    "田中一郎", "佐藤花子", "鈴木次郎", "高橋三郎", "伊藤さくら",
    "渡辺健太", "山本美咲", "中村大輔", "小林陽子", "加藤拓也",
]

NORMAL_MEETING_NOTES = [
    "業況は堅調に推移しており、特段の懸念事項はなし。",
    "売上は計画通りに推移しており、資金繰りも安定している。",
    "定例訪問を実施。経営状況は良好で大きな変化なし。",
]

NORMAL_NEXT_ACTIONS = [
    "次回定例訪問まで特段のフォローなし。",
    "四半期ごとの定例フォローを継続。",
    "次回は3か月後に定例訪問予定。",
]

CAUTION_MEETING_NOTES = [
    "受注がやや減少傾向にあり、今後の推移を注視する必要がある。",
    "売上の伸び悩みが見られ、経営陣も対応を検討中とのこと。",
    "一部取引先から支払サイト延長の要請があり、資金繰りへの影響を確認中。",
]

CAUTION_CONCERNS = [
    "売上減少への対応検討",
    "一部取引先の支払遅延懸念",
    "受注動向の悪化",
]

CAUTION_NEXT_ACTIONS = [
    "次回訪問時に売上動向を確認する。",
    "四半期決算を確認のうえ再訪問予定。",
    "資金繰り状況について追加ヒアリングを実施予定。",
]


# COMMAND ----------

MONTH_LABELS = []

for offset in range(5, -1, -1):
    year = ANCHOR_DATE.year
    month = ANCHOR_DATE.month - offset

    while month <= 0:
        month += 12
        year -= 1

    MONTH_LABELS.append(f"{year}-{month:02d}")

MONTH_LABELS

# COMMAND ----------

rng = np.random.default_rng(SEED)

remaining_scenarios = ["normal"] * N_NORMAL + ["caution"] * N_CAUTION
rng.shuffle(remaining_scenarios)

scenario_types = ["high_priority"] + remaining_scenarios

pd.Series(scenario_types).value_counts()


# COMMAND ----------

# MAGIC %md
# MAGIC ## 企業マスタを生成

# COMMAND ----------

prefix_order = list(rng.permutation(COMPANY_NAME_PREFIXES))
customer_records = []

for i, scenario in enumerate(scenario_types):
    customer_id = f"CUST{i + 1:02d}"

    if scenario == "high_priority":
        company_name = REPRESENTATIVE_COMPANY_NAME
        industry = REPRESENTATIVE_INDUSTRY
    else:
        industry = str(rng.choice(INDUSTRIES))
        prefix = prefix_order[i - 1]
        industry_word = str(rng.choice(INDUSTRY_WORDS[industry]))
        company_name = f"{prefix}{industry_word}株式会社"

    customer_records.append({
        "customer_id": customer_id,
        "company_name": company_name,
        "industry": industry,
        "annual_sales": int(
            rng.integers(300_000_000, 3_000_000_001)
            // 1_000_000
            * 1_000_000
        ),
        "employee_count": int(rng.integers(20, 301)),
        "branch_name": str(rng.choice(BRANCH_NAMES)),
        "relationship_manager": str(rng.choice(RELATIONSHIP_MANAGERS)),
        "scenario_type": scenario,
    })

customers_df = pd.DataFrame(customer_records)

display(customers_df)


# COMMAND ----------

# MAGIC %md
# MAGIC ## 月次取引・融資サマリを生成
# MAGIC

# COMMAND ----------


transaction_rows = []

for i, customer_row in customers_df.iterrows():
    scenario = customer_row["scenario_type"]
    annual_sales = customer_row["annual_sales"]

    base_inflow = annual_sales / 12 * rng.uniform(0.6, 0.9)
    base_outflow = base_inflow * rng.uniform(0.85, 0.95)
    base_deposit = base_inflow * rng.uniform(2.0, 4.0)
    base_loan = annual_sales * rng.uniform(0.1, 0.3)

    if scenario == "high_priority":
        inflow_decline = 0.7 ** (1 / 3)
        monthly_inflows = [base_inflow, base_inflow, base_inflow]

        for _ in range(3):
            monthly_inflows.append(monthly_inflows[-1] * inflow_decline)

        monthly_outflows = [
            base_outflow,
            base_outflow,
            base_outflow,
            base_outflow * 1.05,
            base_outflow * 1.08,
            base_outflow * 1.10,
        ]

        balance_decline = 0.8 ** (1 / 2)
        deposit_balances = [
            base_deposit,
            base_deposit,
            base_deposit,
            base_deposit,
        ]

        for _ in range(2):
            deposit_balances.append(
                deposit_balances[-1] * balance_decline
            )

        loan_balances = [
            base_loan * (1 + 0.01 * month_index)
            for month_index in range(6)
        ]

        overdue_days = [0, 0, 0, 0, 5, 10]

    elif scenario == "caution":
        inflow_growth = rng.uniform(0.97, 0.99)
        balance_growth = rng.uniform(0.97, 0.99)

        monthly_inflows = [
            base_inflow * (inflow_growth ** month_index)
            for month_index in range(6)
        ]

        monthly_outflows = [
            base_outflow * (1 + rng.normal(0, 0.03))
            for _ in range(6)
        ]

        deposit_balances = [
            base_deposit * (balance_growth ** month_index)
            for month_index in range(6)
        ]

        loan_balances = [
            base_loan * (1 + rng.normal(0, 0.02))
            for _ in range(6)
        ]

        overdue_days = [0] * 6

    else:
        monthly_inflows = [
            base_inflow * (1 + rng.normal(0, 0.03))
            for _ in range(6)
        ]

        monthly_outflows = [
            base_outflow * (1 + rng.normal(0, 0.03))
            for _ in range(6)
        ]

        deposit_balances = [
            base_deposit * (1 + rng.normal(0, 0.02))
            for _ in range(6)
        ]

        loan_balances = [
            base_loan * (1 + rng.normal(0, 0.01))
            for _ in range(6)
        ]

        overdue_days = [0] * 6

    for month_index, month_label in enumerate(MONTH_LABELS):
        transaction_rows.append({
            "customer_id": customer_row["customer_id"],
            "month": month_label,
            "monthly_inflow": round(monthly_inflows[month_index], -3),
            "monthly_outflow": round(monthly_outflows[month_index], -3),
            "deposit_balance": round(deposit_balances[month_index], -3),
            "loan_balance": round(loan_balances[month_index], -3),
            "overdue_days": int(overdue_days[month_index]),
        })

transaction_summary_df = pd.DataFrame(transaction_rows)

display(transaction_summary_df)


# COMMAND ----------

transaction_summary_df = (
    transaction_summary_df
    .sort_values(["customer_id", "month"])
)

transaction_summary_df["next_month_overdue"] = (
    transaction_summary_df
    .groupby("customer_id")["overdue_days"]
    .shift(-1)
)

transaction_summary_df["label"] = (
    transaction_summary_df["next_month_overdue"] > 0
).astype(int)

# COMMAND ----------

# MAGIC %md
# MAGIC ## CRM営業活動履歴を生成
# MAGIC

# COMMAND ----------

crm_rows = []

for _, customer_row in customers_df.iterrows():
    scenario = customer_row["scenario_type"]

    if scenario == "high_priority":
        activity_date = ANCHOR_DATE - timedelta(days=120)
        meeting_note = "原材料価格上昇と受注減少により資金繰りに懸念"
        customer_concern = "運転資金不足"
        next_action = "担当者による早期訪問と資金繰り確認"

    elif scenario == "caution":
        activity_date = ANCHOR_DATE - timedelta(
            days=int(rng.integers(30, 60))
        )
        meeting_note = str(rng.choice(CAUTION_MEETING_NOTES))
        customer_concern = str(rng.choice(CAUTION_CONCERNS))
        next_action = str(rng.choice(CAUTION_NEXT_ACTIONS))

    else:
        activity_date = ANCHOR_DATE - timedelta(
            days=int(rng.integers(10, 45))
        )
        meeting_note = str(rng.choice(NORMAL_MEETING_NOTES))
        customer_concern = "特になし"
        next_action = str(rng.choice(NORMAL_NEXT_ACTIONS))

    crm_rows.append({
        "customer_id": customer_row["customer_id"],
        "activity_date": activity_date.isoformat(),
        "meeting_note": meeting_note,
        "customer_concern": customer_concern,
        "next_action": next_action,
    })

crm_activity_df = pd.DataFrame(crm_rows)

display(crm_activity_df)


# COMMAND ----------

# MAGIC %md
# MAGIC ## CSVファイルとしてVolumeへ出力

# COMMAND ----------

rdb_output_path = f"{OUTPUT_ROOT}/rdb"
crm_output_path = f"{OUTPUT_ROOT}/crm"

# COMMAND ----------

rdb_output_path = f"{OUTPUT_ROOT}/rdb"
crm_output_path = f"{OUTPUT_ROOT}/crm"

os.makedirs(rdb_output_path, exist_ok=True)
os.makedirs(crm_output_path, exist_ok=True)

customers_df.drop(columns=["scenario_type"]).to_csv(
    f"{rdb_output_path}/customer.csv",
    index=False,
    encoding="utf-8-sig",
)

transaction_summary_df.to_csv(
    f"{rdb_output_path}/transaction_summary.csv",
    index=False,
    encoding="utf-8-sig",
)

crm_activity_df.to_csv(
    f"{crm_output_path}/crm_activity.csv",
    index=False,
    encoding="utf-8-sig",
)

print("CSV出力が完了しました。")

# COMMAND ----------

print(f"customer.csv            : {len(customers_df)} 行")
print(f"transaction_summary.csv : {len(transaction_summary_df)} 行")
print(f"crm_activity.csv        : {len(crm_activity_df)} 行")

assert len(customers_df) == N_COMPANIES
assert len(transaction_summary_df) == N_COMPANIES * 6
assert len(crm_activity_df) == N_COMPANIES

print("件数チェック：PASS")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 代表企業のシナリオを確認

# COMMAND ----------

representative_customer = customers_df[
    customers_df["customer_id"] == REPRESENTATIVE_CUSTOMER_ID
]

representative_transactions = transaction_summary_df[
    transaction_summary_df["customer_id"] == REPRESENTATIVE_CUSTOMER_ID
].reset_index(drop=True)

representative_crm = crm_activity_df[
    crm_activity_df["customer_id"] == REPRESENTATIVE_CUSTOMER_ID
]

display(representative_customer)
display(representative_transactions)
display(representative_crm)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 代表企業の変化率を検証

# COMMAND ----------


inflow_april = representative_transactions.loc[2, "monthly_inflow"]
inflow_july = representative_transactions.loc[5, "monthly_inflow"]
inflow_change_rate = (inflow_july / inflow_april - 1) * 100

deposit_may = representative_transactions.loc[3, "deposit_balance"]
deposit_july = representative_transactions.loc[5, "deposit_balance"]
deposit_change_rate = (deposit_july / deposit_may - 1) * 100

latest_overdue_days = representative_transactions.loc[5, "overdue_days"]

print(f"売上入金変化率（4月→7月）：{inflow_change_rate:.1f}%")
print(f"預金残高変化率（5月→7月）：{deposit_change_rate:.1f}%")
print(f"直近月の延滞日数：{latest_overdue_days}日")

assert round(inflow_change_rate) == -30
assert round(deposit_change_rate) == -20
assert latest_overdue_days == 10

print("代表企業シナリオチェック：PASS")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Volume上の出力ファイルを確認

# COMMAND ----------

display(dbutils.fs.ls(OUTPUT_ROOT))
display(dbutils.fs.ls(rdb_output_path))
display(dbutils.fs.ls(crm_output_path))
