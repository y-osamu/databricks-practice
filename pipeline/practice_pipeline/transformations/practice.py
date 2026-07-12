# モジュールのインポート
from pyspark import pipelines as dp
from pyspark.sql.functions import *
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructType,TimestampType,StructField 

# Define the path to the source data
SOURCE_PATH = "/Volumes/workspace/practice/vol/"

inventory_schema = StructType([
    StructField("inventory_id", StringType(), True),
    StructField("store_id", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("stock_quantity", IntegerType(), True),
    StructField("reserved_quantity", IntegerType(), True),
    StructField("snapshot_at", TimestampType(), True),
])

# ============================================================
# Bronze
# Volume上のCSVをAuto Loaderで増分取り込み
# ============================================================

@dp.table(
    name="bronze_inventory",
    comment="Raw inventory snapshot data ingested from CSV files"
)

def bronze_inventory():
    return (
        spark.readStream
        .format("cloudFiles")
        .schema(inventory_schema)
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .load(SOURCE_PATH)
        .withColumn(
            "_source_file",
            col("_metadata.file_path")
        )
        .withColumn(
            "_ingested_at",
            current_timestamp()
        )
    )

# ============================================================
# Silver
# 不正値の除外
# ============================================================

@dp.table(
    name="silver_inventory",
    comment="Validated inventory data with available stock quantity"
)
def silver_inventory():
    return (
        spark.readStream.table("bronze_inventory")
        .filter(col("inventory_id").isNotNull())
        .filter(col("store_id").isNotNull())
        .filter(col("product_id").isNotNull())
        .filter(col("snapshot_at").isNotNull())
        .filter(col("stock_quantity") >= 0)
        .filter(col("reserved_quantity") >= 0)
        .withColumn(
            "available_quantity",
            col("stock_quantity") - col("reserved_quantity")
        )
        .withColumn(
            "is_out_of_stock",
            col("stock_quantity") <= 0
        )
    )


# ============================================================
# Gold
# 店舗・日付ごとの在庫状況を集計
# ============================================================

@dp.materialized_view(
    name="gold_daily_store_inventory",
    comment="Daily inventory metrics by store"
)
def gold_daily_store_inventory():
    return (
        spark.read.table("silver_inventory")
        .groupBy(
            to_date("snapshot_at").alias("snapshot_date"),
            "store_id"
        )
        .agg(
            sum("stock_quantity").alias("total_stock_quantity"),
            sum("reserved_quantity").alias("total_reserved_quantity"),
            sum("available_quantity").alias("total_available_quantity"),
            countDistinct("product_id").alias("product_count"),
            sum(
                when(col("is_out_of_stock"), 1).otherwise(0)
            ).alias("out_of_stock_product_count")
        )
    )