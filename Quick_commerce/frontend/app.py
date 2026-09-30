from pathlib import Path
import sys

import pandas as pd
import streamlit as st
import plotly.express as px


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GOLD_DIR = PROJECT_ROOT / "data" / "gold"
ML_DIR = PROJECT_ROOT / "data" / "ml"
RAG_DIR = PROJECT_ROOT / "pipelines" / "rag"

if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))
from hybrid_rag import (
    build_inventory_context,
    generate_business_answer,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Quick-Commerce Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM UI
# ============================================================

st.markdown(
    """
    <style>

    /* ---------- GLOBAL ---------- */

    .stApp {
        background-color: #f5f7fb;
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    /* ---------- SIDEBAR ---------- */

    section[data-testid="stSidebar"] {
        background-color: #111827;
    }

    section[data-testid="stSidebar"] * {
        color: #e5e7eb;
    }

    section[data-testid="stSidebar"] .stRadio label {
        color: #d1d5db !important;
    }

    .sidebar-brand {
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .sidebar-subtitle {
        font-size: 0.75rem;
        color: #9ca3af;
        margin-bottom: 1.8rem;
    }

    .sidebar-section {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }

    /* ---------- HEADER ---------- */

    .page-title {
        font-size: 2rem;
        font-weight: 750;
        color: #111827;
        margin-bottom: 0.2rem;
    }

    .page-subtitle {
        font-size: 0.9rem;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }

    /* ---------- KPI CARDS ---------- */

    .kpi-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1.15rem 1.2rem;
        min-height: 120px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }

    .kpi-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .kpi-value {
        font-size: 1.55rem;
        font-weight: 750;
        color: #111827;
        margin-top: 0.35rem;
    }

    .kpi-description {
        font-size: 0.72rem;
        color: #9ca3af;
        margin-top: 0.3rem;
    }

    /* ---------- PANELS ---------- */

    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #111827;
        margin-top: 1.2rem;
        margin-bottom: 0.7rem;
    }

    .panel {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1rem 1.15rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }

    .panel-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.2rem;
    }

    .panel-subtitle {
        font-size: 0.72rem;
        color: #9ca3af;
        margin-bottom: 0.8rem;
    }

    /* ---------- INSIGHT BOX ---------- */

    .insight-box {
        background: #eef2ff;
        border: 1px solid #c7d2fe;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin-top: 0.8rem;
    }

    .insight-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem;
        min-height: 115px;
    }

    .insight-title {
        font-weight: 700;
        color: #3730a3;
        margin-bottom: 0.25rem;
    }

    .insight-text {
        color: #4b5563;
        font-size: 0.82rem;
    }

    /* ---------- FOOTER ---------- */

    .footer {
        color: #9ca3af;
        font-size: 0.7rem;
        text-align: center;
        margin-top: 2rem;
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
def load_daily_sales():
    return load_csv(GOLD_DIR / "daily_sales" / "data.csv")


@st.cache_data
def load_product_performance():
    return load_csv(GOLD_DIR / "product_performance" / "data.csv")


@st.cache_data
def load_store_performance():
    return load_csv(GOLD_DIR / "store_performance" / "data.csv")


@st.cache_data
def load_customer_metrics():
    return load_csv(GOLD_DIR / "customer_metrics" / "data.csv")


@st.cache_data
def load_inventory():
    return load_csv(GOLD_DIR / "inventory_metrics" / "data.csv")


@st.cache_data
def load_delivery_metrics():
    return load_csv(GOLD_DIR / "delivery_metrics" / "data.csv")


@st.cache_data
def load_demand_predictions():
    return load_csv(ML_DIR / "demand_predictions" / "data.csv")


# Transaction-level Gold data
@st.cache_data
def load_fact_orders():
    return load_csv(GOLD_DIR / "fact_orders" / "data.csv")


@st.cache_data
def load_fact_order_items():
    return load_csv(GOLD_DIR / "fact_order_items" / "data.csv")


@st.cache_data
def load_dim_product():
    return load_csv(GOLD_DIR / "dim_product" / "data.csv")


@st.cache_data
def load_dim_store():
    return load_csv(GOLD_DIR / "dim_store" / "data.csv")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def kpi_card(title, value, subtitle):
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{title}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-description">{subtitle}</div>
    </div>
    """


def panel_header(title, subtitle=""):
    st.markdown(
        f"""
        <div class="panel-title">{title}</div>
        <div class="panel-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def format_currency(value):
    if pd.isna(value):
        return "₹0"
    return f"₹{value:,.0f}"


def prepare_business_data():
    """
    Load transaction-level Gold data and normalize the fields
    required by Business Analytics.
    """

    fact_orders = load_fact_orders().copy()
    fact_items = load_fact_order_items().copy()
    dim_product = load_dim_product().copy()
    dim_store = load_dim_store().copy()

    fact_orders["order_timestamp"] = pd.to_datetime(
        fact_orders["order_timestamp"],
        errors="coerce",
    )

    # Keep numeric fields numeric.
    for col in [
        "total_amount",
    ]:
        if col in fact_orders.columns:
            fact_orders[col] = pd.to_numeric(
                fact_orders[col],
                errors="coerce",
            )

    for col in [
        "quantity",
        "unit_price",
        "discount",
        "line_total",
    ]:
        if col in fact_items.columns:
            fact_items[col] = pd.to_numeric(
                fact_items[col],
                errors="coerce",
            )

    return fact_orders, fact_items, dim_product, dim_store


def apply_business_filters(
    fact_orders,
    fact_items,
    dim_product,
    dim_store,
    date_range,
    selected_city,
    selected_category,
    selected_brand,
):
    """
    Apply all Business Analytics filters at transaction level.

    Important:
    - Only delivered orders are treated as completed sales.
    - Date and city filter orders.
    - Category and brand filter products.
    - Orders are finally restricted to the selected products.
    """

    orders = fact_orders.copy()
    items = fact_items.copy()

    # --------------------------------------------------------
    # 1. SALES STATUS
    # --------------------------------------------------------

    if "order_status" in orders.columns:
        orders = orders[
            orders["order_status"]
            .astype(str)
            .str.strip()
            .str.lower()
            == "delivered"
        ].copy()

    # --------------------------------------------------------
    # 2. DATE FILTER
    # --------------------------------------------------------

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range

        start_timestamp = pd.Timestamp(start_date)
        end_timestamp = (
            pd.Timestamp(end_date)
            + pd.Timedelta(days=1)
            - pd.Timedelta(seconds=1)
        )

        orders = orders[
            (orders["order_timestamp"] >= start_timestamp)
            & (orders["order_timestamp"] <= end_timestamp)
        ].copy()

    elif date_range:
        selected_date = pd.Timestamp(date_range)

        orders = orders[
            orders["order_timestamp"].dt.date
            == selected_date.date()
        ].copy()

    # --------------------------------------------------------
    # 3. CITY FILTER
    # --------------------------------------------------------

    if selected_city != "All Cities":

        selected_store_ids = dim_store.loc[
            dim_store["city"] == selected_city,
            "store_id",
        ].unique()

        orders = orders[
            orders["store_id"].isin(selected_store_ids)
        ].copy()

    # --------------------------------------------------------
    # 4. PRODUCT FILTERS
    # --------------------------------------------------------

    selected_products = dim_product.copy()

    if selected_category != "All Categories":
        selected_products = selected_products[
            selected_products["category"]
            == selected_category
        ].copy()

    if selected_brand != "All Brands":
        selected_products = selected_products[
            selected_products["brand"]
            == selected_brand
        ].copy()

    selected_product_ids = selected_products[
        "product_id"
    ].unique()

    # --------------------------------------------------------
    # 5. FILTER ORDER ITEMS
    # --------------------------------------------------------

    items = items[
        items["product_id"].isin(selected_product_ids)
    ].copy()

    # Only items belonging to filtered orders.
    items = items[
        items["order_id"].isin(
            orders["order_id"]
        )
    ].copy()

    # --------------------------------------------------------
    # 6. KEEP ONLY ORDERS THAT CONTAIN SELECTED PRODUCTS
    # --------------------------------------------------------

    selected_order_ids = items["order_id"].unique()

    orders = orders[
        orders["order_id"].isin(selected_order_ids)
    ].copy()

    return orders, items, selected_products


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    '<div class="sidebar-brand">🛒 QUICK-COMMERCE</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div class="sidebar-subtitle">'
    'Business Intelligence Platform'
    '</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    '<div class="sidebar-section">Workspace</div>',
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Executive Overview",
        "📊 Business Analytics",
        "📦 Inventory Intelligence",
        "🚚 Delivery & Operations",
        "🤖 Business Assistant",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown(
    '<div class="sidebar-section">Platform</div>',
    unsafe_allow_html=True,
)

st.sidebar.caption("Bronze → Silver → Gold")
st.sidebar.caption("ML Demand Intelligence")
st.sidebar.caption("Hybrid RAG")


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if page == "🏠 Executive Overview":

    daily_sales = load_daily_sales()
    products = load_product_performance()
    stores = load_store_performance()
    customers = load_customer_metrics()
    inventory = load_inventory()
    delivery = load_delivery_metrics()

    daily_sales["date"] = pd.to_datetime(
        daily_sales["date"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.markdown(
        '<div class="page-title">'
        'Quick-Commerce Business Overview'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Sales, customer and operational intelligence'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    total_revenue = daily_sales["net_revenue"].sum()
    total_orders = daily_sales["total_orders"].sum()
    total_customers = len(customers)
    total_items = daily_sales["total_items"].sum()

    average_order_value = (
        total_revenue / total_orders
        if total_orders > 0
        else 0
    )

    inventory_value = inventory["inventory_value"].sum()

    stock_at_risk = inventory[
        inventory["stock_status"].isin(
            ["Out of Stock", "Low Stock"]
        )
    ].shape[0]

    kpi_cols = st.columns(6)

    with kpi_cols[0]:
        st.markdown(
            kpi_card(
                "Net Revenue",
                f"₹{total_revenue / 1e6:.1f}M",
                "Delivered-order revenue",
            ),
            unsafe_allow_html=True,
        )

    with kpi_cols[1]:
        st.markdown(
            kpi_card(
                "Total Orders",
                f"{total_orders / 1000:.1f}K",
                "Delivered orders",
            ),
            unsafe_allow_html=True,
        )

    with kpi_cols[2]:
        st.markdown(
            kpi_card(
                "Customers",
                f"{total_customers / 1000:.1f}K",
                "Customer records",
            ),
            unsafe_allow_html=True,
        )

    with kpi_cols[3]:
        st.markdown(
            kpi_card(
                "Average Order Value",
                f"₹{average_order_value:,.0f}",
                "Revenue per order",
            ),
            unsafe_allow_html=True,
        )

    with kpi_cols[4]:
        st.markdown(
            kpi_card(
                "Inventory Value",
                f"₹{inventory_value / 1e6:.1f}M",
                "Current inventory value",
            ),
            unsafe_allow_html=True,
        )

    with kpi_cols[5]:
        st.markdown(
            kpi_card(
                "Stock At Risk",
                f"{stock_at_risk:,}",
                "Low or out of stock",
            ),
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # BUSINESS PERFORMANCE
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Business Performance'
        '</div>',
        unsafe_allow_html=True,
    )

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        st.markdown(
            '<div class="panel">',
            unsafe_allow_html=True,
        )

        panel_header(
            "Revenue Trend",
            "Daily net revenue",
        )

        revenue_trend = (
            daily_sales
            .groupby("date")["net_revenue"]
            .sum()
            .sort_index()
        )

        st.line_chart(
            revenue_trend,
            height=280,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with chart_col2:

        st.markdown(
            '<div class="panel">',
            unsafe_allow_html=True,
        )

        panel_header(
            "Orders Trend",
            "Daily delivered order volume",
        )

        orders_trend = (
            daily_sales
            .groupby("date")["total_orders"]
            .sum()
            .sort_index()
        )

        st.line_chart(
            orders_trend,
            height=280,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # TOP PRODUCTS / STORES
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Commercial Performance'
        '</div>',
        unsafe_allow_html=True,
    )

    top_col1, top_col2 = st.columns(2)

    with top_col1:

        st.markdown(
            '<div class="panel">',
            unsafe_allow_html=True,
        )

        panel_header(
            "Top Products",
            "Products by delivered revenue",
        )

        top_products = (
            products
            .sort_values(
                "total_revenue",
                ascending=False,
            )
            .head(10)
            .sort_values("total_revenue")
        )

        fig = px.bar(
            top_products,
            x="total_revenue",
            y="product_name",
            orientation="h",
            title="",
        )

        fig.update_layout(
            xaxis_title="Revenue",
            yaxis_title="",
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with top_col2:

        st.markdown(
            '<div class="panel">',
            unsafe_allow_html=True,
        )

        panel_header(
            "Store Performance",
            "Stores by delivered revenue",
        )

        top_stores = (
            stores
            .sort_values(
                "total_revenue",
                ascending=False,
            )
            .head(10)
            .sort_values("total_revenue")
        )

        fig = px.bar(
            top_stores,
            x="total_revenue",
            y="store_name",
            orientation="h",
            title="",
        )

        fig.update_layout(
            xaxis_title="Revenue",
            yaxis_title="",
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # OPERATIONAL SNAPSHOT
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Operational Snapshot'
        '</div>',
        unsafe_allow_html=True,
    )

    op_col1, op_col2, op_col3 = st.columns(3)

    with op_col1:

        st.markdown(
            '<div class="panel">',
            unsafe_allow_html=True,
        )

        panel_header(
            "Inventory Health",
            "Current stock status",
        )

        status_counts = (
            inventory["stock_status"]
            .value_counts()
        )

        st.bar_chart(
            status_counts,
            height=220,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with op_col2:

        st.markdown(
            '<div class="panel">',
            unsafe_allow_html=True,
        )

        panel_header(
            "Delivery Performance",
            "Current delivery metrics",
        )

        avg_delivery = delivery[
            "average_delivery_minutes"
        ].mean()

        p95_delivery = delivery[
            "p95_delivery_minutes"
        ].mean()

        total_deliveries = delivery[
            "total_deliveries"
        ].sum()

        st.metric(
            "Average Delivery",
            f"{avg_delivery:.1f} min",
        )

        st.metric(
            "Average P95",
            f"{p95_delivery:.1f} min",
        )

        st.metric(
            "Total Deliveries",
            f"{total_deliveries:,.0f}",
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with op_col3:

        st.markdown(
            '<div class="panel">',
            unsafe_allow_html=True,
        )

        panel_header(
            "Business Summary",
            "Current platform indicators",
        )

        st.write(
            f"**{total_items:,.0f}** items processed"
        )

        st.write(
            f"**{len(products):,}** products in performance data"
        )

        st.write(
            f"**{len(stores):,}** active stores"
        )

        st.write(
            f"**{stock_at_risk:,}** inventory records require attention"
        )

        st.markdown(
            '<div class="insight-box">'
            '<div class="insight-title">'
            'Operational focus'
            '</div>'
            '<div class="insight-text">'
            'Inventory risk and delivery performance '
            'provide the main operational signals '
            'for deeper analysis.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# BUSINESS ANALYTICS
# ============================================================

elif page == "📊 Business Analytics":

    (
        fact_orders,
        fact_order_items,
        dim_product,
        dim_store,
    ) = prepare_business_data()

    # Aggregate Gold tables are still loaded for reference/filter
    # options and are not used for transaction-level KPI logic.
    products = load_product_performance()
    stores = load_store_performance()

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.markdown(
        '<div class="page-title">'
        'Business Analytics'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Interactive sales, product and store analysis using '
        'transaction-level Gold data.'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Analysis Filters</div>',
        unsafe_allow_html=True,
    )

    # Use delivered orders to determine the valid business date range.
    delivered_for_dates = fact_orders[
        fact_orders["order_status"]
        .astype(str)
        .str.strip()
        .str.lower()
        == "delivered"
    ].copy()

    delivered_for_dates = delivered_for_dates[
        delivered_for_dates["order_timestamp"].notna()
    ]

    if delivered_for_dates.empty:
        st.warning("No delivered-order data is available.")
        st.stop()

    min_date = delivered_for_dates[
        "order_timestamp"
    ].min().date()

    max_date = delivered_for_dates[
        "order_timestamp"
    ].max().date()

    f1, f2, f3, f4 = st.columns(4)

    with f1:

        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

    with f2:

        city_options = ["All Cities"] + sorted(
            dim_store["city"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_city = st.selectbox(
            "City",
            city_options,
        )

    with f3:

        category_options = ["All Categories"] + sorted(
            dim_product["category"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_category = st.selectbox(
            "Category",
            category_options,
        )

    with f4:

        brand_options = ["All Brands"] + sorted(
            dim_product["brand"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_brand = st.selectbox(
            "Brand",
            brand_options,
        )

    # --------------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------------

    (
        filtered_orders,
        filtered_items,
        filtered_products,
    ) = apply_business_filters(
        fact_orders=fact_orders,
        fact_items=fact_order_items,
        dim_product=dim_product,
        dim_store=dim_store,
        date_range=date_range,
        selected_city=selected_city,
        selected_category=selected_category,
        selected_brand=selected_brand,
    )

    # --------------------------------------------------------
    # KPI CALCULATIONS
    # --------------------------------------------------------

    revenue = filtered_items["line_total"].sum()

    orders = filtered_items["order_id"].nunique()

    items = filtered_items["quantity"].sum()

    aov = (
        revenue / orders
        if orders > 0
        else 0
    )

    active_products = filtered_items[
        "product_id"
    ].nunique()

    active_stores = filtered_orders[
        "store_id"
    ].nunique()

    # --------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Performance Snapshot'
        '</div>',
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        st.markdown(
            kpi_card(
                "Net Revenue",
                f"₹{revenue:,.0f}",
                "Filtered delivered sales",
            ),
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            kpi_card(
                "Orders",
                f"{orders:,.0f}",
                "Filtered orders",
            ),
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            kpi_card(
                "Units Sold",
                f"{items:,.0f}",
                "Filtered items",
            ),
            unsafe_allow_html=True,
        )

    with k4:
        st.markdown(
            kpi_card(
                "Average Order Value",
                f"₹{aov:,.0f}",
                "Revenue / orders",
            ),
            unsafe_allow_html=True,
        )

    with k5:
        st.markdown(
            kpi_card(
                "Products",
                f"{active_products:,}",
                "Products with sales",
            ),
            unsafe_allow_html=True,
        )

    with k6:
        st.markdown(
            kpi_card(
                "Stores",
                f"{active_stores:,}",
                "Stores with sales",
            ),
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # EMPTY DATA CHECK
    # --------------------------------------------------------

    if filtered_items.empty:

        st.info(
            "No sales records match the selected filters."
        )

    else:

        # ----------------------------------------------------
        # PREPARE ENRICHED TRANSACTION DATA
        # ----------------------------------------------------

        analysis_items = filtered_items.merge(
            filtered_orders[
                [
                    "order_id",
                    "store_id",
                    "customer_id",
                    "order_timestamp",
                ]
            ],
            on="order_id",
            how="left",
        )

        analysis_items = analysis_items.merge(
            dim_product[
                [
                    "product_id",
                    "product_name",
                    "category",
                    "brand",
                ]
            ],
            on="product_id",
            how="left",
        )

        analysis_items = analysis_items.merge(
            dim_store[
                [
                    "store_id",
                    "store_name",
                    "city",
                ]
            ],
            on="store_id",
            how="left",
        )

        # ----------------------------------------------------
        # SALES TRENDS
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">'
            'Sales Performance'
            '</div>',
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)

        with c1:

            daily_revenue = (
                analysis_items
                .assign(
                    date=analysis_items[
                        "order_timestamp"
                    ].dt.date
                )
                .groupby(
                    "date",
                    as_index=False,
                )["line_total"]
                .sum()
            )

            fig = px.line(
                daily_revenue,
                x="date",
                y="line_total",
                markers=True,
                title="Revenue Trend",
            )

            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Net Revenue",
                hovermode="x unified",
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        with c2:

            daily_orders = (
                analysis_items
                .groupby(
                    "order_timestamp",
                    as_index=False,
                )
                .agg(
                    orders=(
                        "order_id",
                        "nunique",
                    )
                )
            )

            daily_orders["date"] = (
                daily_orders["order_timestamp"]
                .dt.date
            )

            daily_orders = (
                daily_orders
                .groupby(
                    "date",
                    as_index=False,
                )["orders"]
                .sum()
            )

            fig = px.line(
                daily_orders,
                x="date",
                y="orders",
                markers=True,
                title="Order Trend",
            )

            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Orders",
                hovermode="x unified",
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        # ----------------------------------------------------
        # PRODUCT PERFORMANCE
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">'
            'Product Performance'
            '</div>',
            unsafe_allow_html=True,
        )

        product_summary = (
            analysis_items
            .groupby(
                [
                    "product_id",
                    "product_name",
                    "category",
                    "brand",
                ],
                as_index=False,
            )
            .agg(
                total_revenue=(
                    "line_total",
                    "sum",
                ),
                total_units_sold=(
                    "quantity",
                    "sum",
                ),
                total_orders=(
                    "order_id",
                    "nunique",
                ),
            )
        )

        p1, p2 = st.columns(2)

        with p1:

            top_products_revenue = (
                product_summary
                .sort_values(
                    "total_revenue",
                    ascending=False,
                )
                .head(10)
                .sort_values("total_revenue")
            )

            fig = px.bar(
                top_products_revenue,
                x="total_revenue",
                y="product_name",
                orientation="h",
                title="Top Products by Revenue",
            )

            fig.update_layout(
                xaxis_title="Revenue",
                yaxis_title="",
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        with p2:

            top_products_units = (
                product_summary
                .sort_values(
                    "total_units_sold",
                    ascending=False,
                )
                .head(10)
                .sort_values("total_units_sold")
            )

            fig = px.bar(
                top_products_units,
                x="total_units_sold",
                y="product_name",
                orientation="h",
                title="Top Products by Units Sold",
            )

            fig.update_layout(
                xaxis_title="Units Sold",
                yaxis_title="",
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        # ----------------------------------------------------
        # CATEGORY PERFORMANCE
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">'
            'Category Performance'
            '</div>',
            unsafe_allow_html=True,
        )

        category_summary = (
            product_summary
            .groupby(
                "category",
                as_index=False,
            )
            .agg(
                revenue=(
                    "total_revenue",
                    "sum",
                ),
                units_sold=(
                    "total_units_sold",
                    "sum",
                ),
                orders=(
                    "total_orders",
                    "sum",
                ),
            )
            .sort_values(
                "revenue",
                ascending=False,
            )
        )

        fig = px.bar(
            category_summary,
            x="category",
            y="revenue",
            title="Revenue by Category",
            text_auto=".2s",
        )

        fig.update_layout(
            xaxis_title="Category",
            yaxis_title="Revenue",
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

        # ----------------------------------------------------
        # STORE PERFORMANCE
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">'
            'Store Performance'
            '</div>',
            unsafe_allow_html=True,
        )

        store_summary = (
            analysis_items
            .groupby(
                [
                    "store_id",
                    "store_name",
                    "city",
                ],
                as_index=False,
            )
            .agg(
                total_orders=(
                    "order_id",
                    "nunique",
                ),
                unique_customers=(
                    "customer_id",
                    "nunique",
                ),
                items_sold=(
                    "quantity",
                    "sum",
                ),
                total_revenue=(
                    "line_total",
                    "sum",
                ),
            )
        )

        store_summary["average_order_value"] = (
            store_summary["total_revenue"]
            / store_summary["total_orders"]
        )

        s1, s2 = st.columns(2)

        with s1:

            top_stores = (
                store_summary
                .sort_values(
                    "total_revenue",
                    ascending=False,
                )
                .head(10)
                .sort_values("total_revenue")
            )

            fig = px.bar(
                top_stores,
                x="total_revenue",
                y="store_name",
                orientation="h",
                title="Top Stores by Revenue",
            )

            fig.update_layout(
                xaxis_title="Revenue",
                yaxis_title="",
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        with s2:

            store_orders = (
                store_summary
                .sort_values(
                    "total_orders",
                    ascending=False,
                )
                .head(10)
                .sort_values("total_orders")
            )

            fig = px.bar(
                store_orders,
                x="total_orders",
                y="store_name",
                orientation="h",
                title="Top Stores by Orders",
            )

            fig.update_layout(
                xaxis_title="Orders",
                yaxis_title="",
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        # ----------------------------------------------------
        # BUSINESS INSIGHTS
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">'
            'Business Insights'
            '</div>',
            unsafe_allow_html=True,
        )

        i1, i2, i3 = st.columns(3)

        # Highest revenue category
        if not category_summary.empty:

            best_category = category_summary.iloc[0]

            category_text = (
                f"<b>{best_category['category']}</b> "
                f"generated "
                f"₹{best_category['revenue']:,.0f} "
                f"in revenue."
            )

        else:
            category_text = "No category data available."

        # Highest revenue product
        if not product_summary.empty:

            best_product = (
                product_summary
                .sort_values(
                    "total_revenue",
                    ascending=False,
                )
                .iloc[0]
            )

            product_text = (
                f"<b>{best_product['product_name']}</b> "
                f"is the highest-revenue product with "
                f"₹{best_product['total_revenue']:,.0f}."
            )

        else:
            product_text = "No product data available."

        # Highest revenue store
        if not store_summary.empty:

            best_store = (
                store_summary
                .sort_values(
                    "total_revenue",
                    ascending=False,
                )
                .iloc[0]
            )

            store_text = (
                f"<b>{best_store['store_name']}</b> "
                f"generated the highest revenue at "
                f"₹{best_store['total_revenue']:,.0f}."
            )

        else:
            store_text = "No store data available."

        with i1:

            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-title">
                        Leading Category
                    </div>
                    <div class="insight-text">
                        {category_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with i2:

            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-title">
                        Leading Product
                    </div>
                    <div class="insight-text">
                        {product_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with i3:

            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-title">
                        Leading Store
                    </div>
                    <div class="insight-text">
                        {store_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# INVENTORY INTELLIGENCE
# ============================================================

elif page == "📦 Inventory Intelligence":

    inventory = load_inventory()
    predictions = load_demand_predictions()

    st.markdown(
        '<div class="page-title">'
        'Inventory Intelligence'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Combine current inventory position with ML demand predictions '
        'to identify products requiring replenishment attention.'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # PREPARE DATA
    # --------------------------------------------------------

    inventory_view = inventory.copy()
    predictions_view = predictions.copy()

    predictions_view["sales_date"] = pd.to_datetime(
        predictions_view["sales_date"],
        errors="coerce",
    )

    latest_predictions = (
        predictions_view
        .sort_values("sales_date")
        .groupby(
            ["store_id", "product_id"],
            as_index=False,
        )
        .tail(1)
    )

    # --------------------------------------------------------
    # MERGE INVENTORY + ML PREDICTION
    # --------------------------------------------------------

    inventory_analysis = inventory_view.merge(
        latest_predictions[
            [
                "store_id",
                "product_id",
                "predicted_demand",
            ]
        ],
        on=["store_id", "product_id"],
        how="left",
    )

    inventory_analysis["predicted_demand"] = (
        pd.to_numeric(
            inventory_analysis["predicted_demand"],
            errors="coerce",
        )
        .fillna(0)
    )

    # --------------------------------------------------------
    # DERIVED BUSINESS METRICS
    # --------------------------------------------------------

    inventory_analysis["demand_coverage_days"] = (
        inventory_analysis["quantity_on_hand"]
        /
        inventory_analysis[
            "predicted_demand"
        ].replace(0, pd.NA)
    )

    inventory_analysis["reorder_gap"] = (
        inventory_analysis["quantity_on_hand"]
        -
        inventory_analysis["reorder_level"]
    )

    inventory_analysis["requires_attention"] = (
        (
            inventory_analysis["quantity_on_hand"]
            <= inventory_analysis["reorder_level"]
        )
        |
        (
            inventory_analysis["quantity_on_hand"]
            <= 0
        )
    )

    # --------------------------------------------------------
    # KPI CALCULATIONS
    # --------------------------------------------------------

    total_records = len(inventory_analysis)

    out_of_stock = (
        inventory_analysis["stock_status"]
        .eq("Out of Stock")
        .sum()
    )

    low_stock = (
        inventory_analysis["stock_status"]
        .eq("Low Stock")
        .sum()
    )

    healthy_stock = (
        inventory_analysis["stock_status"]
        .eq("Healthy Stock")
        .sum()
    )

    attention_required = (
        inventory_analysis["requires_attention"]
        .sum()
    )

    total_inventory_value = (
        inventory_analysis["inventory_value"]
        .sum()
    )

    # --------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Inventory Snapshot'
        '</div>',
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.markdown(
            kpi_card(
                "Inventory Records",
                f"{total_records:,}",
                "Store-product combinations",
            ),
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            kpi_card(
                "Out of Stock",
                f"{out_of_stock:,}",
                "Immediate attention",
            ),
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            kpi_card(
                "Low Stock",
                f"{low_stock:,}",
                "Below reorder level",
            ),
            unsafe_allow_html=True,
        )

    with k4:
        st.markdown(
            kpi_card(
                "Attention Required",
                f"{attention_required:,}",
                "Inventory risk",
            ),
            unsafe_allow_html=True,
        )

    with k5:
        st.markdown(
            kpi_card(
                "Inventory Value",
                f"₹{total_inventory_value:,.0f}",
                "Current inventory",
            ),
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # INVENTORY HEALTH
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Inventory Health'
        '</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:

        status_counts = (
            inventory_analysis["stock_status"]
            .value_counts()
            .reset_index()
        )

        status_counts.columns = [
            "stock_status",
            "count",
        ]

        fig = px.bar(
            status_counts,
            x="stock_status",
            y="count",
            title="Inventory Status Distribution",
            text_auto=True,
        )

        fig.update_layout(
            xaxis_title="Stock Status",
            yaxis_title="Products",
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    with c2:

        attention_summary = pd.DataFrame(
            {
                "Status": [
                    "Healthy",
                    "Attention Required",
                ],
                "Products": [
                    healthy_stock,
                    attention_required,
                ],
            }
        )

        fig = px.pie(
            attention_summary,
            names="Status",
            values="Products",
            title="Inventory Attention",
            hole=0.55,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    # --------------------------------------------------------
    # DEMAND VS INVENTORY
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Inventory vs Predicted Demand'
        '</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Products with low stock and higher predicted demand "
        "are prioritized for attention."
    )

    demand_view = (
        inventory_analysis[
            inventory_analysis["requires_attention"]
        ]
        .sort_values(
            [
                "predicted_demand",
                "quantity_on_hand",
            ],
            ascending=[False, True],
        )
        .head(15)
    )

    if not demand_view.empty:

        fig = px.bar(
            demand_view,
            x="product_name",
            y=[
                "quantity_on_hand",
                "predicted_demand",
            ],
            barmode="group",
            title="Current Stock vs Predicted Next-Day Demand",
        )

        fig.update_layout(
            xaxis_title="Product",
            yaxis_title="Quantity",
            xaxis_tickangle=-45,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    # --------------------------------------------------------
    # REPLENISHMENT PRIORITY
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Replenishment Priority'
        '</div>',
        unsafe_allow_html=True,
    )

    priority_columns = [
        "store_id",
        "store_name",
        "city",
        "product_id",
        "product_name",
        "category",
        "quantity_on_hand",
        "reorder_level",
        "predicted_demand",
        "demand_coverage_days",
        "reorder_gap",
        "stock_status",
    ]

    priority_view = (
        inventory_analysis[
            inventory_analysis["requires_attention"]
        ][priority_columns]
        .sort_values(
            [
                "quantity_on_hand",
                "predicted_demand",
            ],
            ascending=[True, False],
        )
        .head(50)
    )

    st.dataframe(
        priority_view,
        width="stretch",
        hide_index=True,
    )

    # --------------------------------------------------------
    # INVENTORY FILTER
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Inventory Explorer'
        '</div>',
        unsafe_allow_html=True,
    )

    f1, f2, f3 = st.columns(3)

    with f1:

        status_filter = st.selectbox(
            "Stock Status",
            [
                "All",
                "Out of Stock",
                "Low Stock",
                "Healthy Stock",
            ],
        )

    with f2:

        city_filter = st.selectbox(
            "City",
            ["All Cities"]
            + sorted(
                inventory_analysis["city"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            ),
        )

    with f3:

        attention_filter = st.selectbox(
            "Attention",
            [
                "All",
                "Attention Required",
                "No Attention Required",
            ],
        )

    explorer = inventory_analysis.copy()

    if status_filter != "All":

        explorer = explorer[
            explorer["stock_status"]
            == status_filter
        ]

    if city_filter != "All Cities":

        explorer = explorer[
            explorer["city"]
            == city_filter
        ]

    if attention_filter == "Attention Required":

        explorer = explorer[
            explorer["requires_attention"]
        ]

    elif attention_filter == "No Attention Required":

        explorer = explorer[
            ~explorer["requires_attention"]
        ]

    explorer_columns = [
        "store_id",
        "store_name",
        "city",
        "product_id",
        "product_name",
        "category",
        "quantity_on_hand",
        "reorder_level",
        "predicted_demand",
        "demand_coverage_days",
        "stock_status",
    ]

    st.dataframe(
        explorer[explorer_columns],
        width="stretch",
        hide_index=True,
    )


# ============================================================
# DELIVERY & OPERATIONS
# ============================================================

elif page == "🚚 Delivery & Operations":

    delivery = load_delivery_metrics()
    stores = load_store_performance()

    st.markdown(
        '<div class="page-title">'
        'Delivery & Operations'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Delivery partner and store-level operational performance'
        '</div>',
        unsafe_allow_html=True,
    )

    total_deliveries = delivery[
        "total_deliveries"
    ].sum()

    average_delivery = delivery[
        "average_delivery_minutes"
    ].mean()

    average_p95 = delivery[
        "p95_delivery_minutes"
    ].mean()

    cols = st.columns(3)

    with cols[0]:

        st.markdown(
            kpi_card(
                "Total Deliveries",
                f"{total_deliveries:,.0f}",
                "Total delivery volume",
            ),
            unsafe_allow_html=True,
        )

    with cols[1]:

        st.markdown(
            kpi_card(
                "Average Delivery",
                f"{average_delivery:.1f} min",
                "Average delivery time",
            ),
            unsafe_allow_html=True,
        )

    with cols[2]:

        st.markdown(
            kpi_card(
                "Average P95",
                f"{average_p95:.1f} min",
                "95th percentile delivery time",
            ),
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # DELIVERY PARTNER PERFORMANCE
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Delivery Partner Performance'
        '</div>',
        unsafe_allow_html=True,
    )

    # Show the slowest partners so the chart stays readable,
    # while comparing both average and tail (P95) delivery time.
    partner_view = (
        delivery
        .sort_values(
            "average_delivery_minutes",
            ascending=False,
        )
        .head(10)
        .sort_values(
            "average_delivery_minutes",
            ascending=True,
        )
    )

    fig = px.bar(
        partner_view,
        x=["average_delivery_minutes", "p95_delivery_minutes"],
        y="partner_id",
        orientation="h",
        barmode="group",
        title="Top 10 Slowest Delivery Partners",
        labels={
            "value": "Delivery Time (minutes)",
            "variable": "Metric",
            "partner_id": "Partner",
        },
        text_auto=".1f",
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        xaxis_title="Delivery Time (minutes)",
        yaxis_title="Partner",
        legend_title="Metric",
        height=500,
        margin=dict(l=20, r=80, t=60, b=40),
        hovermode="y unified",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    # --------------------------------------------------------
    # STORE OPERATIONS
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Store Operations'
        '</div>',
        unsafe_allow_html=True,
    )

    store_view = (
        stores[
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
        hide_index=True,
    )


# ============================================================
# BUSINESS ASSISTANT
# ============================================================

elif page == "🤖 Business Assistant":

    st.markdown(
        '<div class="page-title">'
        'Business Assistant'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-subtitle">'
        'Ask questions using business policies, Gold data and ML intelligence'
        '</div>',
        unsafe_allow_html=True,
    )

    question = st.text_input(
        "Ask a business question",
        placeholder=(
            "Which products currently need inventory attention?"
        ),
    )

    if question:

        with st.spinner(
            "Retrieving business information..."
        ):

            try:

                with st.spinner("Analyzing business data..."):

                    answer = generate_business_answer(
                        query=question,
                        top_k_documents=1,
                        top_k_products=10,
                    )

                st.success("Business Assistant generated an answer.")

                st.markdown(
                    '<div class="section-title">Business Answer</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(answer)

            except Exception as e:

                st.error(
                    "RAG retrieval failed."
                )

                st.exception(e)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    '<div class="footer">'
    'Quick-Commerce Business Intelligence Platform · '
    'Bronze → Silver → Gold → ML → RAG'
    '</div>',
    unsafe_allow_html=True,
)