# Databricks notebook source
# ============================================
# SILVER LAYER - INITIALIZATION
# ============================================

from pyspark.sql import functions as F
from pyspark.sql.window import Window

print("Silver transformation started.")

# COMMAND ----------

spark.sql("""
CREATE SCHEMA IF NOT EXISTS silver
""")

print("Silver schema created successfully.")

# COMMAND ----------

# ============================================
# LOAD BRONZE TABLES
# ============================================

customers_bronze = spark.table("bronze.customers")
products_bronze = spark.table("bronze.products")
stores_bronze = spark.table("bronze.stores")
orders_bronze = spark.table("bronze.orders")
order_items_bronze = spark.table("bronze.order_items")
inventory_bronze = spark.table("bronze.inventory")
payments_bronze = spark.table("bronze.payments")
deliveries_bronze = spark.table("bronze.deliveries")
promotions_bronze = spark.table("bronze.promotions")
reviews_bronze = spark.table("bronze.reviews")

print("All Bronze tables loaded successfully.")

# COMMAND ----------

customers_bronze.printSchema()

# COMMAND ----------

display(customers_bronze)

# COMMAND ----------

# ============================================
# SILVER - CUSTOMERS
# ============================================

customers_silver = (
    customers_bronze

    # Standardize string fields
    .withColumn(
        "first_name",
        F.initcap(F.trim(F.col("first_name")))
    )

    .withColumn(
        "last_name",
        F.initcap(F.trim(F.col("last_name")))
    )

    .withColumn(
        "email",
        F.lower(F.trim(F.col("email")))
    )

    .withColumn(
        "city",
        F.initcap(F.trim(F.col("city")))
    )

    # Ensure signup_date is a proper date
    .withColumn(
        "signup_date",
        F.to_date(F.col("signup_date"))
    )

    # Remove duplicate customer records
    .dropDuplicates(["customer_id"])

    # Remove records without a customer ID
    .filter(
        F.col("customer_id").isNotNull()
    )
)

# "  rahul  " → "Rahul"
# "HYDERABAD" → "Hyderabad"
# " USER@EMAIL.COM " → "user@email.com"

# COMMAND ----------

print(f"Bronze customers : {customers_bronze.count()}")
print(f"Silver customers : {customers_silver.count()}")

# COMMAND ----------

display(
    customers_silver.select(
        "customer_id",
        "first_name",
        "last_name",
        "email",
        "city",
        "signup_date"
    )
)

# COMMAND ----------

null_customer_ids = (
    customers_silver
    .filter(F.col("customer_id").isNull())
    .count()
)

print(f"Customers with NULL customer_id: {null_customer_ids}")

# COMMAND ----------

duplicate_customer_ids = (
    customers_silver
    .groupBy("customer_id")
    .count()
    .filter(F.col("count") > 1)
)

print(
    f"Duplicate customer IDs: "
    f"{duplicate_customer_ids.count()}"
)

# COMMAND ----------

# ============================================
# CREATE CONTROLLED DATA-QUALITY ISSUES
# FOR SILVER DEMONSTRATION
# ============================================

customers_dirty = (
    customers_bronze
    .withColumn(
        "first_name",
        F.when(
            F.col("customer_id") == "C0001",
            F.lit("  rahul  ")
        ).otherwise(F.col("first_name"))
    )
    .withColumn(
        "last_name",
        F.when(
            F.col("customer_id") == "C0002",
            F.lit("SHARMA")
        ).otherwise(F.col("last_name"))
    )
    .withColumn(
        "email",
        F.when(
            F.col("customer_id") == "C0003",
            F.lit("  USER@EXAMPLE.COM  ")
        ).otherwise(F.col("email"))
    )
    .withColumn(
        "city",
        F.when(
            F.col("customer_id") == "C0004",
            F.lit("hyderabad")
        ).otherwise(F.col("city"))
    )
)

display(
    customers_dirty.filter(
        F.col("customer_id").isin(
            "C0001",
            "C0002",
            "C0003",
            "C0004"
        )
    )
)

