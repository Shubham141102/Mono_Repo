import os
import sys
from pathlib import Path

# Windows + PySpark
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

import pandas as pd

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, to_timestamp, lower, initcap


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]

BRONZE = ROOT / "data" / "bronze" / "payments_csv"
SILVER = ROOT / "data" / "silver" / "payments_csv"
QUARANTINE = ROOT / "data" / "quarantine" / "payments_csv"

ORDERS = ROOT / "data" / "silver" / "orders_csv"


# ---------------------------------------------------------
# SPARK
# ---------------------------------------------------------
spark = (
    SparkSession.builder
    .appName("Silver_Payments")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ---------------------------------------------------------
# WINDOWS-SAFE CSV READER
# ---------------------------------------------------------
def read_csv(path):
    files = list(path.glob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No CSV file found in: {path}"
        )

    pdf = pd.concat(
        [pd.read_csv(file) for file in files],
        ignore_index=True
    )

    return spark.createDataFrame(pdf)


# ---------------------------------------------------------
# SAVE CSV
# ---------------------------------------------------------
def save_csv(df, path):
    path.mkdir(parents=True, exist_ok=True)

    df.toPandas().to_csv(
        path / "data.csv",
        index=False
    )


# ---------------------------------------------------------
# 1. READ BRONZE
# ---------------------------------------------------------
bronze = read_csv(BRONZE)

bronze_count = bronze.count()

print(f"Bronze records: {bronze_count}")


# ---------------------------------------------------------
# 2. CLEAN + TYPE CONVERSION
# ---------------------------------------------------------
df = (
    bronze

    .withColumn(
        "payment_id",
        trim(col("payment_id"))
    )

    .withColumn(
        "order_id",
        trim(col("order_id"))
    )

    .withColumn(
        "payment_timestamp",
        to_timestamp(col("payment_timestamp"))
    )

    .withColumn(
        "payment_method",
        initcap(trim(col("payment_method")))
    )

    .withColumn(
        "payment_status",
        lower(trim(col("payment_status")))
    )

    .withColumn(
        "amount",
        col("amount").cast("double")
    )

    .withColumn(
        "transaction_reference",
        trim(col("transaction_reference"))
    )
)


# ---------------------------------------------------------
# 3. VALIDATE ORDER FOREIGN KEY
# ---------------------------------------------------------
orders = (
    read_csv(ORDERS)
    .select("order_id")
    .dropDuplicates()
)

invalid_orders = (
    df
    .join(
        orders,
        on="order_id",
        how="left_anti"
    )
    .select("payment_id")
)


# ---------------------------------------------------------
# 4. VALIDATION RULES
# ---------------------------------------------------------
valid_methods = [
    "Upi",
    "Credit Card",
    "Debit Card",
    "Cash",
    "Wallet",
    "Cash On Delivery"
]

valid_statuses = [
    "success",
    "failed",
    "pending",
    "refunded"
]

df = (
    df
    .join(
        invalid_orders
        .withColumn("invalid_order", col("payment_id")),
        on="payment_id",
        how="left"
    )

    .withColumn(
        "is_invalid",
        col("payment_id").isNull()
        | col("order_id").isNull()
        | col("payment_timestamp").isNull()
        | col("payment_method").isNull()
        | col("payment_status").isNull()
        | col("amount").isNull()
        | (col("amount") <= 0)
        | col("transaction_reference").isNull()
        | (~col("payment_method").isin(valid_methods))
        | (~col("payment_status").isin(valid_statuses))
        | col("invalid_order").isNotNull()
    )
)


# ---------------------------------------------------------
# 5. QUARANTINE
# ---------------------------------------------------------
quarantine = (
    df
    .filter(col("is_invalid"))
    .drop("invalid_order", "is_invalid")
)


# ---------------------------------------------------------
# 6. VALID SILVER
# ---------------------------------------------------------
valid = (
    df
    .filter(~col("is_invalid"))
    .drop("invalid_order", "is_invalid")
)


# ---------------------------------------------------------
# 7. DUPLICATES
# ---------------------------------------------------------
duplicate_count = (
    valid
    .groupBy("payment_id")
    .count()
    .filter(col("count") > 1)
    .count()
)

silver = valid.dropDuplicates(["payment_id"])


# ---------------------------------------------------------
# 8. COUNTS
# ---------------------------------------------------------
silver_count = silver.count()
quarantine_count = quarantine.count()

null_payment_id = (
    silver
    .filter(col("payment_id").isNull())
    .count()
)

duplicate_payment_id = (
    silver
    .groupBy("payment_id")
    .count()
    .filter(col("count") > 1)
    .count()
)


# ---------------------------------------------------------
# 9. QUALITY
# ---------------------------------------------------------
quality_score = (
    silver_count / bronze_count * 100
    if bronze_count > 0
    else 0
)

reconciliation = (
    bronze_count
    == silver_count + quarantine_count
)


# ---------------------------------------------------------
# 10. SAVE
# ---------------------------------------------------------
save_csv(
    silver,
    SILVER
)

save_csv(
    quarantine,
    QUARANTINE
)


# ---------------------------------------------------------
# 11. RESULTS
# ---------------------------------------------------------
print()
print("=" * 60)
print("PAYMENTS SILVER RESULTS")
print("=" * 60)

print(f"Bronze        : {bronze_count}")
print(f"Silver        : {silver_count}")
print(f"Quarantine    : {quarantine_count}")

print(
    f"Reconciliation: "
    f"{'PASSED' if reconciliation else 'FAILED'}"
)

print()
print("DATA QUALITY")

print(f"NULL payment_id      : {null_payment_id}")
print(f"Duplicate payment_id : {duplicate_payment_id}")
print(f"Duplicate records    : {duplicate_count}")

print()
print("QUALITY REPORT")

print("dataset: payments")
print(f"total_records: {bronze_count}")
print(f"valid_records: {silver_count}")
print(f"invalid_records: {quarantine_count}")
print(f"duplicate_records: {duplicate_count}")
print(f"null_records: {null_payment_id}")
print(f"quality_score: {round(quality_score, 2)}")

print()
print("SAMPLE SILVER DATA")

print("Sample display skipped to avoid Spark driver memory issues.")


# ---------------------------------------------------------
# 12. FINAL CHECKS
# ---------------------------------------------------------
if not reconciliation:
    raise Exception(
        "Reconciliation FAILED"
    )

if null_payment_id != 0:
    raise Exception(
        "NULL payment_id found"
    )

if duplicate_payment_id != 0:
    raise Exception(
        "Duplicate payment_id found"
    )

print()
print(
    "SUCCESS: Payments Silver pipeline completed."
)

spark.stop()

