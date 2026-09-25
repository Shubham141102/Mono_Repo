# Databricks notebook source
# ============================================
# ML DEMAND PREDICTION - INITIALIZATION
# ============================================

from pyspark.sql import functions as F
from pyspark.sql.window import Window

print("Demand prediction pipeline started.")

# COMMAND ----------

# ============================================
# LOAD GOLD DATA
# ============================================

daily_sales = spark.table("gold.daily_sales")
product_performance = spark.table("gold.product_performance")
inventory_metrics = spark.table("gold.inventory_metrics")

print("Gold datasets loaded successfully.")

print("daily_sales:", daily_sales.count())
print("product_performance:", product_performance.count())
print("inventory_metrics:", inventory_metrics.count())

# COMMAND ----------

# ============================================
# LOAD SILVER DATA FOR ML
# ============================================

orders = spark.table("silver.orders")
order_items = spark.table("silver.order_items")
products = spark.table("silver.products")
stores = spark.table("silver.stores")
inventory = spark.table("silver.inventory")
promotions = spark.table("silver.promotions")

print("Silver datasets loaded.")

# COMMAND ----------

# ============================================
# PRODUCT-STORE DAILY SALES
# ============================================

product_store_daily_sales = (
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
    .groupBy(
        "store_id",
        "product_id",
        "sales_date"
    )
    .agg(
        F.sum("quantity").alias("daily_quantity"),
        F.sum("item_revenue").alias("daily_revenue"),
        F.countDistinct("order_id").alias("daily_orders")
    )
)

print(
    "Product-store daily sales rows:",
    product_store_daily_sales.count()
)

display(
    product_store_daily_sales
    .orderBy("sales_date", "store_id", "product_id")
)

# COMMAND ----------

# ============================================
# ADD PRODUCT + STORE FEATURES
# ============================================

demand_base = (
    product_store_daily_sales

    .join(
        products.select(
            "product_id",
            "product_name",
            "category",
            "brand",
            "price"
        ),
        on="product_id",
        how="left"
    )

    .join(
        stores.select(
            "store_id",
            "store_name",
            "city"
        ),
        on="store_id",
        how="left"
    )
)

display(demand_base)

# COMMAND ----------

# ============================================
# DEMAND FEATURE ENGINEERING
# ============================================

demand_window = (
    Window
    .partitionBy("store_id", "product_id")
    .orderBy("sales_date")
)

rolling_window_7 = (
    demand_window
    .rowsBetween(-7, -1)
)

rolling_window_14 = (
    demand_window
    .rowsBetween(-14, -1)
)

demand_features = (
    demand_base

    # Calendar feature
    .withColumn(
        "day_of_week",
        F.dayofweek("sales_date")
    )

    # Previous observed sales
    .withColumn(
        "previous_day_sales",
        F.lag("daily_quantity", 1).over(demand_window)
    )

    # Historical rolling demand
    .withColumn(
        "sales_last_7_days",
        F.sum("daily_quantity").over(rolling_window_7)
    )

    .withColumn(
        "sales_last_14_days",
        F.sum("daily_quantity").over(rolling_window_14)
    )

    # Average historical demand
    .withColumn(
        "average_daily_sales",
        F.avg("daily_quantity").over(rolling_window_14)
    )
)

display(
    demand_features
    .orderBy(
        "store_id",
        "product_id",
        "sales_date"
    )
)

# COMMAND ----------

# ============================================
# ADD INVENTORY FEATURES
# ============================================

inventory_features = inventory.select(
    "store_id",
    "product_id",
    "stock_quantity",
    "reorder_level"
)

demand_features = (
    demand_features
    .join(
        inventory_features,
        on=["store_id", "product_id"],
        how="left"
    )
)

display(demand_features)

# COMMAND ----------

demand_features = (
    demand_features
    .fillna({
        "stock_quantity": 0,
        "reorder_level": 0
    })
)

# COMMAND ----------

# ============================================
# ADD PROMOTION FEATURES
# ============================================

promotion_features = (
    promotions
    .groupBy("product_id")
    .agg(
        F.max("discount_percentage")
        .alias("discount_percentage")
    )
)

demand_features = (
    demand_features
    .join(
        promotion_features,
        on="product_id",
        how="left"
    )
    .fillna({
        "discount_percentage": 0.0
    })
)

display(demand_features)

# COMMAND ----------

# Check the current columns
print("Columns in demand_features:")
print(demand_features.columns)

# COMMAND ----------

# ============================================
# CREATE NEXT-DAY DEMAND TARGET
# ============================================

target_window = (
    Window
    .partitionBy("store_id", "product_id")
    .orderBy("sales_date")
)

demand_ml = (
    demand_features
    .withColumn(
        "next_day_demand",
        F.lead("daily_quantity", 1).over(target_window)
    )
)

