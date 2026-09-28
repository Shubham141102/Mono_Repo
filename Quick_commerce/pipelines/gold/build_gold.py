import os
import sys
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

import pandas as pd

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.window import Window

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "data" / "gold"

spark = (
    SparkSession.builder
    .appName("Gold_Layer")
    .master("local[4]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# =========================================================
# HELPERS
# =========================================================

def read_csv(folder):
    files = list(folder.glob("*.csv"))

    if not files:
        raise FileNotFoundError(f"No CSV files: {folder}")

    pdf = pd.concat(
        [pd.read_csv(f) for f in files],
        ignore_index=True
    )

    return spark.createDataFrame(pdf)


def save(df, name):
    path = GOLD / name
    path.mkdir(parents=True, exist_ok=True)

    pdf = df.toPandas()

    pdf.to_csv(
        path / "data.csv",
        index=False
    )

    print(f"{name:<25} {len(pdf)} rows")

# =========================================================
# READ SILVER
# =========================================================

customers = read_csv(
    ROOT / "data" / "silver" / "customers_csv"
)

products = read_csv(
    ROOT / "data" / "silver" / "products_csv"
)

stores = read_csv(
    ROOT / "data" / "silver" / "stores_csv"
)

partners = read_csv(
    ROOT / "data" / "silver" / "delivery_partners_csv"
)

orders = read_csv(
    ROOT / "data" / "silver" / "orders_csv"
)

items = read_csv(
    ROOT / "data" / "silver" / "order_items"
)

inventory = read_csv(
    ROOT / "data" / "silver" / "inventory_csv"
)

payments = read_csv(
    ROOT / "data" / "silver" / "payments_csv"
)

delivery = read_csv(
    ROOT / "data" / "silver" / "delivery_events_csv"
)

customer_events = read_csv(
    ROOT / "data" / "silver" / "customer_events_csv"
)


# =========================================================
# BASIC TYPE CLEANUP
# =========================================================

orders = orders.withColumn(
    "order_timestamp",
    F.to_timestamp("order_timestamp")
)

items = (
    items
    .withColumn("quantity", F.col("quantity").cast("double"))
    .withColumn("unit_price", F.col("unit_price").cast("double"))
    .withColumn("discount", F.col("discount").cast("double"))
    .withColumn("line_total", F.col("line_total").cast("double"))
)

inventory = (
    inventory
    .withColumn(
        "quantity_on_hand",
        F.col("quantity_on_hand").cast("double")
    )
    .withColumn(
        "reorder_level",
        F.col("reorder_level").cast("double")
    )
    .withColumn(
        "unit_cost",
        F.col("unit_cost").cast("double")
    )
    .withColumn(
        "inventory_value",
        F.col("inventory_value").cast("double")
    )
)

delivery = delivery.withColumn(
    "event_timestamp",
    F.to_timestamp("event_timestamp")
)


# =========================================================
# 1. DIMENSIONS
# =========================================================

dim_customer = customers.select(
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "city",
    "state",
    "signup_date",
    "customer_segment",
    "is_active"
)

dim_product = products.select(
    "product_id",
    "product_name",
    "category",
    "subcategory",
    "brand",
    "unit_price",
    "cost_price",
    "unit",
    "is_active"
)

dim_store = stores.select(
    "store_id",
    "store_name",
    "city",
    "state",
    "pincode",
    "latitude",
    "longitude",
    "opened_date",
    "is_active"
)

dim_delivery_partner = partners.select(
    "partner_id",
    "first_name",
    "last_name",
    "phone",
    "city",
    "vehicle_type",
    "joining_date",
    "rating",
    "is_active"
)


# =========================================================
# 2. DATE DIMENSION
# =========================================================

date_range = (
    orders
    .select(F.to_date("order_timestamp").alias("date"))
    .filter(F.col("date").isNotNull())
    .distinct()
)

dim_date = (
    date_range
    .withColumn("year", F.year("date"))
    .withColumn("month", F.month("date"))
    .withColumn("month_name", F.date_format("date", "MMMM"))
    .withColumn("day", F.dayofmonth("date"))
    .withColumn("day_of_week", F.dayofweek("date"))
    .withColumn("day_name", F.date_format("date", "EEEE"))
    .withColumn("week_of_year", F.weekofyear("date"))
)


# =========================================================
# 3. FACT ORDERS
# =========================================================

fact_orders = (
    orders
    .select(
        "order_id",
        "customer_id",
        "store_id",
        "order_timestamp",
        "order_status",
        "total_amount",
        "payment_method",
        "delivery_type"
    )
)


# =========================================================
# 4. FACT ORDER ITEMS
# =========================================================

fact_order_items = (
    items
    .select(
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount",
        "line_total"
    )
)


# =========================================================
# 5. FACT DELIVERY
# =========================================================

delivery_summary = (
    delivery
    .groupBy("order_id", "partner_id")
    .agg(
        F.min(
            F.when(
                F.col("event_type") == "assigned",
                F.col("event_timestamp")
            )
        ).alias("assigned_at"),

        F.min(
            F.when(
                F.col("event_type") == "picked_up",
                F.col("event_timestamp")
            )
        ).alias("picked_up_at"),

        F.min(
            F.when(
                F.col("event_type") == "out_for_delivery",
                F.col("event_timestamp")
            )
        ).alias("out_for_delivery_at"),

        F.max(
            F.when(
                F.col("event_type") == "delivered",
                F.col("event_timestamp")
            )
        ).alias("delivered_at")
    )
    .withColumn(
        "delivery_minutes",
        (
            F.unix_timestamp("delivered_at")
            - F.unix_timestamp("assigned_at")
        ) / 60
    )
)

fact_delivery = delivery_summary


# =========================================================
# 6. FACT INVENTORY
# =========================================================

fact_inventory = (
    inventory
    .select(
        "inventory_id",
        "store_id",
        "product_id",
        "quantity_on_hand",
        "reorder_level",
        "unit_cost",
        "inventory_value",
        "last_restocked",
        "updated_at"
    )
)


# =========================================================
# 7. DAILY SALES
# =========================================================

delivered_orders = orders.filter(
    F.lower(F.col("order_status")) == "delivered"
)

sales_base = (
    items
    .join(
        delivered_orders.select(
            "order_id",
            "customer_id",
            "store_id",
            "order_timestamp"
        ),
        "order_id",
        "inner"
    )
)

daily_sales = (
    sales_base
    .withColumn(
        "date",
        F.to_date("order_timestamp")
    )
    .groupBy("date", "store_id")
    .agg(
        F.countDistinct("order_id").alias("total_orders"),
        F.sum("quantity").alias("total_items"),
        F.sum(
            F.col("quantity") * F.col("unit_price")
        ).alias("gross_revenue"),
        F.sum("discount").alias("discount_amount"),
        F.sum("line_total").alias("net_revenue")
    )
    .withColumn(
        "average_order_value",
        F.col("net_revenue") / F.col("total_orders")
    )
)


# =========================================================
# 8. PRODUCT PERFORMANCE
# =========================================================

product_performance = (
    sales_base
    .join(
        products.select(
            "product_id",
            "product_name",
            "category",
            "brand"
        ),
        "product_id"
    )
    .groupBy(
        "product_id",
        "product_name",
        "category",
        "brand"
    )
    .agg(
        F.sum("quantity").alias("total_units_sold"),
        F.sum("line_total").alias("total_revenue"),
        F.countDistinct("order_id").alias("total_orders"),
        F.avg("unit_price").alias("average_selling_price")
    )
)


# =========================================================
# 9. STORE PERFORMANCE
# =========================================================

store_performance = (
    sales_base
    .join(
        stores.select(
            "store_id",
            "store_name",
            "city"
        ),
        "store_id"
    )
    .groupBy(
        "store_id",
        "store_name",
        "city"
    )
    .agg(
        F.countDistinct("order_id").alias("total_orders"),
        F.countDistinct("customer_id").alias("unique_customers"),
        F.sum("quantity").alias("items_sold"),
        F.sum("line_total").alias("total_revenue")
    )
    .withColumn(
        "average_order_value",
        F.col("total_revenue") /
        F.col("total_orders")
    )
)


# =========================================================
# 10. CUSTOMER METRICS
# =========================================================

customer_metrics = (
    customers
    .join(
        delivered_orders.select(
            "order_id",
            "customer_id",
            "order_timestamp"
        ),
        "customer_id",
        "left"
    )
    .join(
        items.select(
            "order_id",
            "line_total",
            "quantity"
        ),
        "order_id",
        "left"
    )
    .groupBy(
        "customer_id"
    )
    .agg(
        F.countDistinct("order_id").alias("total_orders"),
        F.sum("line_total").alias("total_spend"),
        F.sum("quantity").alias("total_items"),
        F.max("order_timestamp").alias("last_order_date")
    )
    .withColumn(
        "average_order_value",
        F.when(
            F.col("total_orders") > 0,
            F.col("total_spend") /
            F.col("total_orders")
        ).otherwise(0)
    )
)


# =========================================================
# 11. INVENTORY METRICS
# =========================================================

inventory_metrics = (
    inventory
    .join(
        products.select(
            "product_id",
            "product_name",
            "category"
        ),
        "product_id"
    )
    .join(
        stores.select(
            "store_id",
            "store_name",
            "city"
        ),
        "store_id"
    )
    .withColumn(
        "stock_status",
        F.when(
            F.col("quantity_on_hand") == 0,
            "Out of Stock"
        )
        .when(
            F.col("quantity_on_hand")
            <= F.col("reorder_level"),
            "Low Stock"
        )
        .otherwise("Healthy Stock")
    )
    .select(
        "store_id",
        "store_name",
        "city",
        "product_id",
        "product_name",
        "category",
        "quantity_on_hand",
        "reorder_level",
        "unit_cost",
        "inventory_value",
        "stock_status",
        "last_restocked"
    )
)


# =========================================================
# 12. DELIVERY METRICS
# =========================================================

delivery_metrics = (
    fact_delivery
    .groupBy("partner_id")
    .agg(
        F.countDistinct("order_id").alias("total_deliveries"),
        F.avg("delivery_minutes").alias(
            "average_delivery_minutes"
        ),
        F.expr(
            "percentile_approx(delivery_minutes, 0.95)"
        ).alias("p95_delivery_minutes")
    )
)


# =========================================================
# 13. SAVE EVERYTHING
# =========================================================

print()
print("=" * 60)
print("BUILDING GOLD LAYER")
print("=" * 60)

datasets = {
    "dim_customer": dim_customer,
    "dim_product": dim_product,
    "dim_store": dim_store,
    "dim_delivery_partner": dim_delivery_partner,
    "dim_date": dim_date,
    "fact_orders": fact_orders,
    "fact_order_items": fact_order_items,
    "fact_delivery": fact_delivery,
    "fact_inventory": fact_inventory,
    "daily_sales": daily_sales,
    "product_performance": product_performance,
    "store_performance": store_performance,
    "customer_metrics": customer_metrics,
    "inventory_metrics": inventory_metrics,
    "delivery_metrics": delivery_metrics
}

for name, dataframe in datasets.items():
    save(dataframe, name)


print()
print("=" * 60)
print("GOLD LAYER COMPLETED")
print("=" * 60)

spark.stop()

