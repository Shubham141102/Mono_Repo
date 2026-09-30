from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GOLD_DIR = PROJECT_ROOT / "data" / "gold"
ML_DIR = PROJECT_ROOT / "data" / "ml"


# ------------------------------------------------------------
# Inventory
# ------------------------------------------------------------

INVENTORY_FILE = (
    GOLD_DIR
    / "inventory_metrics"
    / "data.csv"
)
CUSTOMER_METRICS_FILE = GOLD_DIR / "customer_metrics" / "data.csv"

PREDICTION_FILE = (
    ML_DIR
    / "demand_predictions"
    / "data.csv"
)


# ------------------------------------------------------------
# Delivery
# ------------------------------------------------------------

FACT_DELIVERY_FILE = (
    GOLD_DIR
    / "fact_delivery"
    / "data.csv"
)

FACT_ORDERS_FILE = (
    GOLD_DIR
    / "fact_orders"
    / "data.csv"
)

STORE_FILE = (
    GOLD_DIR
    / "dim_store"
    / "data.csv"
)
# ------------------------------------------------------------
# Sales
# ------------------------------------------------------------

DAILY_SALES_FILE = (
    GOLD_DIR
    / "daily_sales"
    / "data.csv"
)

PRODUCT_PERFORMANCE_FILE = (
    GOLD_DIR
    / "product_performance"
    / "data.csv"
)

STORE_PERFORMANCE_FILE = (
    GOLD_DIR
    / "store_performance"
    / "data.csv"
)

# ============================================================
# LOAD INVENTORY DATA
# ============================================================
def load_customer_metrics():
    df = pd.read_csv(CUSTOMER_METRICS_FILE)

    print(
        f"Customer metrics records loaded: {len(df)}"
    )

    return df

def load_inventory_data():

    inventory = pd.read_csv(
        INVENTORY_FILE
    )

    print(
        f"Inventory records loaded: {len(inventory)}"
    )

    return inventory


# ============================================================
# LOAD DEMAND PREDICTIONS
# ============================================================

def load_demand_predictions():

    predictions = pd.read_csv(
        PREDICTION_FILE
    )

    predictions["sales_date"] = pd.to_datetime(
        predictions["sales_date"],
        errors="coerce"
    )

    print(
        f"Demand predictions loaded: {len(predictions)}"
    )

    return predictions


# ============================================================
# GET LATEST PREDICTION
# ============================================================

def get_latest_predictions(predictions):

    latest_predictions = (
        predictions
        .sort_values("sales_date")
        .drop_duplicates(
            subset=[
                "store_id",
                "product_id"
            ],
            keep="last"
        )
    )

    return latest_predictions[
        [
            "store_id",
            "product_id",
            "sales_date",
            "predicted_demand"
        ]
    ]


# ============================================================
# BUILD INVENTORY BUSINESS VIEW
# ============================================================

def build_inventory_view():

    inventory = load_inventory_data()

    predictions = load_demand_predictions()

    latest_predictions = get_latest_predictions(
        predictions
    )

    # --------------------------------------------------------
    # Join inventory with latest demand prediction
    # --------------------------------------------------------

    inventory_view = inventory.merge(
        latest_predictions,
        on=[
            "store_id",
            "product_id"
        ],
        how="left"
    )

    # --------------------------------------------------------
    # Calculate demand coverage
    #
    # How many predicted-demand days can current
    # inventory theoretically cover?
    # --------------------------------------------------------

    inventory_view["demand_coverage_days"] = (
        inventory_view["quantity_on_hand"]
        /
        inventory_view["predicted_demand"].replace(
            0,
            pd.NA
        )
    )

    # --------------------------------------------------------
    # Calculate stock gap relative to reorder level
    # --------------------------------------------------------

    inventory_view["reorder_gap"] = (
        inventory_view["quantity_on_hand"]
        -
        inventory_view["reorder_level"]
    )

    # --------------------------------------------------------
    # Create attention flag
    # --------------------------------------------------------

    inventory_view["requires_attention"] = (
        (
            inventory_view["quantity_on_hand"]
            <= inventory_view["reorder_level"]
        )
        |
        (
            inventory_view["quantity_on_hand"] == 0
        )
    )

    return inventory_view


# ============================================================
# RETRIEVE INVENTORY INFORMATION
# ============================================================

