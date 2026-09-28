import csv
import random
import string
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NUM_EVENTS = 200_000

OUTPUT_DIR = Path("data/raw")

CUSTOMERS_FILE = OUTPUT_DIR / "customers.csv"
PRODUCTS_FILE = OUTPUT_DIR / "products.csv"
STORES_FILE = OUTPUT_DIR / "stores.csv"

OUTPUT_FILE = OUTPUT_DIR / "customer_events.csv"

SEED = 50


# ---------------------------------------------------------
# Event reference data
# ---------------------------------------------------------

EVENT_TYPES = [
    "app_open",
    "search",
    "product_view",
    "add_to_cart",
    "remove_from_cart",
    "purchase",
]

DEVICE_TYPES = [
    "Android",
    "iOS",
    "Web",
]

SEARCH_EVENT_TYPES = {
    "app_open",
    "search",
}

PRODUCT_EVENT_TYPES = {
    "product_view",
    "add_to_cart",
    "remove_from_cart",
    "purchase",
}


# ---------------------------------------------------------
# CSV loader
# ---------------------------------------------------------

def load_ids(file_path, column_name):
    """Load a single ID column from a CSV file."""

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
# Session ID
# ---------------------------------------------------------

def generate_session_id():
    """Generate a simulated session identifier."""

    characters = string.ascii_uppercase + string.digits

    random_part = "".join(
        random.choices(
            characters,
            k=8
        )
    )

    return f"SES{random_part}"


# ---------------------------------------------------------
# Event timestamp
# ---------------------------------------------------------

def random_timestamp(
    start_date,
    end_date
):
    """Generate a random event timestamp."""

    total_seconds = int(
        (
            end_date - start_date
        ).total_seconds()
    )

    random_seconds = random.randint(
        0,
        total_seconds
    )

    return (
        start_date
        + timedelta(
            seconds=random_seconds
        )
    )


# ---------------------------------------------------------
# Event generation
# ---------------------------------------------------------

def generate_customer_events(
    num_events,
    customer_ids,
    product_ids,
    store_ids
):
    """Generate customer activity events."""

    events = []

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
        num_events + 1
    ):

        event_type = random.choice(
            EVENT_TYPES
        )

        event = {
            "event_id": (
                f"EVT{i:08d}"
            ),

            "customer_id": random.choice(
                customer_ids
            ),

            "event_timestamp": (
                random_timestamp(
                    start_date,
                    end_date
                ).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ),

            "event_type": event_type,

            "product_id": "",

            "store_id": "",

            "session_id": (
                generate_session_id()
            ),

            "device_type": random.choice(
                DEVICE_TYPES
            ),
        }

        # Product-related events
        if event_type in PRODUCT_EVENT_TYPES:

            event["product_id"] = random.choice(
                product_ids
            )

            event["store_id"] = random.choice(
                store_ids
            )

        # Search events intentionally don't
        # require a product or store.

        events.append(event)

    return events


# ---------------------------------------------------------
# CSV writer
# ---------------------------------------------------------

def save_events(
    events,
    output_file
):
    """Save customer events to CSV."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "event_id",
        "customer_id",
        "event_timestamp",
        "event_type",
        "product_id",
        "store_id",
        "session_id",
        "device_type",
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

        writer.writerows(events)


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

    print("Loading product IDs...")

    product_ids = load_ids(
        PRODUCTS_FILE,
        "product_id"
    )

    print(
        f"Loaded {len(product_ids)} products."
    )

    print("Loading store IDs...")

    store_ids = load_ids(
        STORES_FILE,
        "store_id"
    )

    print(
        f"Loaded {len(store_ids)} stores."
    )

    print("Generating customer events...")

    events = generate_customer_events(
        NUM_EVENTS,
        customer_ids,
        product_ids,
        store_ids
    )

    save_events(
        events,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(events)} customer events."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
