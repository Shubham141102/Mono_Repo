import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NUM_ORDERS = 100_000

OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "orders.csv"

CUSTOMERS_FILE = OUTPUT_DIR / "customers.csv"
STORES_FILE = OUTPUT_DIR / "stores.csv"

SEED = 46


# ---------------------------------------------------------
# Reference data
# ---------------------------------------------------------

ORDER_STATUSES = [
    "Placed",
    "Confirmed",
    "Preparing",
    "Out for Delivery",
    "Delivered",
    "Cancelled",
]

# More realistic than equal probability.
# Delivered orders are the realized demand used by ML.
ORDER_STATUS_WEIGHTS = [
    0.04,   # Placed
    0.06,   # Confirmed
    0.07,   # Preparing
    0.08,   # Out for Delivery
    0.70,   # Delivered
    0.05,   # Cancelled
]

PAYMENT_METHODS = [
    "UPI",
    "Credit Card",
    "Debit Card",
    "Cash",
    "Wallet",
]

DELIVERY_TYPES = [
    "Standard",
    "Express",
]


# ---------------------------------------------------------
# Load reference IDs
# ---------------------------------------------------------

def load_ids(file_path, column_name):

    with open(
        file_path,
        "r",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        return [
            row[column_name]
            for row in reader
        ]


# ---------------------------------------------------------
# Timestamp generation
# ---------------------------------------------------------

def random_timestamp(start_date, end_date):

    total_seconds = int(
        (end_date - start_date).total_seconds()
    )

    random_seconds = random.randint(
        0,
        total_seconds
    )

    return (
        start_date
        + timedelta(seconds=random_seconds)
    )


# ---------------------------------------------------------
# Amount generation
# ---------------------------------------------------------

def generate_total_amount():

    return round(
        random.uniform(100, 3000),
        2
    )


# ---------------------------------------------------------
# Order generation
# ---------------------------------------------------------

def generate_orders(
    num_orders,
    customer_ids,
    store_ids
):

    orders = []

    start_date = datetime(
        2025,
        1,
        1
    )

    end_date = datetime(
        2025,
        12,
        31,
        23,
        59,
        59
    )

    for i in range(
        1,
        num_orders + 1
    ):

        order_status = random.choices(
            ORDER_STATUSES,
            weights=ORDER_STATUS_WEIGHTS,
            k=1
        )[0]

        order = {

            "order_id":
                f"ORD{i:08d}",

            "customer_id":
                random.choice(customer_ids),

            "store_id":
                random.choice(store_ids),

            "order_timestamp":
                random_timestamp(
                    start_date,
                    end_date
                ).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "order_status":
                order_status,

            "total_amount":
                generate_total_amount(),

            "payment_method":
                random.choice(
                    PAYMENT_METHODS
                ),

            "delivery_type":
                random.choice(
                    DELIVERY_TYPES
                ),
        }

        orders.append(order)

    return orders


# ---------------------------------------------------------
# CSV writer
# ---------------------------------------------------------

def save_orders(
    orders,
    output_file
):

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "order_id",
        "customer_id",
        "store_id",
        "order_timestamp",
        "order_status",
        "total_amount",
        "payment_method",
        "delivery_type",
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(orders)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    random.seed(SEED)

    print("Loading customer IDs...")

    customer_ids = load_ids(
        CUSTOMERS_FILE,
        "customer_id"
    )

    print(
        f"Loaded {len(customer_ids)} customers."
    )

    print("Loading store IDs...")

    store_ids = load_ids(
        STORES_FILE,
        "store_id"
    )

    print(
        f"Loaded {len(store_ids)} stores."
    )

    print("Generating orders...")

    orders = generate_orders(
        NUM_ORDERS,
        customer_ids,
        store_ids
    )

    save_orders(
        orders,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(orders)} orders."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()