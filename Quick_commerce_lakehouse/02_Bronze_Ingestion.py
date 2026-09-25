# Databricks notebook source

from pyspark.sql import functions as F
from datetime import datetime

print("Bronze ingestion started.")

# COMMAND ----------

# Create Bronze schema

spark.sql("""
CREATE SCHEMA IF NOT EXISTS bronze
""")

print("Bronze schema created successfully.")

# COMMAND ----------

# Check whether generated DataFrames are available

required_datasets = [
    "customers_df",
    "products_df",
    "stores_df",
    "orders_df",
    "order_items_df",
    "inventory_df",
    "payments_df",
    "deliveries_df",
    "promotions_df",
    "reviews_df"
]

for dataset in required_datasets:
    print(f"{dataset:<20} : {dataset in globals()}")

# COMMAND ----------

# MAGIC %run ./01_Data_Generation

# COMMAND ----------

required_datasets = {
    "customers_df": customers_df,
    "products_df": products_df,
    "stores_df": stores_df,
    "orders_df": orders_df,
    "order_items_df": order_items_df,
    "inventory_df": inventory_df,
    "payments_df": payments_df,
    "deliveries_df": deliveries_df,
    "promotions_df": promotions_df,
    "reviews_df": reviews_df
}

for name, df in required_datasets.items():
    print(f"{name:<20} : {df.count()} rows")

# COMMAND ----------

spark.sql("""
CREATE SCHEMA IF NOT EXISTS bronze
""")

print("Bronze schema is ready.")

# COMMAND ----------

# ============================================
# BRONZE - CUSTOMERS
# ============================================

customers_bronze_df = (
    customers_df
    .withColumn(
        "ingestion_timestamp",
        F.current_timestamp()
    )
    .withColumn(
        "source_file",
        F.lit("customers.csv")
    )
    .withColumn(
        "batch_id",
        F.lit("batch_001")
    )
)

customers_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.customers")

print("bronze.customers created successfully.")

# COMMAND ----------

bronze_customers = spark.table("bronze.customers")

print(f"Bronze customers rows: {bronze_customers.count()}")

# COMMAND ----------

display(bronze_customers)

# COMMAND ----------

display(
    bronze_customers.select(
        "customer_id",
        "first_name",
        "last_name",
        "ingestion_timestamp",
        "source_file",
        "batch_id"
    )
)

# COMMAND ----------

# ============================================
# BRONZE LAYER - REMAINING 9 TABLES
# ============================================

from pyspark.sql import functions as F

# --------------------------------------------
# 1. PRODUCTS
# --------------------------------------------

products_bronze_df = (
    products_df
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("source_file", F.lit("products.csv"))
    .withColumn("batch_id", F.lit("batch_001"))
)

products_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.products")


# --------------------------------------------
# 2. STORES
# --------------------------------------------

stores_bronze_df = (
    stores_df
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("source_file", F.lit("stores.csv"))
    .withColumn("batch_id", F.lit("batch_001"))
)

stores_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.stores")


# --------------------------------------------
# 3. ORDERS
# --------------------------------------------

orders_bronze_df = (
    orders_df
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("source_file", F.lit("orders.csv"))
    .withColumn("batch_id", F.lit("batch_001"))
)

orders_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.orders")


# --------------------------------------------
# 4. ORDER ITEMS
# --------------------------------------------

order_items_bronze_df = (
    order_items_df
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("source_file", F.lit("order_items.csv"))
    .withColumn("batch_id", F.lit("batch_001"))
)

order_items_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.order_items")


# --------------------------------------------
# 5. INVENTORY
# --------------------------------------------

inventory_bronze_df = (
    inventory_df
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("source_file", F.lit("inventory.csv"))
    .withColumn("batch_id", F.lit("batch_001"))
)

inventory_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.inventory")


# --------------------------------------------
# 6. PAYMENTS
# --------------------------------------------

payments_bronze_df = (
    payments_df
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("source_file", F.lit("payments.csv"))
    .withColumn("batch_id", F.lit("batch_001"))
)

payments_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.payments")


# --------------------------------------------
# 7. DELIVERIES
# --------------------------------------------

deliveries_bronze_df = (
    deliveries_df
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("source_file", F.lit("deliveries.csv"))
    .withColumn("batch_id", F.lit("batch_001"))
)

deliveries_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.deliveries")


# --------------------------------------------
# 8. PROMOTIONS
# --------------------------------------------

promotions_bronze_df = (
    promotions_df
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("source_file", F.lit("promotions.csv"))
    .withColumn("batch_id", F.lit("batch_001"))
)

promotions_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.promotions")


# --------------------------------------------
# 9. REVIEWS
# --------------------------------------------

reviews_bronze_df = (
    reviews_df
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("source_file", F.lit("reviews.csv"))
    .withColumn("batch_id", F.lit("batch_001"))
)

reviews_bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze.reviews")


print("============================================")
print("ALL 10 BRONZE TABLES CREATED SUCCESSFULLY")
print("============================================")

# COMMAND ----------

# ============================================
# BRONZE TABLE VALIDATION
# ============================================

bronze_tables = [
    "customers",
    "products",
    "stores",
    "orders",
    "order_items",
    "inventory",
    "payments",
    "deliveries",
    "promotions",
    "reviews"
]

print("=" * 60)
print("BRONZE TABLE VALIDATION")
print("=" * 60)

total_bronze_records = 0

for table in bronze_tables:
    df = spark.table(f"bronze.{table}")
    row_count = df.count()
    total_bronze_records += row_count

    print(f"bronze.{table:<15} : {row_count:>5} rows")

print("=" * 60)
print(f"Total Bronze records : {total_bronze_records}")
print("=" * 60)

# COMMAND ----------

display(
    spark.sql("SHOW TABLES IN bronze")
)

# COMMAND ----------

