# Databricks notebook source
# ============================================
# GOLD LAYER - INITIALIZATION
# ============================================

from pyspark.sql import functions as F
from pyspark.sql.window import Window

print("Gold transformation started.")

# COMMAND ----------

spark.sql("""
CREATE SCHEMA IF NOT EXISTS gold
""")

print("Gold schema created successfully.")

# COMMAND ----------

# ============================================
# LOAD SILVER TABLES
# ============================================

customers = spark.table("silver.customers")
products = spark.table("silver.products")
stores = spark.table("silver.stores")
orders = spark.table("silver.orders")
order_items = spark.table("silver.order_items")
inventory = spark.table("silver.inventory")
payments = spark.table("silver.payments")
deliveries = spark.table("silver.deliveries")
promotions = spark.table("silver.promotions")
reviews = spark.table("silver.reviews")

print("All Silver tables loaded successfully.")

# COMMAND ----------

# ============================================
# GOLD - DAILY SALES
# ============================================

daily_sales = (
    orders
    .join(
        order_items,
        on="order_id",
        how="inner"
    )
    .filter(
        F.col("order_status") == "delivered"
    )
    .withColumn(
        "sales_date",
        F.to_date("order_timestamp")
    )
    .groupBy("sales_date")
    .agg(
        F.sum("item_revenue").alias("total_revenue"),
        F.sum("quantity").alias("total_items_sold"),
        F.countDistinct("order_id").alias("total_orders"),
        F.countDistinct("customer_id").alias("unique_customers"),
        F.avg("item_revenue").alias("average_item_revenue")
    )
    .withColumn(
        "average_order_value",
        F.when(
            F.col("total_orders") > 0,
            F.col("total_revenue") / F.col("total_orders")
        )
    )
    .orderBy("sales_date")
)

display(daily_sales)

# COMMAND ----------

daily_sales.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("gold.daily_sales")

print("gold.daily_sales created successfully.")

# COMMAND ----------

gold_daily_sales = spark.table("gold.daily_sales")

print(
    f"gold.daily_sales rows: "
    f"{gold_daily_sales.count()}"
)

# COMMAND ----------

display(
    gold_daily_sales
    .orderBy("sales_date")
)

# COMMAND ----------

# ============================================
# GOLD - REMAINING BUSINESS TABLES
# ============================================

# --------------------------------------------
# 1. PRODUCT PERFORMANCE
# --------------------------------------------

product_performance = (
    order_items
    .join(products, "product_id", "inner")
    .join(
        orders.select("order_id", "store_id", "order_status", "order_timestamp"),
        "order_id",
        "inner"
    )
    .filter(F.col("order_status") == "delivered")
    .groupBy(
        "product_id",
        "product_name",
        "category",
        "brand"
    )
    .agg(
        F.sum("quantity").alias("units_sold"),
        F.sum("item_revenue").alias("total_revenue"),
        F.countDistinct("order_id").alias("total_orders"),
        F.avg("unit_price").alias("average_selling_price")
    )
    .withColumn(
        "revenue_per_order",
        F.when(
            F.col("total_orders") > 0,
            F.col("total_revenue") / F.col("total_orders")
        )
    )
)

product_performance.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("gold.product_performance")


# --------------------------------------------
# 2. STORE PERFORMANCE
# --------------------------------------------

store_performance = (
    orders
    .join(order_items, "order_id", "inner")
    .join(stores, "store_id", "inner")
    .filter(F.col("order_status") == "delivered")
    .groupBy(
        "store_id",
        "store_name",
        "city"
    )
    .agg(
        F.countDistinct("order_id").alias("total_orders"),
        F.countDistinct("customer_id").alias("unique_customers"),
        F.sum("quantity").alias("items_sold"),
        F.sum("item_revenue").alias("total_revenue"),
        F.avg("item_revenue").alias("average_item_revenue")
    )
    .withColumn(
        "average_order_value",
        F.when(
            F.col("total_orders") > 0,
            F.col("total_revenue") / F.col("total_orders")
        )
    )
)

store_performance.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("gold.store_performance")


# --------------------------------------------
# 3. CUSTOMER METRICS
# --------------------------------------------

customer_metrics = (
    customers
    .join(
        orders,
        "customer_id",
        "left"
    )
    .join(
        order_items,
        "order_id",
        "left"
    )
    .groupBy(
        "customer_id",
        "first_name",
        "last_name",
        "city"
    )
    .agg(
        F.countDistinct(
            F.when(
                F.col("order_status") == "delivered",
                F.col("order_id")
            )
        ).alias("total_orders"),

        F.sum(
            F.when(
                F.col("order_status") == "delivered",
                F.col("item_revenue")
            )
        ).alias("total_spend"),

        F.sum(
            F.when(
                F.col("order_status") == "delivered",
                F.col("quantity")
            )
        ).alias("total_items_purchased"),

        F.max("order_timestamp").alias("last_order_timestamp")
    )
    .withColumn(
        "average_order_value",
        F.when(
            F.col("total_orders") > 0,
            F.col("total_spend") / F.col("total_orders")
        )
    )
    .fillna({
        "total_orders": 0,
        "total_spend": 0.0,
        "total_items_purchased": 0
    })
)

customer_metrics.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("gold.customer_metrics")


# --------------------------------------------
# 4. INVENTORY METRICS
# --------------------------------------------

inventory_metrics = (
    inventory
    .join(products, "product_id", "inner")
    .join(stores, "store_id", "inner")
    .withColumn(
        "inventory_value",
        F.col("stock_quantity") * F.col("price")
    )
    .withColumn(
        "stock_status",
        F.when(
            F.col("stock_quantity") == 0,
            "Out of Stock"
        )
        .when(
            F.col("stock_quantity") <= F.col("reorder_level"),
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
        "stock_quantity",
        "reorder_level",
        "inventory_value",
        "stock_status",
        "last_restock_date"
    )
)

inventory_metrics.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("gold.inventory_metrics")


print("=" * 60)
print("ALL 5 GOLD TABLES CREATED SUCCESSFULLY")
print("=" * 60)

# COMMAND ----------

# ============================================
# GOLD VALIDATION
# ============================================

gold_tables = [
    "daily_sales",
    "product_performance",
    "store_performance",
    "customer_metrics",
    "inventory_metrics"
]

print("=" * 60)
print("GOLD TABLE VALIDATION")
print("=" * 60)

for table in gold_tables:
    df = spark.table(f"gold.{table}")
    print(f"gold.{table:<22} : {df.count():>5} rows")

print("=" * 60)

# COMMAND ----------

display(
    spark.table("gold.store_performance")
    .orderBy(F.desc("total_revenue"))
)

# COMMAND ----------

display(
    spark.table("gold.inventory_metrics")
    .groupBy("stock_status")
    .count()
)

# COMMAND ----------

