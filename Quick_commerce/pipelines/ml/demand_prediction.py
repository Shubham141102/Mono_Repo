import os
import sys
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

import pandas as pd

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.window import Window

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

ML = ROOT / "data" / "ml"

ML.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# SPARK SESSION
# =========================================================

spark = (
    SparkSession.builder
    .appName("Product_Store_Demand_Prediction")
    .master("local[4]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# =========================================================
# HELPER
# =========================================================

def read_ml_dataset(name):

    path = ML / name / "data.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"ML dataset not found: {path}"
        )

    return (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(str(path))
    )


def save_pandas(df, name):

    path = ML / name

    path.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        path / "data.csv",
        index=False
    )

    print(
        f"{name:<30} {len(df)} rows"
    )


# =========================================================
# START
# =========================================================

print("=" * 70)
print("BUILDING CALENDAR-AWARE PRODUCT-STORE DEMAND PREDICTION")
print("=" * 70)


# =========================================================
# READ DEMAND FEATURES
# =========================================================

demand = read_ml_dataset(
    "product_store_daily_demand"
)

print(
    f"Original demand rows : {demand.count()}"
)


# =========================================================
# PREPARE DATA TYPES
# =========================================================

demand = (
    demand

    .withColumn(
        "sales_date",
        F.to_date("sales_date")
    )

    .withColumn(
        "daily_quantity",
        F.col("daily_quantity").cast("double")
    )

    .withColumn(
        "daily_revenue",
        F.col("daily_revenue").cast("double")
    )

    .withColumn(
        "daily_orders",
        F.col("daily_orders").cast("double")
    )

    .withColumn(
        "average_unit_price",
        F.col("average_unit_price").cast("double")
    )

    .withColumn(
        "daily_discount",
        F.col("daily_discount").cast("double")
    )
)


# =========================================================
# FIND ACTIVE PRODUCT-STORE PAIRS
# =========================================================

pairs = (
    demand
    .select(
        "store_id",
        "product_id"
    )
    .distinct()
)

pair_count = pairs.count()

print(
    f"Active product-store pairs : {pair_count}"
)


# =========================================================
# CREATE CALENDAR FOR EACH ACTIVE PAIR
# =========================================================

date_bounds = demand.agg(
    F.min("sales_date").alias("min_date"),
    F.max("sales_date").alias("max_date")
).collect()[0]

min_date = date_bounds["min_date"]
max_date = date_bounds["max_date"]

print(
    f"Calendar range             : {min_date} to {max_date}"
)


calendar = (
    spark
    .range(1)
    .select(
        F.explode(
            F.sequence(
                F.lit(min_date),
                F.lit(max_date),
                F.expr("INTERVAL 1 DAY")
            )
        ).alias("sales_date")
    )
)


# =========================================================
# PRODUCT-STORE × CALENDAR GRID
# =========================================================

calendarized = (
    pairs
    .crossJoin(calendar)
)


print(
    f"Calendarized rows          : {calendarized.count()}"
)


# =========================================================
# JOIN ACTUAL SALES
# =========================================================

calendarized = (
    calendarized
    .join(
        demand,
        on=[
            "store_id",
            "product_id",
            "sales_date"
        ],
        how="left"
    )
)


# =========================================================
# FILL MISSING SALES DAYS
# =========================================================

calendarized = (
    calendarized

    .withColumn(
        "daily_quantity",
        F.coalesce(
            F.col("daily_quantity"),
            F.lit(0.0)
        )
    )

    .withColumn(
        "daily_revenue",
        F.coalesce(
            F.col("daily_revenue"),
            F.lit(0.0)
        )
    )

    .withColumn(
        "daily_orders",
        F.coalesce(
            F.col("daily_orders"),
            F.lit(0.0)
        )
    )

    .withColumn(
        "average_unit_price",
        F.coalesce(
            F.col("average_unit_price"),
            F.lit(0.0)
        )
    )

    .withColumn(
        "daily_discount",
        F.coalesce(
            F.col("daily_discount"),
            F.lit(0.0)
        )
    )
)


# =========================================================
# CALENDAR FEATURES
# =========================================================

calendarized = (
    calendarized

    .withColumn(
        "day_of_week",
        F.dayofweek("sales_date")
    )

    .withColumn(
        "day_of_month",
        F.dayofmonth("sales_date")
    )

    .withColumn(
        "month",
        F.month("sales_date")
    )

    .withColumn(
        "week_of_year",
        F.weekofyear("sales_date")
    )
)


# =========================================================
# PRODUCT + STORE WINDOW
# =========================================================

