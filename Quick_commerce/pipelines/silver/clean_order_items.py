import os
import sys
from pathlib import Path

# ---------------------------------------------------------
# Windows + PySpark configuration
# ---------------------------------------------------------
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

import pandas as pd

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    trim,
    abs as spark_abs,
    lit,
    when,
    row_number,
)
from pyspark.sql.window import Window

# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

BRONZE_PATH = PROJECT_ROOT / "data" / "bronze" / "order_items_csv"
SILVER_PATH = PROJECT_ROOT / "data" / "silver" / "order_items"
QUARANTINE_PATH = PROJECT_ROOT / "data" / "quarantine" / "order_items"

ORDERS_SILVER_PATH = PROJECT_ROOT / "data" / "silver" / "orders_csv"
PRODUCTS_SILVER_PATH = PROJECT_ROOT / "data" / "silver" / "products_csv"


# ---------------------------------------------------------
# Spark
# ---------------------------------------------------------
spark = (
    SparkSession.builder
    .appName("Silver_Order_Items")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ---------------------------------------------------------
# Windows-safe CSV reader
# ---------------------------------------------------------
def read_csv_as_spark(path):
    """
    Read CSV using Pandas/native filesystem first,
    then convert to Spark DataFrame.

    This avoids Spark/Hadoop local filesystem
    directory access problems on Windows.
    """

    csv_files = list(path.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV file found in: {path}"
        )

    pandas_df = pd.concat(
        [
            pd.read_csv(file)
            for file in csv_files
        ],
        ignore_index=True
    )

    return spark.createDataFrame(pandas_df)


# ---------------------------------------------------------
# Save CSV using Pandas/native filesystem
# ---------------------------------------------------------
def save_csv(df, output_path):

    output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = output_path / "data.csv"

    df.toPandas().to_csv(
        output_file,
        index=False
    )

    return output_file


# ---------------------------------------------------------
# 1. Read Bronze
# ---------------------------------------------------------
bronze_df = read_csv_as_spark(
    BRONZE_PATH
)

bronze_count = bronze_df.count()

print(f"Bronze records: {bronze_count}")


# ---------------------------------------------------------
# 2. Apply explicit data types
# ---------------------------------------------------------
df = (
    bronze_df

    .withColumn(
        "order_item_id",
        trim(col("order_item_id"))
    )

    .withColumn(
        "order_id",
        trim(col("order_id"))
    )

    .withColumn(
        "product_id",
        trim(col("product_id"))
    )

    .withColumn(
        "quantity",
        col("quantity").cast("integer")
    )

    .withColumn(
        "unit_price",
        col("unit_price").cast("double")
    )

    .withColumn(
        "discount",
        col("discount").cast("double")
    )

    .withColumn(
        "line_total",
        col("line_total").cast("double")
    )
)


# ---------------------------------------------------------
# 3. Read Silver reference datasets
# ---------------------------------------------------------
orders_df = (
    read_csv_as_spark(ORDERS_SILVER_PATH)
    .select("order_id")
    .dropDuplicates()
)

products_df = (
    read_csv_as_spark(PRODUCTS_SILVER_PATH)
    .select("product_id")
    .dropDuplicates()
)


# ---------------------------------------------------------
# 4. Validate foreign keys
# ---------------------------------------------------------
#
# IMPORTANT:
# Keep only one validation flag per order_item_id.
# This prevents duplicate rows from multiplying during
# the later joins.
# ---------------------------------------------------------

invalid_order_refs = (
    df
    .join(
        orders_df,
        on="order_id",
        how="left_anti"
    )
    .select("order_item_id")
    .dropDuplicates(["order_item_id"])
    .withColumn(
        "invalid_order_reference",
        lit(True)
    )
)

invalid_product_refs = (
    df
    .join(
        products_df,
        on="product_id",
        how="left_anti"
    )
    .select("order_item_id")
    .dropDuplicates(["order_item_id"])
    .withColumn(
        "invalid_product_reference",
        lit(True)
    )
)
# ---------------------------------------------------------
# 5. Add validation flags
# ---------------------------------------------------------
df = (
    df

    .join(
        invalid_order_refs,
        on="order_item_id",
        how="left"
    )

    .join(
        invalid_product_refs,
        on="order_item_id",
        how="left"
    )

    .withColumn(
        "invalid_order_reference",
        when(
            col("invalid_order_reference").isNull(),
            False
        ).otherwise(
            col("invalid_order_reference")
        )
    )

    .withColumn(
        "invalid_product_reference",
        when(
            col("invalid_product_reference").isNull(),
            False
        ).otherwise(
            col("invalid_product_reference")
        )
    )
)


# ---------------------------------------------------------
# 6. Business validation rules
# ---------------------------------------------------------
expected_line_total = (
    col("quantity") * col("unit_price")
    - col("discount")
)

invalid_basic = (
    col("order_item_id").isNull()
    | col("order_id").isNull()
    | col("product_id").isNull()
    | col("quantity").isNull()
    | (col("quantity") <= 0)
    | col("unit_price").isNull()
    | (col("unit_price") <= 0)
    | col("discount").isNull()
    | (col("discount") < 0)
    | col("line_total").isNull()
    | (col("line_total") < 0)
)

invalid_line_total = (
    spark_abs(
        col("line_total")
        - expected_line_total
    ) > 0.01
)


# ---------------------------------------------------------
# 7. Mark invalid records
# ---------------------------------------------------------
df = df.withColumn(
    "is_invalid",
    invalid_basic
    | invalid_line_total
    | col("invalid_order_reference")
    | col("invalid_product_reference")
)


# ---------------------------------------------------------
# 8. Detect duplicates BEFORE separating final outputs
# ---------------------------------------------------------

duplicate_window = (
    Window
    .partitionBy("order_item_id")
    .orderBy(col("order_item_id"))
)

df_with_duplicate_number = (
    df
    .withColumn(
        "duplicate_number",
        row_number().over(duplicate_window)
    )
)


# ---------------------------------------------------------
# 9. Separate invalid records
# ---------------------------------------------------------

invalid_df = (
    df_with_duplicate_number
    .filter(col("is_invalid"))
)


# ---------------------------------------------------------
# 10. Separate valid records
# ---------------------------------------------------------

valid_df = (
    df_with_duplicate_number
    .filter(~col("is_invalid"))
)


# ---------------------------------------------------------
# 11. Separate duplicate valid records
# ---------------------------------------------------------
#
# First occurrence  -> Silver
# Additional copies -> Quarantine
# ---------------------------------------------------------

duplicate_valid_df = (
    valid_df
    .filter(col("duplicate_number") > 1)
    .withColumn(
        "validation_error",
        lit("Duplicate order_item_id")
    )
)


# ---------------------------------------------------------
# 12. Keep first valid occurrence in Silver
# ---------------------------------------------------------

silver_df = (
    valid_df
    .filter(col("duplicate_number") == 1)
)


# ---------------------------------------------------------
# 13. Add validation errors to invalid records
# ---------------------------------------------------------

invalid_df = (
    invalid_df
    .withColumn(
        "validation_error",
        when(
            col("invalid_order_reference"),
            lit("Invalid order reference")
        )
        .when(
            col("invalid_product_reference"),
            lit("Invalid product reference")
        )
        .when(
            col("quantity").isNull() | (col("quantity") <= 0),
            lit("Invalid quantity")
        )
        .when(
            col("unit_price").isNull() | (col("unit_price") <= 0),
            lit("Invalid unit_price")
        )
        .when(
            col("discount").isNull() | (col("discount") < 0),
            lit("Invalid discount")
        )
        .when(
            col("line_total").isNull() | (col("line_total") < 0),
            lit("Invalid line_total")
        )
        .when(
            invalid_line_total,
            lit("Invalid line_total calculation")
        )
        .otherwise(
            lit("Invalid record")
        )
    )
)


# ---------------------------------------------------------
# 14. Combine all quarantine records
# ---------------------------------------------------------
#
# Invalid records + duplicate occurrences
# ---------------------------------------------------------

quarantine_df = (
    invalid_df
    .unionByName(
        duplicate_valid_df,
        allowMissingColumns=True
    )
)


# ---------------------------------------------------------
# 15. Remove helper columns
# ---------------------------------------------------------

columns_to_drop = [
    "invalid_order_reference",
    "invalid_product_reference",
    "is_invalid",
    "duplicate_number",
]

silver_df = silver_df.drop(*columns_to_drop)

quarantine_df = quarantine_df.drop(*columns_to_drop)

# ---------------------------------------------------------
# 16. Counts
# ---------------------------------------------------------

silver_count = silver_df.count()
quarantine_count = quarantine_df.count()


# ---------------------------------------------------------
# 17. Data quality checks
# ---------------------------------------------------------

null_order_item_id = (
    silver_df
    .filter(col("order_item_id").isNull())
    .count()
)

duplicate_order_item_id = (
    silver_df
    .groupBy("order_item_id")
    .count()
    .filter(col("count") > 1)
    .count()
)


# ---------------------------------------------------------
# 18. Duplicate count
# ---------------------------------------------------------
#
# Count actual duplicate rows that are being quarantined,
# not merely the number of duplicate groups.
# ---------------------------------------------------------

duplicate_count = (
    duplicate_valid_df.count()
)


# ---------------------------------------------------------
# 19. Quality score
# ---------------------------------------------------------

quality_score = (
    (silver_count / bronze_count) * 100
    if bronze_count > 0
    else 0
)


# ---------------------------------------------------------
# 20. Reconciliation
# ---------------------------------------------------------

reconciliation = (
    bronze_count
    == silver_count + quarantine_count
)


# ---------------------------------------------------------
# 21. Save outputs
# ---------------------------------------------------------

save_csv(
    silver_df,
    SILVER_PATH
)

save_csv(
    quarantine_df,
    QUARANTINE_PATH
)


# ---------------------------------------------------------
# 22. Results
# ---------------------------------------------------------

print()
print("=" * 60)
print("ORDER ITEMS SILVER RESULTS")
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
    f"NULL order_item_id      : "
    f"{null_order_item_id}"
)

