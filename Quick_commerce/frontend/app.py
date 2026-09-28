from pathlib import Path
import sys

import pandas as pd
import streamlit as st


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GOLD_DIR = PROJECT_ROOT / "data" / "gold"
ML_DIR = PROJECT_ROOT / "data" / "ml"

RAG_DIR = PROJECT_ROOT / "pipelines" / "rag"

if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from hybrid_rag import build_inventory_context

# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GOLD_DIR = PROJECT_ROOT / "data" / "gold"
ML_DIR = PROJECT_ROOT / "data" / "ml"


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Quick-Commerce Business Assistant",
    page_icon="🛒",
    layout="wide",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
    }

    .subtitle {
        font-size: 1rem;
        opacity: 0.7;
        margin-bottom: 1.5rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data
def load_csv(path):
    return pd.read_csv(path)


@st.cache_data
def load_inventory():
    return load_csv(
        GOLD_DIR / "inventory_metrics" / "data.csv"
    )


@st.cache_data
def load_daily_sales():
    return load_csv(
        GOLD_DIR / "daily_sales" / "data.csv"
    )


@st.cache_data
def load_product_performance():
    return load_csv(
        GOLD_DIR / "product_performance" / "data.csv"
    )


@st.cache_data
def load_store_performance():
    return load_csv(
        GOLD_DIR / "store_performance" / "data.csv"
    )


@st.cache_data
def load_delivery_metrics():
    return load_csv(
        GOLD_DIR / "delivery_metrics" / "data.csv"
    )


@st.cache_data
def load_customer_metrics():
    return load_csv(
        GOLD_DIR / "customer_metrics" / "data.csv"
    )


@st.cache_data
def load_demand_predictions():
    return load_csv(
        ML_DIR / "demand_predictions" / "data.csv"
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🛒 Quick-Commerce")

st.sidebar.caption(
    "Business Intelligence Platform"
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Executive Overview",
        "Sales Analytics",
        "Product Analytics",
        "Inventory Intelligence",
        "Delivery Analytics",
        "Business Assistant",
    ],
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    'Quick-Commerce Business Platform'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Gold analytics + ML demand intelligence + RAG business assistant'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if page == "Executive Overview":

    daily_sales = load_daily_sales()
    customer_metrics = load_customer_metrics()
    store_performance = load_store_performance()

    # Actual Gold schema:
    # date, store_id, total_orders, total_items,
    # gross_revenue, discount_amount, net_revenue,
    # average_order_value

    total_revenue = daily_sales["net_revenue"].sum()

    total_orders = daily_sales["total_orders"].sum()

    total_customers = len(customer_metrics)

    total_stores = len(store_performance)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Revenue",
        f"₹{total_revenue:,.0f}",
    )

    col2.metric(
        "Total Orders",
        f"{total_orders:,.0f}",
    )

    col3.metric(
        "Customers",
        f"{total_customers:,}",
    )

    col4.metric(
        "Stores",
        f"{total_stores:,}",
    )

    st.divider()

    # --------------------------------------------------------
    # Revenue Trend
    # --------------------------------------------------------

    st.subheader("Revenue Trend")

    daily_sales["date"] = pd.to_datetime(
        daily_sales["date"]
    )

    revenue_trend = (
        daily_sales
        .groupby("date")["net_revenue"]
        .sum()
        .sort_index()
    )

    st.line_chart(
        revenue_trend
    )

    # --------------------------------------------------------
    # Orders Trend
    # --------------------------------------------------------

    st.subheader("Orders Trend")

    orders_trend = (
        daily_sales
        .groupby("date")["total_orders"]
        .sum()
        .sort_index()
    )

    st.line_chart(
        orders_trend
    )


# ============================================================
# SALES ANALYTICS
# ============================================================

elif page == "Sales Analytics":

    daily_sales = load_daily_sales()

    st.subheader("Sales Analytics")

    daily_sales["date"] = pd.to_datetime(
        daily_sales["date"]
    )

    col1, col2 = st.columns(2)

    with col1:

        st.write("Revenue Over Time")

        revenue = (
            daily_sales
            .groupby("date")["net_revenue"]
            .sum()
            .sort_index()
        )

        st.line_chart(revenue)

    with col2:

        st.write("Orders Over Time")

        orders = (
            daily_sales
            .groupby("date")["total_orders"]
            .sum()
            .sort_index()
        )

        st.line_chart(orders)

    st.subheader("Daily Sales Data")

    st.dataframe(
        daily_sales,
        width="stretch",
    )


# ============================================================
# PRODUCT ANALYTICS
# ============================================================

elif page == "Product Analytics":

    products = load_product_performance()

    st.subheader("Product Analytics")

    # Actual Gold schema:
    # product_id, product_name, category, brand,
    # total_units_sold, total_revenue,
    # total_orders, average_selling_price

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Products",
        f"{len(products):,}",
    )

    col2.metric(
        "Units Sold",
        f"{products['total_units_sold'].sum():,.0f}",
    )

    col3.metric(
        "Revenue",
        f"₹{products['total_revenue'].sum():,.0f}",
    )

    st.divider()

    st.subheader("Top Products by Revenue")

    top_products = (
        products
        .sort_values(
            "total_revenue",
            ascending=False,
        )
        .head(10)
    )

    st.bar_chart(
        top_products.set_index(
            "product_name"
        )["total_revenue"]
    )

    st.subheader("Top Products by Units Sold")

    top_units = (
        products
        .sort_values(
            "total_units_sold",
            ascending=False,
        )
        .head(10)
    )

    st.bar_chart(
        top_units.set_index(
            "product_name"
        )["total_units_sold"]
    )

    st.subheader("Product Performance")

    st.dataframe(
        products,
        width="stretch",
    )


