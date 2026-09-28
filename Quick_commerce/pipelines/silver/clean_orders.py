import os
import sys
import shutil

# ---------------------------------------------------------
# Project / Python configuration
# ---------------------------------------------------------

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure Spark uses the same Python interpreter
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable


# ---------------------------------------------------------
# Data Quality Framework
# ---------------------------------------------------------

from quality.data_quality import (
    check_not_null,
    check_unique,
    check_range,
    check_allowed_values,
    create_quality_report,
)


# ---------------------------------------------------------
# PySpark imports
# ---------------------------------------------------------

from pyspark.sql import SparkSession

from pyspark.sql.functions import (
    col,
    trim,
    initcap,
    to_timestamp,
    try_to_timestamp,
    row_number,
    when,
    lit,
)

from pyspark.sql.window import Window

from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SOURCE_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "bronze",
    "orders_csv",
    "orders.csv",
)

SILVER_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "silver",
    "orders_csv",
)

SILVER_FILE = os.path.join(
    SILVER_PATH,
    "orders.csv",
)

QUARANTINE_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "quarantine",
    "orders_csv",
)

QUARANTINE_FILE = os.path.join(
    QUARANTINE_PATH,
    "invalid_orders.csv",
)


# ---------------------------------------------------------
# Create Spark Session
# ---------------------------------------------------------

