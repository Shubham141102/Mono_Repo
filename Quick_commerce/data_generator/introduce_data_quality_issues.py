import pandas as pd
import random
from pathlib import Path


RAW_DIR = Path("data/raw")
DIRTY_DIR = Path("data/raw_dirty")

DIRTY_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
random.seed(SEED)


def pick_indices(df, n, exclude=None):
    exclude = set(exclude or [])
    available = [i for i in df.index if i not in exclude]
    return random.sample(available, min(n, len(available)))


# =========================================================
# Customers
# =========================================================

def corrupt_customers():
    df = pd.read_csv(RAW_DIR / "customers.csv")
    used = set()

    # These demonstrate NULL, empty-string, whitespace and
    # inconsistent capitalization. Standardization should fix
    # some of these; NULL/empty values should be quarantined.
    for idx in pick_indices(df, 25, used):
        df.loc[idx, "city"] = None
        used.add(idx)

    for idx in pick_indices(df, 25, used):
        df.loc[idx, "city"] = ""
        used.add(idx)

    for idx in pick_indices(df, 25, used):
        df.loc[idx, "city"] = "   "
        used.add(idx)

    city_variations = [" delhi ", "DELHI", "Delhi ", " mumbai", "HYDERABAD"]
    for idx, value in zip(pick_indices(df, 50, used), city_variations * 10):
        df.loc[idx, "city"] = value
        used.add(idx)

    # Invalid business keys / values
    for idx in pick_indices(df, 25, used):
        df.loc[idx, "customer_id"] = f"BAD_CUST_{idx}"
        used.add(idx)

    for idx in pick_indices(df, 25, used):
        df.loc[idx, "customer_segment"] = "UnknownSegment"
        used.add(idx)

    df.to_csv(DIRTY_DIR / "customers.csv", index=False)
    print(f"Customers: {len(used)} affected records")


# =========================================================
# Products
# =========================================================

def corrupt_products():
    df = pd.read_csv(RAW_DIR / "products.csv")
    used = set()

    # Numeric/range/business-rule violations
    for idx in pick_indices(df, 10, used):
        df.loc[idx, "unit_price"] = -100
        used.add(idx)

    for idx in pick_indices(df, 10, used):
        df.loc[idx, "cost_price"] = -50
        used.add(idx)

    # Cost greater than selling price
    for idx in pick_indices(df, 10, used):
        df.loc[idx, "cost_price"] = df.loc[idx, "unit_price"] + 100
        used.add(idx)

    # NULL and empty values
    for idx in pick_indices(df, 5, used):
        df.loc[idx, "unit_price"] = None
        used.add(idx)

    for idx in pick_indices(df, 5, used):
        df.loc[idx, "product_name"] = ""
        used.add(idx)

    # Invalid categorical value
    for idx in pick_indices(df, 10, used):
        df.loc[idx, "unit"] = "invalid_unit"
        used.add(idx)

    # Formatting noise that Silver should standardize
    for idx in pick_indices(df, 20, used):
        df.loc[idx, "category"] = f"  {str(df.loc[idx, 'category']).upper()}  "
        used.add(idx)

    df.to_csv(DIRTY_DIR / "products.csv", index=False)
    print(f"Products: {len(used)} affected records")


# =========================================================
# Orders
# =========================================================

def corrupt_orders():
    df = pd.read_csv(RAW_DIR / "orders.csv")
    used = set()

    # Duplicate 250 existing orders
    duplicates = df.sample(250, random_state=SEED)
    df = pd.concat([df, duplicates], ignore_index=True)

    # Invalid customer foreign keys
    for idx in pick_indices(df, 250, used):
        df.loc[idx, "customer_id"] = f"INVALID_CUSTOMER_{idx}"
        used.add(idx)

    # Invalid store foreign keys
    for idx in pick_indices(df, 200, used):
        df.loc[idx, "store_id"] = f"INVALID_STORE_{idx}"
        used.add(idx)

    # Invalid timestamps
    for idx in pick_indices(df, 150, used):
        df.loc[idx, "order_timestamp"] = "INVALID_TIMESTAMP"
        used.add(idx)

    # Invalid/negative amounts
    for idx in pick_indices(df, 150, used):
        df.loc[idx, "total_amount"] = -abs(float(df.loc[idx, "total_amount"]))
        used.add(idx)

    # Invalid order status
    for idx in pick_indices(df, 150, used):
        df.loc[idx, "order_status"] = "UnknownStatus"
        used.add(idx)

    # Invalid payment method
    for idx in pick_indices(df, 150, used):
        df.loc[idx, "payment_method"] = "Crypto"
        used.add(idx)

    # Invalid delivery type
    for idx in pick_indices(df, 100, used):
        df.loc[idx, "delivery_type"] = "Drone"
        used.add(idx)

    # Formatting noise
    for idx in pick_indices(df, 100, used):
        df.loc[idx, "order_status"] = f"  {str(df.loc[idx, 'order_status']).lower()}  "
        used.add(idx)

    df.to_csv(DIRTY_DIR / "orders.csv", index=False)
    print(
        f"Orders: {len(used)} directly corrupted records + "
        f"{len(duplicates)} duplicate rows"
    )


# =========================================================
# Order Items
# =========================================================

def corrupt_order_items():
    df = pd.read_csv(RAW_DIR / "order_items.csv")
    used = set()

    # Negative quantities
    for idx in pick_indices(df, 800, used):
        df.loc[idx, "quantity"] = -abs(int(df.loc[idx, "quantity"]))
        used.add(idx)

    # Negative unit prices
    for idx in pick_indices(df, 700, used):
        df.loc[idx, "unit_price"] = -abs(float(df.loc[idx, "unit_price"]))
        used.add(idx)

    # Invalid order foreign keys
    for idx in pick_indices(df, 700, used):
        df.loc[idx, "order_id"] = f"INVALID_ORDER_{idx}"
        used.add(idx)

    # Invalid product foreign keys
    for idx in pick_indices(df, 600, used):
        df.loc[idx, "product_id"] = f"INVALID_PRODUCT_{idx}"
        used.add(idx)

    # Invalid discount/range values
    for idx in pick_indices(df, 500, used):
        df.loc[idx, "discount"] = 150
        used.add(idx)

    # Empty/whitespace IDs
    for idx in pick_indices(df, 400, used):
        df.loc[idx, "product_id"] = "   "
        used.add(idx)

    # Duplicate item IDs
    duplicate_indices = df.sample(300, random_state=SEED + 1).index
    source_indices = df.sample(300, random_state=SEED + 2).index
    for target, source in zip(duplicate_indices, source_indices):
        df.loc[target, "order_item_id"] = df.loc[source, "order_item_id"]

    df.to_csv(DIRTY_DIR / "order_items.csv", index=False)
    print(
        f"Order items: {len(used)} directly corrupted records + "
        f"{len(duplicate_indices)} duplicate IDs"
    )


# =========================================================
# Main
# =========================================================

def main():
    print("=" * 70)
    print("Introducing controlled data-quality issues - V2")
    print("=" * 70)
    print("Seed:", SEED)

    corrupt_customers()
    corrupt_products()
    corrupt_orders()
    corrupt_order_items()

    print("\nCompleted.")
    print(f"Dirty datasets written to: {DIRTY_DIR}")


if __name__ == "__main__":
    main()
