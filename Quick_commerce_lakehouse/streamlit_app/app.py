import streamlit as st

from databricks.connect import DatabricksSession

from router import classify_question
from retriever import retrieve_documents
from data_queries import (
    get_top_products,
    get_store_performance,
    get_inventory_status,
    get_demand_predictions
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Quick-Commerce AI Platform",
    page_icon="🛒",
    layout="wide"
)


# ============================================================
# DATABRICKS CONNECTION
# ============================================================

spark = DatabricksSession.builder.getOrCreate()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🛒 Quick-Commerce")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Demand Prediction",
        "AI Business Assistant"
    ]
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.title("📊 Business Dashboard")

    daily_sales = spark.table("gold.daily_sales")
    customer_metrics = spark.table("gold.customer_metrics")

    total_revenue = (
        daily_sales
        .agg({"total_revenue": "sum"})
        .collect()[0][0]
    )

    total_orders = (
        daily_sales
        .agg({"total_orders": "sum"})
        .collect()[0][0]
    )

    total_customers = customer_metrics.count()

    total_items = (
        daily_sales
        .agg({"total_items_sold": "sum"})
        .collect()[0][0]
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Revenue",
        f"₹{total_revenue:,.0f}"
    )

    col2.metric(
        "Total Orders",
        f"{total_orders:,}"
    )

    col3.metric(
        "Customers",
        f"{total_customers:,}"
    )

    col4.metric(
        "Items Sold",
        f"{total_items:,}"
    )

    st.divider()

    st.subheader("Daily Revenue")

    revenue_data = (
        daily_sales
        .select(
            "sales_date",
            "total_revenue"
        )
        .orderBy("sales_date")
        .toPandas()
    )

    st.line_chart(
        revenue_data.set_index("sales_date")
    )

    st.subheader("Store Performance")

    store_data = (
        get_store_performance(spark)
        .toPandas()
    )

    st.dataframe(
        store_data,
        use_container_width=True
    )


# ============================================================
# DEMAND PREDICTION
# ============================================================

elif page == "Demand Prediction":

    st.title("📈 Demand Prediction")

    predictions = get_demand_predictions(spark)

    stores = [
        row["store_id"]
        for row in
        predictions
        .select("store_id")
        .distinct()
        .orderBy("store_id")
        .collect()
    ]

    if stores:

        selected_store = st.selectbox(
            "Select Store",
            stores
        )

        products = [
            row["product_id"]
            for row in
            predictions
            .filter(
                predictions.store_id == selected_store
            )
            .select("product_id")
            .distinct()
            .orderBy("product_id")
            .collect()
        ]

        if products:

            selected_product = st.selectbox(
                "Select Product",
                products
            )

            result = (
                predictions
                .filter(
                    (predictions.store_id == selected_store) &
                    (predictions.product_id == selected_product)
                )
                .orderBy("sales_date", ascending=False)
                .limit(1)
                .toPandas()
            )

            if not result.empty:

                row = result.iloc[0]

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Predicted Demand",
                    f"{row['predicted_demand']:.2f}"
                )

                col2.metric(
                    "Actual Demand",
                    f"{row['next_day_demand']:.0f}"
                )

                col3.metric(
                    "Prediction Error",
                    f"{row['prediction_error']:.2f}"
                )

                st.subheader("Prediction Record")

                st.dataframe(
                    result,
                    use_container_width=True
                )

            else:

                st.info(
                    "No prediction available."
                )


# ============================================================
# AI BUSINESS ASSISTANT
# ============================================================

elif page == "AI Business Assistant":

    st.title("🤖 AI Business Assistant")

    question = st.text_input(
        "Ask a business question",
        placeholder=(
            "Example: What is the cancellation policy?"
        )
    )

    if st.button("Ask Assistant"):

        if not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            route = classify_question(question)

            st.caption(
                f"Detected route: **{route}**"
            )

            # ------------------------------------------
            # DOCUMENT
            # ------------------------------------------

            if route == "DOCUMENT":

                results = retrieve_documents(
                    question,
                    top_k=2
                )

                if results:

                    result = results[0]

                    st.subheader(
                        result["title"]
                    )

                    st.write(
                        result["content"].strip()
                    )

                    st.caption(
                        f"Retrieval score: "
                        f"{result['score']:.4f}"
                    )

            # ------------------------------------------
            # DATA
            # ------------------------------------------

            elif route == "DATA":

                st.info(
                    "Analytics question detected."
                )

                st.subheader(
                    "Top Products by Revenue"
                )

                top_products = (
                    get_top_products(spark)
                    .toPandas()
                )

                st.dataframe(
                    top_products,
                    use_container_width=True
                )

            # ------------------------------------------
            # ML
            # ------------------------------------------

            elif route == "ML":

                st.info(
                    "Demand prediction question detected."
                )

                prediction_data = (
                    get_demand_predictions(spark)
                    .toPandas()
                )

                st.dataframe(
                    prediction_data,
                    use_container_width=True
                )

            # ------------------------------------------
            # UNKNOWN
            # ------------------------------------------

            else:

                st.warning(
                    "I couldn't determine the question type."
                )