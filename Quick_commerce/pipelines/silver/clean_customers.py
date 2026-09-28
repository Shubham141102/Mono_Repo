import os
import sys
import shutil

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    BooleanType,
)
from pyspark.sql.functions import (
    col,
    trim,
    lower,
    initcap,
    lit,
    to_date,
    to_timestamp,
    when,
    row_number,
)
from pyspark.sql.window import Window


# ============================================================
# 1. PROJECT PATH + PYTHON CONFIGURATION
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Make sure Spark uses the same Python environment
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable


# Import reusable Data Quality functions
from quality.data_quality import (
    check_not_null,
    check_unique,
    check_allowed_values,
    create_quality_report,
)


# ============================================================
# 2. PATHS
# ============================================================

BRONZE_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "bronze",
    "customers_csv",
    "customers.csv",
)

SILVER_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "silver",
    "customers_csv",
)

SILVER_FILE = os.path.join(
    SILVER_PATH,
    "customers.csv",
)

QUARANTINE_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "quarantine",
    "customers_csv",
)

QUARANTINE_FILE = os.path.join(
    QUARANTINE_PATH,
    "customers.csv",
)


# ============================================================
# 3. CREATE SPARK SESSION
# ============================================================

spark = (
    SparkSession.builder
    .appName("CleanCustomersSilver")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

print("=" * 70)
print("CUSTOMERS - BRONZE TO SILVER")
print("=" * 70)


# ============================================================
# 4. EXPLICIT BRONZE SCHEMA
# ============================================================
#
# IMPORTANT:
# Bronze contains the original business columns PLUS
# ingestion metadata added by the Bronze pipeline.
#
# Correct metadata order:
#
# source_file
# source_system
# ingestion_timestamp
# batch_id
# ingestion_date
# record_hash
#
# ============================================================

customer_schema = StructType([
    # -------------------------
    # Business columns
    # -------------------------
    StructField("customer_id", StringType(), True),
    StructField("first_name", StringType(), True),
    StructField("last_name", StringType(), True),
    StructField("email", StringType(), True),
    StructField("phone", StringType(), True),
    StructField("city", StringType(), True),
    StructField("state", StringType(), True),
    StructField("signup_date", StringType(), True),
    StructField("customer_segment", StringType(), True),
    StructField("is_active", BooleanType(), True),

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


# ============================================================
# 5. READ BRONZE
# ============================================================

df = (
    spark.read
    .option("header", True)
    .schema(customer_schema)
    .csv(BRONZE_FILE)
)

bronze_count = df.count()

print(f"\nBronze records: {bronze_count}")


# ============================================================
# 6. STRING CLEANING
# ============================================================

string_columns = [
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "city",
    "state",
    "signup_date",
    "customer_segment",

    # Bronze metadata
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


# ============================================================
# 7. STANDARDIZE VALUES
# ============================================================

df = (
    df
    .withColumn("first_name", initcap(col("first_name")))
    .withColumn("last_name", initcap(col("last_name")))
    .withColumn("city", initcap(col("city")))
    .withColumn("state", initcap(col("state")))
    .withColumn("email", lower(col("email")))
    .withColumn(
        "customer_segment",
        initcap(col("customer_segment"))
    )
)


# ============================================================
# 8. CONVERT DATE / TIMESTAMP
# ============================================================

df = (
    df
    .withColumn(
        "signup_date",
        to_date(col("signup_date"), "yyyy-MM-dd")
    )
    .withColumn(
        "ingestion_timestamp",
        to_timestamp(col("ingestion_timestamp"))
    )
)


# ============================================================
# 9. VALIDATION RULES
# ============================================================

valid_segments = [
    "Standard",
    "Premium",
    "Vip",
]


validation_reason = (
    when(
        col("customer_id").isNull() |
        (col("customer_id") == ""),
        lit("Missing customer_id")
    )
    .when(
        col("first_name").isNull() |
        (col("first_name") == ""),
        lit("Missing first_name")
    )
    .when(
        col("last_name").isNull() |
        (col("last_name") == ""),
        lit("Missing last_name")
    )
    .when(
        col("email").isNull() |
        (col("email") == ""),
        lit("Missing email")
    )
    .when(
        ~col("email").rlike(
            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        ),
        lit("Invalid email")
    )
    .when(
        col("phone").isNull() |
        (col("phone") == ""),
        lit("Missing phone")
    )
    .when(
        ~col("phone").rlike(r"^[6-9][0-9]{9}$"),
        lit("Invalid phone")
    )
    .when(
        col("city").isNull() |
        (col("city") == ""),
        lit("Missing city")
    )
    .when(
        col("state").isNull() |
        (col("state") == ""),
        lit("Missing state")
    )
    .when(
        col("signup_date").isNull(),
        lit("Invalid signup_date")
    )
    .when(
        ~col("customer_segment").isin(valid_segments),
        lit("Invalid customer_segment")
    )
    .when(
        col("is_active").isNull(),
        lit("Missing is_active")
    )
)


# ============================================================
# 10. ADD VALIDATION RESULT
# ============================================================

df_validated = df.withColumn(
    "validation_reason",
    validation_reason
)

df_valid = df_validated.filter(
    col("validation_reason").isNull()
)

df_invalid = df_validated.filter(
    col("validation_reason").isNotNull()
)

invalid_before_dedup = df_invalid.count()


# ============================================================
# 11. DEDUPLICATION
# ============================================================

window_spec = (
    Window
    .partitionBy("customer_id")
    .orderBy(
        col("ingestion_timestamp").asc_nulls_last()
    )
)

df_ranked = (
    df_valid
    .withColumn(
        "row_number",
        row_number().over(window_spec)
    )
)

# Keep first occurrence
df_deduplicated = (
    df_ranked
    .filter(col("row_number") == 1)
    .drop("row_number")
)

# Find duplicate records that were removed
df_duplicates = (
    df_ranked
    .filter(col("row_number") > 1)
)


# ============================================================
# 12. ADD DUPLICATES TO QUARANTINE
# ============================================================

df_duplicates = df_duplicates.withColumn(
    "validation_reason",
    lit("Duplicate customer_id")
)

df_invalid_final = df_invalid.unionByName(
    df_duplicates.select(df_invalid.columns)
)


# ============================================================
# 13. FINAL SILVER COLUMNS
# ============================================================
#
# Keep business columns + complete Bronze lineage metadata.
#
# ============================================================

silver_columns = [
    # Business columns
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "city",
    "state",
    "signup_date",
    "customer_segment",
    "is_active",

    # Lineage / Bronze metadata
    "source_file",
    "source_system",
    "ingestion_timestamp",
    "batch_id",
    "ingestion_date",
    "record_hash",
]

df_silver = df_deduplicated.select(
    silver_columns
)

df_quarantine = df_invalid_final


# ============================================================
# 14. CREATE OUTPUT DIRECTORIES
# ============================================================

if os.path.exists(SILVER_PATH):
    shutil.rmtree(SILVER_PATH)

if os.path.exists(QUARANTINE_PATH):
    shutil.rmtree(QUARANTINE_PATH)

os.makedirs(SILVER_PATH, exist_ok=True)
os.makedirs(QUARANTINE_PATH, exist_ok=True)


# ============================================================
# 15. WRITE SILVER CSV
# ============================================================

silver_pdf = df_silver.toPandas()

silver_pdf.to_csv(
    SILVER_FILE,
    index=False
)


# ============================================================
# 16. WRITE QUARANTINE CSV
# ============================================================

quarantine_pdf = df_quarantine.toPandas()

quarantine_pdf.to_csv(
    QUARANTINE_FILE,
    index=False
)


# ============================================================
# 17. COUNTS + RECONCILIATION
# ============================================================

silver_count = len(silver_pdf)
quarantine_count = len(quarantine_pdf)

print("\n" + "=" * 70)
print("CUSTOMER SILVER RESULTS")
print("=" * 70)

print(f"Bronze records       : {bronze_count}")
print(f"Silver records       : {silver_count}")
print(f"Quarantine records   : {quarantine_count}")

print("\nReconciliation:")

if silver_count + quarantine_count == bronze_count:
    print("PASSED: Silver + Quarantine = Bronze")
else:
    print("FAILED: Record reconciliation mismatch")


# ============================================================
# 18. REUSABLE DATA QUALITY CHECKS
# ============================================================

null_customer_ids = check_not_null(
    df_silver,
    "customer_id"
)

duplicate_customer_ids = check_unique(
    df_silver,
    "customer_id"
)

invalid_segments = check_allowed_values(
    df_silver,
    "customer_segment",
    valid_segments
)


print("\n" + "=" * 70)
print("DATA QUALITY CHECKS")
print("=" * 70)

print(f"NULL customer_id       : {null_customer_ids}")
print(f"Duplicate customer_id  : {duplicate_customer_ids}")
print(f"Invalid segments       : {invalid_segments}")


# ============================================================
# 19. QUALITY REPORT
# ============================================================

quality_report = create_quality_report(
    dataset_name="customers",
    total_records=bronze_count,
    invalid_records=quarantine_count,
    duplicate_records=duplicate_customer_ids,
    null_records=null_customer_ids,
)

print("\n" + "=" * 70)
print("REUSABLE QUALITY REPORT")
print("=" * 70)

for key, value in quality_report.items():
    print(f"{key}: {value}")


# ============================================================
# 20. DISPLAY QUARANTINE RECORDS
# ============================================================

if quarantine_count > 0:

    print("\n" + "=" * 70)
    print("QUARANTINE SAMPLE")
    print("=" * 70)

    df_quarantine.select(
        "customer_id",
        "email",
        "phone",
        "customer_segment",
        "validation_reason"
    ).show(20, truncate=False)

else:

    print("\nNo invalid customer records found.")


# ============================================================
# 21. DISPLAY SILVER SAMPLE
# ============================================================

print("\n" + "=" * 70)
print("SILVER SAMPLE")
print("=" * 70)

df_silver.show(10, truncate=False)


# ============================================================
# 22. FILE VERIFICATION
# ============================================================

print("\n" + "=" * 70)
print("OUTPUT VERIFICATION")
print("=" * 70)

print(f"Silver file exists     : {os.path.exists(SILVER_FILE)}")
print(f"Quarantine file exists : {os.path.exists(QUARANTINE_FILE)}")

print("\nSilver file:")
print(SILVER_FILE)

print("\nQuarantine file:")
print(QUARANTINE_FILE)


# ============================================================
# 23. STOP SPARK
# ============================================================

spark.stop()

print("\n" + "=" * 70)
print("CUSTOMERS SILVER PIPELINE COMPLETED")
print("=" * 70)