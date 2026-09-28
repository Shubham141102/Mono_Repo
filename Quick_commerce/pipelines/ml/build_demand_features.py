
import os
import sys
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from pyspark.sql import SparkSession, functions as F


# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

GOLD = ROOT / "data" / "gold"
ML = ROOT / "data" / "ml"

ML.mkdir(parents=True, exist_ok=True)


# =========================================================
# SPARK SESSION
# =========================================================

spark = (
    SparkSession.builder
    .appName("Build_Product_Store_Demand_Features")
    .master("local[4]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# =========================================================
# HELPER
# =========================================================

def read_gold(name):
    path = GOLD / name / "data.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Gold dataset not found: {path}"
        )

    return (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(str(path))
    )


# =========================================================
# START
# =========================================================

print("=" * 65)
print("BUILDING PRODUCT-STORE DEMAND FEATURES")
print("=" * 65)


# =========================================================
# READ GOLD TABLES
# =========================================================

orders = read_gold("fact_orders")

order_items = read_gold("fact_order_items")


print(f"Orders       : {orders.count()}")
print(f"Order Items  : {order_items.count()}")


# =========================================================
# KEEP DELIVERED ORDERS ONLY
# =========================================================

valid_store_condition = F.col("store_id").rlike("^STORE[0-9]{3}$")

delivered_orders = (
    orders
    .filter(
        (F.col("order_status") == "Delivered") &
        valid_store_condition
    )
)


print(
    f"Delivered Orders : {delivered_orders.count()}"
)


# =========================================================
# SELECT REQUIRED ORDER COLUMNS
# =========================================================

delivered_orders = delivered_orders.select(
    "order_id",
    "store_id",
    "order_timestamp"
)


# =========================================================
# PREPARE ORDER ITEMS
# =========================================================

order_items = order_items.select(
    "order_item_id",
    "order_id",
    "product_id",
    "quantity",
    "unit_price",
    "discount",
    "line_total"
)


# =========================================================
# JOIN ORDERS + ORDER ITEMS
# =========================================================

order_data = (
    delivered_orders
    .join(
        order_items,
        on="order_id",
        how="inner"
    )
)


print(
    f"Delivered Order Items : {order_data.count()}"
)


# =========================================================
# CREATE SALES DATE
# =========================================================

order_data = order_data.withColumn(
    "sales_date",
    F.to_date("order_timestamp")
)


# =========================================================
# STANDARDIZE NUMERIC COLUMNS
# =========================================================

order_data = (
    order_data
    .withColumn(
        "quantity",
        F.col("quantity").cast("double")
    )
    .withColumn(
        "line_total",
        F.col("line_total").cast("double")
    )
)


# =========================================================
# AGGREGATE TO PRODUCT × STORE × DAY
# =========================================================

demand_features = (
    order_data
    .groupBy(
        "sales_date",
        "store_id",
        "product_id"
    )
    .agg(
        F.sum("quantity").alias(
            "daily_quantity"
        ),

        F.sum("line_total").alias(
            "daily_revenue"
        ),

        F.countDistinct("order_id").alias(
            "daily_orders"
        ),

        F.avg("unit_price").alias(
            "average_unit_price"
        ),

        F.sum("discount").alias(
            "daily_discount"
        )
    )
)


# =========================================================
# SORT
# =========================================================

demand_features = demand_features.orderBy(
    "sales_date",
    "store_id",
    "product_id"
)


# =========================================================
# CONVERT TO PANDAS
# =========================================================

demand_pdf = demand_features.toPandas()


# =========================================================
# SAVE
# =========================================================

output_path = (
    ML / "product_store_daily_demand"
)

output_path.mkdir(
    parents=True,
    exist_ok=True
)


demand_pdf.to_csv(
    output_path / "data.csv",
    index=False
)


# =========================================================
# SUMMARY
# =========================================================

print()
print("=" * 65)
print("PRODUCT-STORE DEMAND DATASET")
print("=" * 65)

print(
    f"Rows              : {len(demand_pdf)}"
)

print(
    f"Unique Stores     : "
    f"{demand_pdf['store_id'].nunique()}"
)

print(
    f"Unique Products   : "
    f"{demand_pdf['product_id'].nunique()}"
)

print(
    f"Date Range        : "
    f"{demand_pdf['sales_date'].min()} "
    f"to "
    f"{demand_pdf['sales_date'].max()}"
)

print(
    f"Total Quantity    : "
    f"{demand_pdf['daily_quantity'].sum():,.0f}"
)

print(
    f"Total Revenue     : "
    f"{demand_pdf['daily_revenue'].sum():,.2f}"
)

print()
print("SAMPLE DATA")
print("-" * 65)

print(
    demand_pdf.head(10).to_string(
        index=False
    )
)


print()
print("=" * 65)
print("DEMAND FEATURE BUILD COMPLETED")
print("=" * 65)


spark.stop()