window_spec = (
    Window
    .partitionBy(
        "store_id",
        "product_id"
    )
    .orderBy(
        "sales_date"
    )
)


# =========================================================
# CALENDAR-AWARE LAG FEATURES
# =========================================================

calendarized = (
    calendarized

    .withColumn(
        "previous_day_sales",
        F.lag(
            "daily_quantity",
            1
        ).over(window_spec)
    )

    .withColumn(
        "sales_7_days_ago",
        F.lag(
            "daily_quantity",
            7
        ).over(window_spec)
    )

    .withColumn(
        "sales_14_days_ago",
        F.lag(
            "daily_quantity",
            14
        ).over(window_spec)
    )
)


# =========================================================
# CALENDAR-AWARE ROLLING WINDOWS
# =========================================================

calendarized = (
    calendarized

    .withColumn(
        "date_number",
        F.datediff(
            F.col("sales_date"),
            F.lit("1970-01-01")
        )
    )
)


rolling_window_7 = (
    Window
    .partitionBy(
        "store_id",
        "product_id"
    )
    .orderBy(
        F.col("date_number")
    )
    .rangeBetween(
        -7,
        -1
    )
)


rolling_window_14 = (
    Window
    .partitionBy(
        "store_id",
        "product_id"
    )
    .orderBy(
        F.col("date_number")
    )
    .rangeBetween(
        -14,
        -1
    )
)
# =========================================================
# INTERMITTENT DEMAND WINDOW
# =========================================================

rolling_window_7_current = (
    Window
    .partitionBy(
        "store_id",
        "product_id"
    )
    .orderBy(
        F.col("date_number")
    )
    .rangeBetween(
        -7,
        0
    )
)


rolling_window_14_current = (
    Window
    .partitionBy(
        "store_id",
        "product_id"
    )
    .orderBy(
        F.col("date_number")
    )
    .rangeBetween(
        -14,
        0
    )
)

# =========================================================
# ROLLING FEATURES
# =========================================================

calendarized = (
    calendarized
        .withColumn(
        "is_weekend",
        F.when(
            F.dayofweek("sales_date").isin([1, 7]),
            1
        ).otherwise(0)
    )

    .withColumn(
        "nonzero_days_last_7",
        F.sum(
            F.when(
                F.col("daily_quantity") > 0,
                1
            ).otherwise(0)
        ).over(
            rolling_window_7_current
        )
    )

    .withColumn(
        "nonzero_days_last_14",
        F.sum(
            F.when(
                F.col("daily_quantity") > 0,
                1
            ).otherwise(0)
        ).over(
            rolling_window_14_current
        )
    )

    .withColumn(
        "demand_std_14_days",
        F.stddev(
            "daily_quantity"
        ).over(
            rolling_window_14
        )
    )
    .withColumn(
        "sales_last_7_days",
        F.sum(
            "daily_quantity"
        ).over(
            rolling_window_7
        )
    )

    .withColumn(
        "sales_last_14_days",
        F.sum(
            "daily_quantity"
        ).over(
            rolling_window_14
        )
    )

    .withColumn(
        "average_daily_sales",
        F.avg(
            "daily_quantity"
        ).over(
            rolling_window_7
        )
    )
)


# =========================================================
# TARGET
# =========================================================

calendarized = (
    calendarized
    .withColumn(
        "next_day_demand",
        F.lead(
            "daily_quantity",
            1
        ).over(
            window_spec
        )
    )
)


# =========================================================
# SAVE CALENDARIZED DATASET
# =========================================================

# =========================================================
# SAVE CALENDARIZED DATASET
# =========================================================




# =========================================================
# REMOVE INCOMPLETE MODEL RECORDS
# =========================================================

model_df = calendarized.dropna(
    subset=[
        "previous_day_sales",
        "sales_7_days_ago",
        "sales_14_days_ago",
        "sales_last_7_days",
        "sales_last_14_days",
        "average_daily_sales",
        "next_day_demand"
    ]
)


print()
print(
    f"Model rows : {model_df.count()}"
)


# =========================================================
# MODEL FEATURES
# =========================================================

feature_columns = [

    "previous_day_sales",

    "sales_7_days_ago",

    "sales_14_days_ago",

    "sales_last_7_days",

    "sales_last_14_days",

    "average_daily_sales",

    "demand_std_14_days",

    "nonzero_days_last_7",

    "nonzero_days_last_14",

    "is_weekend",

    "day_of_week",

    "day_of_month",

    "month",

    "week_of_year",

    "daily_orders",

    "average_unit_price",

    "daily_discount"
]

# =========================================================
# CONVERT MODEL DATA TO PANDAS
# =========================================================

