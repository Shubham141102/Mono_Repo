def get_gold_tables(spark):

    return {
        "daily_sales": spark.table("gold.daily_sales"),
        "product_performance": spark.table(
            "gold.product_performance"
        ),
        "store_performance": spark.table(
            "gold.store_performance"
        ),
        "customer_metrics": spark.table(
            "gold.customer_metrics"
        ),
        "inventory_metrics": spark.table(
            "gold.inventory_metrics"
        ),
        "demand_predictions": spark.table(
            "gold.demand_predictions"
        )
    }


def get_top_products(spark, limit=10):

    return (
        spark.table("gold.product_performance")
        .select(
            "product_id",
            "product_name",
            "category",
            "units_sold",
            "total_revenue"
        )
        .orderBy(
            "total_revenue",
            ascending=False
        )
        .limit(limit)
    )


def get_store_performance(spark):

    return (
        spark.table("gold.store_performance")
        .select(
            "store_id",
            "store_name",
            "city",
            "total_orders",
            "total_revenue",
            "average_order_value"
        )
        .orderBy(
            "total_revenue",
            ascending=False
        )
    )


def get_inventory_status(spark):

    return (
        spark.table("gold.inventory_metrics")
        .select(
            "store_id",
            "product_id",
            "product_name",
            "stock_quantity",
            "reorder_level",
            "stock_status"
        )
    )


def get_demand_predictions(spark):

    return (
        spark.table("gold.demand_predictions")
        .orderBy("sales_date")
    )