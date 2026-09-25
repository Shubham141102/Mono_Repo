# Databricks notebook source
from pyspark.sql import functions as F
from pyspark.sql.types import *
import random
from datetime import datetime, timedelta

random.seed(42)

print("QuickCommerce data generation started.")

# COMMAND ----------

# ============================================================
# CONFIGURATION
# ============================================================

NUM_CUSTOMERS = 400
NUM_PRODUCTS = 100
NUM_STORES = 10
NUM_ORDERS = 1000
NUM_ORDER_ITEMS = 2000
NUM_REVIEWS = 400
NUM_PROMOTIONS = 50

print("Configuration loaded.")

print(f"Customers    : {NUM_CUSTOMERS}")
print(f"Products     : {NUM_PRODUCTS}")
print(f"Stores       : {NUM_STORES}")
print(f"Orders       : {NUM_ORDERS}")
print(f"Order Items  : {NUM_ORDER_ITEMS}")
print(f"Reviews      : {NUM_REVIEWS}")
print(f"Promotions   : {NUM_PROMOTIONS}")

# COMMAND ----------

# ============================================================
# 1. GENERATE CUSTOMERS
# ============================================================

first_names = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Rahul",
    "Rohan", "Karan", "Amit", "Neha", "Priya",
    "Ananya", "Sneha", "Pooja", "Kavya", "Isha"
]

last_names = [
    "Sharma", "Verma", "Patel", "Reddy", "Gupta",
    "Singh", "Kumar", "Mehta", "Shah", "Nair"
]

cities = [
    "Hyderabad",
    "Bangalore",
    "Mumbai",
    "Delhi",
    "Pune"
]

customers = []

for i in range(1, NUM_CUSTOMERS + 1):

    first_name = random.choice(first_names)
    last_name = random.choice(last_names)

    customer = {
        "customer_id": f"C{i:04d}",
        "first_name": first_name,
        "last_name": last_name,
        "email": f"{first_name.lower()}.{last_name.lower()}{i}@example.com",
        "city": random.choice(cities),
        "signup_date": (
            datetime(2024, 1, 1)
            + timedelta(days=random.randint(0, 730))
        ).date()
    }

    customers.append(customer)

print(f"Generated {len(customers)} customers.")

# COMMAND ----------

# ============================================================
# QUICKCOMMERCE LAKEHOUSE
# PHASE 2 — DATA GENERATION
# ============================================================

from pyspark.sql import functions as F
from pyspark.sql.types import *
import random
from datetime import datetime, timedelta

# Make our generated data reproducible
random.seed(42)

print("QuickCommerce data generation started.")

# COMMAND ----------



# COMMAND ----------

# ============================================================
# 2. GENERATE PRODUCTS
# ============================================================

categories = [
    "Fruits",
    "Vegetables",
    "Dairy",
    "Beverages",
    "Snacks",
    "Bakery",
    "Personal Care",
    "Household"
]

brands = [
    "FreshMart",
    "DailyNeeds",
    "QuickChoice",
    "NatureBest",
    "UrbanBasket",
    "FarmFresh",
    "HomeCare"
]

product_names = [
    "Milk",
    "Bread",
    "Eggs",
    "Banana",
    "Apple",
    "Orange",
    "Potato",
    "Tomato",
    "Onion",
    "Rice",
    "Wheat Flour",
    "Biscuits",
    "Chips",
    "Chocolate",
    "Coffee",
    "Tea",
    "Juice",
    "Cola",
    "Water",
    "Curd",
    "Butter",
    "Cheese",
    "Shampoo",
    "Soap",
    "Toothpaste",
    "Detergent",
    "Dishwash",
    "Cooking Oil",
    "Salt",
    "Sugar"
]

products = []

for i in range(1, NUM_PRODUCTS + 1):

    product_name = random.choice(product_names)
    category = random.choice(categories)
    brand = random.choice(brands)

    product = {
        "product_id": f"P{i:04d}",
        "product_name": product_name,
        "category": category,
        "brand": brand,
        "price": round(random.uniform(20, 500), 2)
    }

    products.append(product)

print(f"Generated {len(products)} products.")

# COMMAND ----------

# ============================================================
# CONVERT PRODUCTS TO SPARK DATAFRAME
# ============================================================

products_df = spark.createDataFrame(products)

print("Products DataFrame created.")
print(f"Number of rows: {products_df.count()}")
print(f"Number of columns: {len(products_df.columns)}")

# COMMAND ----------