# =========================================================
# CONVERT MODEL DATA TO PANDAS
# =========================================================

# =========================================================
# TIME-BASED TRAIN / TEST SPLIT
# =========================================================

split_date = (
    model_df
    .select(
        F.expr(
            "percentile_approx(sales_date, 0.80)"
        ).alias("split_date")
    )
    .collect()[0]["split_date"]
)

print()
print("=" * 70)
print("TRAIN / TEST SPLIT")
print("=" * 70)

print(
    f"Split date : {split_date}"
)


# =========================================================
# CONVERT ONLY TRAINING DATA TO PANDAS
# =========================================================

train_df = (
    model_df
    .filter(
        F.col("sales_date") < F.lit(split_date)
    )
    .select(
        "store_id",
        "product_id",
        "sales_date",
        *feature_columns,
        "next_day_demand"
    )
    .toPandas()
)


# =========================================================
# CONVERT ONLY TEST DATA TO PANDAS
# =========================================================

test_df = (
    model_df
    .filter(
        F.col("sales_date") >= F.lit(split_date)
    )
    .select(
        "store_id",
        "product_id",
        "sales_date",
        *feature_columns,
        "next_day_demand"
    )
    .toPandas()
)


print(
    f"Training   : {len(train_df)}"
)

print(
    f"Testing    : {len(test_df)}"
)


print()
print("=" * 70)
print("TRAIN / TEST SPLIT")
print("=" * 70)

print(
    f"Split date : {split_date}"
)

print(
    f"Training   : {len(train_df)}"
)

print(
    f"Testing    : {len(test_df)}"
)


# =========================================================
# PREPARE X / Y
# =========================================================

X_train = train_df[
    feature_columns
]

y_train = train_df[
    "next_day_demand"
]


X_test = test_df[
    feature_columns
]

y_test = test_df[
    "next_day_demand"
]


# =========================================================
# TRAIN RANDOM FOREST
# =========================================================

print()
print(
    "TRAINING RANDOM FOREST MODEL..."
)


model = RandomForestRegressor(

    n_estimators=100,

    max_depth=12,

    min_samples_leaf=2,

    random_state=42,

    n_jobs=-1
)


model.fit(
    X_train,
    y_train
)


# =========================================================
# PREDICTIONS
# =========================================================

predictions = model.predict(
    X_test
)


test_df[
    "predicted_demand"
] = predictions


# =========================================================
# EVALUATION
# =========================================================

mae = mean_absolute_error(
    y_test,
    predictions
)


rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5


r2 = r2_score(
    y_test,
    predictions
)


print()
print(
    "MODEL EVALUATION"
)

print(
    "-" * 45
)

print(
    f"MAE  : {mae:.4f}"
)

print(
    f"RMSE : {rmse:.4f}"
)

print(
    f"R2   : {r2:.4f}"
)


# =========================================================
# FEATURE IMPORTANCE
# =========================================================

feature_importance = (
    pd.DataFrame({

        "feature":
        feature_columns,

        "importance":
        model.feature_importances_

    })

    .sort_values(
        "importance",
        ascending=False
    )
)


# =========================================================
# SAVE PREDICTIONS
# =========================================================

save_pandas(

    test_df[
        [
            "store_id",

            "product_id",

            "sales_date",

            "next_day_demand",

            "predicted_demand"
        ]
    ],

    "demand_predictions"
)


# =========================================================
# SAVE FEATURE IMPORTANCE
# =========================================================

save_pandas(

    feature_importance,

    "feature_importance"
)


# =========================================================
# SAVE MODEL METRICS
# =========================================================

metrics = pd.DataFrame([{

    "model":
    "RandomForestRegressor",

    "training_rows":
    len(train_df),

    "testing_rows":
    len(test_df),

    "features":
    len(feature_columns),

    "mae":
    round(mae, 4),

    "rmse":
    round(rmse, 4),

    "r2":
    round(r2, 4)

}])


save_pandas(
    metrics,
    "model_metrics"
)


# =========================================================
# SUMMARY
# =========================================================

print()
print("=" * 70)
print("PRODUCT-STORE DEMAND PREDICTION COMPLETED")
print("=" * 70)

print(
    f"Active pairs          : {pair_count}"
)

print(
    f"Calendarized rows     : {calendarized.count()}"
)

print(
    f"Training rows         : {len(train_df)}"
)

print(
    f"Testing rows          : {len(test_df)}"
)

print(
    f"MAE                   : {mae:.4f}"
)

print(
    f"RMSE                  : {rmse:.4f}"
)

print(
    f"R2                    : {r2:.4f}"
)


spark.stop()