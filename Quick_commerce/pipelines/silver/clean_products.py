import os
import sys
import shutil

from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import col, trim, initcap, lower, lit, when, row_number
from pyspark.sql.window import Window

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from quality.data_quality import (
    check_not_null,
    check_unique,
    create_quality_report
)

BRONZE = os.path.join(
    PROJECT_ROOT, "data", "bronze", "products_csv", "products.csv"
)

SILVER_DIR = os.path.join(
    PROJECT_ROOT, "data", "silver", "products_csv"
)

QUARANTINE_DIR = os.path.join(
    PROJECT_ROOT, "data", "quarantine", "products_csv"
)

if os.path.exists(SILVER_DIR):
    shutil.rmtree(SILVER_DIR)

if os.path.exists(QUARANTINE_DIR):
    shutil.rmtree(QUARANTINE_DIR)

os.makedirs(SILVER_DIR)
os.makedirs(QUARANTINE_DIR)

spark = (
    SparkSession.builder
    .appName("CleanProductsSilver")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

schema = StructType([
    StructField("product_id", StringType(), True),
    StructField("product_name", StringType(), True),
    StructField("category", StringType(), True),
    StructField("subcategory", StringType(), True),
    StructField("brand", StringType(), True),
    StructField("unit_price", DoubleType(), True),
    StructField("cost_price", DoubleType(), True),
    StructField("unit", StringType(), True),
    StructField("is_active", BooleanType(), True),

    StructField("source_file", StringType(), True),
    StructField("source_system", StringType(), True),
    StructField("ingestion_timestamp", StringType(), True),
    StructField("batch_id", StringType(), True),
    StructField("ingestion_date", StringType(), True),
    StructField("record_hash", StringType(), True),
])

df = (
    spark.read
    .option("header", True)
    .schema(schema)
    .csv(BRONZE)
)

bronze_count = df.count()
print(f"Bronze records: {bronze_count}")

# -----------------------------
# CLEANING
# -----------------------------

for c in [
    "product_id",
    "product_name",
    "category",
    "subcategory",
    "brand",
    "unit"
]:
    df = df.withColumn(c, trim(col(c)))

df = (
    df
    .withColumn("product_name", initcap(col("product_name")))
    .withColumn("category", initcap(col("category")))
    .withColumn("subcategory", initcap(col("subcategory")))
    .withColumn("brand", initcap(col("brand")))
    .withColumn("unit", lower(col("unit")))
)

# -----------------------------
# VALIDATION
# -----------------------------

df = df.withColumn(
    "validation_reason",
    when(
        col("product_id").isNull() | (col("product_id") == ""),
        lit("Missing product_id")
    )
    .when(
        col("product_name").isNull() | (col("product_name") == ""),
        lit("Missing product_name")
    )
    .when(
        col("category").isNull() | (col("category") == ""),
        lit("Missing category")
    )
    .when(
        col("subcategory").isNull() | (col("subcategory") == ""),
        lit("Missing subcategory")
    )
    .when(
        col("brand").isNull() | (col("brand") == ""),
        lit("Missing brand")
    )
    .when(
        col("unit_price").isNull() | (col("unit_price") <= 0),
        lit("Invalid unit_price")
    )
    .when(
        col("cost_price").isNull() | (col("cost_price") <= 0),
        lit("Invalid cost_price")
    )
    .when(
        col("cost_price") > col("unit_price"),
        lit("cost_price greater than unit_price")
    )
    .when(
        col("unit").isNull() | (col("unit") == ""),
        lit("Missing unit")
    )
    .when(
        col("is_active").isNull(),
        lit("Missing is_active")
    )
)

valid = df.filter(col("validation_reason").isNull())
invalid = df.filter(col("validation_reason").isNotNull())

# -----------------------------
# DEDUPLICATION
# -----------------------------

window = (
    Window
    .partitionBy("product_id")
    .orderBy(col("ingestion_timestamp").asc())
)

ranked = valid.withColumn(
    "rn",
    row_number().over(window)
)

duplicates = (
    ranked
    .filter(col("rn") > 1)
    .drop("rn")
    .withColumn(
        "validation_reason",
        lit("Duplicate product_id")
    )
)

silver = (
    ranked
    .filter(col("rn") == 1)
    .drop("rn", "validation_reason")
)

quarantine = invalid.unionByName(
    duplicates.select(invalid.columns)
)

# -----------------------------
# WRITE
# -----------------------------

silver_pdf = silver.toPandas()
quarantine_pdf = quarantine.toPandas()

silver_pdf.to_csv(
    os.path.join(SILVER_DIR, "products.csv"),
    index=False
)

quarantine_pdf.to_csv(
    os.path.join(QUARANTINE_DIR, "products.csv"),
    index=False
)

silver_count = len(silver_pdf)
quarantine_count = len(quarantine_pdf)

# -----------------------------
# RESULTS
# -----------------------------

print("\n" + "=" * 60)
print("PRODUCT SILVER RESULTS")
print("=" * 60)

print(f"Bronze        : {bronze_count}")
print(f"Silver        : {silver_count}")
print(f"Quarantine    : {quarantine_count}")

print(
    "Reconciliation: "
    + (
        "PASSED"
        if silver_count + quarantine_count == bronze_count
        else "FAILED"
    )
)

nulls = check_not_null(silver, "product_id")
duplicates_count = check_unique(silver, "product_id")

print("\nDATA QUALITY")
print(f"NULL product_id      : {nulls}")
print(f"Duplicate product_id : {duplicates_count}")

report = create_quality_report(
    "products",
    bronze_count,
    quarantine_count,
    duplicates_count,
    nulls
)

print("\nQUALITY REPORT")

for k, v in report.items():
    print(f"{k}: {v}")

silver.show(5, truncate=False)

spark.stop()