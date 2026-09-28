import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

OUTPUT_DIR = Path("data/raw")

STORES_FILE = OUTPUT_DIR / "stores.csv"
PRODUCTS_FILE = OUTPUT_DIR / "products.csv"

OUTPUT_FILE = OUTPUT_DIR / "inventory.csv"

SEED = 49


# ---------------------------------------------------------
# Load CSV
# ---------------------------------------------------------

def load_csv(file_path):
    """Load CSV records into a list of dictionaries."""

    with open(
        file_path,
        "r",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        return list(reader)


# ---------------------------------------------------------
# Generate restock date
# ---------------------------------------------------------

def random_date(start_date, end_date):
    """Generate a random date between two dates."""

    days_difference = (
        end_date - start_date
    ).days

    random_days = random.randint(
        0,
        days_difference
    )

    return (
        start_date
        + timedelta(days=random_days)
    )


# ---------------------------------------------------------
# Generate inventory
# ---------------------------------------------------------

def generate_inventory(
    stores,
    products
):
    """
    Generate inventory records.

    One record represents one product
    at one store.
    """

    inventory = []

    inventory_counter = 1

    start_date = date(
        2025,
        1,
        1
    )

    end_date = date(
        2025,
        12,
        31
    )

    updated_at = datetime(
        2025,
        12,
        31,
        23,
        59,
        59
    )

    for store in stores:

        for product in products:

            quantity_on_hand = random.randint(
                0,
                200
            )

            reorder_level = random.randint(
                10,
                50
            )

            unit_cost = float(
                product["cost_price"]
            )

            inventory_value = round(
                quantity_on_hand
                * unit_cost,
                2
            )

            last_restocked = random_date(
                start_date,
                end_date
            )

            record = {
                "inventory_id": (
                    f"INV{inventory_counter:08d}"
                ),

                "store_id": store["store_id"],

                "product_id": product["product_id"],

                "quantity_on_hand": (
                    quantity_on_hand
                ),

                "reorder_level": (
                    reorder_level
                ),

                "unit_cost": unit_cost,

                "inventory_value": (
                    inventory_value
                ),

                "last_restocked": (
                    last_restocked.isoformat()
                ),

                "updated_at": (
                    updated_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ),
            }

            inventory.append(record)

            inventory_counter += 1

    return inventory


# ---------------------------------------------------------
# Save CSV
# ---------------------------------------------------------

def save_inventory(
    inventory,
    output_file
):
    """Save inventory records to CSV."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "inventory_id",
        "store_id",
        "product_id",
        "quantity_on_hand",
        "reorder_level",
        "unit_cost",
        "inventory_value",
        "last_restocked",
        "updated_at",
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

        writer.writerows(inventory)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    random.seed(SEED)

    print("Loading stores...")

    stores = load_csv(
        STORES_FILE
    )

    print(
        f"Loaded {len(stores)} stores."
    )

    print("Loading products...")

    products = load_csv(
        PRODUCTS_FILE
    )

    print(
        f"Loaded {len(products)} products."
    )

    print("Generating inventory...")

    inventory = generate_inventory(
        stores,
        products
    )

    save_inventory(
        inventory,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(inventory)} "
        "inventory records."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()