# COMMAND ----------

# ============================================
# CLEAN CUSTOMER DATA
# ============================================

customers_silver = (
    customers_dirty

    # Clean names
    .withColumn(
        "first_name",
        F.initcap(F.trim(F.col("first_name")))
    )
    .withColumn(
        "last_name",
        F.initcap(F.trim(F.col("last_name")))
    )

    # Normalize email
    .withColumn(
        "email",
        F.lower(F.trim(F.col("email")))
    )

    # Standardize city
    .withColumn(
        "city",
        F.initcap(F.trim(F.col("city")))
    )

    # Convert signup date
    .withColumn(
        "signup_date",
        F.to_date(F.col("signup_date"))
    )

    # Remove duplicate IDs
    .dropDuplicates(["customer_id"])

    # Remove records without IDs
    .filter(
        F.col("customer_id").isNotNull()
    )
)

# COMMAND ----------

display(
    customers_silver.filter(
        F.col("customer_id").isin(
            "C0001",
            "C0002",
            "C0003",
            "C0004"
        )
    )
)

# COMMAND ----------

# ============================================
# WRITE SILVER CUSTOMERS
# ============================================

customers_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("silver.customers")

print("silver.customers created successfully.")

# COMMAND ----------

silver_customers = spark.table("silver.customers")

print(
    f"silver.customers rows: "
    f"{silver_customers.count()}"
)

# COMMAND ----------

# ============================================
# SILVER - PRODUCTS
# ============================================

products_silver = (
    products_bronze

    # Standardize text fields
    .withColumn(
        "product_name",
        F.initcap(F.trim(F.col("product_name")))
    )
    .withColumn(
        "category",
        F.initcap(F.trim(F.col("category")))
    )
    .withColumn(
        "brand",
        F.initcap(F.trim(F.col("brand")))
    )

    # Ensure price is numeric
    .withColumn(
        "price",
        F.col("price").cast("double")
    )

    # Keep only valid product IDs
    .filter(
        F.col("product_id").isNotNull()
    )

    # Keep only valid prices
    .filter(
        F.col("price") > 0
    )

    # Remove duplicate products
    .dropDuplicates(["product_id"])
)

# COMMAND ----------

print(f"Bronze products : {products_bronze.count()}")
print(f"Silver products : {products_silver.count()}")

# COMMAND ----------

display(
    products_silver.select(
        "product_id",
        "product_name",
        "category",
        "brand",
        "price"
    )
)

# COMMAND ----------

invalid_product_prices = (
    products_silver
    .filter(
        (F.col("price").isNull()) |
        (F.col("price") <= 0)
    )
    .count()
)

print(f"Invalid product prices: {invalid_product_prices}")

# COMMAND ----------

products_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("silver.products")

print("silver.products created successfully.")

# COMMAND ----------

# ============================================
# SILVER - STORES
# ============================================

stores_silver = (
    stores_bronze

    .withColumn(
        "store_name",
        F.initcap(F.trim(F.col("store_name")))
    )

    .withColumn(
        "city",
        F.initcap(F.trim(F.col("city")))
    )

    .withColumn(
        "manager_name",
        F.initcap(F.trim(F.col("manager_name")))
    )

    .withColumn(
        "opening_date",
        F.to_date(F.col("opening_date"))
    )

    .filter(
        F.col("store_id").isNotNull()
    )

    .dropDuplicates(["store_id"])
)

print(f"Bronze stores : {stores_bronze.count()}")
print(f"Silver stores : {stores_silver.count()}")

# COMMAND ----------

stores_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("silver.stores")

print("silver.stores created successfully.")

# COMMAND ----------

# ============================================
# SILVER - ORDERS
# ============================================