display(products_df)

# COMMAND ----------

products_df.printSchema()

# COMMAND ----------

display(
    products_df
    .groupBy("category")
    .count()
    .orderBy(F.desc("count"))
)

# COMMAND ----------

display(
    products_df
    .groupBy("category")
    .agg(
        F.count("*").alias("product_count"),
        F.avg("price").alias("average_price"),
        F.min("price").alias("minimum_price"),
        F.max("price").alias("maximum_price")
    )
    .orderBy(F.desc("product_count"))
)

# COMMAND ----------

products_df.groupBy("category")

# COMMAND ----------

# ============================================================
# 3. GENERATE STORES
# ============================================================

store_names = [
    "Madhapur Dark Store",
    "Gachibowli Dark Store",
    "Kondapur Dark Store",
    "Hitech City Dark Store",
    "Banjara Hills Dark Store",
    "Indiranagar Dark Store",
    "Koramangala Dark Store",
    "Andheri Dark Store",
    "Viman Nagar Dark Store",
    "Saket Dark Store"
]

cities = [
    "Hyderabad",
    "Bangalore",
    "Mumbai",
    "Delhi",
    "Pune"
]

stores = []

for i in range(1, NUM_STORES + 1):

    store = {
        "store_id": f"S{i:03d}",
        "store_name": store_names[i - 1],
        "city": cities[(i - 1) % len(cities)],
        "manager_name": f"Manager_{i}",
        "opening_date": (
            datetime(2023, 1, 1)
            + timedelta(days=random.randint(0, 730))
        ).date()
    }

    stores.append(store)

print(f"Generated {len(stores)} stores.")

# COMMAND ----------

# ============================================================
# CONVERT STORES TO SPARK DATAFRAME
# ============================================================

stores_df = spark.createDataFrame(stores)

print("Stores DataFrame created.")
print(f"Number of rows: {stores_df.count()}")
print(f"Number of columns: {len(stores_df.columns)}")

# COMMAND ----------

display(stores_df)

# COMMAND ----------

stores_df.printSchema()

# COMMAND ----------

print("customers" in globals())
print("products" in globals())
print("stores" in globals())

# COMMAND ----------

# ============================================================
# 3. GENERATE STORES
# ============================================================

store_names = [
    "Madhapur Dark Store",
    "Gachibowli Dark Store",
    "Kondapur Dark Store",
    "Hitech City Dark Store",
    "Banjara Hills Dark Store",
    "Indiranagar Dark Store",
    "Koramangala Dark Store",
    "Andheri Dark Store",
    "Viman Nagar Dark Store",
    "Saket Dark Store"
]

cities = [
    "Hyderabad",
    "Bangalore",
    "Mumbai",
    "Delhi",
    "Pune"
]

stores = []

for i in range(1, NUM_STORES + 1):

    store = {
        "store_id": f"S{i:03d}",
        "store_name": store_names[i - 1],
        "city": cities[(i - 1) % len(cities)],
        "manager_name": f"Manager_{i}",
        "opening_date": (
            datetime(2023, 1, 1)
            + timedelta(days=random.randint(0, 730))
        ).date()
    }

    stores.append(store)

print(f"Generated {len(stores)} stores.")

# COMMAND ----------

orders = []

order_start = datetime(2026, 1, 1)
order_end = datetime(2026, 6, 30)

order_statuses = [
    "delivered",
    "delivered",
    "delivered",
    "delivered",
    "processing",
    "cancelled"
]

for i in range(1, NUM_ORDERS + 1):

    customer = random.choice(customers)
    store = random.choice(stores)

    order_timestamp = (
        order_start
        + timedelta(
            seconds=random.randint(
                0,
                int((order_end - order_start).total_seconds())
            )
        )
    )

    order = {
        "order_id": f"O{i:05d}",
        "customer_id": customer["customer_id"],
        "store_id": store["store_id"],
        "order_timestamp": order_timestamp,
        "order_status": random.choice(order_statuses)
    }

    orders.append(order)

print(f"Generated {len(orders)} orders.")

# COMMAND ----------

# ============================================================
# 5. GENERATE ORDER ITEMS
# ============================================================

order_items = []

for i in range(1, NUM_ORDER_ITEMS + 1):

    # Select an existing order
    order = random.choice(orders)

    # Select an existing product
    product = random.choice(products)

    # Generate quantity
    quantity = random.randint(1, 5)

    order_item = {
        "order_item_id": f"OI{i:05d}",
        "order_id": order["order_id"],
        "product_id": product["product_id"],
        "quantity": quantity,
        "unit_price": product["price"]
    }

    order_items.append(order_item)

