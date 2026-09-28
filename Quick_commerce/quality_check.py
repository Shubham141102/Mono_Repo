import pandas as pd

print("=" * 70)

# Customers
c = pd.read_csv("data/raw_dirty/customers.csv")
print(f"Customers: {len(c)} rows")
print("Customer NULLs:")
print(c.isna().sum()[c.isna().sum() > 0])

# Products
p = pd.read_csv("data/raw_dirty/products.csv")
print(f"\nProducts: {len(p)} rows")
print("Product NULLs:")
print(p.isna().sum()[p.isna().sum() > 0])
print("Negative prices:", ((p["unit_price"] < 0) | (p["cost_price"] < 0)).sum())

# Orders
o = pd.read_csv("data/raw_dirty/orders.csv")
print(f"\nOrders: {len(o)} rows")
print("Duplicate order IDs:", o["order_id"].duplicated().sum())
print(
    "Invalid customer IDs:",
    (~o["customer_id"].astype(str).str.match(r"^CUST\d{6}$")).sum()
)
print(
    "Invalid timestamps:",
    pd.to_datetime(o["order_timestamp"], errors="coerce").isna().sum()
)

# Order items
oi = pd.read_csv("data/raw_dirty/order_items.csv")
print(f"\nOrder Items: {len(oi)} rows")
print("Negative quantity:", (oi["quantity"] < 0).sum())
print("Negative unit price:", (oi["unit_price"] < 0).sum())

print("=" * 70)