def retrieve_inventory(
    query=None,
    top_k=10
):
    """
    Retrieve inventory records based on the user's question.

    Supported intents:
    - restock / attention / low stock
    - sufficient / healthy / in stock
    - out of stock
    - high demand
    - default inventory attention
    """

    inventory_view = build_inventory_view()

    # --------------------------------------------------------
    # Normalize query
    # --------------------------------------------------------

    query_text = (
        query or ""
    ).lower().strip()

    # --------------------------------------------------------
    # 1. Sufficient / healthy stock
    # --------------------------------------------------------

    sufficient_keywords = [
        "sufficient stock",
        "sufficient inventory",
        "enough stock",
        "enough inventory",
        "healthy stock",
        "well stocked",
        "well-stocked",
        "in stock",
        "products are sufficient",
        "products sufficient",
        "do not need restocking",
        "don't need restocking",
        "do not need replenishment",
        "don't need replenishment",
    ]

    if any(
        keyword in query_text
        for keyword in sufficient_keywords
    ):

        results = (
            inventory_view[
                inventory_view["quantity_on_hand"]
                >
                inventory_view["reorder_level"]
            ]
            .sort_values(
                [
                    "quantity_on_hand",
                    "predicted_demand"
                ],
                ascending=[
                    False,
                    False
                ]
            )
            .head(top_k)
        )

    # --------------------------------------------------------
    # 2. Out-of-stock products
    # --------------------------------------------------------

    elif any(
        keyword in query_text
        for keyword in [
            "out of stock",
            "out-of-stock",
            "zero stock",
            "no stock",
        ]
    ):

        results = (
            inventory_view[
                inventory_view["quantity_on_hand"] <= 0
            ]
            .sort_values(
                "predicted_demand",
                ascending=False
            )
            .head(top_k)
        )

    # --------------------------------------------------------
    # 3. High-demand products
    # --------------------------------------------------------

    elif any(
        keyword in query_text
        for keyword in [
            "high demand",
            "highest demand",
            "most demanded",
            "best selling",
            "fast moving",
            "fast-moving",
        ]
    ):

        results = (
            inventory_view
            .sort_values(
                "predicted_demand",
                ascending=False
            )
            .head(top_k)
        )

    # --------------------------------------------------------
    # 4. Restocking / inventory attention
    # --------------------------------------------------------

    elif any(
        keyword in query_text
        for keyword in [
            "restock",
            "replenish",
            "replenishment",
            "low stock",
            "inventory attention",
            "need attention",
            "inventory risk",
            "stock risk",
            "shortage",
        ]
    ):

        results = (
            inventory_view[
                inventory_view["requires_attention"]
            ]
            .sort_values(
                [
                    "quantity_on_hand",
                    "predicted_demand"
                ],
                ascending=[
                    True,
                    False
                ]
            )
            .head(top_k)
        )

    # --------------------------------------------------------
    # 5. Default behaviour
    # --------------------------------------------------------

    else:

        results = (
            inventory_view[
                inventory_view["requires_attention"]
            ]
            .sort_values(
                [
                    "quantity_on_hand",
                    "predicted_demand"
                ],
                ascending=[
                    True,
                    False
                ]
            )
            .head(top_k)
        )

    # --------------------------------------------------------
    # Return business-relevant columns
    # --------------------------------------------------------

    return results[
        [
            "store_id",
            "store_name",
            "city",
            "product_id",
            "product_name",
            "category",
            "quantity_on_hand",
            "reorder_level",
            "stock_status",
            "predicted_demand",
            "demand_coverage_days",
            "reorder_gap"
        ]
    ]


# ============================================================
# LOAD DELIVERY DATA
# ============================================================

def load_delivery_data():

    delivery = pd.read_csv(
        FACT_DELIVERY_FILE
    )

    delivery["delivery_minutes"] = pd.to_numeric(
        delivery["delivery_minutes"],
        errors="coerce"
    )

    print(
        f"Delivery records loaded: {len(delivery)}"
    )

    return delivery


# ============================================================
# LOAD ORDER DATA
# ============================================================

def load_order_data():

    orders = pd.read_csv(
        FACT_ORDERS_FILE
    )

    print(
        f"Order records loaded: {len(orders)}"
    )

    return orders


# ============================================================
# LOAD STORE DATA
# ============================================================

def load_store_data():

    stores = pd.read_csv(
        STORE_FILE
    )

    print(
        f"Store records loaded: {len(stores)}"
    )

    return stores


# ============================================================
# RETRIEVE DELIVERY INFORMATION
# ============================================================
# ============================================================
# LOAD SALES DATA
# ============================================================

def load_daily_sales():

    sales = pd.read_csv(
        DAILY_SALES_FILE
    )

    sales["date"] = pd.to_datetime(
        sales["date"],
        errors="coerce"
    )

    print(
        f"Daily sales records loaded: {len(sales)}"
    )

    return sales


def load_product_performance():

    products = pd.read_csv(
        PRODUCT_PERFORMANCE_FILE
    )

    print(
        f"Product performance records loaded: {len(products)}"
    )

    return products