print(f"Generated {len(order_items)} order items.")

# COMMAND ----------

# ============================================================
# CONVERT ORDER ITEMS TO SPARK DATAFRAME
# ============================================================

order_items_df = spark.createDataFrame(order_items)

print("Order Items DataFrame created.")
print(f"Number of rows: {order_items_df.count()}")
print(f"Number of columns: {len(order_items_df.columns)}")

# COMMAND ----------

order_items_revenue_df = (
    order_items_df
    .withColumn(
        "item_revenue",
        F.col("quantity") * F.col("unit_price")
    )
)

display(order_items_revenue_df)

# COMMAND ----------

order_revenue_df = (
    order_items_revenue_df
    .groupBy("order_id")
    .agg(
        F.sum("item_revenue").alias("order_revenue"),
        F.sum("quantity").alias("total_items")
    )
)

display(
    order_revenue_df
    .orderBy(F.desc("order_revenue"))
)

# COMMAND ----------

print("customers:", "customers" in globals())
print("customers_df:", "customers_df" in globals())

print("products:", "products" in globals())
print("products_df:", "products_df" in globals())

print("stores:", "stores" in globals())
print("stores_df:", "stores_df" in globals())

print("orders:", "orders" in globals())
print("orders_df:", "orders_df" in globals())

print("order_items:", "order_items" in globals())
print("order_items_df:", "order_items_df" in globals())

# COMMAND ----------

customers_df = spark.createDataFrame(customers)

print(f"Customers DataFrame: {customers_df.count()} rows")

# COMMAND ----------

orders_df = spark.createDataFrame(orders)

print(f"Orders DataFrame: {orders_df.count()} rows")

# COMMAND ----------

print("customers_df:", "customers_df" in globals())
print("products_df:", "products_df" in globals())
print("stores_df:", "stores_df" in globals())
print("orders_df:", "orders_df" in globals())
print("order_items_df:", "order_items_df" in globals())

# COMMAND ----------

invalid_order_ids = (
    order_items_df
    .join(
        orders_df.select("order_id"),
        on="order_id",
        how="left_anti"
    )
)

print(
    f"Order items with invalid order_id: "
    f"{invalid_order_ids.count()}"
)

# COMMAND ----------

invalid_product_ids = (
    order_items_df
    .join(
        products_df.select("product_id"),
        on="product_id",
        how="left_anti"
    )
)

print(
    f"Order items with invalid product_id: "
    f"{invalid_product_ids.count()}"
)

# COMMAND ----------

# ============================================
# INVENTORY DATA GENERATION
# ============================================

inventory = []

for store in stores:
    # Each store carries a random selection of products
    selected_products = random.sample(
        products,
        random.randint(60, 90)
    )

    for product in selected_products:
        inventory_record = {
            "store_id": store["store_id"],
            "product_id": product["product_id"],
            "stock_quantity": random.randint(0, 100),
            "reorder_level": random.randint(10, 30),
            "last_restock_date": (
                datetime(2026, 1, 1)
                + timedelta(days=random.randint(0, 180))
            ).date()
        }

        inventory.append(inventory_record)

print(f"Generated {len(inventory)} inventory records.")

# COMMAND ----------

inventory_df = spark.createDataFrame(inventory)

print("Inventory DataFrame created.")
print(f"Number of rows: {inventory_df.count()}")
print(f"Number of columns: {len(inventory_df.columns)}")

# COMMAND ----------

display(inventory_df)

# COMMAND ----------

inventory_df.printSchema()

# COMMAND ----------

invalid_inventory_stores = (
    inventory_df
    .join(
        stores_df.select("store_id"),
        on="store_id",
        how="left_anti"
    )
)

print(
    f"Inventory records with invalid store_id: "
    f"{invalid_inventory_stores.count()}"
)

# COMMAND ----------

invalid_inventory_products = (
    inventory_df
    .join(
        products_df.select("product_id"),
        on="product_id",
        how="left_anti"
    )
)

print(
    f"Inventory records with invalid product_id: "
    f"{invalid_inventory_products.count()}"
)

# COMMAND ----------

display(
    inventory_df
    .groupBy("store_id")
    .agg(
        F.count("*").alias("product_count"),
        F.sum("stock_quantity").alias("total_stock"),
        F.avg("stock_quantity").alias("avg_stock")
    )
    .orderBy(F.desc("total_stock"))
)

