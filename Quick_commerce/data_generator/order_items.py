import csv
import random
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

MAX_ITEMS_PER_ORDER = 5

PRODUCTS_PER_STORE = 150

OUTPUT_DIR = Path("data/raw")

ORDERS_FILE = OUTPUT_DIR / "orders.csv"
PRODUCTS_FILE = OUTPUT_DIR / "products.csv"

OUTPUT_FILE = OUTPUT_DIR / "order_items.csv"

SEED = 47


# ---------------------------------------------------------
# Load CSV
# ---------------------------------------------------------

def load_csv(file_path):

    with open(
        file_path,
        "r",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        return list(reader)


# ---------------------------------------------------------
# Build store-specific product pools
# ---------------------------------------------------------

def build_store_product_pools(
    orders,
    products
):
    """
    Create a stable product assortment for every store.

    Each store gets its own product pool.
    Orders from that store repeatedly select
    products from the same pool.
    """

    store_ids = sorted(
        {
            order["store_id"]
            for order in orders
        }
    )

    product_ids = [
        product["product_id"]
        for product in products
    ]

    store_product_pools = {}

    for index, store_id in enumerate(store_ids):

        # Use a deterministic seed for every store.
        store_random = random.Random(
            SEED + index
        )

        pool_size = min(
            PRODUCTS_PER_STORE,
            len(product_ids)
        )

        store_product_pools[store_id] = (
            store_random.sample(
                product_ids,
                pool_size
            )
        )

    return store_product_pools


# ---------------------------------------------------------
# Generate order items
# ---------------------------------------------------------

def generate_order_items(
    orders,
    products,
    store_product_pools
):

    order_items = []

    item_counter = 1

    # Fast product lookup
    products_by_id = {
        product["product_id"]: product
        for product in products
    }

    for order in orders:

        store_id = order["store_id"]

        product_pool = [
            products_by_id[product_id]
            for product_id
            in store_product_pools[store_id]
        ]

        number_of_items = random.randint(
            1,
            MAX_ITEMS_PER_ORDER
        )

        selected_products = random.sample(
            product_pool,
            min(
                number_of_items,
                len(product_pool)
            )
        )

        for product in selected_products:

            quantity = random.randint(
                1,
                5
            )

            unit_price = float(
                product["unit_price"]
            )

            discount_percentage = random.uniform(
                0,
                0.20
            )

            gross_amount = (
                quantity
                * unit_price
            )

            discount = round(
                gross_amount
                * discount_percentage,
                2
            )

            line_total = round(
                gross_amount
                - discount,
                2
            )

            item = {

                "order_item_id":
                    f"ITEM{item_counter:08d}",

                "order_id":
                    order["order_id"],

                "product_id":
                    product["product_id"],

                "quantity":
                    quantity,

                "unit_price":
                    unit_price,

                "discount":
                    discount,

                "line_total":
                    line_total,
            }

            order_items.append(item)

            item_counter += 1

    return order_items


# ---------------------------------------------------------
# Save CSV
# ---------------------------------------------------------

def save_order_items(
    order_items,
    output_file
):

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount",
        "line_total",
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

        writer.writerows(order_items)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    random.seed(SEED)

    print("Loading orders...")

    orders = load_csv(
        ORDERS_FILE
    )

    print(
        f"Loaded {len(orders)} orders."
    )

    print("Loading products...")

    products = load_csv(
    PRODUCTS_FILE
)

    print(
        f"Loaded {len(products)} products."
    )

    # ---------------------------------------------------------
    # Use only transaction-ready products
    # ---------------------------------------------------------
    # The raw products file intentionally contains some
    # data-quality issues for the Bronze/Silver pipeline.
    # For transaction generation, exclude products whose
    # unit_price cannot be used to calculate an order line.

    valid_products = []

    for product in products:

        try:
            unit_price = float(
                product["unit_price"]
            )

            if unit_price > 0:
                valid_products.append(product)

        except (TypeError, ValueError):
            continue

    print(
        f"Transaction-ready products: "
        f"{len(valid_products)}"
    )

    print(
        "Building store-specific product pools..."
    )

    store_product_pools = (
    build_store_product_pools(
        orders,
        valid_products
    )
)

    print(
        f"Created product pools for "
        f"{len(store_product_pools)} stores."
    )

    print(
        f"Products per store: "
        f"{PRODUCTS_PER_STORE}"
    )

    print("Generating order items...")

    order_items = generate_order_items(
    orders,
    valid_products,
    store_product_pools
)

    save_order_items(
        order_items,
        OUTPUT_FILE
    )

    print(
        f"Generated {len(order_items)} order items."
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()