orders_silver = (
    orders_bronze
    .withColumn("customer_id", F.trim(F.col("customer_id")))
    .withColumn("store_id", F.trim(F.col("store_id")))
    .withColumn("order_status", F.lower(F.trim(F.col("order_status"))))
    .withColumn("order_timestamp", F.to_timestamp("order_timestamp"))
    .withColumn("order_date", F.to_date("order_timestamp"))
    .filter(F.col("order_id").isNotNull())
    .filter(F.col("customer_id").isNotNull())
    .filter(F.col("store_id").isNotNull())
    .dropDuplicates(["order_id"])
)

# Keep only orders with valid customer and store references
orders_silver = (
    orders_silver
    .join(
        customers_silver.select("customer_id").distinct(),
        "customer_id",
        "left_semi"
    )
    .join(
        stores_silver.select("store_id").distinct(),
        "store_id",
        "left_semi"
    )
)

orders_silver.write.format("delta").mode("overwrite").saveAsTable(
    "silver.orders"
)


# ============================================
# SILVER - ORDER ITEMS
# ============================================

order_items_silver = (
    order_items_bronze
    .withColumn("order_id", F.trim(F.col("order_id")))
    .withColumn("product_id", F.trim(F.col("product_id")))
    .withColumn("quantity", F.col("quantity").cast("int"))
    .withColumn("unit_price", F.col("unit_price").cast("double"))
    .withColumn(
        "item_revenue",
        F.col("quantity") * F.col("unit_price")
    )
    .filter(F.col("order_item_id").isNotNull())
    .filter(F.col("quantity") > 0)
    .filter(F.col("unit_price") > 0)
    .dropDuplicates(["order_item_id"])
)

# Keep only valid order/product references
order_items_silver = (
    order_items_silver
    .join(
        orders_silver.select("order_id").distinct(),
        "order_id",
        "left_semi"
    )
    .join(
        products_silver.select("product_id").distinct(),
        "product_id",
        "left_semi"
    )
)

order_items_silver.write.format("delta").mode("overwrite").saveAsTable(
    "silver.order_items"
)


# ============================================
# SILVER - INVENTORY
# ============================================

inventory_silver = (
    inventory_bronze
    .withColumn("store_id", F.trim(F.col("store_id")))
    .withColumn("product_id", F.trim(F.col("product_id")))
    .withColumn("stock_quantity", F.col("stock_quantity").cast("int"))
    .withColumn("reorder_level", F.col("reorder_level").cast("int"))
    .withColumn(
        "last_restock_date",
        F.to_date("last_restock_date")
    )
    .filter(F.col("stock_quantity") >= 0)
    .filter(F.col("reorder_level") >= 0)
    .dropDuplicates(["store_id", "product_id"])
)

inventory_silver.write.format("delta").mode("overwrite").saveAsTable(
    "silver.inventory"
)


# ============================================
# SILVER - PAYMENTS
# ============================================

payments_silver = (
    payments_bronze
    .withColumn("order_id", F.trim(F.col("order_id")))
    .withColumn(
        "payment_method",
        F.initcap(F.trim(F.col("payment_method")))
    )
    .withColumn(
        "payment_status",
        F.lower(F.trim(F.col("payment_status")))
    )
    .withColumn(
        "payment_amount",
        F.col("payment_amount").cast("double")
    )
    .withColumn(
        "payment_timestamp",
        F.to_timestamp("payment_timestamp")
    )
    .filter(F.col("payment_id").isNotNull())
    .filter(F.col("payment_amount") > 0)
    .dropDuplicates(["payment_id"])
)

payments_silver = payments_silver.join(
    orders_silver.select("order_id").distinct(),
    "order_id",
    "left_semi"
)

payments_silver.write.format("delta").mode("overwrite").saveAsTable(
    "silver.payments"
)


# ============================================
# SILVER - DELIVERIES
# ============================================

