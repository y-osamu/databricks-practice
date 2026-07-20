# Databricks notebook source
"""
地方銀行向けDatabricksデモ用ダミーデータ生成スクリプト。

出力先（Unity Catalog Volume）:
  /Volumes/workspace/bank/raw/rdb/customer.csv
  /Volumes/workspace/bank/raw/rdb/transaction_summary.csv
  /Volumes/workspace/bank/raw/crm/crm_activity.csv

Databricks Notebook上でそのまま実行可能（SparkSession/dbutilsは不要）。
ローカルで動作確認する場合は環境変数 DUMMY_BANK_OUTPUT_ROOT で出力先を上書きできる。
"""

import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 定数・マスタデータ
# ---------------------------------------------------------------------------

SEED = 42
ANCHOR_DATE = date(2026, 7, 20)

OUTPUT_ROOT = os.environ.get("DUMMY_BANK_OUTPUT_ROOT", "/Volumes/workspace/bank/raw")

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

# 「山城」は代表企業専用に予約し、他社には使わない
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
NORMAL_CONCERN = "特になし"

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

HIGH_PRIORITY_MEETING_NOTE = "原材料価格上昇と受注減少により資金繰りに懸念"
HIGH_PRIORITY_CONCERN = "運転資金不足"
HIGH_PRIORITY_NEXT_ACTION = "担当者による早期訪問と資金繰り確認"


def month_labels(anchor_date: date, n_months: int = 6) -> list[str]:
    """anchor_dateの月を含む直近n_months分の 'YYYY-MM' ラベルを古い順で返す。"""
    labels = []
    for offset in range(n_months - 1, -1, -1):
        y, m = anchor_date.year, anchor_date.month - offset
        while m <= 0:
            m += 12
            y -= 1
        labels.append(f"{y}-{m:02d}")
    return labels


MONTH_LABELS = month_labels(ANCHOR_DATE, 6)


# ---------------------------------------------------------------------------
# シナリオ割り当て
# ---------------------------------------------------------------------------

def assign_scenarios(rng: np.random.Generator) -> list[str]:
    """10社分のシナリオを割り当てる。index0 は必ず high_priority(代表企業)。"""
    rest = ["normal"] * N_NORMAL + ["caution"] * N_CAUTION
    rng.shuffle(rest)
    return ["high_priority"] + rest


# ---------------------------------------------------------------------------
# customer.csv
# ---------------------------------------------------------------------------