def load_store_performance():

    stores = pd.read_csv(
        STORE_PERFORMANCE_FILE
    )

    print(
        f"Store performance records loaded: {len(stores)}"
    )

    return stores

# ============================================================
# RETRIEVE SALES INFORMATION
# ============================================================

def retrieve_sales(query=None, top_k=10):
    """
    Query-aware sales retrieval.

    Supports:
    - total revenue
    - average order value
    - order volume
    - top products
    - top stores
    - top categories
    """

    daily_sales = load_daily_sales()
    product_performance = load_product_performance()
    store_performance = load_store_performance()

    q = (query or "").lower()

    # ---------------------------------------------------------
    # 1. TOTAL REVENUE
    # ---------------------------------------------------------
    if "total revenue" in q or "overall revenue" in q:
        result = pd.DataFrame([{
            "metric": "Total Revenue",
            "total_revenue": daily_sales["net_revenue"].sum(),
            "total_orders": daily_sales["total_orders"].sum()
        }])

        return result

    # ---------------------------------------------------------
    # 2. AVERAGE ORDER VALUE
    # ---------------------------------------------------------
    if (
        "average order value" in q
        or "average order" in q
        or "aov" in q
    ):
        total_revenue = daily_sales["net_revenue"].sum()
        total_orders = daily_sales["total_orders"].sum()

        aov = (
            total_revenue / total_orders
            if total_orders > 0
            else 0
        )

        result = pd.DataFrame([{
            "metric": "Average Order Value",
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "average_order_value": round(aov, 2)
        }])

        return result

    # ---------------------------------------------------------
    # 3. ORDER VOLUME
    # ---------------------------------------------------------
    if (
        "number of orders" in q
        or "how many orders" in q
        or "total orders" in q
        or "order volume" in q
    ):
        result = pd.DataFrame([{
            "metric": "Total Orders",
            "total_orders": daily_sales["total_orders"].sum()
        }])

        return result

    # ---------------------------------------------------------
    # 4. CATEGORY REVENUE
    # IMPORTANT: Must come BEFORE generic store logic
    # ---------------------------------------------------------
    if (
        "category" in q
        and (
            "revenue" in q
            or "sales" in q
            or "sell" in q
        )
    ):
        category_sales = (
            product_performance
            .groupby("category", as_index=False)
            .agg(
                total_revenue=("total_revenue", "sum"),
                total_units_sold=("total_units_sold", "sum"),
                total_orders=("total_orders", "sum")
            )
            .sort_values("total_revenue", ascending=False)
            .head(top_k)
        )

        return category_sales

    # ---------------------------------------------------------
    # 5. PRODUCT REVENUE / SALES
    # ---------------------------------------------------------
    if (
        "product" in q
        and (
            "revenue" in q
            or "sales" in q
            or "sell" in q
            or "top" in q
            or "most" in q
        )
    ):
        return (
            product_performance
            .sort_values("total_revenue", ascending=False)
            .head(top_k)
        )

    # ---------------------------------------------------------
    # 6. STORE REVENUE / SALES
    # ---------------------------------------------------------
    if (
        "store" in q
        and (
            "revenue" in q
            or "sales" in q
            or "top" in q
            or "most" in q
        )
    ):
        return (
            store_performance
            .sort_values("total_revenue", ascending=False)
            .head(top_k)
        )

    # ---------------------------------------------------------
    # 7. DEFAULT
    # ---------------------------------------------------------
    return (
        store_performance
        .sort_values("total_revenue", ascending=False)
        .head(top_k)
    )