# COMMAND ----------

# ============================================
# PAYMENTS DATA GENERATION
# ============================================

payment_methods = [
    "UPI",
    "Credit Card",
    "Debit Card",
    "Cash on Delivery",
    "Wallet"
]

payment_statuses = [
    "successful",
    "successful",
    "successful",
    "successful",
    "failed",
    "pending"
]

payments = []

for order in orders:

    payment = {
        "payment_id": f"PAY{len(payments) + 1:05d}",
        "order_id": order["order_id"],
        "payment_method": random.choice(payment_methods),
        "payment_status": random.choice(payment_statuses),
        "payment_amount": round(random.uniform(50, 2500), 2),
        "payment_timestamp": (
            order["order_timestamp"]
            + timedelta(minutes=random.randint(1, 30))
        )
    }

    payments.append(payment)

print(f"Generated {len(payments)} payment records.")

# COMMAND ----------

# Create Payments DataFrame

payments_df = spark.createDataFrame(payments)

print("Payments DataFrame created.")
print(f"Number of rows: {payments_df.count()}")
print(f"Number of columns: {len(payments_df.columns)}")

# COMMAND ----------

display(payments_df)

# COMMAND ----------

invalid_payment_orders = (
    payments_df
    .join(
        orders_df.select("order_id"),
        on="order_id",
        how="left_anti"
    )
)

print(
    f"Payments with invalid order_id: "
    f"{invalid_payment_orders.count()}"
)

# COMMAND ----------

display(
    payments_df
    .groupBy("payment_status")
    .count()
    .orderBy(F.desc("count"))
)

# COMMAND ----------

display(
    payments_df
    .groupBy("payment_method")
    .agg(
        F.count("*").alias("payment_count"),
        F.sum("payment_amount").alias("total_amount"),
        F.avg("payment_amount").alias("average_amount")
    )
    .orderBy(F.desc("payment_count"))
)

# COMMAND ----------

# ============================================
# DELIVERIES DATA GENERATION
# ============================================

delivery_statuses = [
    "delivered",
    "delivered",
    "delivered",
    "out_for_delivery",
    "delayed",
    "cancelled"
]

deliveries = []

for order in orders:

    order_time = order["order_timestamp"]

    # Delivery timeline
    dispatch_time = order_time + timedelta(
        minutes=random.randint(5, 30)
    )

    out_for_delivery_time = dispatch_time + timedelta(
        minutes=random.randint(10, 60)
    )

    delivery_time = out_for_delivery_time + timedelta(
        minutes=random.randint(10, 120)
    )

    status = random.choice(delivery_statuses)

    # Intentionally introduce missing delivery timestamps
    # so the Silver layer has realistic data-quality issues.
    if random.random() < 0.08:
        delivery_time = None

    if random.random() < 0.05:
        out_for_delivery_time = None

    delivery = {
        "delivery_id": f"DEL{len(deliveries) + 1:05d}",
        "order_id": order["order_id"],
        "delivery_partner": random.choice([
            "Blinkit Rider",
            "QuickDrop",
            "FastKart",
            "UrbanExpress"
        ]),
        "delivery_status": status,
        "dispatch_timestamp": dispatch_time,
        "out_for_delivery_timestamp": out_for_delivery_time,
        "delivery_timestamp": delivery_time
    }

    deliveries.append(delivery)

print(f"Generated {len(deliveries)} delivery records.")

# COMMAND ----------

# Create Deliveries DataFrame

deliveries_df = spark.createDataFrame(deliveries)

print("Deliveries DataFrame created.")
print(f"Number of rows: {deliveries_df.count()}")
print(f"Number of columns: {len(deliveries_df.columns)}")

# COMMAND ----------

display(deliveries_df)

# COMMAND ----------

deliveries_df.printSchema()

# COMMAND ----------

invalid_delivery_orders = (
    deliveries_df
    .join(
        orders_df.select("order_id"),
        on="order_id",
        how="left_anti"
    )
)

print(
    f"Deliveries with invalid order_id: "
    f"{invalid_delivery_orders.count()}"
)

# COMMAND ----------

display(
    deliveries_df.select(
        F.count("*").alias("total_records"),
        F.sum(
            F.when(
                F.col("out_for_delivery_timestamp").isNull(),
                1
            ).otherwise(0)
        ).alias("missing_out_for_delivery"),
        F.sum(
            F.when(
                F.col("delivery_timestamp").isNull(),
                1
            ).otherwise(0)
        ).alias("missing_delivery_timestamp")
    )
)

