import os
import sys
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

import pandas as pd

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, to_timestamp, when, lower


ROOT = Path(__file__).resolve().parents[2]

BRONZE = ROOT / "data" / "bronze" / "customer_events_csv"
SILVER = ROOT / "data" / "silver" / "customer_events_csv"
QUARANTINE = ROOT / "data" / "quarantine" / "customer_events_csv"

CUSTOMERS = ROOT / "data" / "silver" / "customers_csv"
PRODUCTS = ROOT / "data" / "silver" / "products_csv"
STORES = ROOT / "data" / "silver" / "stores_csv"


spark = (
    SparkSession.builder
    .appName("Silver_Customer_Events")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


def read_csv(path):
    files = list(path.glob("*.csv"))

    if not files:
        raise FileNotFoundError(f"No CSV found: {path}")

    pdf = pd.concat(
        [pd.read_csv(f) for f in files],
        ignore_index=True
    )

    return spark.createDataFrame(pdf)


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
    .withColumn("event_id", trim(col("event_id")))
    .withColumn("customer_id", trim(col("customer_id")))
    .withColumn(
        "event_timestamp",
        to_timestamp(col("event_timestamp"))
    )
    .withColumn("event_type", lower(trim(col("event_type"))))
    .withColumn(
        "product_id",
        when(
            trim(col("product_id")) == "",
            None
        ).otherwise(trim(col("product_id")))
    )
    .withColumn(
        "store_id",
        when(
            trim(col("store_id")) == "",
            None
        ).otherwise(trim(col("store_id")))
    )
    .withColumn("session_id", trim(col("session_id")))
    .withColumn("device_type", lower(trim(col("device_type"))))
)


# ---------------------------------------------------------
# 3. REFERENCE DATA
# ---------------------------------------------------------
customers = (
    read_csv(CUSTOMERS)
    .select("customer_id")
    .dropDuplicates()
)

products = (
    read_csv(PRODUCTS)
    .select("product_id")
    .dropDuplicates()
)

stores = (
    read_csv(STORES)
    .select("store_id")
    .dropDuplicates()
)


# ---------------------------------------------------------
# 4. FK VALIDATION
# ---------------------------------------------------------
df = (
    df
    .join(
        customers.withColumn("valid_customer", col("customer_id")),
        "customer_id",
        "left"
    )
    .join(
        products.withColumn("valid_product", col("product_id")),
        "product_id",
        "left"
    )
    .join(
        stores.withColumn("valid_store", col("store_id")),
        "store_id",
        "left"
    )
)


# ---------------------------------------------------------
# 5. BUSINESS RULES
# ---------------------------------------------------------
allowed_events = [
    "app_open",
    "search",
    "product_view",
    "add_to_cart",
    "remove_from_cart",
    "purchase"
]

allowed_devices = [
    "android",
    "ios",
    "web"
]

product_events = [
    "product_view",
    "add_to_cart",
    "remove_from_cart",
    "purchase"
]


df = df.withColumn(
    "is_invalid",
    col("event_id").isNull()
    | col("customer_id").isNull()
    | col("valid_customer").isNull()
    | col("event_timestamp").isNull()
    | (~col("event_type").isin(allowed_events))
    | col("session_id").isNull()
    | (~col("device_type").isin(allowed_devices))

    # Product/store required for product-related events
    | (
        col("event_type").isin(product_events)
        & (
            col("product_id").isNull()
            | col("valid_product").isNull()
            | col("store_id").isNull()
            | col("valid_store").isNull()
        )
    )
)


# ---------------------------------------------------------
# 6. QUARANTINE
# ---------------------------------------------------------
quarantine = (
    df
    .filter(col("is_invalid"))
    .drop(
        "valid_customer",
        "valid_product",
        "valid_store",
        "is_invalid"
    )
)


# ---------------------------------------------------------
# 7. VALID RECORDS
# ---------------------------------------------------------
valid = (
    df
    .filter(~col("is_invalid"))
    .drop(
        "valid_customer",
        "valid_product",
        "valid_store",
        "is_invalid"
    )
)


# ---------------------------------------------------------
# 8. DEDUPLICATION
# ---------------------------------------------------------
duplicate_count = (
    valid
    .groupBy("event_id")
    .count()
    .filter(col("count") > 1)
    .count()
)

silver = valid.dropDuplicates(["event_id"])


# ---------------------------------------------------------
# 9. QUALITY CHECKS
# ---------------------------------------------------------
silver_count = silver.count()
quarantine_count = quarantine.count()

null_event_id = (
    silver.filter(col("event_id").isNull()).count()
)

duplicate_event_id = (
    silver
    .groupBy("event_id")
    .count()
    .filter(col("count") > 1)
    .count()
)

quality_score = (
    silver_count / bronze_count * 100
    if bronze_count else 0
)

reconciliation = (
    bronze_count ==
    silver_count + quarantine_count
)


# ---------------------------------------------------------
# 10. SAVE
# ---------------------------------------------------------
save_csv(silver, SILVER)
save_csv(quarantine, QUARANTINE)


# ---------------------------------------------------------
# 11. RESULTS
# ---------------------------------------------------------
print()
print("=" * 60)
print("CUSTOMER EVENTS SILVER RESULTS")
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
print(f"NULL event_id       : {null_event_id}")
print(f"Duplicate event_id  : {duplicate_event_id}")
print(f"Duplicate records   : {duplicate_count}")

print()
print("QUALITY REPORT")
print(f"total_records: {bronze_count}")
print(f"valid_records: {silver_count}")
print(f"invalid_records: {quarantine_count}")
print(f"duplicate_records: {duplicate_count}")
print(f"null_records: {null_event_id}")
print(f"quality_score: {round(quality_score, 2)}")

print()
silver.show(5, truncate=False)


# ---------------------------------------------------------
# 12. FINAL VALIDATION
# ---------------------------------------------------------
if not reconciliation:
    raise Exception("Reconciliation FAILED")

if null_event_id != 0:
    raise Exception("NULL event_id found")

if duplicate_event_id != 0:
    raise Exception("Duplicate event_id found")

print()
print("SUCCESS: Customer Events Silver pipeline completed.")

spark.stop()

