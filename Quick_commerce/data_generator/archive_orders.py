import csv
import random
from datetime import date, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NUM_ARCHIVE_ORDERS = 10_000

OUTPUT_DIR = Path("data/raw")

OUTPUT_FILE = (
    OUTPUT_DIR / "archive_orders.csv"
)

SEED = 53


# ---------------------------------------------------------
# Reference data
# ---------------------------------------------------------

ORDER_STATUSES = [
    "Completed",
    "Cancelled",
    "Pending",
]

PAYMENT_TYPES = [
    "UPI",
    "Card",
    "Cash",
    "Wallet",
]


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def random_date(
    start_date,
    end_date
):
    """Generate a random date."""

    days_difference = (
        end_date - start_date
    ).days

    random_days = random.randint(
        0,
        days_difference
    )

    return (
        start_date
        + timedelta(
            days=random_days
        )
    )


def load_ids(
    file_path,
    column_name
):
    """Load IDs from a CSV."""

    with open(
        file_path,
        "r",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        reader = csv.DictReader(
            csv_file
        )

        return [
            row[column_name]
            for row in reader
        ]


# ---------------------------------------------------------
# Generate archive orders
# ---------------------------------------------------------

def generate_archive_orders(
    num_orders,
    customer_ids,
    store_ids
):
    """Generate historical orders."""

    orders = []

    start_date = date(
        2019,
        1,
        1
    )

    end_date = date(
        2021,
        12,
        31
    )

    for i in range(
        1,
        num_orders + 1
    ):

        order = {
            "order_id": (
                f"ARCH_ORD{i:08d}"
            ),

            "customer_id": random.choice(
                customer_ids
            ),

            "store_id": random.choice(
                store_ids
            ),

            "order_date": (
                random_date(
                    start_date,
                    end_date
                ).isoformat()
            ),

            "status": random.choice(
                ORDER_STATUSES
            ),

            "amount": round(
                random.uniform(
                    100,
                    2500
                ),
                2
            ),

            "payment_type": random.choice(
                PAYMENT_TYPES
            ),
        }

        orders.append(order)

    return orders


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

def save_archive_orders(
    orders,
    output_file
):
    """Save archive orders."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "order_id",
        "customer_id",
        "store_id",
        "order_date",
        "status",
        "amount",
        "payment_type",
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

    print(
        "Loading current customer IDs..."
    )

    customer_ids = load_ids(
        Path("data/raw/customers.csv"),
        "customer_id"
    )

    print(
        f"Loaded {len(customer_ids)} "
        "customer IDs."
    )

    print(
        "Loading current store IDs..."
    )

    store_ids = load_ids(
        Path("data/raw/stores.csv"),
        "store_id"
    )

    print(
        f"Loaded {len(store_ids)} "
        "store IDs."
    )

    print(
        "Generating archive orders..."
    )

    orders = generate_archive_orders(
        NUM_ARCHIVE_ORDERS,
        customer_ids,
        store_ids
    )

    save_archive_orders(
        orders,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(orders)} "
        "archive orders."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