# COMMAND ----------

# ============================================
# PROMOTIONS DATA GENERATION
# ============================================

promotion_types = [
    "Percentage Discount",
    "Flat Discount",
    "Buy One Get One",
    "Free Delivery"
]

promotions = []

for i in range(1, NUM_PROMOTIONS + 1):

    product = random.choice(products)

    start_date = (
        datetime(2026, 1, 1)
        + timedelta(days=random.randint(0, 120))
    ).date()

    end_date = (
        start_date
        + timedelta(days=random.randint(7, 30))
    )

    promotion = {
        "promotion_id": f"PR{i:04d}",
        "product_id": product["product_id"],
        "promotion_type": random.choice(promotion_types),
        "discount_percentage": round(random.uniform(5, 40), 2),
        "start_date": start_date,
        "end_date": end_date
    }

    promotions.append(promotion)

print(f"Generated {len(promotions)} promotion records.")

# COMMAND ----------

promotions_df = spark.createDataFrame(promotions)

print(f"Promotions DataFrame: {promotions_df.count()} rows")

# COMMAND ----------

invalid_promotion_products = (
    promotions_df
    .join(
        products_df.select("product_id"),
        on="product_id",
        how="left_anti"
    )
)

print(
    f"Promotions with invalid product_id: "
    f"{invalid_promotion_products.count()}"
)

# COMMAND ----------

# ============================================
# REVIEWS DATA GENERATION
# ============================================

review_texts = [
    "Very good service",
    "Fast delivery",
    "Product quality was excellent",
    "Good experience",
    "Average service",
    "Delivery was late",
    "Product was damaged",
    "Could be better",
    "Excellent experience"
]

reviews = []

for i in range(1, NUM_REVIEWS + 1):

    order = random.choice(orders)
    customer_id = order["customer_id"]

    review = {
        "review_id": f"R{i:04d}",
        "customer_id": customer_id,
        "order_id": order["order_id"],
        "rating": random.randint(1, 5),
        "review_text": random.choice(review_texts),
        "review_date": (
            order["order_timestamp"]
            + timedelta(days=random.randint(1, 7))
        ).date()
    }

    reviews.append(review)

print(f"Generated {len(reviews)} review records.")

# COMMAND ----------

reviews_df = spark.createDataFrame(reviews)

print(f"Reviews DataFrame: {reviews_df.count()} rows")

# COMMAND ----------

invalid_review_customers = (
    reviews_df
    .join(
        customers_df.select("customer_id"),
        on="customer_id",
        how="left_anti"
    )
)

print(
    f"Reviews with invalid customer_id: "
    f"{invalid_review_customers.count()}"
)

# COMMAND ----------

invalid_review_orders = (
    reviews_df
    .join(
        orders_df.select("order_id"),
        on="order_id",
        how="left_anti"
    )
)

print(
    f"Reviews with invalid order_id: "
    f"{invalid_review_orders.count()}"
)

# COMMAND ----------

# ============================================
# FINAL SOURCE DATA GENERATION CHECK
# ============================================

datasets = {
    "Customers": customers_df,
    "Products": products_df,
    "Stores": stores_df,
    "Orders": orders_df,
    "Order Items": order_items_df,
    "Inventory": inventory_df,
    "Payments": payments_df,
    "Deliveries": deliveries_df,
    "Promotions": promotions_df,
    "Reviews": reviews_df
}

print("=" * 55)
print("QUICK-COMMERCE SOURCE DATASET SUMMARY")
print("=" * 55)

total_records = 0

for name, df in datasets.items():
    count = df.count()
    total_records += count
    print(f"{name:<20} : {count:>6} rows")

print("=" * 55)
print(f"Total records        : {total_records:>6}")
print("=" * 55)

# COMMAND ----------

# ============================================
# EXPORT GENERATED DATASETS FOR BRONZE
# ============================================

generated_datasets = {
    "customers": customers_df,
    "products": products_df,
    "stores": stores_df,
    "orders": orders_df,
    "order_items": order_items_df,
    "inventory": inventory_df,
    "payments": payments_df,
    "deliveries": deliveries_df,
    "promotions": promotions_df,
    "reviews": reviews_df
}

print("All source datasets prepared for Bronze ingestion.")

for name, df in generated_datasets.items():
    print(f"{name:<15} : {df.count()} rows")

# COMMAND ----------