spark = (
    SparkSession.builder
    .appName("SilverOrdersTransformation")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ---------------------------------------------------------
# Pipeline information
# ---------------------------------------------------------

print("=" * 70)
print("SILVER ORDERS TRANSFORMATION")
print("=" * 70)

print(f"Source      : {SOURCE_FILE}")
print(f"Silver      : {SILVER_FILE}")
print(f"Quarantine  : {QUARANTINE_FILE}")


# ---------------------------------------------------------
# Define explicit Bronze schema
# ---------------------------------------------------------
#
# IMPORTANT:
# Bronze contains the business columns followed by:
#
# source_file
# source_system
# ingestion_timestamp
# batch_id
# ingestion_date
# record_hash
#
# source_system MUST be present here.
# ---------------------------------------------------------

orders_schema = StructType([

    # -------------------------
    # Business columns
    # -------------------------

    StructField("order_id", StringType(), True),
    StructField("customer_id", StringType(), True),
    StructField("store_id", StringType(), True),
    StructField("order_timestamp", StringType(), True),
    StructField("order_status", StringType(), True),
    StructField("total_amount", DoubleType(), True),
    StructField("payment_method", StringType(), True),
    StructField("delivery_type", StringType(), True),

    # -------------------------
    # Bronze metadata
    # -------------------------

    StructField("source_file", StringType(), True),
    StructField("source_system", StringType(), True),
    StructField("ingestion_timestamp", StringType(), True),
    StructField("batch_id", StringType(), True),
    StructField("ingestion_date", StringType(), True),
    StructField("record_hash", StringType(), True),
])


# ---------------------------------------------------------
# Read Bronze
# ---------------------------------------------------------

df = (
    spark.read
    .option("header", True)
    .schema(orders_schema)
    .csv(SOURCE_FILE)
)

bronze_count = df.count()

print(f"\nBronze record count: {bronze_count}")


# ---------------------------------------------------------
# Clean string columns
# ---------------------------------------------------------

string_columns = [
    "order_id",
    "customer_id",
    "store_id",
    "order_status",
    "payment_method",
    "delivery_type",
    "source_file",
    "source_system",
    "batch_id",
    "record_hash",
]

for column_name in string_columns:
    df = df.withColumn(
        column_name,
        trim(col(column_name))
    )


# ---------------------------------------------------------
# Standardize categorical values
# ---------------------------------------------------------

df_clean = (
    df
    .withColumn(
        "order_status",
        initcap(col("order_status"))
    )
    .withColumn(
        "payment_method",
        initcap(col("payment_method"))
    )
    .withColumn(
        "delivery_type",
        initcap(col("delivery_type"))
    )
)


# ---------------------------------------------------------
# Convert order timestamp
# ---------------------------------------------------------
#
# Invalid timestamps become NULL and are quarantined
# instead of crashing the pipeline.
# ---------------------------------------------------------

df_clean = df_clean.withColumn(
    "order_timestamp",
    try_to_timestamp(
        col("order_timestamp"),
        lit("yyyy-MM-dd HH:mm:ss")
    )
)


# ---------------------------------------------------------
# Convert metadata timestamps / dates
# ---------------------------------------------------------

df_clean = (
    df_clean

    # Bronze metadata timestamp
    .withColumn(
        "ingestion_timestamp",
        try_to_timestamp(
            col("ingestion_timestamp"),
            lit("yyyy-MM-dd HH:mm:ss.SSSSSS")
        )
    )

    # Bronze ingestion date
    .withColumn(
        "ingestion_date",
        col("ingestion_date").cast("date")
    )
)


# ---------------------------------------------------------
# Define allowed values
# ---------------------------------------------------------

valid_statuses = [
    "Placed",
    "Confirmed",
    "Preparing",
    "Out For Delivery",
    "Delivered",
    "Cancelled",
]

valid_payment_methods = [
    "UPI",
    "Credit Card",
    "Debit Card",
    "Cash",
    "Wallet",
]

valid_delivery_types = [
    "Standard",
    "Express",
]


# ---------------------------------------------------------
# Build validation reason
# ---------------------------------------------------------

df_validated = (
    df_clean

    .withColumn(
        "validation_error",

        when(
            col("order_id").isNull()
            | (col("order_id") == ""),
            lit("Missing order_id")
        )

        .when(
            col("customer_id").isNull()
            | (col("customer_id") == ""),
            lit("Missing customer_id")
        )

        .when(
            col("store_id").isNull()
            | (col("store_id") == ""),
            lit("Missing store_id")
        )

        .when(
            col("order_timestamp").isNull(),
            lit("Invalid order_timestamp")
        )

        .when(
            col("total_amount").isNull(),
            lit("Missing total_amount")
        )

        .when(
            col("total_amount") <= 0,
            lit("Invalid total_amount")
        )

        .when(
            col("order_status").isNull()
            | (~col("order_status").isin(valid_statuses)),
            lit("Invalid order_status")
        )

        .when(
            col("payment_method").isNull()
            | (~col("payment_method").isin(valid_payment_methods)),
            lit("Invalid payment_method")
        )

        .when(
            col("delivery_type").isNull()
            | (~col("delivery_type").isin(valid_delivery_types)),
            lit("Invalid delivery_type")
        )

        .when(
            col("source_file").isNull()
            | (col("source_file") == ""),
            lit("Missing source_file")
        )

        .when(
            col("source_system").isNull()
            | (col("source_system") == ""),
            lit("Missing source_system")
        )

        .when(
            col("ingestion_timestamp").isNull(),
            lit("Invalid ingestion_timestamp")
        )

        .when(
            col("ingestion_date").isNull(),
            lit("Invalid ingestion_date")
        )
    )
)


# ---------------------------------------------------------
# Separate valid and invalid records
# ---------------------------------------------------------

df_invalid = df_validated.filter(
    col("validation_error").isNotNull()
)

df_valid = df_validated.filter(
    col("validation_error").isNull()
)


# ---------------------------------------------------------
# Detect duplicate orders
# ---------------------------------------------------------

duplicate_window = (
    Window
    .partitionBy("order_id")
    .orderBy(
        col("ingestion_timestamp").asc()
    )
)

df_with_duplicate_number = (
    df_valid
    .withColumn(
        "duplicate_number",
        row_number().over(duplicate_window)
    )
)


# ---------------------------------------------------------
# Keep first occurrence
# ---------------------------------------------------------

df_valid = (
    df_with_duplicate_number
    .filter(col("duplicate_number") == 1)
    .drop("duplicate_number")
)


# ---------------------------------------------------------
# Send additional duplicate occurrences to quarantine
# ---------------------------------------------------------

df_duplicates = (
    df_with_duplicate_number
    .filter(col("duplicate_number") > 1)
    .drop("duplicate_number")
    .withColumn(
        "validation_error",
        lit("Duplicate order_id")
    )
)


# ---------------------------------------------------------
# Add duplicate records to quarantine
# ---------------------------------------------------------

df_invalid = df_invalid.unionByName(
    df_duplicates,
    allowMissingColumns=True
)


# ---------------------------------------------------------
# Remove validation helper column from Silver
# ---------------------------------------------------------

df_valid = df_valid.drop("validation_error")


# ---------------------------------------------------------
# Final Silver column order
# ---------------------------------------------------------

silver_columns = [

    # Business columns
    "order_id",
    "customer_id",
    "store_id",
    "order_timestamp",
    "order_status",
    "total_amount",
    "payment_method",
    "delivery_type",

    # Lineage metadata
    "source_file",
    "source_system",
    "ingestion_timestamp",
    "batch_id",
    "ingestion_date",
    "record_hash",
]

df_valid = df_valid.select(
    silver_columns
)


# =========================================================
# REUSABLE DATA QUALITY CHECKS
# =========================================================

print("\n" + "=" * 70)
print("DATA QUALITY CHECKS - SILVER ORDERS")
print("=" * 70)


# ---------------------------------------------------------
# 1. NULL check
# ---------------------------------------------------------

null_customer_ids = check_not_null(
    df_valid,
    "customer_id"
)


# ---------------------------------------------------------
# 2. Uniqueness check
# ---------------------------------------------------------

duplicate_order_ids = check_unique(
    df_valid,
    "order_id"
)


# ---------------------------------------------------------
# 3. Range check
# ---------------------------------------------------------

invalid_amounts = check_range(
    df_valid,
    "total_amount",
    minimum=0
)


# ---------------------------------------------------------
# 4. Allowed-value check
# ---------------------------------------------------------

invalid_statuses = check_allowed_values(
    df_valid,
    "order_status",
    valid_statuses
)


# ---------------------------------------------------------
# Display reusable DQ results
# ---------------------------------------------------------

print(
    f"NULL customer_id records : {null_customer_ids}"
)

print(
    f"Duplicate order_id values : {duplicate_order_ids}"
)

print(
    f"Invalid total_amount      : {invalid_amounts}"
)

print(
    f"Invalid order_status      : {invalid_statuses}"
)


# ---------------------------------------------------------
# Prepare output directories
# ---------------------------------------------------------

if os.path.exists(SILVER_PATH):
    shutil.rmtree(SILVER_PATH)

if os.path.exists(QUARANTINE_PATH):
    shutil.rmtree(QUARANTINE_PATH)

os.makedirs(SILVER_PATH, exist_ok=True)
os.makedirs(QUARANTINE_PATH, exist_ok=True)


# ---------------------------------------------------------
# Write Silver CSV
# ---------------------------------------------------------

silver_pdf = df_valid.toPandas()

silver_pdf.to_csv(
    SILVER_FILE,
    index=False
)


# ---------------------------------------------------------
# Write Quarantine CSV
# ---------------------------------------------------------

invalid_pdf = df_invalid.toPandas()

invalid_pdf.to_csv(
    QUARANTINE_FILE,
    index=False
)


# =========================================================
# FINAL QUALITY METRICS
# =========================================================

silver_count = len(silver_pdf)
quarantine_count = len(invalid_pdf)

print("\n" + "=" * 70)
print("SILVER DATA QUALITY REPORT")
print("=" * 70)

print(f"Bronze records       : {bronze_count}")
print(f"Valid Silver records : {silver_count}")
print(f"Quarantine records   : {quarantine_count}")

print(
    f"Records accounted for: "
    f"{silver_count + quarantine_count}"
)


# ---------------------------------------------------------
# Reconciliation check
# ---------------------------------------------------------

if silver_count + quarantine_count == bronze_count:
    print("Record reconciliation: PASSED")
else:
    print("Record reconciliation: FAILED")


# =========================================================
# REUSABLE QUALITY REPORT
# =========================================================

quality_report = create_quality_report(
    dataset_name="orders",
    total_records=bronze_count,
    invalid_records=quarantine_count,
    duplicate_records=duplicate_order_ids,
    null_records=null_customer_ids,
)

print("\nReusable Quality Report:")

for key, value in quality_report.items():
    print(f"{key}: {value}")


# ---------------------------------------------------------
# Show quarantine records
# ---------------------------------------------------------

print("\nQuarantined records:")

(
    df_invalid
    .select(
        "order_id",
        "customer_id",
        "store_id",
        "order_timestamp",
        "total_amount",
        "validation_error",
    )
    .show(20, truncate=False)
)


# ---------------------------------------------------------
# Show Silver sample
# ---------------------------------------------------------

print("\nSilver sample:")

(
    df_valid
    .select(
        "order_id",
        "customer_id",
        "store_id",
        "order_timestamp",
        "order_status",
        "total_amount",
        "source_system",
        "ingestion_timestamp",
        "batch_id",
    )
    .show(5, truncate=False)
)


# ---------------------------------------------------------
# Stop Spark
# ---------------------------------------------------------

spark.stop()

print("\n" + "=" * 70)
print("ORDERS SILVER PIPELINE COMPLETED")
print("=" * 70)