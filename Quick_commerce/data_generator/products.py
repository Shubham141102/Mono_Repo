import csv
import random
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

NUM_PRODUCTS = 1_000

OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "products.csv"

SEED = 43


# ---------------------------------------------------------
# Product reference data
# ---------------------------------------------------------

PRODUCT_CATALOG = [
    ("Dairy", "Milk", "Amul"),
    ("Dairy", "Curd", "Mother Dairy"),
    ("Dairy", "Cheese", "Amul"),
    ("Beverages", "Soft Drinks", "Coca-Cola"),
    ("Beverages", "Juice", "Real"),
    ("Beverages", "Energy Drinks", "Red Bull"),
    ("Snacks", "Chips", "Lays"),
    ("Snacks", "Biscuits", "Parle"),
    ("Snacks", "Namkeen", "Haldiram"),
    ("Fruits", "Fresh Fruits", "Fresho"),
    ("Vegetables", "Fresh Vegetables", "Fresho"),
    ("Bakery", "Bread", "Britannia"),
    ("Bakery", "Cakes", "Monginis"),
    ("Personal Care", "Shampoo", "Dove"),
    ("Personal Care", "Soap", "Lux"),
    ("Household", "Cleaning", "Harpic"),
    ("Household", "Laundry", "Surf Excel"),
    ("Grocery", "Rice", "India Gate"),
    ("Grocery", "Atta", "Aashirvaad"),
    ("Grocery", "Cooking Oil", "Fortune"),
]

PRODUCT_NAMES = [
    "Classic",
    "Premium",
    "Fresh",
    "Organic",
    "Daily",
    "Family",
    "Original",
    "Natural",
    "Special",
    "Value",
]


UNITS = [
    "piece",
    "pack",
    "kg",
    "gram",
    "litre",
    "ml",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def generate_product_name(category, subcategory, brand, index):
    """
    Generate a readable product name.
    """

    style = random.choice(PRODUCT_NAMES)

    return (
        f"{brand} {style} "
        f"{subcategory} {index}"
    )


def generate_price():
    """
    Generate a realistic selling price.
    """

    return round(
        random.uniform(20, 2000),
        2
    )


# ---------------------------------------------------------
# Product generation
# ---------------------------------------------------------

def generate_products(num_products):
    """
    Generate product records.
    """

    products = []

    for i in range(1, num_products + 1):

        category, subcategory, brand = random.choice(
            PRODUCT_CATALOG
        )

        unit_price = generate_price()

        # Cost price is lower than selling price.
        cost_price = round(
            unit_price * random.uniform(0.55, 0.85),
            2
        )

        product = {
            "product_id": f"PROD{i:06d}",

            "product_name": generate_product_name(
                category,
                subcategory,
                brand,
                i
            ),

            "category": category,

            "subcategory": subcategory,

            "brand": brand,

            "unit_price": unit_price,

            "cost_price": cost_price,

            "unit": random.choice(UNITS),

            "is_active": random.choice(
                [True, True, True, False]
            ),
        }

        products.append(product)

    return products


# ---------------------------------------------------------
# CSV writer
# ---------------------------------------------------------

def save_products(products, output_file):
    """
    Save product records to CSV.
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "product_id",
        "product_name",
        "category",
        "subcategory",
        "brand",
        "unit_price",
        "cost_price",
        "unit",
        "is_active",
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

        writer.writerows(products)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    random.seed(SEED)

    print("Generating products...")

    products = generate_products(
        NUM_PRODUCTS
    )

    save_products(
        products,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(products)} products."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
