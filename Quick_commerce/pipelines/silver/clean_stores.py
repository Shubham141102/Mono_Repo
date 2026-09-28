import os
import sys
import shutil

from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import col, trim, initcap, lit, when, row_number
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
    PROJECT_ROOT, "data", "bronze", "stores_csv", "stores.csv"
)

SILVER_DIR = os.path.join(
    PROJECT_ROOT, "data", "silver", "stores_csv"
)

QUARANTINE_DIR = os.path.join(
    PROJECT_ROOT, "data", "quarantine", "stores_csv"
)

if os.path.exists(SILVER_DIR):
    shutil.rmtree(SILVER_DIR)

if os.path.exists(QUARANTINE_DIR):
    shutil.rmtree(QUARANTINE_DIR)

os.makedirs(SILVER_DIR)
os.makedirs(QUARANTINE_DIR)

spark = (
    SparkSession.builder
    .appName("CleanStoresSilver")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

schema = StructType([
    StructField("store_id", StringType(), True),
    StructField("store_name", StringType(), True),
    StructField("city", StringType(), True),
    StructField("state", StringType(), True),
    StructField("pincode", StringType(), True),
    StructField("latitude", DoubleType(), True),
    StructField("longitude", DoubleType(), True),
    StructField("opened_date", StringType(), True),
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
    "store_id",
    "store_name",
    "city",
    "state",
    "pincode",
    "opened_date"
]:
    df = df.withColumn(c, trim(col(c)))

df = (
    df
    .withColumn("store_name", initcap(col("store_name")))
    .withColumn("city", initcap(col("city")))
    .withColumn("state", initcap(col("state")))
)

# -----------------------------
# VALIDATION
# -----------------------------

df = df.withColumn(
    "validation_reason",
    when(
        col("store_id").isNull() | (col("store_id") == ""),
        lit("Missing store_id")
    )
    .when(
        col("store_name").isNull() | (col("store_name") == ""),
        lit("Missing store_name")
    )
    .when(
        col("city").isNull() | (col("city") == ""),
        lit("Missing city")
    )
    .when(
        col("state").isNull() | (col("state") == ""),
        lit("Missing state")
    )
    .when(
        col("pincode").isNull() |
        ~col("pincode").rlike(r"^[1-9][0-9]{5}$"),
        lit("Invalid pincode")
    )
    .when(
        col("latitude").isNull() |
        (col("latitude") < -90) |
        (col("latitude") > 90),
        lit("Invalid latitude")
    )
    .when(
        col("longitude").isNull() |
        (col("longitude") < -180) |
        (col("longitude") > 180),
        lit("Invalid longitude")
    )
    .when(
        col("opened_date").isNull() | (col("opened_date") == ""),
        lit("Missing opened_date")
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
    .partitionBy("store_id")
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
        lit("Duplicate store_id")
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
    os.path.join(SILVER_DIR, "stores.csv"),
    index=False
)

quarantine_pdf.to_csv(
    os.path.join(QUARANTINE_DIR, "stores.csv"),
    index=False
)

silver_count = len(silver_pdf)
quarantine_count = len(quarantine_pdf)

# -----------------------------
# RESULTS
# -----------------------------

print("\n" + "=" * 60)
print("STORE SILVER RESULTS")
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

nulls = check_not_null(silver, "store_id")
duplicates_count = check_unique(silver, "store_id")

print("\nDATA QUALITY")
print(f"NULL store_id      : {nulls}")
print(f"Duplicate store_id : {duplicates_count}")

report = create_quality_report(
    "stores",
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