# ============================================================
# INVENTORY INTELLIGENCE
# ============================================================

elif page == "Inventory Intelligence":

    inventory = load_inventory()

    predictions = load_demand_predictions()

    st.subheader(
        "Inventory Intelligence"
    )

    # --------------------------------------------------------
    # KPI CALCULATIONS
    # --------------------------------------------------------

    total_inventory_records = len(inventory)

    out_of_stock = (
        inventory["stock_status"]
        .eq("Out of Stock")
        .sum()
    )

    low_stock = (
        inventory["stock_status"]
        .eq("Low Stock")
        .sum()
    )

    healthy_stock = (
        inventory["stock_status"]
        .eq("Healthy Stock")
        .sum()
    )

    total_inventory_value = (
        inventory["inventory_value"]
        .sum()
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Inventory Records",
        f"{total_inventory_records:,}",
    )

    col2.metric(
        "Out of Stock",
        f"{out_of_stock:,}",
    )

    col3.metric(
        "Low Stock",
        f"{low_stock:,}",
    )

    col4.metric(
        "Inventory Value",
        f"₹{total_inventory_value:,.0f}",
    )

    st.divider()

    # --------------------------------------------------------
    # STOCK STATUS
    # --------------------------------------------------------

    st.subheader(
        "Inventory Status"
    )

    status_counts = (
        inventory["stock_status"]
        .value_counts()
    )

    st.bar_chart(
        status_counts
    )

    # --------------------------------------------------------
    # INVENTORY FILTER
    # --------------------------------------------------------

    st.subheader(
        "Inventory Records"
    )

    selected_status = st.selectbox(
        "Filter by Stock Status",
        [
            "All",
            "Out of Stock",
            "Low Stock",
            "Healthy Stock",
        ],
    )

    if selected_status != "All":

        filtered_inventory = inventory[
            inventory["stock_status"]
            == selected_status
        ]

    else:

        filtered_inventory = inventory

    st.dataframe(
        filtered_inventory,
        width="stretch",
    )

    # --------------------------------------------------------
    # DEMAND PREDICTIONS
    # --------------------------------------------------------

    st.subheader(
        "Demand Predictions"
    )

    st.caption(
        "Predicted next-day demand generated by the ML pipeline."
    )

    st.dataframe(
        predictions.head(100),
        width="stretch",
    )


# ============================================================
# DELIVERY ANALYTICS
# ============================================================

elif page == "Delivery Analytics":

    delivery = load_delivery_metrics()

    store_performance = load_store_performance()

    st.subheader(
        "Delivery Analytics"
    )

    # Actual Gold schema:
    # partner_id
    # total_deliveries
    # average_delivery_minutes
    # p95_delivery_minutes

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Delivery Partners",
        f"{len(delivery):,}",
    )

    col2.metric(
        "Total Deliveries",
        f"{delivery['total_deliveries'].sum():,.0f}",
    )

    col3.metric(
        "Average Delivery Time",
        f"{delivery['average_delivery_minutes'].mean():.1f} min",
    )

    st.divider()

    st.subheader(
        "Average Delivery Time by Partner"
    )

    top_delivery = (
        delivery
        .sort_values(
            "average_delivery_minutes",
            ascending=False,
        )
        .head(15)
    )

    st.bar_chart(
        top_delivery.set_index(
            "partner_id"
        )["average_delivery_minutes"]
    )

    st.subheader(
        "Delivery Performance"
    )

    st.dataframe(
        delivery,
        width="stretch",
    )

    st.divider()

    st.subheader(
        "Store-Level Order Performance"
    )

    store_view = (
        store_performance[
            [
                "store_id",
                "store_name",
                "city",
                "total_orders",
                "unique_customers",
                "items_sold",
                "total_revenue",
                "average_order_value",
            ]
        ]
        .sort_values(
            "total_orders",
            ascending=False,
        )
    )

    st.dataframe(
        store_view,
        width="stretch",
    )


# ============================================================
# BUSINESS ASSISTANT
# ============================================================

elif page == "Business Assistant":

    st.subheader(
        "🤖 Quick-Commerce Business Assistant"
    )

    st.info(
        "Hybrid RAG retrieves business policies together "
        "with current Gold + ML inventory information."
    )

    question = st.text_input(
        "Ask a business question",
        placeholder=(
            "Which products currently need inventory attention?"
        ),
    )

    if question:

        st.write("### Your Question")

        st.write(question)

        st.divider()

        # ----------------------------------------------------
        # RUN HYBRID RAG
        # ----------------------------------------------------

        with st.spinner(
            "Retrieving business policy and current data..."
        ):

            try:

                context = build_inventory_context(
                    query=question,
                    top_k_documents=1,
                    top_k_products=10,
                )

                st.success(
                    "Hybrid RAG retrieval completed successfully."
                )

                # ------------------------------------------------
                # DISPLAY RETRIEVED CONTEXT
                # ------------------------------------------------

                st.subheader(
                    "Retrieved Business Context"
                )

                st.text_area(
                    "Hybrid RAG Context",
                    context,
                    height=600,
                )

            except Exception as e:

                st.error(
                    "RAG retrieval failed."
                )

                st.exception(e)