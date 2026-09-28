import os
import sys
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

import pandas as pd

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    trim,
    to_date,
    to_timestamp,
    abs as spark_abs
)

ROOT = Path(__file__).resolve().parents[2]

BRONZE = ROOT / "data" / "bronze" / "inventory_csv"
SILVER = ROOT / "data" / "silver" / "inventory_csv"
QUARANTINE = ROOT / "data" / "quarantine" / "inventory_csv"

STORES = ROOT / "data" / "silver" / "stores_csv"
PRODUCTS = ROOT / "data" / "silver" / "products_csv"


spark = (
    SparkSession.builder
    .appName("Silver_Inventory")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


def read_csv(path):
    files = list(path.glob("*.csv"))

    if not files:
        raise FileNotFoundError(
            f"No CSV file found in: {path}"
        )

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
# 2. TYPE CONVERSION + STANDARDIZATION
# ---------------------------------------------------------
df = (
    bronze
    .withColumn("inventory_id", trim(col("inventory_id")))
    .withColumn("store_id", trim(col("store_id")))
    .withColumn("product_id", trim(col("product_id")))

    .withColumn(
        "quantity_on_hand",
        col("quantity_on_hand").cast("integer")
    )

    .withColumn(
        "reorder_level",
        col("reorder_level").cast("integer")
    )

    .withColumn(
        "unit_cost",
        col("unit_cost").cast("double")
    )

    .withColumn(
        "inventory_value",
        col("inventory_value").cast("double")
    )

    .withColumn(
        "last_restocked",
        to_date(col("last_restocked"))
    )

    .withColumn(
        "updated_at",
        to_timestamp(col("updated_at"))
    )
)


# ---------------------------------------------------------
# 3. FOREIGN KEY VALIDATION
# ---------------------------------------------------------
stores = (
    read_csv(STORES)
    .select("store_id")
    .dropDuplicates()
)

products = (
    read_csv(PRODUCTS)
    .select("product_id")
    .dropDuplicates()
)

invalid_store = (
    df.join(
        stores,
        "store_id",
        "left_anti"
    )
    .select("inventory_id")
)

invalid_product = (
    df.join(
        products,
        "product_id",
        "left_anti"
    )
    .select("inventory_id")
)


# ---------------------------------------------------------
# 4. BUSINESS VALIDATION
# ---------------------------------------------------------
df = (
    df
    .join(
        invalid_store
        .withColumn("bad_store", col("inventory_id")),
        "inventory_id",
        "left"
    )
    .join(
        invalid_product
        .withColumn("bad_product", col("inventory_id")),
        "inventory_id",
        "left"
    )
)


expected_value = (
    col("quantity_on_hand") * col("unit_cost")
)


df = df.withColumn(
    "is_invalid",
    col("inventory_id").isNull()
    | col("store_id").isNull()
    | col("product_id").isNull()
    | col("quantity_on_hand").isNull()
    | (col("quantity_on_hand") < 0)
    | col("reorder_level").isNull()
    | (col("reorder_level") < 0)
    | col("unit_cost").isNull()
    | (col("unit_cost") <= 0)
    | col("inventory_value").isNull()
    | (col("inventory_value") < 0)
    | col("last_restocked").isNull()
    | col("updated_at").isNull()
    | (
        spark_abs(
            col("inventory_value") - expected_value
        ) > 0.01
    )
    | col("bad_store").isNotNull()
    | col("bad_product").isNotNull()
)


# ---------------------------------------------------------
# 5. QUARANTINE
# ---------------------------------------------------------
quarantine = (
    df
    .filter(col("is_invalid"))
    .drop(
        "bad_store",
        "bad_product",
        "is_invalid"
    )
)


# ---------------------------------------------------------
# 6. VALID RECORDS
# ---------------------------------------------------------
valid = (
    df
    .filter(~col("is_invalid"))
    .drop(
        "bad_store",
        "bad_product",
        "is_invalid"
    )
)


# ---------------------------------------------------------
# 7. DUPLICATE BUSINESS KEY
#
# One product at one store = one inventory record
# ---------------------------------------------------------
duplicate_count = (
    valid
    .groupBy("store_id", "product_id")
    .count()
    .filter(col("count") > 1)
    .count()
)

silver = (
    valid
    .dropDuplicates(
        ["store_id", "product_id"]
    )
)


# ---------------------------------------------------------
# 8. COUNTS
# ---------------------------------------------------------
silver_count = silver.count()
quarantine_count = quarantine.count()

null_inventory_id = (
    silver
    .filter(col("inventory_id").isNull())
    .count()
)

duplicate_business_key = (
    silver
    .groupBy("store_id", "product_id")
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
print("INVENTORY SILVER RESULTS")
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

print(
    f"NULL inventory_id       : "
    f"{null_inventory_id}"
)

print(
    f"Duplicate store/product : "
    f"{duplicate_business_key}"
)

print(
    f"Duplicate records found : "
    f"{duplicate_count}"
)

print()
print("QUALITY REPORT")

print("dataset: inventory")
print(f"total_records: {bronze_count}")
print(f"valid_records: {silver_count}")
print(f"invalid_records: {quarantine_count}")
print(f"duplicate_records: {duplicate_count}")
print(f"null_records: {null_inventory_id}")
print(
    f"quality_score: "
    f"{round(quality_score, 2)}"
)

print()
print("SAMPLE SILVER DATA")

silver.show(
    5,
    truncate=False
)


# ---------------------------------------------------------
# 12. FINAL CHECKS
# ---------------------------------------------------------
if not reconciliation:
    raise Exception(
        "Reconciliation FAILED"
    )

if null_inventory_id != 0:
    raise Exception(
        "NULL inventory_id found"
    )

if duplicate_business_key != 0:
    raise Exception(
        "Duplicate store/product inventory key found"
    )

print()
print(
    "SUCCESS: Inventory Silver pipeline completed."
)

spark.stop()