deliveries_silver = (
    deliveries_bronze
    .withColumn("order_id", F.trim(F.col("order_id")))
    .withColumn(
        "delivery_partner",
        F.initcap(F.trim(F.col("delivery_partner")))
    )
    .withColumn(
        "delivery_status",
        F.lower(F.trim(F.col("delivery_status")))
    )
    .withColumn(
        "dispatch_timestamp",
        F.to_timestamp("dispatch_timestamp")
    )
    .withColumn(
        "out_for_delivery_timestamp",
        F.to_timestamp("out_for_delivery_timestamp")
    )
    .withColumn(
        "delivery_timestamp",
        F.to_timestamp("delivery_timestamp")
    )
    .withColumn(
        "delivery_duration_minutes",
        (
            F.col("delivery_timestamp").cast("long")
            - F.col("dispatch_timestamp").cast("long")
        ) / 60
    )
    .filter(F.col("delivery_id").isNotNull())
    .dropDuplicates(["delivery_id"])
)

deliveries_silver = deliveries_silver.join(
    orders_silver.select("order_id").distinct(),
    "order_id",
    "left_semi"
)

deliveries_silver.write.format("delta").mode("overwrite").saveAsTable(
    "silver.deliveries"
)


# ============================================
# SILVER - PROMOTIONS
# ============================================

promotions_silver = (
    promotions_bronze
    .withColumn("product_id", F.trim(F.col("product_id")))
    .withColumn(
        "promotion_type",
        F.initcap(F.trim(F.col("promotion_type")))
    )
    .withColumn(
        "discount_percentage",
        F.col("discount_percentage").cast("double")
    )
    .withColumn("start_date", F.to_date("start_date"))
    .withColumn("end_date", F.to_date("end_date"))
    .filter(F.col("promotion_id").isNotNull())
    .filter(
        (F.col("discount_percentage") >= 0) &
        (F.col("discount_percentage") <= 100)
    )
    .filter(F.col("end_date") >= F.col("start_date"))
    .dropDuplicates(["promotion_id"])
)

promotions_silver = promotions_silver.join(
    products_silver.select("product_id").distinct(),
    "product_id",
    "left_semi"
)

promotions_silver.write.format("delta").mode("overwrite").saveAsTable(
    "silver.promotions"
)


# ============================================
# SILVER - REVIEWS
# ============================================

reviews_silver = (
    reviews_bronze
    .withColumn("customer_id", F.trim(F.col("customer_id")))
    .withColumn("order_id", F.trim(F.col("order_id")))
    .withColumn("rating", F.col("rating").cast("int"))
    .withColumn("review_text", F.trim(F.col("review_text")))
    .withColumn("review_date", F.to_date("review_date"))
    .filter(F.col("review_id").isNotNull())
    .filter(F.col("rating").between(1, 5))
    .dropDuplicates(["review_id"])
)

reviews_silver = (
    reviews_silver
    .join(
        customers_silver.select("customer_id").distinct(),
        "customer_id",
        "left_semi"
    )
    .join(
        orders_silver.select("order_id").distinct(),
        "order_id",
        "left_semi"
    )
)

reviews_silver.write.format("delta").mode("overwrite").saveAsTable(
    "silver.reviews"
)

print("=" * 60)
print("ALL SILVER TRANSFORMATIONS COMPLETED")
print("=" * 60)

# COMMAND ----------

# ============================================
# SILVER LAYER VALIDATION
# ============================================

silver_tables = [
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
print("SILVER TABLE VALIDATION")
print("=" * 60)

total_silver_records = 0

for table in silver_tables:
    df = spark.table(f"silver.{table}")
    count = df.count()
    total_silver_records += count
    print(f"silver.{table:<15} : {count:>5} rows")

print("=" * 60)
print(f"Total Silver records : {total_silver_records}")
print("=" * 60)

# COMMAND ----------

display(
    spark.table("silver.deliveries")
    .select(
        "delivery_id",
        "order_id",
        "delivery_status",
        "dispatch_timestamp",
        "out_for_delivery_timestamp",
        "delivery_timestamp",
        "delivery_duration_minutes"
    )
    .filter(
        F.col("delivery_timestamp").isNull()
    )
    .limit(10)
)

# COMMAND ----------