display(
    demand_ml
    .select(
        "store_id",
        "product_id",
        "sales_date",
        "daily_quantity",
        "previous_day_sales",
        "sales_last_7_days",
        "sales_last_14_days",
        "next_day_demand"
    )
    .orderBy("store_id", "product_id", "sales_date")
)

# COMMAND ----------

# ============================================
# CLEAN ML FEATURE DATASET
# ============================================

ml_dataset = (
    demand_ml
    .filter(F.col("next_day_demand").isNotNull())
    .filter(F.col("previous_day_sales").isNotNull())
    .filter(F.col("sales_last_7_days").isNotNull())
    .filter(F.col("sales_last_14_days").isNotNull())
    .filter(F.col("average_daily_sales").isNotNull())
)

print(
    f"ML dataset rows: {ml_dataset.count()}"
)

# COMMAND ----------

# ============================================
# FINAL MODEL DATASET
# ============================================

model_data = ml_dataset.select(
    "store_id",
    "product_id",
    "category",
    "brand",
    "price",
    "day_of_week",
    "previous_day_sales",
    "sales_last_7_days",
    "sales_last_14_days",
    "average_daily_sales",
    "stock_quantity",
    "reorder_level",
    "discount_percentage",
    "next_day_demand"
)

display(model_data)

# COMMAND ----------

# ============================================
# BUILD SPARK ML PIPELINE
# ============================================

from pyspark.ml import Pipeline
from pyspark.ml.feature import (
    StringIndexer,
    OneHotEncoder,
    VectorAssembler
)
from pyspark.ml.regression import RandomForestRegressor

categorical_columns = [
    "store_id",
    "product_id",
    "category",
    "brand"
]

numeric_columns = [
    "price",
    "day_of_week",
    "previous_day_sales",
    "sales_last_7_days",
    "sales_last_14_days",
    "average_daily_sales",
    "stock_quantity",
    "reorder_level",
    "discount_percentage"
]

indexers = [
    StringIndexer(
        inputCol=column,
        outputCol=f"{column}_index",
        handleInvalid="keep"
    )
    for column in categorical_columns
]

encoders = [
    OneHotEncoder(
        inputCol=f"{column}_index",
        outputCol=f"{column}_encoded"
    )
    for column in categorical_columns
]

assembler = VectorAssembler(
    inputCols=(
        [f"{column}_encoded" for column in categorical_columns]
        + numeric_columns
    ),
    outputCol="features",
    handleInvalid="keep"
)

rf = RandomForestRegressor(
    featuresCol="features",
    labelCol="next_day_demand",
    numTrees=100,
    maxDepth=8,
    seed=42
)

pipeline = Pipeline(
    stages=indexers + encoders + [assembler, rf]
)

print("ML pipeline created successfully.")

# COMMAND ----------

# ============================================
# TIME-BASED TRAIN / TEST SPLIT
# ============================================

max_date = model_data.agg(
    F.max("sales_date")
).collect()[0][0]

split_date = max_date - timedelta(days=30)

train_data = model_data.filter(
    F.col("sales_date") < split_date
)

test_data = model_data.filter(
    F.col("sales_date") >= split_date
)

print(f"Maximum date : {max_date}")
print(f"Split date   : {split_date}")
print(f"Training rows: {train_data.count()}")
print(f"Testing rows : {test_data.count()}")

# COMMAND ----------

print("demand_features columns:")
print(demand_features.columns)

print("\ndemand_ml columns:")
print(demand_ml.columns if "demand_ml" in locals() else "demand_ml does not exist")

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

target_window = (
    Window
    .partitionBy("store_id", "product_id")
    .orderBy("sales_date")
)

demand_ml = (
    demand_features
    .withColumn(
        "next_day_demand",
        F.lead("daily_quantity", 1).over(target_window)
    )
)

print("Target created successfully.")

display(
    demand_ml.select(
        "store_id",
        "product_id",
        "sales_date",
        "daily_quantity",
        "next_day_demand"
    ).limit(20)
)

# COMMAND ----------

# Create a clean copy of demand_ml
model_base = demand_ml.select(
    "sales_date",
    "store_id",
    "product_id",
    "category",
    "brand",
    "price",
    "day_of_week",
    "previous_day_sales",
    "sales_last_7_days",
    "sales_last_14_days",
    "average_daily_sales",
    "stock_quantity",
    "reorder_level",
    "discount_percentage",
    "next_day_demand"
)

print("model_base columns:")
print(model_base.columns)

display(model_base.limit(10))

# COMMAND ----------