def retrieve_customers(query=None, top_k=10):
    """
    Query-aware customer retrieval.

    Supports:
    - top customers by spending
    - top customers by order count
    - average customer spend
    - average customer orders
    - highest customer AOV
    """

    customer_metrics = load_customer_metrics()

    q = (query or "").lower()

    # ---------------------------------------------------------
    # 1. AVERAGE CUSTOMER SPEND
    # ---------------------------------------------------------
    if (
        "average customer spend" in q
        or "average customer spending" in q
        or "average spend per customer" in q
    ):
        result = pd.DataFrame([{
            "metric": "Average Customer Spend",
            "average_customer_spend":
                round(
                    customer_metrics["total_spend"].mean(),
                    2
                )
        }])

        return result

    # ---------------------------------------------------------
    # 2. AVERAGE CUSTOMER ORDERS
    # ---------------------------------------------------------
    if (
    "average customer orders" in q
    or "average orders per customer" in q
    or "average number of orders per customer" in q
    or "average number of orders" in q
    ):
        result = pd.DataFrame([{
            "metric": "Average Orders Per Customer",
            "average_orders":
                round(
                    customer_metrics["total_orders"].mean(),
                    2
                )
        }])

        return result

    # ---------------------------------------------------------
    # 3. HIGHEST SPENDING CUSTOMERS
    # ---------------------------------------------------------
    if (
        "spending" in q
        or "spend" in q
        or "highest spending" in q
        or "top customers" in q
        or "most valuable customers" in q
    ):
        return (
            customer_metrics
            .sort_values(
                "total_spend",
                ascending=False
            )
            .head(top_k)
        )

    # ---------------------------------------------------------
    # 4. MOST ORDERS
    # ---------------------------------------------------------
    if (
        "most orders" in q
        or "highest number of orders" in q
        or "most frequent customers" in q
    ):
        return (
            customer_metrics
            .sort_values(
                "total_orders",
                ascending=False
            )
            .head(top_k)
        )

    # ---------------------------------------------------------
    # 5. HIGHEST AOV
    # ---------------------------------------------------------
    if (
        "highest average order value" in q
        or "highest aov" in q
        or "highest average order" in q
    ):
        return (
            customer_metrics
            .sort_values(
                "average_order_value",
                ascending=False
            )
            .head(top_k)
        )

    # ---------------------------------------------------------
    # 6. DEFAULT
    # ---------------------------------------------------------
    return (
        customer_metrics
        .sort_values(
            "total_spend",
            ascending=False
        )
        .head(top_k)
    )


def retrieve_delivery(
    query=None,
    top_k=10
):
    """
    Retrieve delivery performance based on the user's question.

    The retriever joins:

        fact_delivery
              |
              | order_id
              v
        fact_orders
              |
              | store_id
              v
        dim_store

    This allows delivery questions to be answered
    at store and city level.
    """

    delivery = load_delivery_data()

    orders = load_order_data()

    stores = load_store_data()

    # --------------------------------------------------------
    # Keep valid delivery measurements
    # --------------------------------------------------------

    delivery = delivery[
        delivery["delivery_minutes"].notna()
        &
        (
            delivery["delivery_minutes"] >= 0
        )
    ].copy()

    # --------------------------------------------------------
    # Join delivery -> orders -> stores
    # --------------------------------------------------------

    delivery_view = (
        delivery
        .merge(
            orders[
                [
                    "order_id",
                    "store_id"
                ]
            ],
            on="order_id",
            how="inner"
        )
        .merge(
            stores[
                [
                    "store_id",
                    "store_name",
                    "city"
                ]
            ],
            on="store_id",
            how="inner"
        )
    )

    # --------------------------------------------------------
    # Normalize query
    # --------------------------------------------------------

    query_text = (
        query or ""
    ).lower().strip()

    # --------------------------------------------------------
    # Detect city mentioned in the question
    # --------------------------------------------------------

    cities = (
        stores["city"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    matched_city = None

    for city in cities:

        if city.lower() in query_text:

            matched_city = city

            break

    # --------------------------------------------------------
    # Filter by city when mentioned
    # --------------------------------------------------------

    if matched_city:

        delivery_view = delivery_view[
            delivery_view["city"].str.lower()
            ==
            matched_city.lower()
        ]

    # --------------------------------------------------------
    # Aggregate delivery performance by store
    # --------------------------------------------------------

    store_delivery = (
        delivery_view
        .groupby(
            [
                "store_id",
                "store_name",
                "city"
            ],
            as_index=False
        )
        .agg(
            total_deliveries=(
                "order_id",
                "nunique"
            ),
            average_delivery_minutes=(
                "delivery_minutes",
                "mean"
            ),
            p95_delivery_minutes=(
                "delivery_minutes",
                lambda x: x.quantile(0.95)
            )
        )
    )

    # --------------------------------------------------------
    # Sort by delivery volume
    # --------------------------------------------------------

    store_delivery = (
        store_delivery
        .sort_values(
            "total_deliveries",
            ascending=False
        )
        .head(top_k)
    )

    # --------------------------------------------------------
    # Round metrics
    # --------------------------------------------------------

    store_delivery[
        "average_delivery_minutes"
    ] = (
        store_delivery[
            "average_delivery_minutes"
        ].round(2)
    )

    store_delivery[
        "p95_delivery_minutes"
    ] = (
        store_delivery[
            "p95_delivery_minutes"
        ].round(2)
    )

    return store_delivery


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("CUSTOMER RETRIEVER TEST")
    print("=" * 70)

    questions = [
        "Who are the highest spending customers?",
        "Which customers have placed the most orders?",
        "What is the average customer spend?",
        "What is the average number of orders per customer?",
        "Which customers have the highest average order value?"
    ]

    for question in questions:

        print("\n" + "=" * 70)
        print(f"QUESTION: {question}")
        print("=" * 70)

        result = retrieve_customers(
            query=question,
            top_k=10
        )

        print(result.to_string(index=False))