def generate_customers(rng: np.random.Generator, scenario_types: list[str]) -> pd.DataFrame:
    prefix_order = list(rng.permutation(COMPANY_NAME_PREFIXES))
    prefix_iter = iter(prefix_order)

    records = []
    for i, scenario in enumerate(scenario_types):
        customer_id = f"CUST{i + 1:02d}"

        if scenario == "high_priority":
            company_name = REPRESENTATIVE_COMPANY_NAME
            industry = REPRESENTATIVE_INDUSTRY
        else:
            industry = str(rng.choice(INDUSTRIES))
            prefix = next(prefix_iter)
            word = str(rng.choice(INDUSTRY_WORDS[industry]))
            company_name = f"{prefix}{word}株式会社"

        employee_count = int(rng.integers(20, 301))
        annual_sales = int(rng.integers(300_000_000, 3_000_000_001) // 1_000_000 * 1_000_000)
        branch_name = str(rng.choice(BRANCH_NAMES))
        relationship_manager = str(rng.choice(RELATIONSHIP_MANAGERS))

        records.append({
            "customer_id": customer_id,
            "company_name": company_name,
            "industry": industry,
            "annual_sales": annual_sales,
            "employee_count": employee_count,
            "branch_name": branch_name,
            "relationship_manager": relationship_manager,
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# transaction_summary.csv
# ---------------------------------------------------------------------------

def generate_transaction_summary(
    rng: np.random.Generator, customers_df: pd.DataFrame, scenario_types: list[str]
) -> pd.DataFrame:
    rows = []

    for i, customer_row in customers_df.iterrows():
        scenario = scenario_types[i]
        annual_sales = customer_row["annual_sales"]

        base_inflow = annual_sales / 12 * rng.uniform(0.6, 0.9)
        base_outflow = base_inflow * rng.uniform(0.85, 0.95)
        base_deposit = base_inflow * rng.uniform(2.0, 4.0)
        base_loan = annual_sales * rng.uniform(0.1, 0.3)

        if scenario == "high_priority":
            # 直近3か月(5〜7月)で売上入金が合計約30%減少
            inflow_decline = 0.7 ** (1 / 3)
            inflow = [base_inflow, base_inflow, base_inflow]
            for _ in range(3):
                inflow.append(inflow[-1] * inflow_decline)

            # 原材料価格上昇を反映し、直近3か月は支出がやや増加
            outflow = [base_outflow, base_outflow, base_outflow,
                       base_outflow * 1.05, base_outflow * 1.08, base_outflow * 1.10]

            # 直近2か月(6〜7月)で預金残高が合計約20%減少
            balance_decline = 0.8 ** (1 / 2)
            deposit = [base_deposit, base_deposit, base_deposit, base_deposit]
            for _ in range(2):
                deposit.append(deposit[-1] * balance_decline)

            # 融資残高は横ばい〜微増
            loan = [base_loan * (1 + 0.01 * m) for m in range(6)]

            # 延滞は直近2か月で発生し始め、最新月で10日
            overdue = [0, 0, 0, 0, 5, 10]

        elif scenario == "caution":
            inflow_growth = rng.uniform(0.97, 0.99)
            inflow = [base_inflow * (inflow_growth ** m) for m in range(6)]
            outflow = [base_outflow * (1 + rng.normal(0, 0.03)) for _ in range(6)]

            balance_growth = rng.uniform(0.97, 0.99)
            deposit = [base_deposit * (balance_growth ** m) for m in range(6)]

            loan = [base_loan * (1 + rng.normal(0, 0.02)) for _ in range(6)]
            overdue = [0] * 6

        else:  # normal
            inflow = [base_inflow * (1 + rng.normal(0, 0.03)) for _ in range(6)]
            outflow = [base_outflow * (1 + rng.normal(0, 0.03)) for _ in range(6)]
            deposit = [base_deposit * (1 + rng.normal(0, 0.02)) for _ in range(6)]
            loan = [base_loan * (1 + rng.normal(0, 0.01)) for _ in range(6)]
            overdue = [0] * 6

        for m in range(6):
            rows.append({
                "customer_id": customer_row["customer_id"],
                "month": MONTH_LABELS[m],
                "monthly_inflow": round(inflow[m], -3),
                "monthly_outflow": round(outflow[m], -3),
                "deposit_balance": round(deposit[m], -3),
                "loan_balance": round(loan[m], -3),
                "overdue_days": int(overdue[m]),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# crm_activity.csv
# ---------------------------------------------------------------------------

def generate_crm_activity(
    rng: np.random.Generator, customers_df: pd.DataFrame, scenario_types: list[str]
) -> pd.DataFrame:
    rows = []

    for i, customer_row in customers_df.iterrows():
        scenario = scenario_types[i]

        if scenario == "high_priority":
            activity_date = ANCHOR_DATE - timedelta(days=3)
            meeting_note = HIGH_PRIORITY_MEETING_NOTE
            customer_concern = HIGH_PRIORITY_CONCERN
            next_action = HIGH_PRIORITY_NEXT_ACTION
        elif scenario == "caution":
            activity_date = ANCHOR_DATE - timedelta(days=int(rng.integers(30, 60)))
            meeting_note = str(rng.choice(CAUTION_MEETING_NOTES))
            customer_concern = str(rng.choice(CAUTION_CONCERNS))
            next_action = str(rng.choice(CAUTION_NEXT_ACTIONS))
        else:  # normal
            activity_date = ANCHOR_DATE - timedelta(days=int(rng.integers(10, 45)))
            meeting_note = str(rng.choice(NORMAL_MEETING_NOTES))
            customer_concern = NORMAL_CONCERN
            next_action = str(rng.choice(NORMAL_NEXT_ACTIONS))

        rows.append({
            "customer_id": customer_row["customer_id"],
            "activity_date": activity_date.isoformat(),
            "meeting_note": meeting_note,
            "customer_concern": customer_concern,
            "next_action": next_action,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 書き込み・検証
# ---------------------------------------------------------------------------

def write_csv_bom(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def validate(
    customers_df: pd.DataFrame,
    transaction_summary_df: pd.DataFrame,
    crm_activity_df: pd.DataFrame,
    scenario_types: list[str],
) -> None:
    print("=" * 60)
    print("件数チェック")
    print("=" * 60)
    print(f"customer.csv           : {len(customers_df)} 行 (期待値 {N_COMPANIES})")
    print(f"transaction_summary.csv: {len(transaction_summary_df)} 行 (期待値 {N_COMPANIES * 6})")
    print(f"crm_activity.csv       : {len(crm_activity_df)} 行 (期待値 {N_COMPANIES})")

    print()
    print("=" * 60)
    print("シナリオ別企業数")
    print("=" * 60)
    counts = pd.Series(scenario_types).value_counts()
    print(counts.to_string())
    assert counts.get("normal", 0) == N_NORMAL
    assert counts.get("caution", 0) == N_CAUTION
    assert counts.get("high_priority", 0) == N_HIGH_PRIORITY

    print()
    print("=" * 60)
    print(f"代表企業（{REPRESENTATIVE_CUSTOMER_ID} / {REPRESENTATIVE_COMPANY_NAME}）の確認")
    print("=" * 60)

    rep_customer = customers_df[customers_df["customer_id"] == REPRESENTATIVE_CUSTOMER_ID].iloc[0]
    print(rep_customer.to_string())

    rep_txn = transaction_summary_df[
        transaction_summary_df["customer_id"] == REPRESENTATIVE_CUSTOMER_ID
    ].reset_index(drop=True)
    print()
    print(rep_txn.to_string(index=False))

    inflow_apr = rep_txn.loc[2, "monthly_inflow"]
    inflow_jul = rep_txn.loc[5, "monthly_inflow"]
    inflow_change = (inflow_jul / inflow_apr - 1) * 100
    print(f"\n売上入金 変化率(4月→7月): {inflow_change:.1f}% (期待値: 約-30%)")

    deposit_may = rep_txn.loc[3, "deposit_balance"]
    deposit_jul = rep_txn.loc[5, "deposit_balance"]
    deposit_change = (deposit_jul / deposit_may - 1) * 100
    print(f"預金残高 変化率(5月→7月): {deposit_change:.1f}% (期待値: 約-20%)")

    overdue_jul = rep_txn.loc[5, "overdue_days"]
    print(f"延滞日数(直近月): {overdue_jul} 日 (期待値: 10日)")
    assert overdue_jul == 10

    rep_crm = crm_activity_df[crm_activity_df["customer_id"] == REPRESENTATIVE_CUSTOMER_ID].iloc[0]
    print()
    print(rep_crm.to_string())
    assert rep_crm["meeting_note"] == HIGH_PRIORITY_MEETING_NOTE
    assert rep_crm["customer_concern"] == HIGH_PRIORITY_CONCERN
    assert rep_crm["next_action"] == HIGH_PRIORITY_NEXT_ACTION

    print()
    print("すべての検証項目がPASSしました。")


def main() -> None:
    rng = np.random.default_rng(SEED)

    scenario_types = assign_scenarios(rng)
    customers_df = generate_customers(rng, scenario_types)
    transaction_summary_df = generate_transaction_summary(rng, customers_df, scenario_types)
    crm_activity_df = generate_crm_activity(rng, customers_df, scenario_types)

    write_csv_bom(customers_df, os.path.join(OUTPUT_ROOT, "rdb", "customer.csv"))
    write_csv_bom(transaction_summary_df, os.path.join(OUTPUT_ROOT, "rdb", "transaction_summary.csv"))
    write_csv_bom(crm_activity_df, os.path.join(OUTPUT_ROOT, "crm", "crm_activity.csv"))

    print(f"出力先: {OUTPUT_ROOT}")
    print()
    validate(customers_df, transaction_summary_df, crm_activity_df, scenario_types)


main()
