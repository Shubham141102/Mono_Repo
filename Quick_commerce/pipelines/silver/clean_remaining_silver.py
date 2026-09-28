import os
import sys
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

import pandas as pd
from pyspark.sql.functions import (
    col, trim, lower, upper, initcap,
    to_timestamp, to_date, split
)
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, trim, lower, initcap,
    to_timestamp, to_date, split
)

ROOT = Path(__file__).resolve().parents[2]

spark = (
    SparkSession.builder
    .appName("Remaining_Silver")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# =========================================================
# HELPERS
# =========================================================

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


def process(name, df, silver_path, quarantine_path,
            key, validation):

    total = df.count()

    df = validation(df)

    invalid = df.filter(col("_invalid"))
    valid = df.filter(~col("_invalid"))

    invalid_count = invalid.count()

    valid = valid.drop("_invalid")

    duplicate_count = (
        valid.groupBy(key)
        .count()
        .filter(col("count") > 1)
        .count()
    )

    silver = valid.dropDuplicates(key)

    silver_count = silver.count()

    save_csv(silver, silver_path)
    save_csv(
        invalid.drop("_invalid"),
        quarantine_path
    )

    print(
        f"{name:<20} "
        f"Bronze={total:<6} "
        f"Silver={silver_count:<6} "
        f"Quarantine={invalid_count:<5} "
        f"Quality={round(silver_count / total * 100, 2)}%"
    )


# =========================================================
# REFERENCE DATA
# =========================================================

orders = read_csv(
    ROOT / "data" / "silver" / "orders_csv"
).select("order_id").dropDuplicates()

partners = read_csv(
    ROOT / "data" / "silver" / "delivery_partners_csv"
).select("partner_id").dropDuplicates()

customers = read_csv(
    ROOT / "data" / "silver" / "customers_csv"
).select("customer_id").dropDuplicates()

stores = read_csv(
    ROOT / "data" / "silver" / "stores_csv"
).select("store_id").dropDuplicates()


# =========================================================
# 1. DELIVERY EVENTS
# =========================================================

path = ROOT / "data" / "bronze" / "delivery_events_csv"

df = read_csv(path)

df = (
    df
    .withColumn("delivery_event_id", trim(col("delivery_event_id")))
    .withColumn("order_id", trim(col("order_id")))
    .withColumn("partner_id", trim(col("partner_id")))
    .withColumn(
        "event_timestamp",
        to_timestamp(col("event_timestamp"))
    )
    .withColumn(
        "event_type",
        lower(trim(col("event_type")))
    )
    .withColumn("latitude", col("latitude").cast("double"))
    .withColumn("longitude", col("longitude").cast("double"))
)

df = (
    df.join(
        orders.withColumn("valid_order", col("order_id")),
        "order_id",
        "left"
    )
    .join(
        partners.withColumn("valid_partner", col("partner_id")),
        "partner_id",
        "left"
    )
)

df = df.withColumn(
    "_invalid",
    col("delivery_event_id").isNull()
    | col("order_id").isNull()
    | col("valid_order").isNull()
    | col("partner_id").isNull()
    | col("valid_partner").isNull()
    | col("event_timestamp").isNull()
    | (~col("event_type").isin(
        "assigned",
        "picked_up",
        "out_for_delivery",
        "delivered"
    ))
    | col("latitude").isNull()
    | (col("latitude") < -90)
    | (col("latitude") > 90)
    | col("longitude").isNull()
    | (col("longitude") < -180)
    | (col("longitude") > 180)
)

df = df.drop("valid_order", "valid_partner")

process(
    "Delivery Events",
    df,
    ROOT / "data" / "silver" / "delivery_events_csv",
    ROOT / "data" / "quarantine" / "delivery_events_csv",
    ["delivery_event_id"],
    lambda x: x
)


# =========================================================
# 2. APPLICATION LOGS
# =========================================================

path = ROOT / "data" / "bronze" / "application_logs_csv"

df = read_csv(path)

df = (
    df
    .withColumn("log_id", trim(col("log_id")))
    .withColumn("timestamp", to_timestamp(col("timestamp")))
    .withColumn("level", upper(trim(col("level"))))
    .withColumn("service", trim(col("service")))
    .withColumn("endpoint", trim(col("endpoint")))
    .withColumn("status_code", col("status_code").cast("integer"))
    .withColumn("latency_ms", col("latency_ms").cast("integer"))
    .withColumn("message", trim(col("message")))
)

df = df.withColumn(
    "_invalid",
    col("log_id").isNull()
    | col("timestamp").isNull()
    | col("level").isNull()
    | (~col("level").isin("INFO", "WARNING", "ERROR"))
    | col("service").isNull()
    | col("endpoint").isNull()
    | col("status_code").isNull()
    | (col("status_code") < 100)
    | (col("status_code") > 599)
    | col("latency_ms").isNull()
    | (col("latency_ms") < 0)
    | col("message").isNull()
)

process(
    "Application Logs",
    df,
    ROOT / "data" / "silver" / "application_logs_csv",
    ROOT / "data" / "quarantine" / "application_logs_csv",
    ["log_id"],
    lambda x: x
)


# =========================================================
# 3. ARCHIVE CUSTOMERS
# =========================================================

path = ROOT / "data" / "bronze" / "archive_customers_csv"

df = read_csv(path)

name_parts = split(trim(col("full_name")), " ", 2)

df = (
    df
    .withColumn("customer_id", trim(col("customer_id")))
    .withColumn("first_name", name_parts.getItem(0))
    .withColumn("last_name", name_parts.getItem(1))
    .withColumn("email", lower(trim(col("email"))))
    .withColumn("phone", trim(col("phone")))
    .withColumn("city", initcap(trim(col("city"))))
    .withColumn(
        "signup_date",
        to_date(col("registration_date"))
    )
    .withColumn(
        "customer_segment",
        initcap(trim(col("segment")))
    )
    .withColumn(
        "is_active",
        lower(trim(col("status"))) == "active"
    )
    .withColumn("state", col("city"))
)

df = df.withColumn(
    "_invalid",
    col("customer_id").isNull()
    | col("first_name").isNull()
    | col("email").isNull()
    | col("phone").isNull()
    | col("city").isNull()
    | col("signup_date").isNull()
    | col("customer_segment").isNull()
)

df = df.select(
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "city",
    "state",
    "signup_date",
    "customer_segment",
    "is_active",
    "_invalid"
)

process(
    "Archive Customers",
    df,
    ROOT / "data" / "silver" / "archive_customers_csv",
    ROOT / "data" / "quarantine" / "archive_customers_csv",
    ["customer_id"],
    lambda x: x
)


# =========================================================
# 4. ARCHIVE ORDERS
# =========================================================

path = ROOT / "data" / "bronze" / "archive_orders_csv"

df = read_csv(path)

df = (
    df
    .withColumn("order_id", trim(col("order_id")))
    .withColumn("customer_id", trim(col("customer_id")))
    .withColumn("store_id", trim(col("store_id")))
    .withColumn(
        "order_timestamp",
        to_timestamp(col("order_date"))
    )
    .withColumn(
        "order_status",
        initcap(trim(col("status")))
    )
    .withColumn(
        "total_amount",
        col("amount").cast("double")
    )
    .withColumn(
        "payment_method",
        initcap(trim(col("payment_type")))
    )
    .withColumn(
        "delivery_type",
        col("payment_method")
    )
)

df = (
    df.join(
        customers.withColumn("valid_customer", col("customer_id")),
        "customer_id",
        "left"
    )
    .join(
        stores.withColumn("valid_store", col("store_id")),
        "store_id",
        "left"
    )
)

df = df.withColumn(
    "_invalid",
    col("order_id").isNull()
    | col("customer_id").isNull()
    | col("valid_customer").isNull()
    | col("store_id").isNull()
    | col("valid_store").isNull()
    | col("order_timestamp").isNull()
    | col("total_amount").isNull()
    | (col("total_amount") <= 0)
    | col("order_status").isNull()
    | col("payment_method").isNull()
)

df = df.drop(
    "valid_customer",
    "valid_store"
)

df = df.select(
    "order_id",
    "customer_id",
    "store_id",
    "order_timestamp",
    "order_status",
    "total_amount",
    "payment_method",
    "delivery_type",
    "_invalid"
)

process(
    "Archive Orders",
    df,
    ROOT / "data" / "silver" / "archive_orders_csv",
    ROOT / "data" / "quarantine" / "archive_orders_csv",
    ["order_id"],
    lambda x: x
)


# =========================================================
# DONE
# =========================================================

print()
print("==============================================")
print("ALL REMAINING SILVER DATASETS COMPLETED")
print("==============================================")

spark.stop()