print(
    f"Duplicate order_item_id : "
    f"{duplicate_order_item_id}"
)

print(
    f"Duplicate records found : "
    f"{duplicate_count}"
)


print()
print("QUALITY REPORT")

print("dataset: order_items")
print(f"total_records: {bronze_count}")
print(f"valid_records: {silver_count}")
print(f"invalid_records: {quarantine_count}")
print(f"duplicate_records: {duplicate_count}")
print(f"null_records: {null_order_item_id}")

print(
    f"quality_score: "
    f"{round(quality_score, 2)}"
)


# ---------------------------------------------------------
# 23. Sample Silver data
# ---------------------------------------------------------

print()
print("SAMPLE SILVER DATA")

silver_df.show(
    5,
    truncate=False
)


# ---------------------------------------------------------
# 24. Final validation
# ---------------------------------------------------------

if not reconciliation:
    raise Exception(
        "Reconciliation FAILED: "
        "Bronze != Silver + Quarantine"
    )

if null_order_item_id != 0:
    raise Exception(
        "Data quality FAILED: "
        "NULL order_item_id found"
    )

if duplicate_order_item_id != 0:
    raise Exception(
        "Data quality FAILED: "
        "duplicate order_item_id found"
    )


print()
print(
    "SUCCESS: "
    "Order Items Silver pipeline completed."
)


# ---------------------------------------------------------
# Stop Spark
# ---------------------------------------------------------

spark.stop()

