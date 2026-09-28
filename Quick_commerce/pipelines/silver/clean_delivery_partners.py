import os
import sys
import shutil

from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import col, trim, initcap, lit, when, row_number, concat_ws
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
    PROJECT_ROOT,
    "data", "bronze", "delivery_partners_csv", "delivery_partners.csv"
)

SILVER_DIR = os.path.join(
    PROJECT_ROOT,
    "data", "silver", "delivery_partners_csv"
)

QUARANTINE_DIR = os.path.join(
    PROJECT_ROOT,
    "data", "quarantine", "delivery_partners_csv"
)

if os.path.exists(SILVER_DIR):
    shutil.rmtree(SILVER_DIR)

if os.path.exists(QUARANTINE_DIR):
    shutil.rmtree(QUARANTINE_DIR)

os.makedirs(SILVER_DIR)
os.makedirs(QUARANTINE_DIR)

spark = (
    SparkSession.builder
    .appName("CleanDeliveryPartnersSilver")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

schema = StructType([
    StructField("partner_id", StringType(), True),
    StructField("first_name", StringType(), True),
    StructField("last_name", StringType(), True),
    StructField("phone", StringType(), True),
    StructField("city", StringType(), True),
    StructField("vehicle_type", StringType(), True),
    StructField("joining_date", StringType(), True),
    StructField("rating", DoubleType(), True),
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
    "partner_id",
    "first_name",
    "last_name",
    "phone",
    "city",
    "vehicle_type",
    "joining_date"
]:
    df = df.withColumn(c, trim(col(c)))

df = (
    df
    .withColumn("first_name", initcap(col("first_name")))
    .withColumn("last_name", initcap(col("last_name")))
    .withColumn("city", initcap(col("city")))
    .withColumn("vehicle_type", initcap(col("vehicle_type")))
)

# -----------------------------
# VALIDATION
# -----------------------------

valid_vehicle_types = [
    "Bike",
    "Scooter",
    "Electric Bike"
]

df = df.withColumn(
    "validation_reason",
    when(
        col("partner_id").isNull() | (col("partner_id") == ""),
        lit("Missing partner_id")
    )
    .when(
        col("first_name").isNull() | (col("first_name") == ""),
        lit("Missing first_name")
    )
    .when(
        col("last_name").isNull() | (col("last_name") == ""),
        lit("Missing last_name")
    )
    .when(
        col("phone").isNull() |
        ~col("phone").rlike(r"^[6-9][0-9]{9}$"),
        lit("Invalid phone")
    )
    .when(
        col("city").isNull() | (col("city") == ""),
        lit("Missing city")
    )
    .when(
        ~col("vehicle_type").isin(valid_vehicle_types),
        lit("Invalid vehicle_type")
    )
    .when(
        col("rating").isNull() |
        (col("rating") < 0) |
        (col("rating") > 5),
        lit("Invalid rating")
    )
    .when(
        col("joining_date").isNull() | (col("joining_date") == ""),
        lit("Missing joining_date")
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
    .partitionBy("partner_id")
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
        lit("Duplicate partner_id")
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
    os.path.join(SILVER_DIR, "delivery_partners.csv"),
    index=False
)

quarantine_pdf.to_csv(
    os.path.join(QUARANTINE_DIR, "delivery_partners.csv"),
    index=False
)

silver_count = len(silver_pdf)
quarantine_count = len(quarantine_pdf)

print("\n" + "=" * 60)
print("DELIVERY PARTNER SILVER RESULTS")
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

nulls = check_not_null(silver, "partner_id")
duplicates_count = check_unique(silver, "partner_id")

print("\nDATA QUALITY")
print(f"NULL partner_id      : {nulls}")
print(f"Duplicate partner_id : {duplicates_count}")

report = create_quality_report(
    "delivery_partners",
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