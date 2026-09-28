import os
import sys
import shutil
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    lit,
    current_timestamp,
    to_date,
    sha2,
    concat_ws
)

# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable


# ============================================================
# PATHS
# ============================================================

RAW_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw"
)

BRONZE_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "bronze"
)


# ============================================================
# SPARK
# ============================================================

spark = (
    SparkSession.builder
    .appName("IngestAllBronze")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

print("=" * 70)
print("BATCH BRONZE INGESTION - ALL DATASETS")
print("=" * 70)


# ============================================================
# BATCH ID
# ============================================================

batch_id = datetime.now().strftime(
    "batch_%Y%m%d_%H%M%S"
)

print(f"\nBatch ID: {batch_id}")


# ============================================================
# DISCOVER CSV FILES
# ============================================================

csv_files = [
    file
    for file in os.listdir(RAW_PATH)
    if file.lower().endswith(".csv")
]

csv_files.sort()

print(f"\nCSV files discovered: {len(csv_files)}")

for file in csv_files:
    print(f"  - {file}")


# ============================================================
# PROCESS EACH CSV
# ============================================================

summary = []

for filename in csv_files:

    print("\n" + "=" * 70)
    print(f"PROCESSING: {filename}")
    print("=" * 70)

    source_file = os.path.join(
        RAW_PATH,
        filename
    )

    dataset_name = os.path.splitext(filename)[0]

    output_directory = os.path.join(
        BRONZE_PATH,
        f"{dataset_name}_csv"
    )

    output_file = os.path.join(
        output_directory,
        filename
    )

    # --------------------------------------------------------
    # Read raw CSV
    # --------------------------------------------------------

    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(source_file)
    )

    raw_count = df.count()

    print(f"Raw records: {raw_count}")

    # --------------------------------------------------------
    # Add Bronze metadata
    # --------------------------------------------------------

    df_bronze = (
        df
        .withColumn(
            "source_file",
            lit(filename)
        )
        .withColumn(
            "source_system",
            lit("local_csv")
        )
        .withColumn(
            "ingestion_timestamp",
            current_timestamp()
        )
        .withColumn(
            "batch_id",
            lit(batch_id)
        )
        .withColumn(
            "ingestion_date",
            to_date(current_timestamp())
        )
    )

    # --------------------------------------------------------
    # Record hash
    # --------------------------------------------------------

    original_columns = df.columns

    df_bronze = df_bronze.withColumn(
        "record_hash",
        sha2(
            concat_ws(
                "||",
                *[
                    col(c).cast("string")
                    for c in original_columns
                ]
            ),
            256
        )
    )

    # --------------------------------------------------------
    # Prepare output directory
    # --------------------------------------------------------

    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    # --------------------------------------------------------
    # CSV persistence
    # --------------------------------------------------------

    bronze_pdf = df_bronze.toPandas()

    bronze_pdf.to_csv(
        output_file,
        index=False
    )

    bronze_count = len(bronze_pdf)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if raw_count == bronze_count:
        status = "PASSED"
    else:
        status = "FAILED"

    print(f"Bronze records: {bronze_count}")
    print(f"Reconciliation: {status}")
    print(f"Output: {output_file}")

    summary.append({
        "dataset": dataset_name,
        "raw_records": raw_count,
        "bronze_records": bronze_count,
        "status": status
    })


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("BRONZE INGESTION SUMMARY")
print("=" * 70)

total_raw = 0
total_bronze = 0

for item in summary:

    total_raw += item["raw_records"]
    total_bronze += item["bronze_records"]

    print(
        f"{item['dataset']:<30}"
        f"Raw: {item['raw_records']:<8}"
        f"Bronze: {item['bronze_records']:<8}"
        f"{item['status']}"
    )

print("-" * 70)

print(f"Total raw records    : {total_raw}")
print(f"Total bronze records : {total_bronze}")

if total_raw == total_bronze:
    print("OVERALL RECONCILIATION: PASSED")
else:
    print("OVERALL RECONCILIATION: FAILED")


spark.stop()

print("\n" + "=" * 70)
print("ALL BRONZE INGESTION COMPLETED")
print("=" * 70)
