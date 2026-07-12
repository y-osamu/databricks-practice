# モジュールのインポート
from pyspark import pipelines as dp
from pyspark.sql.functions import *
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructType,TimestampType,StructField 

# Define the path to the source data
SOURCE_PATH = ""

inventory_schema = StructType([
    StructField("", StringType(), True),
])

# ============================================================
# Bronze
# Volume上のCSVをAuto Loaderで増分取り込み
# ============================================================

@dp.table(
    name="bronze_",
    comment=""
)

def bronze_():
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
    name="silver_",
    comment=""
)
def silver_():
    return (
        spark.readStream.table("bronze_")
    )


# ============================================================
# Gold
# 
# ============================================================

@dp.materialized_view(
    name="gold_",
    comment=""
)
def gold_():
    return (
        spark.read.table("silver_")
    )