from pyspark.sql.functions import col


def check_not_null(df, column_name):
    """
    Count NULL or empty-string values in a column.
    """
    return df.filter(
        col(column_name).isNull() |
        (col(column_name) == "")
    ).count()


def check_unique(df, column_name):
    """
    Count duplicate values for a column.
    Returns the number of duplicate records beyond the first occurrence.
    """
    duplicate_count = (
        df.groupBy(column_name)
        .count()
        .filter(col("count") > 1)
        .selectExpr("sum(count - 1) as duplicate_count")
        .collect()[0]["duplicate_count"]
    )

    return duplicate_count or 0


def check_range(df, column_name, minimum=None, maximum=None):
    """
    Count records outside the specified numeric range.
    """
    condition = None

    if minimum is not None:
        condition = col(column_name) < minimum

    if maximum is not None:
        max_condition = col(column_name) > maximum

        if condition is None:
            condition = max_condition
        else:
            condition = condition | max_condition

    if condition is None:
        return 0

    return df.filter(condition).count()


def check_allowed_values(df, column_name, allowed_values):
    """
    Count records whose value is not in the allowed-value list.
    """
    return df.filter(
        col(column_name).isNull() |
        (~col(column_name).isin(allowed_values))
    ).count()


def create_quality_report(
    dataset_name,
    total_records,
    invalid_records,
    duplicate_records=0,
    null_records=0
):
    """
    Create a reusable data-quality summary.
    """

    valid_records = total_records - invalid_records

    quality_percentage = (
        (valid_records / total_records) * 100
        if total_records > 0
        else 0
    )

    return {
        "dataset": dataset_name,
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "duplicate_records": duplicate_records,
        "null_records": null_records,
        "quality_percentage": round(quality_percentage, 2),
    }