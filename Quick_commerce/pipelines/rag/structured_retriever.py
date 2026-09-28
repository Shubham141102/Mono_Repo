from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GOLD_DIR = PROJECT_ROOT / "data" / "gold"
ML_DIR = PROJECT_ROOT / "data" / "ml"


INVENTORY_FILE = (
    GOLD_DIR
    / "inventory_metrics"
    / "data.csv"
)

PREDICTION_FILE = (
    ML_DIR
    / "demand_predictions"
    / "data.csv"
)


# ============================================================
# LOAD INVENTORY DATA
# ============================================================

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
        (inventory_view["quantity_on_hand"]
         <= inventory_view["reorder_level"])
        |
        (inventory_view["quantity_on_hand"] == 0)
    )

    return inventory_view


# ============================================================
# RETRIEVE INVENTORY INFORMATION
# ============================================================

def retrieve_inventory(
    top_k=10
):

    inventory_view = build_inventory_view()

    attention_items = (
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

    return attention_items[
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
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("STRUCTURED INVENTORY RETRIEVER")
    print("=" * 70)

    results = retrieve_inventory(
        top_k=10
    )

    print()
    print("PRODUCTS REQUIRING INVENTORY ATTENTION")
    print("=" * 70)

    print(
        results.to_string(
            index=False
        )
    )