model_data = (
    model_base
    .filter(F.col("next_day_demand").isNotNull())
    .filter(F.col("previous_day_sales").isNotNull())
    .filter(F.col("sales_last_7_days").isNotNull())
    .filter(F.col("sales_last_14_days").isNotNull())
    .filter(F.col("average_daily_sales").isNotNull())
)

print("Model dataset created.")
print("Rows:", model_data.count())

display(model_data.limit(20))

# COMMAND ----------

date_range = model_data.agg(
    F.min("sales_date").alias("min_date"),
    F.max("sales_date").alias("max_date")
).collect()[0]

print("Minimum date:", date_range["min_date"])
print("Maximum date:", date_range["max_date"])

# COMMAND ----------

from datetime import timedelta

max_date = date_range["max_date"]
split_date = max_date - timedelta(days=30)

train_data = model_data.filter(
    F.col("sales_date") < split_date
)

test_data = model_data.filter(
    F.col("sales_date") >= split_date
)

print("Split date:", split_date)
print("Training rows:", train_data.count())
print("Testing rows:", test_data.count())

print("\nTraining date range:")
train_data.agg(
    F.min("sales_date").alias("min_date"),
    F.max("sales_date").alias("max_date")
).show()

print("Testing date range:")
test_data.agg(
    F.min("sales_date").alias("min_date"),
    F.max("sales_date").alias("max_date")
).show()

# COMMAND ----------

from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler
from pyspark.ml.regression import RandomForestRegressor

# Categorical features
categorical_cols = [
    "store_id",
    "product_id",
    "category",
    "brand"
]

# Numerical features
numeric_cols = [
    "price",
    "day_of_week",
    "previous_day_sales",
    "sales_last_7_days",
    "sales_last_14_days",
    "average_daily_sales",
    "stock_quantity",
    "reorder_level",
    "discount_percentage"
]

# Create indexers
indexers = [
    StringIndexer(
        inputCol=col,
        outputCol=f"{col}_index",
        handleInvalid="keep"
    )
    for col in categorical_cols
]

# One-hot encode categorical features
encoder = OneHotEncoder(
    inputCols=[f"{col}_index" for col in categorical_cols],
    outputCols=[f"{col}_encoded" for col in categorical_cols]
)

# Combine all features
assembler = VectorAssembler(
    inputCols=(
        numeric_cols +
        [f"{col}_encoded" for col in categorical_cols]
    ),
    outputCol="features",
    handleInvalid="keep"
)

# Random Forest model
rf = RandomForestRegressor(
    featuresCol="features",
    labelCol="next_day_demand",
    predictionCol="prediction",
    numTrees=100,
    maxDepth=8,
    seed=42
)

# Complete ML pipeline
pipeline = Pipeline(
    stages=indexers + [encoder, assembler, rf]
)

print("Random Forest pipeline created successfully.")

# COMMAND ----------

print("Training Random Forest model...")

model = pipeline.fit(train_data)

print("Model training completed successfully.")

# COMMAND ----------

predictions = model.transform(test_data)

print("Predictions generated.")

display(
    predictions.select(
        "sales_date",
        "store_id",
        "product_id",
        "next_day_demand",
        "prediction"
    ).orderBy("sales_date")
)

# COMMAND ----------

from pyspark.ml.evaluation import RegressionEvaluator

# MAE
mae_evaluator = RegressionEvaluator(
    labelCol="next_day_demand",
    predictionCol="prediction",
    metricName="mae"
)

# RMSE
rmse_evaluator = RegressionEvaluator(
    labelCol="next_day_demand",
    predictionCol="prediction",
    metricName="rmse"
)

# R²
r2_evaluator = RegressionEvaluator(
    labelCol="next_day_demand",
    predictionCol="prediction",
    metricName="r2"
)

mae = mae_evaluator.evaluate(predictions)
rmse = rmse_evaluator.evaluate(predictions)
r2 = r2_evaluator.evaluate(predictions)

print("===== MODEL EVALUATION =====")
print(f"MAE  : {mae:.4f}")
print(f"RMSE : {rmse:.4f}")
print(f"R²   : {r2:.4f}")

# COMMAND ----------

demand_predictions = (
    predictions
    .select(
        "sales_date",
        "store_id",
        "product_id",
        "next_day_demand",
        F.round("prediction", 2).alias("predicted_demand")
    )
    .withColumn(
        "prediction_error",
        F.round(
            F.col("next_day_demand") - F.col("predicted_demand"),
            2
        )
    )
)

display(demand_predictions)

# COMMAND ----------

demand_predictions.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("gold.demand_predictions")

print("gold.demand_predictions created successfully.")

# COMMAND ----------

print(
    "Rows in gold.demand_predictions:",
    spark.table("gold.demand_predictions").count()
)

display(
    spark.table("gold.demand_predictions")
    .orderBy("sales_date")
)

# COMMAND ----------

